#include "speaker_player.h"

#include <math.h>
#include <stdbool.h>
#include <string.h>
#include <stdint.h>

#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "voice_node_config.h"

#define BEEP_BUFFER_FRAMES 256
#define STEREO_CHANNELS 2
#define TWO_PI 6.28318530717958647692f
#define WAV_MIN_HEADER_BYTES 44
#define SILENCE_DRAIN_MS 300
#define REPLY_FADE_MS 30
#define STREAM_STEREO_BUFFER_FRAMES 256

static const char *TAG = "speaker_player";

static i2s_chan_handle_t s_tx_handle;
static bool s_speaker_ready;
static bool s_tx_enabled;

esp_err_t speaker_player_init(void)
{
    if (!VOICE_NODE_SPEAKER_ENABLED) {
        ESP_LOGI(TAG, "MAX98357A speaker disabled");
        return ESP_OK;
    }

    i2s_chan_config_t channel_config = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    ESP_RETURN_ON_ERROR(
        i2s_new_channel(&channel_config, &s_tx_handle, NULL),
        TAG,
        "create I2S TX channel failed");

    i2s_std_config_t std_config = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(CONFIG_VOICE_NODE_SPEAKER_SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_16BIT,
            I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = (gpio_num_t)CONFIG_VOICE_NODE_SPEAKER_BCLK_GPIO,
            .ws = (gpio_num_t)CONFIG_VOICE_NODE_SPEAKER_LRC_GPIO,
            .dout = (gpio_num_t)CONFIG_VOICE_NODE_SPEAKER_DIN_GPIO,
            .din = I2S_GPIO_UNUSED,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };
    std_config.slot_cfg.slot_mask = I2S_STD_SLOT_BOTH;

    ESP_RETURN_ON_ERROR(
        i2s_channel_init_std_mode(s_tx_handle, &std_config),
        TAG,
        "init I2S TX standard mode failed");
    s_speaker_ready = true;
    ESP_LOGI(
        TAG,
        "MAX98357A enabled: lrc=%d bclk=%d din=%d sample_rate=%d",
        CONFIG_VOICE_NODE_SPEAKER_LRC_GPIO,
        CONFIG_VOICE_NODE_SPEAKER_BCLK_GPIO,
        CONFIG_VOICE_NODE_SPEAKER_DIN_GPIO,
        CONFIG_VOICE_NODE_SPEAKER_SAMPLE_RATE);
    return ESP_OK;
}

static esp_err_t ensure_output_enabled(void)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    if (s_tx_enabled) {
        return ESP_OK;
    }

    ESP_RETURN_ON_ERROR(i2s_channel_enable(s_tx_handle), TAG, "enable I2S TX failed");
    s_tx_enabled = true;
    return ESP_OK;
}

static void drain_silence_and_disable(void)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready || !s_tx_enabled) {
        return;
    }

    const int sample_rate = CONFIG_VOICE_NODE_SPEAKER_SAMPLE_RATE;
    const int total_frames = (sample_rate * SILENCE_DRAIN_MS) / 1000;
    int16_t silence[BEEP_BUFFER_FRAMES * STEREO_CHANNELS] = { 0 };
    int frames_written = 0;

    while (frames_written < total_frames) {
        int chunk_frames = total_frames - frames_written;
        if (chunk_frames > BEEP_BUFFER_FRAMES) {
            chunk_frames = BEEP_BUFFER_FRAMES;
        }

        size_t bytes_written = 0;
        esp_err_t err = i2s_channel_write(
            s_tx_handle,
            silence,
            chunk_frames * STEREO_CHANNELS * sizeof(silence[0]),
            &bytes_written,
            pdMS_TO_TICKS(500));
        if (err != ESP_OK || bytes_written == 0) {
            ESP_LOGW(TAG, "Silence drain failed: %s", esp_err_to_name(err));
            break;
        }
        frames_written += bytes_written / (STEREO_CHANNELS * sizeof(silence[0]));
    }

    esp_err_t err = i2s_channel_disable(s_tx_handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Disable I2S TX failed: %s", esp_err_to_name(err));
        return;
    }
    s_tx_enabled = false;
}

