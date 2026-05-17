#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "esp_err.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "button_reader.h"
#include "http_client.h"
#include "mic_reader.h"
#include "speaker_player.h"
#include "stream_client.h"
#include "voice_node_config.h"
#include "voice_state.h"
#include "wifi_manager.h"

static const char *TAG = "voice_node";
static const uint32_t VOICE_NODE_TASK_STACK_SIZE = 12288;
static const UBaseType_t VOICE_NODE_TASK_PRIORITY = 5;
static const int64_t VOICE_NODE_COMMAND_POLL_INTERVAL_MS = 1500;
static const int64_t VOICE_NODE_CONFIG_REFRESH_INTERVAL_MS = 10000;
static const int64_t VOICE_NODE_CONVERSATION_COOLDOWN_MS = 800;
static const int64_t VOICE_NODE_WAKE_IDLE_RETRY_MS = 2500;
static const int VOICE_NODE_RECORD_START_SETTLE_MS = 350;

static voice_node_state_t s_state = VOICE_NODE_STATE_BOOT;
static voice_node_server_config_t s_server_config;
static bool s_conversation_mode = false;
static bool s_wake_listen_mode = false;
static int64_t s_next_conversation_record_ms = 0;

static esp_err_t stream_reply_audio_chunk(const uint8_t *data, size_t data_size, void *user_data)
{
    return speaker_player_wav_stream_write((speaker_wav_stream_t *)user_data, data, data_size);
}

static void set_state(voice_node_state_t next_state)
{
    if (s_state == next_state) {
        return;
    }
    s_state = next_state;
    ESP_LOGI(TAG, "State -> %s", voice_node_state_to_string(s_state));
}

static esp_err_t init_nvs(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    return err;
}

static void log_runtime_config(void)
{
    ESP_LOGI(TAG, "Device id: %s", VOICE_NODE_DEVICE_ID);
    ESP_LOGI(TAG, "Firmware: %s", VOICE_NODE_FIRMWARE_VERSION);
    ESP_LOGI(TAG, "Server: %s", VOICE_NODE_SERVER_BASE_URL);
    ESP_LOGI(TAG, "Heartbeat interval: %d ms", VOICE_NODE_HEARTBEAT_INTERVAL_MS);
}

static esp_err_t play_reply_audio_download_fallback(const char *reply_audio_url, size_t *reply_audio_size)
{
    uint8_t *reply_audio = NULL;
    size_t downloaded_size = 0;
    esp_err_t err = voice_node_http_download_reply_audio(
        reply_audio_url,
        &reply_audio,
        &downloaded_size);
    if (err == ESP_OK && reply_audio != NULL && downloaded_size > 0) {
        ESP_LOGI(TAG, "Fallback reply audio ready: bytes=%u", (unsigned int)downloaded_size);
        err = speaker_player_play_wav(reply_audio, downloaded_size);
    }
    free(reply_audio);
    if (reply_audio_size != NULL) {
        *reply_audio_size = downloaded_size;
    }
    return err;
}

static esp_err_t play_reply_audio_streaming(const char *reply_audio_url)
{
    if (reply_audio_url == NULL || reply_audio_url[0] == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    size_t reply_audio_size = 0;
    speaker_wav_stream_t wav_stream;
    esp_err_t err = speaker_player_wav_stream_begin(&wav_stream);
    if (err == ESP_OK) {
        set_state(VOICE_NODE_STATE_PLAYING_REPLY);
        err = voice_node_http_stream_reply_audio(
            reply_audio_url,
            stream_reply_audio_chunk,
            &wav_stream,
            &reply_audio_size);
        esp_err_t end_err = speaker_player_wav_stream_end(&wav_stream);
        if (err == ESP_OK) {
            err = end_err;
        }
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Reply audio stream playback failed: %s", esp_err_to_name(err));
            (void)voice_node_http_report_playback_status(
                "stream_playback",
                false,
                esp_err_to_name(err),
                reply_audio_url,
                reply_audio_size);
            ESP_LOGI(TAG, "Trying fallback full-file playback");
            err = play_reply_audio_download_fallback(reply_audio_url, &reply_audio_size);
            if (err != ESP_OK) {
                ESP_LOGW(TAG, "Fallback reply audio playback failed: %s", esp_err_to_name(err));
                (void)voice_node_http_report_playback_status(
                    "fallback_playback",
                    false,
                    esp_err_to_name(err),
                    reply_audio_url,
                    reply_audio_size);
            } else {
                ESP_LOGI(TAG, "Fallback reply audio playback done");
                (void)voice_node_http_report_playback_status(
                    "fallback_playback",
                    true,
                    NULL,
                    reply_audio_url,
                    reply_audio_size);
            }
        } else {
            ESP_LOGI(TAG, "Reply audio stream playback done: bytes=%u", (unsigned int)reply_audio_size);
            (void)voice_node_http_report_playback_status(
                "stream_playback",
                true,
                NULL,
                reply_audio_url,
                reply_audio_size);
        }
    } else {
        ESP_LOGW(TAG, "Reply audio stream init failed: %s", esp_err_to_name(err));
        (void)voice_node_http_report_playback_status(
            "stream_playback",
            false,
            esp_err_to_name(err),
            reply_audio_url,
            reply_audio_size);
    }
    return err;
}

