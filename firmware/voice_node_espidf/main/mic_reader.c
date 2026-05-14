#include "mic_reader.h"

#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "voice_node_config.h"

#define MIC_SAMPLE_BUFFER_COUNT 512
#define WAV_HEADER_SIZE 44
#define MS_PER_SECOND 1000

static const char *TAG = "mic_reader";
static i2s_chan_handle_t s_rx_handle;
static bool s_mic_ready;

static void write_le16(uint8_t *output, uint16_t value)
{
    output[0] = (uint8_t)(value & 0xff);
    output[1] = (uint8_t)((value >> 8) & 0xff);
}

static void write_le32(uint8_t *output, uint32_t value)
{
    output[0] = (uint8_t)(value & 0xff);
    output[1] = (uint8_t)((value >> 8) & 0xff);
    output[2] = (uint8_t)((value >> 16) & 0xff);
    output[3] = (uint8_t)((value >> 24) & 0xff);
}

static void write_wav_header(uint8_t *output, uint32_t pcm_bytes, uint32_t sample_rate)
{
    memcpy(output + 0, "RIFF", 4);
    write_le32(output + 4, pcm_bytes + 36);
    memcpy(output + 8, "WAVE", 4);
    memcpy(output + 12, "fmt ", 4);
    write_le32(output + 16, 16);
    write_le16(output + 20, 1);
    write_le16(output + 22, 1);
    write_le32(output + 24, sample_rate);
    write_le32(output + 28, sample_rate * 2);
    write_le16(output + 32, 2);
    write_le16(output + 34, 16);
    memcpy(output + 36, "data", 4);
    write_le32(output + 40, pcm_bytes);
}

static int16_t clamp_i16(int value)
{
    if (value > INT16_MAX) {
        return INT16_MAX;
    }
    if (value < INT16_MIN) {
        return INT16_MIN;
    }
    return (int16_t)value;
}

esp_err_t mic_reader_init(void)
{
    if (!VOICE_NODE_MIC_ENABLED) {
        ESP_LOGI(TAG, "Microphone test disabled in menuconfig");
        return ESP_OK;
    }

    i2s_chan_config_t channel_config = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    ESP_RETURN_ON_ERROR(
        i2s_new_channel(&channel_config, NULL, &s_rx_handle),
        TAG,
        "create I2S RX channel failed");

    i2s_std_config_t std_config = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(CONFIG_VOICE_NODE_MIC_SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_32BIT,
            I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = (gpio_num_t)CONFIG_VOICE_NODE_MIC_SCK_GPIO,
            .ws = (gpio_num_t)CONFIG_VOICE_NODE_MIC_WS_GPIO,
            .dout = I2S_GPIO_UNUSED,
            .din = (gpio_num_t)CONFIG_VOICE_NODE_MIC_SD_GPIO,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };
    std_config.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;

    ESP_RETURN_ON_ERROR(
        i2s_channel_init_std_mode(s_rx_handle, &std_config),
        TAG,
        "init I2S RX standard mode failed");
    ESP_RETURN_ON_ERROR(i2s_channel_enable(s_rx_handle), TAG, "enable I2S RX failed");

    s_mic_ready = true;
    ESP_LOGI(
        TAG,
        "INMP441 enabled: ws=%d sck=%d sd=%d sample_rate=%d",
        CONFIG_VOICE_NODE_MIC_WS_GPIO,
        CONFIG_VOICE_NODE_MIC_SCK_GPIO,
        CONFIG_VOICE_NODE_MIC_SD_GPIO,
        CONFIG_VOICE_NODE_MIC_SAMPLE_RATE);
    return ESP_OK;
}