static esp_err_t play_tone(int frequency_hz, int duration_ms, int amplitude)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    ESP_RETURN_ON_ERROR(ensure_output_enabled(), TAG, "enable output for tone failed");

    const int sample_rate = CONFIG_VOICE_NODE_SPEAKER_SAMPLE_RATE;
    const int total_samples = (sample_rate * duration_ms) / 1000;
    const float phase_step = TWO_PI * (float)frequency_hz / (float)sample_rate;
    int16_t buffer[BEEP_BUFFER_FRAMES * STEREO_CHANNELS] = { 0 };
    float phase = 0.0f;
    int frames_written = 0;

    ESP_LOGI(TAG, "Playing tone: %d Hz %d ms amp=%d", frequency_hz, duration_ms, amplitude);

    esp_err_t result = ESP_OK;
    while (frames_written < total_samples) {
        int chunk_frames = total_samples - frames_written;
        if (chunk_frames > BEEP_BUFFER_FRAMES) {
            chunk_frames = BEEP_BUFFER_FRAMES;
        }

        for (int index = 0; index < chunk_frames; index++) {
            const int16_t sample = (int16_t)(sinf(phase) * (float)amplitude);
            buffer[index * STEREO_CHANNELS] = sample;
            buffer[index * STEREO_CHANNELS + 1] = sample;
            phase += phase_step;
            if (phase > TWO_PI) {
                phase -= TWO_PI;
            }
        }

        size_t bytes_written = 0;
        esp_err_t err = i2s_channel_write(
            s_tx_handle,
            buffer,
            chunk_frames * STEREO_CHANNELS * sizeof(buffer[0]),
            &bytes_written,
            pdMS_TO_TICKS(500));
        if (err != ESP_OK) {
            result = err;
            break;
        }
        frames_written += bytes_written / (STEREO_CHANNELS * sizeof(buffer[0]));
    }

    drain_silence_and_disable();
    return result;
}

esp_err_t speaker_player_play_beep(void)
{
    return play_tone(
        CONFIG_VOICE_NODE_SPEAKER_BEEP_FREQUENCY_HZ,
        CONFIG_VOICE_NODE_SPEAKER_BEEP_DURATION_MS,
        CONFIG_VOICE_NODE_SPEAKER_BEEP_AMPLITUDE);
}

esp_err_t speaker_player_play_record_start_cue(void)
{
    return play_tone(880, 70, CONFIG_VOICE_NODE_SPEAKER_BEEP_AMPLITUDE / 2);
}

esp_err_t speaker_player_play_record_end_cue(void)
{
    return play_tone(660, 60, CONFIG_VOICE_NODE_SPEAKER_BEEP_AMPLITUDE / 3);
}

esp_err_t speaker_player_play_self_test(void)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    ESP_LOGI(TAG, "Speaker self-test start");
    int frequencies[] = { 440, 660, 880 };
    for (size_t index = 0; index < sizeof(frequencies) / sizeof(frequencies[0]); index++) {
        esp_err_t err = play_tone(frequencies[index], 120, CONFIG_VOICE_NODE_SPEAKER_BEEP_AMPLITUDE);
        if (err != ESP_OK) {
            return err;
        }
        vTaskDelay(pdMS_TO_TICKS(120));
    }
    ESP_LOGI(TAG, "Speaker self-test end");
    return ESP_OK;
}

esp_err_t speaker_player_play_diagnostic_tone(void)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    ESP_LOGI(TAG, "Speaker diagnostic tone start");
    esp_err_t err = play_tone(1000, 600, CONFIG_VOICE_NODE_SPEAKER_BEEP_AMPLITUDE);
    if (err != ESP_OK) {
        return err;
    }
    vTaskDelay(pdMS_TO_TICKS(200));
    err = play_tone(500, 600, CONFIG_VOICE_NODE_SPEAKER_BEEP_AMPLITUDE);
    ESP_LOGI(TAG, "Speaker diagnostic tone end");
    return err;
}

static uint16_t read_le16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

static uint32_t read_le32(const uint8_t *data)
{
    return (uint32_t)data[0] |
           ((uint32_t)data[1] << 8) |
           ((uint32_t)data[2] << 16) |
           ((uint32_t)data[3] << 24);
}

static int16_t scale_reply_sample(int16_t sample, size_t frame_index, size_t total_frames, uint32_t sample_rate)
{
    int32_t scaled = ((int32_t)sample * CONFIG_VOICE_NODE_SPEAKER_REPLY_VOLUME_PERCENT) / 100;
    const size_t fade_frames = ((size_t)sample_rate * REPLY_FADE_MS) / 1000;
    if (fade_frames > 0) {
        size_t fade_percent = 100;
        if (frame_index < fade_frames) {
            fade_percent = (frame_index * 100) / fade_frames;
        }
        const size_t frames_remaining = total_frames > frame_index ? total_frames - frame_index : 0;
        if (frames_remaining < fade_frames) {
            const size_t end_percent = (frames_remaining * 100) / fade_frames;
            if (end_percent < fade_percent) {
                fade_percent = end_percent;
            }
        }
        scaled = (scaled * (int32_t)fade_percent) / 100;
    }
    if (scaled > INT16_MAX) {
        return INT16_MAX;
    }
    if (scaled < INT16_MIN) {
        return INT16_MIN;
    }
    return (int16_t)scaled;
}

