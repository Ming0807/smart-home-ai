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

esp_err_t mic_reader_init(void);
esp_err_t mic_reader_read_level(mic_level_stats_t *stats);
esp_err_t mic_reader_record_wav(uint8_t **wav_data, size_t *wav_size, int record_seconds);
void mic_reader_free_wav(uint8_t *wav_data);
