#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#include "voice_node_config.h"
#include "voice_state.h"

typedef esp_err_t (*voice_node_audio_chunk_handler_t)(
    const uint8_t *data,
    size_t data_size,
    void *user_data);

typedef struct {
    char reply_audio_url[192];
    bool keep_mic_open;
} voice_node_upload_result_t;

esp_err_t voice_node_http_get_config(voice_node_server_config_t *config);
esp_err_t voice_node_http_send_heartbeat(voice_node_state_t state);
esp_err_t voice_node_http_poll_command(
    char *command_type,
    size_t command_type_size,
    char *audio_url,
    size_t audio_url_size);
esp_err_t voice_node_http_upload_audio(
    const uint8_t *wav_data,
    size_t wav_size,
    int pir_state,
    const char *source,
    voice_node_upload_result_t *result);
esp_err_t voice_node_http_download_reply_audio(
    const char *reply_audio_url,
    uint8_t **audio_data,
    size_t *audio_size);
esp_err_t voice_node_http_stream_reply_audio(
    const char *reply_audio_url,
    voice_node_audio_chunk_handler_t chunk_handler,
    void *user_data,
    size_t *audio_size);
esp_err_t voice_node_http_report_playback_status(
    const char *stage,
    bool ok,
    const char *error,
    const char *audio_url,
    size_t audio_size);
