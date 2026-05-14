#include "http_client.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "cJSON.h"
#include "esp_check.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "wifi_manager.h"

#define HTTP_RESPONSE_BUFFER_SIZE 2048
#define HTTP_URL_BUFFER_SIZE 256
#define HTTP_MULTIPART_BOUNDARY "----ai-smart-home-voice-node"
#define HTTP_AUDIO_UPLOAD_TIMEOUT_MS 45000
#define HTTP_REPLY_AUDIO_TIMEOUT_MS 30000
#define HTTP_REPLY_AUDIO_DOWNLOAD_MAX_BYTES (512 * 1024)
#define HTTP_REPLY_AUDIO_STREAM_MAX_BYTES (2 * 1024 * 1024)
#define HTTP_REPLY_AUDIO_STREAM_BUFFER_SIZE 2048

typedef struct {
    char data[HTTP_RESPONSE_BUFFER_SIZE];
    int length;
} http_response_buffer_t;

static const char *TAG = "voice_http";

static esp_err_t http_event_handler(esp_http_client_event_t *event)
{
    if (event->event_id != HTTP_EVENT_ON_DATA || event->data == NULL) {
        return ESP_OK;
    }

    http_response_buffer_t *buffer = (http_response_buffer_t *)event->user_data;
    if (buffer == NULL) {
        return ESP_OK;
    }

    int copy_len = event->data_len;
    int available = HTTP_RESPONSE_BUFFER_SIZE - buffer->length - 1;
    if (copy_len > available) {
        copy_len = available;
    }
    if (copy_len <= 0) {
        return ESP_OK;
    }

    memcpy(buffer->data + buffer->length, event->data, copy_len);
    buffer->length += copy_len;
    buffer->data[buffer->length] = '\0';
    return ESP_OK;
}

static void build_url(char *output, size_t output_size, const char *path)
{
    const char *base_url = VOICE_NODE_SERVER_BASE_URL;
    const size_t base_len = strlen(base_url);
    const bool has_trailing_slash = base_len > 0 && base_url[base_len - 1] == '/';
    const bool path_has_slash = path[0] == '/';

    if (has_trailing_slash && path_has_slash) {
        snprintf(output, output_size, "%.*s%s", (int)(base_len - 1), base_url, path);
    } else if (!has_trailing_slash && !path_has_slash) {
        snprintf(output, output_size, "%s/%s", base_url, path);
    } else {
        snprintf(output, output_size, "%s%s", base_url, path);
    }
}

static esp_err_t run_json_request(
    const char *url,
    esp_http_client_method_t method,
    const char *body,
    http_response_buffer_t *response)
{
    esp_http_client_config_t config = {
        .url = url,
        .method = method,
        .timeout_ms = 10000,
        .event_handler = http_event_handler,
        .user_data = response,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_http_client_set_header(client, "Content-Type", "application/json");
    if (body != NULL) {
        esp_http_client_set_post_field(client, body, strlen(body));
    }

    esp_err_t err = esp_http_client_perform(client);
    const int status_code = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);

    if (err != ESP_OK) {
        ESP_LOGW(TAG, "HTTP request failed: %s", esp_err_to_name(err));
        return err;
    }
    if (status_code < 200 || status_code >= 300) {
        ESP_LOGW(TAG, "HTTP status not ok: %d", status_code);
        return ESP_FAIL;
    }
    return ESP_OK;
}

static void parse_string_field(
    const cJSON *root,
    const char *field_name,
    char *output,
    size_t output_size)
{
    const cJSON *item = cJSON_GetObjectItemCaseSensitive(root, field_name);
    if (cJSON_IsString(item) && item->valuestring != NULL) {
        strlcpy(output, item->valuestring, output_size);
    }
}

static void parse_nested_string_field(
    const cJSON *root,
    const char *object_name,
    const char *field_name,
    char *output,
    size_t output_size)
{
    const cJSON *object = cJSON_GetObjectItemCaseSensitive(root, object_name);
    if (!cJSON_IsObject(object)) {
        return;
    }
    parse_string_field(object, field_name, output, output_size);
}

