#include "stream_client.h"

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "esp_check.h"
#include "esp_log.h"
#include "esp_websocket_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "mic_reader.h"
#include "voice_node_config.h"

#define STREAM_CONNECT_TIMEOUT_MS 3000
#define STREAM_SEND_TIMEOUT_TICKS pdMS_TO_TICKS(2000)

static const char *TAG = "voice_stream";

typedef struct {
    esp_websocket_client_handle_t client;
} stream_context_t;

static void build_stream_url(char *output, size_t output_size, bool process_on_server)
{
    const char *base_url = VOICE_NODE_SERVER_BASE_URL;
    const char *scheme = "ws://";
    size_t offset = 0;

    if (strncmp(base_url, "http://", 7) == 0) {
        base_url += 7;
    } else if (strncmp(base_url, "https://", 8) == 0) {
        scheme = "wss://";
        base_url += 8;
    }

    offset = (size_t)snprintf(output, output_size, "%s%s", scheme, base_url);
    if (offset > 0 && offset < output_size && output[offset - 1] == '/') {
        output[offset - 1] = '\0';
    }

    (void)snprintf(
        output + strlen(output),
        output_size - strlen(output),
        "/voice-node/audio/stream?device_id=%s&sample_rate=%d&channels=1&bits_per_sample=16&process=%s&pir_state=1",
        VOICE_NODE_DEVICE_ID,
        CONFIG_VOICE_NODE_MIC_SAMPLE_RATE,
        process_on_server ? "true" : "false");
}

static esp_err_t send_pcm_chunk(const uint8_t *data, size_t data_size, void *user_data)
{
    stream_context_t *context = (stream_context_t *)user_data;
    if (context == NULL || context->client == NULL || data == NULL || data_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    if (!esp_websocket_client_is_connected(context->client)) {
        return ESP_ERR_INVALID_STATE;
    }

    const int written = esp_websocket_client_send_bin(
        context->client,
        (const char *)data,
        (int)data_size,
        STREAM_SEND_TIMEOUT_TICKS);
    if (written < 0 || (size_t)written != data_size) {
        ESP_LOGW(TAG, "WebSocket send failed: written=%d size=%u", written, (unsigned int)data_size);
        return ESP_FAIL;
    }
    return ESP_OK;
}

esp_err_t voice_node_stream_pcm_diagnostics(
    int stream_seconds,
    int record_gain,
    bool process_on_server)
{
    char url[256] = { 0 };
    build_stream_url(url, sizeof(url), process_on_server);
    ESP_LOGI(TAG, "Opening PCM diagnostic stream: %s", url);

    esp_websocket_client_config_t config = {
        .uri = url,
        .network_timeout_ms = 5000,
    };
    esp_websocket_client_handle_t client = esp_websocket_client_init(&config);
    if (client == NULL) {
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = esp_websocket_client_start(client);
    if (err != ESP_OK) {
        esp_websocket_client_destroy(client);
        return err;
    }

    const int max_wait_loops = STREAM_CONNECT_TIMEOUT_MS / 100;
    bool connected = false;
    for (int index = 0; index < max_wait_loops; index++) {
        if (esp_websocket_client_is_connected(client)) {
            connected = true;
            break;
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    if (!connected) {
        ESP_LOGW(TAG, "WebSocket stream connect timeout");
        esp_websocket_client_close(client, pdMS_TO_TICKS(500));
        esp_websocket_client_destroy(client);
        return ESP_ERR_TIMEOUT;
    }

    stream_context_t context = {
        .client = client,
    };
    err = mic_reader_stream_pcm_seconds(
        stream_seconds,
        record_gain,
        send_pcm_chunk,
        &context);

    esp_websocket_client_close(client, pdMS_TO_TICKS(500));
    esp_websocket_client_destroy(client);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "PCM diagnostic stream finished");
    } else {
        ESP_LOGW(TAG, "PCM diagnostic stream failed: %s", esp_err_to_name(err));
    }
    return err;
}