static bool record_and_upload_audio(
    const char *reason,
    bool conversation_turn,
    const char *upload_source,
    bool play_record_cues,
    bool *reply_audio_played)
{
    ESP_LOGI(TAG, "%s flow started", reason);
    if (reply_audio_played != NULL) {
        *reply_audio_played = false;
    }
    if (!VOICE_NODE_MIC_ENABLED) {
        ESP_LOGW(TAG, "%s needs microphone enabled", reason);
        return false;
    }
    if (!s_server_config.enabled) {
        ESP_LOGW(TAG, "Voice node disabled by server config, skip %s", reason);
        return false;
    }

    esp_err_t err = ESP_OK;
    if (play_record_cues) {
        set_state(VOICE_NODE_STATE_BEEPING);
        err = speaker_player_play_record_start_cue();
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Record start cue failed: %s", esp_err_to_name(err));
        }
        vTaskDelay(pdMS_TO_TICKS(VOICE_NODE_RECORD_START_SETTLE_MS));
    }

    set_state(VOICE_NODE_STATE_RECORDING_COMMAND);
    uint8_t *wav_data = NULL;
    size_t wav_size = 0;
    const mic_record_config_t record_config = {
        .record_seconds = s_server_config.record_seconds,
        .record_gain = s_server_config.mic_record_gain,
        .vad_enabled = s_server_config.vad_enabled,
        .vad_threshold = s_server_config.vad_threshold,
        .vad_min_record_ms = s_server_config.vad_min_record_ms,
        .vad_silence_stop_ms = s_server_config.vad_silence_stop_ms,
    };
    err = mic_reader_record_wav(
        &wav_data,
        &wav_size,
        &record_config);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "%s record failed: %s", reason, esp_err_to_name(err));
        set_state(VOICE_NODE_STATE_WAKE_LISTENING);
        return false;
    }
    ESP_LOGI(TAG, "Record done: wav_size=%u", (unsigned int)wav_size);
    if (play_record_cues) {
        err = speaker_player_play_record_end_cue();
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Record end cue failed: %s", esp_err_to_name(err));
        }
    }

    set_state(VOICE_NODE_STATE_UPLOADING_AUDIO);
    voice_node_upload_result_t upload_result = { 0 };
    err = voice_node_http_upload_audio(
        wav_data,
        wav_size,
        conversation_turn ? 1 : 0,
        upload_source,
        &upload_result);
    mic_reader_free_wav(wav_data);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "%s upload failed: %s", reason, esp_err_to_name(err));
        set_state(VOICE_NODE_STATE_WAKE_LISTENING);
        return false;
    }
    ESP_LOGI(
        TAG,
        "Upload done: reply_audio_url=%s keep_mic_open=%d",
        upload_result.reply_audio_url[0] != '\0' ? upload_result.reply_audio_url : "(empty)",
        upload_result.keep_mic_open);

    if (upload_result.reply_audio_url[0] != '\0') {
        if (reply_audio_played != NULL) {
            *reply_audio_played = true;
        }
        set_state(VOICE_NODE_STATE_WAITING_SERVER_REPLY);
        (void)play_reply_audio_streaming(upload_result.reply_audio_url);
    } else {
        ESP_LOGW(TAG, "Assistant response has no speaker audio yet");
    }

    set_state(VOICE_NODE_STATE_WAKE_LISTENING);
    return upload_result.keep_mic_open;
}

