#pragma once

#include <stdbool.h>

#include "esp_err.h"

esp_err_t voice_node_stream_pcm_diagnostics(
    int stream_seconds,
    int record_gain,
    bool process_on_server);
