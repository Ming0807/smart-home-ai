import time
import ujson
import urequests

from config import (
    BOARD_TYPE,
    DEVICE_ID,
    DHT22_PIN,
    FIRMWARE_VERSION,
    HTTP_TIMEOUT_SECONDS,
    I2S_SCK_PIN,
    I2S_SD_PIN,
    I2S_WS_PIN,
    MIC_ENABLED,
    MOTION_ENABLED,
    PIR_PIN,
    RELAY_PIN,
    SERVER_BASE_URL,
)


def _url(path):
    return SERVER_BASE_URL.rstrip("/") + path


def _request_json(method, path, payload=None, retries=2):
    last_error = None

    for attempt in range(retries + 1):
        response = None
        try:
            if method == "POST":
                response = urequests.post(
                    _url(path),
                    data=ujson.dumps(payload),
                    headers={"Content-Type": "application/json"},
                    timeout=HTTP_TIMEOUT_SECONDS,
                )
            else:
                response = urequests.get(
                    _url(path),
                    timeout=HTTP_TIMEOUT_SECONDS,
                )

            return response.json()

        except OSError as exc:
            last_error = exc
            if not _is_transient_network_error(exc) or attempt >= retries:
                raise
            print("HTTP retry", attempt + 1, "error:", exc)
            time.sleep(1)

        finally:
            if response is not None:
                response.close()

    if last_error is not None:
        raise last_error

    raise RuntimeError("request failed")


def _post_json(path, payload):
    return _request_json("POST", path, payload=payload)


def _get_json(path):
    return _request_json("GET", path)


def send_heartbeat():
    return _post_json("/esp32/heartbeat", {"device_id": DEVICE_ID})


def send_capabilities():
    capabilities = ["relay", "dht22"]
    if MOTION_ENABLED:
        capabilities.append("pir")
    if MIC_ENABLED:
        capabilities.append("i2s_microphone")

    reserved_pins = [DHT22_PIN, RELAY_PIN]
    sensor_pins = [DHT22_PIN]
    if MOTION_ENABLED:
        reserved_pins.append(PIR_PIN)
        sensor_pins.append(PIR_PIN)
    if MIC_ENABLED:
        reserved_pins.extend([I2S_WS_PIN, I2S_SCK_PIN, I2S_SD_PIN])

    payload = {
        "device_id": DEVICE_ID,
        "board_type": BOARD_TYPE,
        "firmware_version": FIRMWARE_VERSION,
        "capabilities": capabilities,
        "relay_pins": [RELAY_PIN],
        "sensor_pins": sensor_pins,
        "reserved_pins": _unique_ints(reserved_pins),
        "i2s_pins": [I2S_WS_PIN, I2S_SCK_PIN, I2S_SD_PIN] if MIC_ENABLED else [],
        "available_pins": [],
        "timestamp": _iso_timestamp(),
    }
    return _post_json("/esp32/capabilities", payload)


def send_sensor_reading(reading):
    payload = {
        "device_id": DEVICE_ID,
        "temperature": reading["temperature"],
        "humidity": reading["humidity"],
        "timestamp": reading["timestamp"],
    }
    return _post_json("/esp32/sensor", payload)


def send_motion_event(motion):
    payload = {
        "device_id": DEVICE_ID,
        "motion": bool(motion),
        "timestamp": _iso_timestamp(),
    }
    return _post_json("/esp32/motion", payload)


def get_next_command():
    return _get_json("/esp32/commands?device_id=" + _query_escape(DEVICE_ID))


def send_command_result(command, result):
    command_id = command.get("command_id")
    if not command_id:
        return {"status": "skipped", "reason": "missing command_id"}

    payload = {
        "device_id": DEVICE_ID,
        "command_id": command_id,
        "status": result.get("status", "failed"),
        "state": result.get("state"),
        "error": result.get("error"),
        "timestamp": _iso_timestamp(),
    }
    return _post_json("/esp32/command-result", payload)


def _query_escape(value):
    return str(value).replace(" ", "%20")


def _unique_ints(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _iso_timestamp():
    year, month, day, hour, minute, second, _, _ = time.localtime()
    return "%04d-%02d-%02dT%02d:%02d:%02d" % (
        year,
        month,
        day,
        hour,
        minute,
        second,
    )


def _is_transient_network_error(exc):
    if getattr(exc, "errno", None) in (103, 104, 110, 113, 116):
        return True

    message = str(exc).upper()
    return (
        "ECONNABORTED" in message
        or "TIMED OUT" in message
        or "EHOSTUNREACH" in message
        or "ECONNRESET" in message
    )