static void poll_remote_commands(void)
{
    if (!s_server_config.enabled) {
        return;
    }
    if (s_state != VOICE_NODE_STATE_WAKE_LISTENING) {
        return;
    }

    char command_type[32] = { 0 };
    char audio_url[192] = { 0 };
    esp_err_t err = voice_node_http_poll_command(
        command_type,
        sizeof(command_type),
        audio_url,
        sizeof(audio_url));
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Command poll failed: %s", esp_err_to_name(err));
        return;
    }
    if (command_type[0] == '\0') {
        return;
    }

    if (strcmp(command_type, "speaker_test") == 0) {
        ESP_LOGI(TAG, "Remote command: speaker diagnostic tone");
        err = speaker_player_play_diagnostic_tone();
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Remote speaker diagnostic failed: %s", esp_err_to_name(err));
        }
        return;
    }
    if (strcmp(command_type, "record_once") == 0) {
        ESP_LOGI(TAG, "Remote command: record one voice command");
        (void)record_and_upload_audio(
            "Remote UI audio upload test",
            false,
            "voice_node",
            true,
            NULL);
        return;
    }
    if (strcmp(command_type, "conversation_start") == 0) {
        ESP_LOGI(TAG, "Remote command: start continuous conversation");
        s_conversation_mode = true;
        s_wake_listen_mode = false;
        s_next_conversation_record_ms = esp_timer_get_time() / 1000;
        return;
    }
    if (strcmp(command_type, "conversation_stop") == 0) {
        ESP_LOGI(TAG, "Remote command: stop continuous conversation");
        s_conversation_mode = false;
        return;
    }
    if (strcmp(command_type, "wake_listen_start") == 0) {
        ESP_LOGI(TAG, "Remote command: start wake listening loop");
        s_wake_listen_mode = true;
        s_conversation_mode = false;
        s_next_conversation_record_ms = esp_timer_get_time() / 1000;
        return;
    }
    if (strcmp(command_type, "wake_listen_stop") == 0) {
        ESP_LOGI(TAG, "Remote command: stop wake listening loop");
        s_wake_listen_mode = false;
        s_conversation_mode = false;
        return;
    }
    if (strcmp(command_type, "stream_test_start") == 0 || strcmp(command_type, "stream_process_start") == 0) {
        const bool process_on_server = strcmp(command_type, "stream_process_start") == 0;
        ESP_LOGI(
            TAG,
            "Remote command: start PCM stream process=%d",
            process_on_server);
        if (process_on_server) {
            (void)speaker_player_play_record_start_cue();
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
        const voice_node_state_t previous_state = s_state;
        set_state(VOICE_NODE_STATE_RECORDING_COMMAND);
        err = voice_node_stream_pcm_diagnostics(
            process_on_server ? 7 : 5,
            s_server_config.mic_record_gain,
            process_on_server);
        if (process_on_server) {
            (void)speaker_player_play_record_end_cue();
        }
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "PCM stream failed: %s", esp_err_to_name(err));
        }
        set_state(previous_state == VOICE_NODE_STATE_RECORDING_COMMAND
            ? VOICE_NODE_STATE_WAKE_LISTENING
            : previous_state);
        return;
    }
    if (strcmp(command_type, "play_audio") == 0) {
        ESP_LOGI(TAG, "Remote command: play audio URL");
        if (audio_url[0] == '\0') {
            ESP_LOGW(TAG, "play_audio command missing audio_url");
            return;
        }
        set_state(VOICE_NODE_STATE_WAITING_SERVER_REPLY);
        err = play_reply_audio_streaming(audio_url);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Remote play audio failed: %s", esp_err_to_name(err));
        }
        set_state(VOICE_NODE_STATE_WAKE_LISTENING);
        return;
    }

    ESP_LOGW(TAG, "Unknown remote command: %s", command_type);
}