static esp_err_t write_scaled_mono_pcm(
    const uint8_t *pcm_data,
    size_t pcm_size,
    size_t *frame_index,
    size_t total_frames,
    uint32_t sample_rate)
{
    if (pcm_data == NULL || pcm_size == 0 || frame_index == NULL) {
        return ESP_OK;
    }

    int16_t stereo_buffer[STREAM_STEREO_BUFFER_FRAMES * STEREO_CHANNELS];
    size_t written_total = 0;
    esp_err_t result = ESP_OK;

    while (written_total < pcm_size) {
        size_t mono_bytes = pcm_size - written_total;
        const size_t max_mono_bytes = STREAM_STEREO_BUFFER_FRAMES * sizeof(int16_t);
        if (mono_bytes > max_mono_bytes) {
            mono_bytes = max_mono_bytes;
        }
        mono_bytes -= mono_bytes % sizeof(int16_t);
        if (mono_bytes == 0) {
            break;
        }

        const int16_t *mono_samples = (const int16_t *)(pcm_data + written_total);
        const size_t frame_count = mono_bytes / sizeof(int16_t);
        for (size_t index = 0; index < frame_count; index++) {
            const int16_t sample = scale_reply_sample(
                mono_samples[index],
                *frame_index + index,
                total_frames,
                sample_rate);
            stereo_buffer[index * STEREO_CHANNELS] = sample;
            stereo_buffer[index * STEREO_CHANNELS + 1] = sample;
        }

        size_t bytes_written = 0;
        esp_err_t err = i2s_channel_write(
            s_tx_handle,
            stereo_buffer,
            frame_count * STEREO_CHANNELS * sizeof(stereo_buffer[0]),
            &bytes_written,
            pdMS_TO_TICKS(1000));
        if (err != ESP_OK) {
            result = err;
            break;
        }
        if (bytes_written == 0) {
            result = ESP_ERR_TIMEOUT;
            break;
        }

        const size_t frames_written = bytes_written / (STEREO_CHANNELS * sizeof(stereo_buffer[0]));
        *frame_index += frames_written;
        written_total += frames_written * sizeof(int16_t);
    }

    return result;
}

static bool wav_stream_format_is_supported(const speaker_wav_stream_t *stream)
{
    return stream->audio_format == 1 &&
           stream->channels == 1 &&
           stream->bits_per_sample == 16 &&
           stream->sample_rate > 0;
}

static esp_err_t speaker_player_wav_stream_write_pcm(
    speaker_wav_stream_t *stream,
    const uint8_t *pcm_data,
    size_t pcm_size)
{
    if (stream == NULL || pcm_data == NULL || pcm_size == 0) {
        return ESP_OK;
    }
    if (stream->data_remaining == 0) {
        return ESP_OK;
    }
    if (pcm_size > stream->data_remaining) {
        pcm_size = stream->data_remaining;
    }

    esp_err_t err = ESP_OK;
    size_t cursor = 0;

    if (stream->has_pending_pcm_byte && pcm_size > 0) {
        uint8_t pair[2] = { stream->pending_pcm_byte, pcm_data[0] };
        err = write_scaled_mono_pcm(
            pair,
            sizeof(pair),
            &stream->frame_index,
            stream->total_frames,
            stream->sample_rate);
        if (err != ESP_OK) {
            return err;
        }
        stream->has_pending_pcm_byte = false;
        cursor = 1;
    }

    size_t aligned_size = pcm_size - cursor;
    if (aligned_size % sizeof(int16_t) != 0) {
        aligned_size -= 1;
        stream->pending_pcm_byte = pcm_data[cursor + aligned_size];
        stream->has_pending_pcm_byte = true;
    }

    if (aligned_size > 0) {
        err = write_scaled_mono_pcm(
            pcm_data + cursor,
            aligned_size,
            &stream->frame_index,
            stream->total_frames,
            stream->sample_rate);
        if (err != ESP_OK) {
            return err;
        }
    }

    stream->data_remaining -= pcm_size;
    return ESP_OK;
}

