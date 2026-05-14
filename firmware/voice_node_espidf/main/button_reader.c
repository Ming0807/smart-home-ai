#include "button_reader.h"

#include "driver/gpio.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "voice_node_config.h"

static const char *TAG = "button_reader";

static bool s_ready;
static bool s_last_active;
static int64_t s_last_event_ms;
static int64_t s_last_debug_ms;
static int64_t s_pressed_at_ms;
static bool s_long_press_reported;

esp_err_t button_reader_init(void)
{
    if (!VOICE_NODE_BUTTON_UPLOAD_TEST_ENABLED) {
        ESP_LOGI(TAG, "Button audio upload trigger disabled");
        return ESP_OK;
    }

    gpio_config_t config = {
        .pin_bit_mask = 1ULL << CONFIG_VOICE_NODE_BUTTON_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = VOICE_NODE_BUTTON_ACTIVE_LOW ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE,
        .pull_down_en = VOICE_NODE_BUTTON_ACTIVE_LOW ? GPIO_PULLDOWN_DISABLE : GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };

    ESP_RETURN_ON_ERROR(gpio_config(&config), TAG, "button gpio config failed");
    s_ready = true;
    s_last_active = false;
    s_last_event_ms = 0;
    s_last_debug_ms = 0;
    s_pressed_at_ms = 0;
    s_long_press_reported = false;

    ESP_LOGI(
        TAG,
        "Button audio upload trigger enabled: gpio=%d active_low=%d",
        CONFIG_VOICE_NODE_BUTTON_GPIO,
        VOICE_NODE_BUTTON_ACTIVE_LOW);
    return ESP_OK;
}

button_event_t button_reader_poll(void)
{
    if (!VOICE_NODE_BUTTON_UPLOAD_TEST_ENABLED || !s_ready) {
        return BUTTON_EVENT_NONE;
    }

    const int level = gpio_get_level((gpio_num_t)CONFIG_VOICE_NODE_BUTTON_GPIO);
    const bool active = VOICE_NODE_BUTTON_ACTIVE_LOW ? level == 0 : level == 1;
    const int64_t now_ms = esp_timer_get_time() / 1000;
    button_event_t event = BUTTON_EVENT_NONE;

    if (active && !s_last_active) {
        s_pressed_at_ms = now_ms;
        s_long_press_reported = false;
        ESP_LOGI(TAG, "Button active: gpio=%d level=%d", CONFIG_VOICE_NODE_BUTTON_GPIO, level);
    } else if (active && s_pressed_at_ms > 0) {
        const int64_t held_ms = now_ms - s_pressed_at_ms;
        if (!s_long_press_reported && held_ms >= CONFIG_VOICE_NODE_BUTTON_LONG_PRESS_MS) {
            s_long_press_reported = true;
            ESP_LOGI(TAG, "Button long press armed: held=%lld ms", held_ms);
        } else if (now_ms - s_last_debug_ms >= 1000) {
            s_last_debug_ms = now_ms;
            ESP_LOGI(TAG, "Button held: held=%lld ms gpio=%d level=%d", held_ms, CONFIG_VOICE_NODE_BUTTON_GPIO, level);
        }
    } else if (!active && s_last_active) {
        const int64_t held_ms = s_pressed_at_ms > 0 ? now_ms - s_pressed_at_ms : 0;
        ESP_LOGI(TAG, "Button released: held=%lld ms gpio=%d level=%d", held_ms, CONFIG_VOICE_NODE_BUTTON_GPIO, level);
        if (held_ms >= CONFIG_VOICE_NODE_BUTTON_LONG_PRESS_MS) {
            event = BUTTON_EVENT_LONG_PRESS;
            s_last_event_ms = now_ms;
        } else if (held_ms >= CONFIG_VOICE_NODE_BUTTON_DEBOUNCE_MS && now_ms - s_last_event_ms >= CONFIG_VOICE_NODE_BUTTON_DEBOUNCE_MS) {
            event = BUTTON_EVENT_SHORT_PRESS;
            s_last_event_ms = now_ms;
        } else {
            ESP_LOGI(TAG, "Button short bounce ignored: held=%lld ms", held_ms);
        }
        s_pressed_at_ms = 0;
        s_long_press_reported = false;
    }

    s_last_active = active;
    return event;
}

bool button_reader_was_pressed(void)
{
    return button_reader_poll() == BUTTON_EVENT_SHORT_PRESS;
}