static void voice_node_main_loop(void)
{
    int64_t last_heartbeat_ms = -VOICE_NODE_HEARTBEAT_INTERVAL_MS;
    int64_t last_mic_log_ms = -CONFIG_VOICE_NODE_MIC_LOG_INTERVAL_MS;
    int64_t last_command_poll_ms = -VOICE_NODE_COMMAND_POLL_INTERVAL_MS;
    int64_t last_config_refresh_ms = -VOICE_NODE_CONFIG_REFRESH_INTERVAL_MS;

    while (true) {
        const int64_t now_ms = esp_timer_get_time() / 1000;

        if (now_ms - last_heartbeat_ms >= VOICE_NODE_HEARTBEAT_INTERVAL_MS) {
            last_heartbeat_ms = now_ms;
            esp_err_t err = voice_node_http_send_heartbeat(s_state);
            if (err != ESP_OK) {
                ESP_LOGW(TAG, "Heartbeat failed, keeping local state alive");
            }

            if (!s_server_config.enabled) {
                ESP_LOGW(TAG, "Voice node disabled by server config");
            } else {
                ESP_LOGI(
                    TAG,
                    "Ready: wake=%s record=%ds sample_rate=%d gain=%d vad=%d threshold=%d",
                    s_server_config.wake_word,
                    s_server_config.record_seconds,
                    s_server_config.sample_rate,
                    s_server_config.mic_record_gain,
                    s_server_config.vad_enabled,
                    s_server_config.vad_threshold);
            }
        }

        if (
            s_state == VOICE_NODE_STATE_WAKE_LISTENING &&
            now_ms - last_config_refresh_ms >= VOICE_NODE_CONFIG_REFRESH_INTERVAL_MS
        ) {
            last_config_refresh_ms = now_ms;
            voice_node_server_config_t next_config = s_server_config;
            esp_err_t err = voice_node_http_get_config(&next_config);
            if (err == ESP_OK) {
                s_server_config = next_config;
            } else {
                ESP_LOGW(TAG, "Config refresh failed, keeping previous config");
            }
        }

        if (VOICE_NODE_MIC_ENABLED && now_ms - last_mic_log_ms >= CONFIG_VOICE_NODE_MIC_LOG_INTERVAL_MS) {
            last_mic_log_ms = now_ms;
            mic_level_stats_t stats = { 0 };
            esp_err_t err = mic_reader_read_level(&stats);
            if (err == ESP_OK && stats.enabled) {
                ESP_LOGI(
                    TAG,
                    "Mic level: samples=%d avg_abs=%.1f rms=%.1f peak=%d",
                    stats.sample_count,
                    stats.average_abs,
                    stats.rms,
                    stats.peak);
            } else if (err != ESP_OK) {
                ESP_LOGW(TAG, "Mic read failed: %s", esp_err_to_name(err));
            }
        }

        if (now_ms - last_command_poll_ms >= VOICE_NODE_COMMAND_POLL_INTERVAL_MS) {
            last_command_poll_ms = now_ms;
            poll_remote_commands();
        }

        if (
            s_conversation_mode &&
            s_state == VOICE_NODE_STATE_WAKE_LISTENING &&
            now_ms >= s_next_conversation_record_ms
        ) {
            bool reply_audio_played = false;
            bool keep_mic_open = record_and_upload_audio(
                "Continuous conversation",
                true,
                "voice_node",
                true,
                &reply_audio_played);
            if (keep_mic_open) {
                s_next_conversation_record_ms =
                    (esp_timer_get_time() / 1000) + VOICE_NODE_CONVERSATION_COOLDOWN_MS;
            } else {
                ESP_LOGI(TAG, "Continuous conversation stopped by assistant response");
                s_conversation_mode = false;
            }
            last_heartbeat_ms = -VOICE_NODE_HEARTBEAT_INTERVAL_MS;
            last_command_poll_ms = -VOICE_NODE_COMMAND_POLL_INTERVAL_MS;
            last_mic_log_ms = esp_timer_get_time() / 1000;
        }

        if (
            s_wake_listen_mode &&
            s_state == VOICE_NODE_STATE_WAKE_LISTENING &&
            now_ms >= s_next_conversation_record_ms
        ) {
            bool reply_audio_played = false;
            bool keep_listening = record_and_upload_audio(
                "Server wake listening",
                false,
                "voice_node_wake",
                false,
                &reply_audio_played);
            if (keep_listening) {
                const int64_t cooldown_ms = reply_audio_played
                    ? VOICE_NODE_CONVERSATION_COOLDOWN_MS
                    : VOICE_NODE_WAKE_IDLE_RETRY_MS;
                s_next_conversation_record_ms =
                    (esp_timer_get_time() / 1000) + cooldown_ms;
            } else {
                ESP_LOGI(TAG, "Wake listening loop stopped by assistant response");
                s_wake_listen_mode = false;
            }
            last_heartbeat_ms = -VOICE_NODE_HEARTBEAT_INTERVAL_MS;
            last_command_poll_ms = -VOICE_NODE_COMMAND_POLL_INTERVAL_MS;
            last_mic_log_ms = esp_timer_get_time() / 1000;
        }

        button_event_t button_event = button_reader_poll();
        if (button_event == BUTTON_EVENT_LONG_PRESS) {
            ESP_LOGI(TAG, "Button long press: play speaker diagnostic tone only");
            esp_err_t err = speaker_player_play_diagnostic_tone();
            if (err != ESP_OK) {
                ESP_LOGW(TAG, "Speaker diagnostic tone failed: %s", esp_err_to_name(err));
            }
            last_heartbeat_ms = -VOICE_NODE_HEARTBEAT_INTERVAL_MS;
            last_mic_log_ms = esp_timer_get_time() / 1000;
        } else if (button_event == BUTTON_EVENT_SHORT_PRESS) {
            ESP_LOGI(TAG, "Button short press: record and upload one voice command");
            (void)record_and_upload_audio(
                "Button audio upload test",
                false,
                "voice_node",
                true,
                NULL);
            last_heartbeat_ms = -VOICE_NODE_HEARTBEAT_INTERVAL_MS;
            last_mic_log_ms = esp_timer_get_time() / 1000;
        }

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

static void run_audio_upload_test_once(void)
{
    if (!VOICE_NODE_AUDIO_UPLOAD_TEST_ENABLED) {
        return;
    }
    if (!VOICE_NODE_MIC_ENABLED) {
        ESP_LOGW(TAG, "Audio upload test needs microphone enabled");
        return;
    }

    if (CONFIG_VOICE_NODE_AUDIO_UPLOAD_TEST_DELAY_MS > 0) {
        ESP_LOGI(TAG, "Audio upload test starts in %d ms", CONFIG_VOICE_NODE_AUDIO_UPLOAD_TEST_DELAY_MS);
        vTaskDelay(pdMS_TO_TICKS(CONFIG_VOICE_NODE_AUDIO_UPLOAD_TEST_DELAY_MS));
    }

    (void)record_and_upload_audio(
        "Boot audio upload test",
        false,
        "voice_node",
        true,
        NULL);
}

static void voice_node_task(void *params)
{
    (void)params;

    log_runtime_config();
    set_state(VOICE_NODE_STATE_BOOT);

    ESP_ERROR_CHECK(init_nvs());

    set_state(VOICE_NODE_STATE_WIFI_CONNECTING);
    esp_err_t err = wifi_manager_connect();
    if (err != ESP_OK) {
        set_state(VOICE_NODE_STATE_ERROR);
        ESP_LOGE(TAG, "Wi-Fi setup failed. Check menuconfig and router.");
        return;
    }

    set_state(VOICE_NODE_STATE_REGISTERING);
    s_server_config = voice_node_default_server_config();
    err = voice_node_http_get_config(&s_server_config);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Could not fetch server config. Using safe defaults.");
    }

    err = mic_reader_init();
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Microphone init failed. Continuing heartbeat-only mode.");
    }

    err = button_reader_init();
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Button trigger init failed. Continuing without button upload test.");
    }

    err = speaker_player_init();
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Speaker init failed. Continuing without speaker output.");
    } else if (VOICE_NODE_SPEAKER_SELF_TEST_ON_BOOT) {
        err = speaker_player_play_self_test();
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Speaker self-test failed: %s", esp_err_to_name(err));
        }
    }

    set_state(VOICE_NODE_STATE_WAKE_LISTENING);
    run_audio_upload_test_once();
    voice_node_main_loop();
}

void app_main(void)
{
    BaseType_t created = xTaskCreate(
        voice_node_task,
        "voice_node",
        VOICE_NODE_TASK_STACK_SIZE,
        NULL,
        VOICE_NODE_TASK_PRIORITY,
        NULL);

    if (created != pdPASS) {
        ESP_LOGE(TAG, "Failed to create voice node task");
    }
}