static esp_err_t speaker_player_wav_stream_parse_header(speaker_wav_stream_t *stream)
{
    if (stream->header_size < 12) {
        return ESP_OK;
    }
    if (!stream->riff_checked) {
        if (memcmp(stream->header, "RIFF", 4) != 0 || memcmp(stream->header + 8, "WAVE", 4) != 0) {
            ESP_LOGW(TAG, "Stream reply audio is not a RIFF/WAVE file");
            return ESP_ERR_INVALID_ARG;
        }
        stream->riff_checked = true;
    }

    size_t offset = 12;
    while (offset + 8 <= stream->header_size) {
        const uint8_t *chunk = stream->header + offset;
        const uint32_t chunk_size = read_le32(chunk + 4);
        const size_t chunk_data_offset = offset + 8;

        if (memcmp(chunk, "data", 4) == 0) {
            if (!wav_stream_format_is_supported(stream)) {
                ESP_LOGW(
                    TAG,
                    "Unsupported stream WAV: format=%u channels=%u bits=%u",
                    stream->audio_format,
                    stream->channels,
                    stream->bits_per_sample);
                return ESP_ERR_NOT_SUPPORTED;
            }
            stream->data_ready = true;
            stream->data_remaining = chunk_size;
            stream->total_frames = chunk_size / sizeof(int16_t);
            ESP_LOGI(
                TAG,
                "Streaming reply WAV: bytes=%u sample_rate=%u volume=%d%%",
                (unsigned int)chunk_size,
                (unsigned int)stream->sample_rate,
                CONFIG_VOICE_NODE_SPEAKER_REPLY_VOLUME_PERCENT);

            const size_t available_pcm = stream->header_size - chunk_data_offset;
            if (available_pcm > 0) {
                return speaker_player_wav_stream_write_pcm(
                    stream,
                    stream->header + chunk_data_offset,
                    available_pcm);
            }
            return ESP_OK;
        }

        if (chunk_data_offset + chunk_size > stream->header_size) {
            return ESP_OK;
        }

        if (memcmp(chunk, "fmt ", 4) == 0 && chunk_size >= 16) {
            stream->audio_format = read_le16(stream->header + chunk_data_offset);
            stream->channels = read_le16(stream->header + chunk_data_offset + 2);
            stream->sample_rate = read_le32(stream->header + chunk_data_offset + 4);
            stream->bits_per_sample = read_le16(stream->header + chunk_data_offset + 14);
            stream->format_ready = true;
        }

        offset = chunk_data_offset + chunk_size + (chunk_size & 1U);
    }

    if (stream->header_size >= SPEAKER_WAV_STREAM_HEADER_BYTES) {
        ESP_LOGW(TAG, "WAV stream header too large before data chunk");
        return ESP_ERR_INVALID_SIZE;
    }
    return ESP_OK;
}

esp_err_t speaker_player_wav_stream_begin(speaker_wav_stream_t *stream)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    if (stream == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    memset(stream, 0, sizeof(*stream));
    ESP_RETURN_ON_ERROR(ensure_output_enabled(), TAG, "enable output for WAV stream failed");
    return ESP_OK;
}

esp_err_t speaker_player_wav_stream_write(
    speaker_wav_stream_t *stream,
    const uint8_t *data,
    size_t data_size)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    if (stream == NULL || data == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    if (data_size == 0) {
        return ESP_OK;
    }

    if (stream->data_ready) {
        return speaker_player_wav_stream_write_pcm(stream, data, data_size);
    }

    if (stream->header_size + data_size > SPEAKER_WAV_STREAM_HEADER_BYTES) {
        const size_t available = SPEAKER_WAV_STREAM_HEADER_BYTES - stream->header_size;
        if (available > 0) {
            memcpy(stream->header + stream->header_size, data, available);
            stream->header_size += available;
        }
        esp_err_t err = speaker_player_wav_stream_parse_header(stream);
        if (err != ESP_OK) {
            return err;
        }
        if (!stream->data_ready) {
            return ESP_ERR_INVALID_SIZE;
        }
        return speaker_player_wav_stream_write(stream, data + available, data_size - available);
    }

    memcpy(stream->header + stream->header_size, data, data_size);
    stream->header_size += data_size;
    return speaker_player_wav_stream_parse_header(stream);
}

esp_err_t speaker_player_wav_stream_end(speaker_wav_stream_t *stream)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    if (stream == NULL) {
        drain_silence_and_disable();
        return ESP_ERR_INVALID_ARG;
    }
    esp_err_t err = ESP_OK;
    if (!stream->data_ready) {
        ESP_LOGW(TAG, "WAV stream ended before data chunk");
        err = ESP_ERR_INVALID_SIZE;
    } else if (stream->data_remaining > 0) {
        ESP_LOGW(TAG, "WAV stream ended early: remaining=%u", (unsigned int)stream->data_remaining);
        err = ESP_ERR_INVALID_SIZE;
    } else if (stream->has_pending_pcm_byte) {
        ESP_LOGW(TAG, "WAV stream ended with an odd PCM byte");
        err = ESP_ERR_INVALID_SIZE;
    }
    drain_silence_and_disable();
    return err;
}

