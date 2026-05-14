#pragma once

#include <stdbool.h>

#include "esp_err.h"

typedef enum {
    BUTTON_EVENT_NONE = 0,
    BUTTON_EVENT_SHORT_PRESS,
    BUTTON_EVENT_LONG_PRESS,
} button_event_t;

esp_err_t button_reader_init(void);
button_event_t button_reader_poll(void);
bool button_reader_was_pressed(void);
