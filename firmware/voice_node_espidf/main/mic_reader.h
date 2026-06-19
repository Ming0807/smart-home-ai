#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

typedef struct {
    bool enabled;
    int sample_count;
    int peak;
    double rms;
    double average_abs;
} mic_level_stats_t;

typedef struct {
    int record_seconds;
    int record_gain;
    bool vad_enabled;
    int vad_threshold;
    int vad_min_record_ms;
    int vad_silence_stop_ms;
    int no_speech_timeout_ms;
} mic_record_config_t;

typedef esp_err_t (*mic_pcm_chunk_handler_t)(
    const uint8_t *data,
    size_t data_size,
    void *user_data);

esp_err_t mic_reader_init(void);
esp_err_t mic_reader_read_level(mic_level_stats_t *stats);
esp_err_t mic_reader_record_wav(
    uint8_t **wav_data,
    size_t *wav_size,
    const mic_record_config_t *record_config,
    bool *speech_detected);
esp_err_t mic_reader_stream_pcm_seconds(
    int stream_seconds,
    int record_gain,
    mic_pcm_chunk_handler_t chunk_handler,
    void *user_data);
void mic_reader_free_wav(uint8_t *wav_data);