esp_err_t speaker_player_play_wav(const uint8_t *wav_data, size_t wav_size)
{
    if (!VOICE_NODE_SPEAKER_ENABLED || !s_speaker_ready) {
        return ESP_OK;
    }
    ESP_RETURN_ON_ERROR(ensure_output_enabled(), TAG, "enable output for WAV failed");
    if (wav_data == NULL || wav_size < WAV_MIN_HEADER_BYTES) {
        drain_silence_and_disable();
        return ESP_ERR_INVALID_ARG;
    }
    if (memcmp(wav_data, "RIFF", 4) != 0 || memcmp(wav_data + 8, "WAVE", 4) != 0) {
        ESP_LOGW(TAG, "Reply audio is not a RIFF/WAVE file");
        drain_silence_and_disable();
        return ESP_ERR_INVALID_ARG;
    }

    uint16_t audio_format = 0;
    uint16_t channels = 0;
    uint32_t sample_rate = 0;
    uint16_t bits_per_sample = 0;
    const uint8_t *pcm_data = NULL;
    size_t pcm_size = 0;

    size_t offset = 12;
    while (offset + 8 <= wav_size) {
        const uint8_t *chunk = wav_data + offset;
        const uint32_t chunk_size = read_le32(chunk + 4);
        const size_t chunk_data_offset = offset + 8;
        if (chunk_data_offset + chunk_size > wav_size) {
            break;
        }

        if (memcmp(chunk, "fmt ", 4) == 0 && chunk_size >= 16) {
            audio_format = read_le16(wav_data + chunk_data_offset);
            channels = read_le16(wav_data + chunk_data_offset + 2);
            sample_rate = read_le32(wav_data + chunk_data_offset + 4);
            bits_per_sample = read_le16(wav_data + chunk_data_offset + 14);
        } else if (memcmp(chunk, "data", 4) == 0) {
            pcm_data = wav_data + chunk_data_offset;
            pcm_size = chunk_size;
        }

        offset = chunk_data_offset + chunk_size + (chunk_size & 1U);
    }

    if (audio_format != 1 || channels != 1 || bits_per_sample != 16 || pcm_data == NULL || pcm_size == 0) {
        ESP_LOGW(
            TAG,
            "Unsupported WAV: format=%u channels=%u bits=%u data=%u",
            audio_format,
            channels,
            bits_per_sample,
            (unsigned int)pcm_size);
        drain_silence_and_disable();
        return ESP_ERR_NOT_SUPPORTED;
    }
    if (sample_rate != CONFIG_VOICE_NODE_SPEAKER_SAMPLE_RATE) {
        ESP_LOGW(
            TAG,
            "WAV sample rate %u differs from speaker sample rate %d",
            (unsigned int)sample_rate,
            CONFIG_VOICE_NODE_SPEAKER_SAMPLE_RATE);
    }

    ESP_LOGI(
        TAG,
        "Playing reply WAV: bytes=%u sample_rate=%u volume=%d%%",
        (unsigned int)pcm_size,
        (unsigned int)sample_rate,
        CONFIG_VOICE_NODE_SPEAKER_REPLY_VOLUME_PERCENT);

    size_t written_total = 0;
    const size_t total_frames = pcm_size / sizeof(int16_t);
    esp_err_t result = ESP_OK;
    while (written_total < pcm_size) {
        size_t mono_bytes = pcm_size - written_total;
        const size_t max_mono_bytes = STREAM_STEREO_BUFFER_FRAMES * sizeof(int16_t);
        if (mono_bytes > max_mono_bytes) {
            mono_bytes = max_mono_bytes;
        }
        mono_bytes -= mono_bytes % sizeof(int16_t);
        if (mono_bytes == 0) {
            break;
        }

        size_t frame_index = written_total / sizeof(int16_t);
        esp_err_t err = write_scaled_mono_pcm(
            pcm_data + written_total,
            mono_bytes,
            &frame_index,
            total_frames,
            sample_rate);
        if (err != ESP_OK) {
            result = err;
            break;
        }
        written_total = frame_index * sizeof(int16_t);
    }

    drain_silence_and_disable();
    return result;
}
