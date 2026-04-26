import time
import ujson
import urequests

from config import DEVICE_ID, HTTP_TIMEOUT_SECONDS, SERVER_BASE_URL


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


def _query_escape(value):
    return str(value).replace(" ", "%20")


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