esp_err_t mic_reader_read_level(mic_level_stats_t *stats)
{
    if (stats == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    memset(stats, 0, sizeof(*stats));
    stats->enabled = VOICE_NODE_MIC_ENABLED;

    if (!VOICE_NODE_MIC_ENABLED || !s_mic_ready) {
        return ESP_OK;
    }

    int32_t samples[MIC_SAMPLE_BUFFER_COUNT] = { 0 };
    size_t bytes_read = 0;
    esp_err_t err = i2s_channel_read(
        s_rx_handle,
        samples,
        sizeof(samples),
        &bytes_read,
        pdMS_TO_TICKS(250));
    if (err != ESP_OK) {
        return err;
    }

    const int sample_count = bytes_read / sizeof(samples[0]);
    if (sample_count <= 0) {
        return ESP_ERR_INVALID_SIZE;
    }

    double mean = 0.0;
    for (int index = 0; index < sample_count; index++) {
        mean += (double)(samples[index] >> 16);
    }
    mean /= (double)sample_count;

    int peak = 0;
    double sum_abs = 0.0;
    double sum_square = 0.0;

    for (int index = 0; index < sample_count; index++) {
        const double centered = (double)(samples[index] >> 16) - mean;
        const int magnitude = abs((int)centered);
        if (magnitude > peak) {
            peak = magnitude;
        }
        sum_abs += (double)magnitude;
        sum_square += centered * centered;
    }

    stats->sample_count = sample_count;
    stats->peak = peak;
    stats->average_abs = sum_abs / (double)sample_count;
    stats->rms = sqrt(sum_square / (double)sample_count);
    return ESP_OK;
}

esp_err_t mic_reader_record_wav(uint8_t **wav_data, size_t *wav_size, int record_seconds)
{
    if (wav_data == NULL || wav_size == NULL || record_seconds <= 0) {
        return ESP_ERR_INVALID_ARG;
    }
    *wav_data = NULL;
    *wav_size = 0;

    if (!VOICE_NODE_MIC_ENABLED || !s_mic_ready) {
        return ESP_ERR_INVALID_STATE;
    }

    const int sample_rate = CONFIG_VOICE_NODE_MIC_SAMPLE_RATE;
    const int total_samples = sample_rate * record_seconds;
    const size_t pcm_bytes = (size_t)total_samples * sizeof(int16_t);
    const size_t total_bytes = WAV_HEADER_SIZE + pcm_bytes;
    const int min_record_samples = (sample_rate * CONFIG_VOICE_NODE_MIC_VAD_MIN_RECORD_MS) / MS_PER_SECOND;
    const int silence_stop_samples = (sample_rate * CONFIG_VOICE_NODE_MIC_VAD_SILENCE_STOP_MS) / MS_PER_SECOND;

    uint8_t *buffer = malloc(total_bytes);
    if (buffer == NULL) {
        return ESP_ERR_NO_MEM;
    }
    write_wav_header(buffer, (uint32_t)pcm_bytes, (uint32_t)sample_rate);

    int samples_written = 0;
    bool speech_detected = false;
    int silence_samples_after_speech = 0;
    int32_t samples[MIC_SAMPLE_BUFFER_COUNT] = { 0 };
    int16_t *pcm = (int16_t *)(buffer + WAV_HEADER_SIZE);

    while (samples_written < total_samples) {
        size_t bytes_read = 0;
        esp_err_t err = i2s_channel_read(
            s_rx_handle,
            samples,
            sizeof(samples),
            &bytes_read,
            pdMS_TO_TICKS(500));
        if (err != ESP_OK) {
            free(buffer);
            return err;
        }

        int sample_count = bytes_read / sizeof(samples[0]);
        if (sample_count <= 0) {
            continue;
        }

        int remaining = total_samples - samples_written;
        if (sample_count > remaining) {
            sample_count = remaining;
        }

        double mean = 0.0;
        for (int index = 0; index < sample_count; index++) {
            mean += (double)(samples[index] >> 16);
        }
        mean /= (double)sample_count;

        double sum_abs = 0.0;
        for (int index = 0; index < sample_count; index++) {
            const double centered = (double)(samples[index] >> 16) - mean;
            sum_abs += fabs(centered);
        }
        const double average_abs = sum_abs / (double)sample_count;
        const bool chunk_has_speech = average_abs >= (double)CONFIG_VOICE_NODE_MIC_VAD_THRESHOLD;
        if (chunk_has_speech) {
            speech_detected = true;
            silence_samples_after_speech = 0;
        } else if (speech_detected) {
            silence_samples_after_speech += sample_count;
        }

        for (int index = 0; index < sample_count; index++) {
            const double centered = (double)(samples[index] >> 16) - mean;
            const int amplified = (int)(centered * CONFIG_VOICE_NODE_MIC_RECORD_GAIN);
            pcm[samples_written++] = clamp_i16(amplified);
        }

        if (
            VOICE_NODE_MIC_VAD_ENABLED &&
            speech_detected &&
            samples_written >= min_record_samples &&
            silence_samples_after_speech >= silence_stop_samples
        ) {
            ESP_LOGI(
                TAG,
                "VAD stop: recorded_ms=%d threshold=%d last_avg_abs=%.1f",
                (samples_written * MS_PER_SECOND) / sample_rate,
                CONFIG_VOICE_NODE_MIC_VAD_THRESHOLD,
                average_abs);
            break;
        }
    }

    *wav_data = buffer;
    const size_t actual_pcm_bytes = (size_t)samples_written * sizeof(int16_t);
    const size_t actual_total_bytes = WAV_HEADER_SIZE + actual_pcm_bytes;
    write_wav_header(buffer, (uint32_t)actual_pcm_bytes, (uint32_t)sample_rate);
    uint8_t *shrunk_buffer = realloc(buffer, actual_total_bytes);
    if (shrunk_buffer != NULL) {
        *wav_data = shrunk_buffer;
    }
    *wav_size = actual_total_bytes;
    ESP_LOGI(
        TAG,
        "Recorded WAV: max_seconds=%d actual_ms=%d bytes=%u speech=%d",
        record_seconds,
        (samples_written * MS_PER_SECOND) / sample_rate,
        (unsigned int)actual_total_bytes,
        speech_detected);
    return ESP_OK;
}

void mic_reader_free_wav(uint8_t *wav_data)
{
    free(wav_data);
}
