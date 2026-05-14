#pragma once

#include "esp_err.h"
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#define SPEAKER_WAV_STREAM_HEADER_BYTES 512

typedef struct {
    uint8_t header[SPEAKER_WAV_STREAM_HEADER_BYTES];
    size_t header_size;
    bool riff_checked;
    bool format_ready;
    bool data_ready;
    uint16_t audio_format;
    uint16_t channels;
    uint32_t sample_rate;
    uint16_t bits_per_sample;
    uint32_t data_remaining;
    size_t frame_index;
    size_t total_frames;
    uint8_t pending_pcm_byte;
    bool has_pending_pcm_byte;
} speaker_wav_stream_t;

esp_err_t speaker_player_init(void);
esp_err_t speaker_player_play_beep(void);
esp_err_t speaker_player_play_record_start_cue(void);
esp_err_t speaker_player_play_record_end_cue(void);
esp_err_t speaker_player_play_self_test(void);
esp_err_t speaker_player_play_diagnostic_tone(void);
esp_err_t speaker_player_play_wav(const uint8_t *wav_data, size_t wav_size);
esp_err_t speaker_player_wav_stream_begin(speaker_wav_stream_t *stream);
esp_err_t speaker_player_wav_stream_write(
    speaker_wav_stream_t *stream,
    const uint8_t *data,
    size_t data_size);
esp_err_t speaker_player_wav_stream_end(speaker_wav_stream_t *stream);