static esp_err_t http_write_all(esp_http_client_handle_t client, const void *data, size_t data_size)
{
    const char *cursor = (const char *)data;
    size_t remaining = data_size;

    while (remaining > 0) {
        const int written = esp_http_client_write(client, cursor, remaining);
        if (written < 0) {
            return ESP_FAIL;
        }
        if (written == 0) {
            return ESP_ERR_TIMEOUT;
        }
        cursor += written;
        remaining -= written;
    }
    return ESP_OK;
}

static void read_response_body(esp_http_client_handle_t client, http_response_buffer_t *response)
{
    if (response == NULL) {
        return;
    }

    while (response->length < HTTP_RESPONSE_BUFFER_SIZE - 1) {
        const int available = HTTP_RESPONSE_BUFFER_SIZE - response->length - 1;
        const int read_len = esp_http_client_read(client, response->data + response->length, available);
        if (read_len <= 0) {
            break;
        }
        response->length += read_len;
        response->data[response->length] = '\0';
    }
}

esp_err_t voice_node_http_get_config(voice_node_server_config_t *config)
{
    if (config == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    *config = voice_node_default_server_config();

    char url[HTTP_URL_BUFFER_SIZE];
    build_url(url, sizeof(url), "/voice-node/config?device_id=" VOICE_NODE_DEVICE_ID);

    http_response_buffer_t *response = calloc(1, sizeof(http_response_buffer_t));
    if (response == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = run_json_request(url, HTTP_METHOD_GET, NULL, response);
    if (err != ESP_OK) {
        free(response);
        return err;
    }

    cJSON *root = cJSON_Parse(response->data);
    if (root == NULL) {
        ESP_LOGW(TAG, "Failed to parse config JSON");
        free(response);
        return ESP_FAIL;
    }

    const cJSON *enabled = cJSON_GetObjectItemCaseSensitive(root, "enabled");
    const cJSON *record_seconds = cJSON_GetObjectItemCaseSensitive(root, "record_seconds");
    const cJSON *sample_rate = cJSON_GetObjectItemCaseSensitive(root, "sample_rate");

    if (cJSON_IsBool(enabled)) {
        config->enabled = cJSON_IsTrue(enabled);
    }
    if (cJSON_IsNumber(record_seconds)) {
        config->record_seconds = record_seconds->valueint;
    }
    if (cJSON_IsNumber(sample_rate)) {
        config->sample_rate = sample_rate->valueint;
    }

    parse_string_field(root, "wake_word", config->wake_word, sizeof(config->wake_word));
    parse_string_field(root, "audio_format", config->audio_format, sizeof(config->audio_format));
    parse_string_field(
        root,
        "reply_audio_format",
        config->reply_audio_format,
        sizeof(config->reply_audio_format));

    cJSON_Delete(root);
    free(response);
    ESP_LOGI(
        TAG,
        "Config: enabled=%d wake_word=%s record_seconds=%d sample_rate=%d audio=%s reply=%s",
        config->enabled,
        config->wake_word,
        config->record_seconds,
        config->sample_rate,
        config->audio_format,
        config->reply_audio_format);
    return ESP_OK;
}

esp_err_t voice_node_http_send_heartbeat(voice_node_state_t state)
{
    char url[HTTP_URL_BUFFER_SIZE];
    build_url(url, sizeof(url), "/voice-node/heartbeat");

    char body[384];
    snprintf(
        body,
        sizeof(body),
        "{\"device_id\":\"%s\",\"firmware_version\":\"%s\",\"state\":\"%s\",\"ip_address\":\"%s\"}",
        VOICE_NODE_DEVICE_ID,
        VOICE_NODE_FIRMWARE_VERSION,
        voice_node_state_to_string(state),
        wifi_manager_get_ip_address());

    esp_err_t err = run_json_request(url, HTTP_METHOD_POST, body, NULL);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Heartbeat ok: %s", voice_node_state_to_string(state));
    }
    return err;
}

esp_err_t voice_node_http_poll_command(
    char *command_type,
    size_t command_type_size,
    char *audio_url,
    size_t audio_url_size)
{
    if (command_type == NULL || command_type_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    command_type[0] = '\0';
    if (audio_url != NULL && audio_url_size > 0) {
        audio_url[0] = '\0';
    }

    char url[HTTP_URL_BUFFER_SIZE];
    build_url(url, sizeof(url), "/voice-node/commands?device_id=" VOICE_NODE_DEVICE_ID);

    http_response_buffer_t *response = calloc(1, sizeof(http_response_buffer_t));
    if (response == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = run_json_request(url, HTTP_METHOD_GET, NULL, response);
    if (err != ESP_OK) {
        free(response);
        return err;
    }

    cJSON *root = cJSON_Parse(response->data);
    if (root == NULL) {
        ESP_LOGW(TAG, "Failed to parse command JSON");
        free(response);
        return ESP_FAIL;
    }

    const cJSON *command = cJSON_GetObjectItemCaseSensitive(root, "command");
    if (cJSON_IsObject(command)) {
        parse_string_field(command, "type", command_type, command_type_size);
        if (audio_url != NULL && audio_url_size > 0) {
            parse_string_field(command, "audio_url", audio_url, audio_url_size);
        }
        if (command_type[0] != '\0') {
            ESP_LOGI(TAG, "Command received: %s", command_type);
        }
    }

    cJSON_Delete(root);
    free(response);
    return ESP_OK;
}

esp_err_t voice_node_http_upload_audio(
    const uint8_t *wav_data,
    size_t wav_size,
    char *reply_audio_url,
    size_t reply_audio_url_size)
{
    if (wav_data == NULL || wav_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    if (reply_audio_url != NULL && reply_audio_url_size > 0) {
        reply_audio_url[0] = '\0';
    }

    char url[HTTP_URL_BUFFER_SIZE];
    build_url(url, sizeof(url), "/assistant/audio");

    char prefix[512];
    snprintf(
        prefix,
        sizeof(prefix),
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n"
        "%s\r\n"
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"pir_state\"\r\n\r\n"
        "0\r\n"
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"source\"\r\n\r\n"
        "voice_node\r\n"
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"audio\"; filename=\"command.wav\"\r\n"
        "Content-Type: audio/wav\r\n\r\n",
        HTTP_MULTIPART_BOUNDARY,
        VOICE_NODE_DEVICE_ID,
        HTTP_MULTIPART_BOUNDARY,
        HTTP_MULTIPART_BOUNDARY,
        HTTP_MULTIPART_BOUNDARY);

    char suffix[96];
    snprintf(suffix, sizeof(suffix), "\r\n--%s--\r\n", HTTP_MULTIPART_BOUNDARY);

    const size_t prefix_len = strlen(prefix);
    const size_t suffix_len = strlen(suffix);
    const size_t body_size = prefix_len + wav_size + suffix_len;

    http_response_buffer_t *response = calloc(1, sizeof(http_response_buffer_t));
    if (response == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .timeout_ms = HTTP_AUDIO_UPLOAD_TIMEOUT_MS,
        .event_handler = http_event_handler,
        .user_data = response,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == NULL) {
        free(response);
        return ESP_ERR_NO_MEM;
    }

    char content_type[96];
    snprintf(
        content_type,
        sizeof(content_type),
        "multipart/form-data; boundary=%s",
        HTTP_MULTIPART_BOUNDARY);
    esp_http_client_set_header(client, "Content-Type", content_type);

    ESP_LOGI(TAG, "Uploading audio: wav=%u multipart=%u", (unsigned int)wav_size, (unsigned int)body_size);
    esp_err_t err = esp_http_client_open(client, (int)body_size);
    if (err == ESP_OK) {
        err = http_write_all(client, prefix, prefix_len);
    }
    if (err == ESP_OK) {
        err = http_write_all(client, wav_data, wav_size);
    }
    if (err == ESP_OK) {
        err = http_write_all(client, suffix, suffix_len);
    }
    if (err == ESP_OK) {
        (void)esp_http_client_fetch_headers(client);
        read_response_body(client, response);
    }
    const int status_code = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);

    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Audio upload failed: %s", esp_err_to_name(err));
        free(response);
        return err;
    }
    if (status_code < 200 || status_code >= 300) {
        ESP_LOGW(TAG, "Audio upload HTTP status not ok: %d body=%s", status_code, response->data);
        free(response);
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Audio upload ok: %s", response->data);
    if (reply_audio_url != NULL && reply_audio_url_size > 0) {
        cJSON *root = cJSON_Parse(response->data);
        if (root != NULL) {
            parse_nested_string_field(root, "data", "reply_audio_url", reply_audio_url, reply_audio_url_size);
            cJSON_Delete(root);
        }
        if (reply_audio_url[0] != '\0') {
            ESP_LOGI(TAG, "Reply audio URL: %s", reply_audio_url);
        } else {
            ESP_LOGW(TAG, "No reply audio URL in assistant response");
        }
    }
    free(response);
    return ESP_OK;
}

esp_err_t voice_node_http_download_reply_audio(
    const char *reply_audio_url,
    uint8_t **audio_data,
    size_t *audio_size)
{
    if (reply_audio_url == NULL || reply_audio_url[0] == '\0' || audio_data == NULL || audio_size == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    *audio_data = NULL;
    *audio_size = 0;

    char url[HTTP_URL_BUFFER_SIZE];
    if (strncmp(reply_audio_url, "http://", 7) == 0 || strncmp(reply_audio_url, "https://", 8) == 0) {
        strlcpy(url, reply_audio_url, sizeof(url));
    } else {
        build_url(url, sizeof(url), reply_audio_url);
    }

    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_GET,
        .timeout_ms = HTTP_REPLY_AUDIO_TIMEOUT_MS,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == NULL) {
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "Downloading reply audio: %s", url);
    esp_err_t err = esp_http_client_open(client, 0);
    int status_code = 0;
    if (err == ESP_OK) {
        const int64_t content_length = esp_http_client_fetch_headers(client);
        status_code = esp_http_client_get_status_code(client);
        if (status_code < 200 || status_code >= 300) {
            ESP_LOGW(TAG, "Reply audio HTTP status not ok: %d", status_code);
            err = ESP_FAIL;
        } else if (content_length <= 0 || content_length > HTTP_REPLY_AUDIO_DOWNLOAD_MAX_BYTES) {
            ESP_LOGW(TAG, "Reply audio size invalid: %lld", content_length);
            err = ESP_ERR_INVALID_SIZE;
        } else {
            uint8_t *buffer = malloc((size_t)content_length);
            if (buffer == NULL) {
                err = ESP_ERR_NO_MEM;
            } else {
                size_t total_read = 0;
                while (total_read < (size_t)content_length) {
                    const int read_len = esp_http_client_read(
                        client,
                        (char *)buffer + total_read,
                        (int)((size_t)content_length - total_read));
                    if (read_len < 0) {
                        err = ESP_FAIL;
                        break;
                    }
                    if (read_len == 0) {
                        break;
                    }
                    total_read += (size_t)read_len;
                }

                if (err == ESP_OK && total_read > 0) {
                    *audio_data = buffer;
                    *audio_size = total_read;
                    ESP_LOGI(TAG, "Reply audio downloaded: %u bytes", (unsigned int)total_read);
                } else {
                    free(buffer);
                    if (err == ESP_OK) {
                        err = ESP_ERR_TIMEOUT;
                    }
                }
            }
        }
    }

    esp_http_client_close(client);
    esp_http_client_cleanup(client);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Reply audio download failed: %s", esp_err_to_name(err));
    }
    return err;
}

esp_err_t voice_node_http_stream_reply_audio(
    const char *reply_audio_url,
    voice_node_audio_chunk_handler_t chunk_handler,
    void *user_data,
    size_t *audio_size)
{
    if (reply_audio_url == NULL || reply_audio_url[0] == '\0' || chunk_handler == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (audio_size != NULL) {
        *audio_size = 0;
    }

    char url[HTTP_URL_BUFFER_SIZE];
    if (strncmp(reply_audio_url, "http://", 7) == 0 || strncmp(reply_audio_url, "https://", 8) == 0) {
        strlcpy(url, reply_audio_url, sizeof(url));
    } else {
        build_url(url, sizeof(url), reply_audio_url);
    }

    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_GET,
        .timeout_ms = HTTP_REPLY_AUDIO_TIMEOUT_MS,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == NULL) {
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "Streaming reply audio: %s", url);
    esp_err_t err = esp_http_client_open(client, 0);
    int status_code = 0;
    uint8_t *buffer = NULL;
    size_t total_read = 0;

    if (err == ESP_OK) {
        const int64_t content_length = esp_http_client_fetch_headers(client);
        status_code = esp_http_client_get_status_code(client);
        if (status_code < 200 || status_code >= 300) {
            ESP_LOGW(TAG, "Reply audio stream HTTP status not ok: %d", status_code);
            err = ESP_FAIL;
        } else if (content_length <= 0 || content_length > HTTP_REPLY_AUDIO_STREAM_MAX_BYTES) {
            ESP_LOGW(TAG, "Reply audio stream size invalid: %lld", content_length);
            err = ESP_ERR_INVALID_SIZE;
        } else {
            buffer = malloc(HTTP_REPLY_AUDIO_STREAM_BUFFER_SIZE);
            if (buffer == NULL) {
                err = ESP_ERR_NO_MEM;
            }
        }
    }

    while (err == ESP_OK && buffer != NULL) {
        const int read_len = esp_http_client_read(
            client,
            (char *)buffer,
            HTTP_REPLY_AUDIO_STREAM_BUFFER_SIZE);
        if (read_len < 0) {
            err = ESP_FAIL;
            break;
        }
        if (read_len == 0) {
            break;
        }

        err = chunk_handler(buffer, (size_t)read_len, user_data);
        if (err != ESP_OK) {
            break;
        }
        total_read += (size_t)read_len;
    }

    free(buffer);
    esp_http_client_close(client);
    esp_http_client_cleanup(client);

    if (audio_size != NULL) {
        *audio_size = total_read;
    }
    if (err == ESP_OK && total_read == 0) {
        err = ESP_ERR_TIMEOUT;
    }
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Reply audio stream failed: %s", esp_err_to_name(err));
    } else {
        ESP_LOGI(TAG, "Reply audio streamed: %u bytes", (unsigned int)total_read);
    }
    return err;
}

esp_err_t voice_node_http_report_playback_status(
    const char *stage,
    bool ok,
    const char *error,
    const char *audio_url,
    size_t audio_size)
{
    if (stage == NULL || stage[0] == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    char url[HTTP_URL_BUFFER_SIZE];
    build_url(url, sizeof(url), "/voice-node/playback-status");

    cJSON *root = cJSON_CreateObject();
    if (root == NULL) {
        return ESP_ERR_NO_MEM;
    }

    cJSON_AddStringToObject(root, "device_id", VOICE_NODE_DEVICE_ID);
    cJSON_AddStringToObject(root, "stage", stage);
    cJSON_AddBoolToObject(root, "ok", ok);
    if (error != NULL && error[0] != '\0') {
        cJSON_AddStringToObject(root, "error", error);
    }
    if (audio_url != NULL && audio_url[0] != '\0') {
        cJSON_AddStringToObject(root, "audio_url", audio_url);
    }
    cJSON_AddNumberToObject(root, "audio_size_bytes", (double)audio_size);

    char *body = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (body == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = run_json_request(url, HTTP_METHOD_POST, body, NULL);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Playback status report failed: %s", esp_err_to_name(err));
    }
    free(body);
    return err;
}
