import socket

import ujson
import urequests

from config import DEVICE_ID, HTTP_TIMEOUT_SECONDS, SERVER_BASE_URL

socket.setdefaulttimeout(HTTP_TIMEOUT_SECONDS)


def _url(path):
    return SERVER_BASE_URL.rstrip("/") + path


def _post_json(path, payload):
    response = None
    try:
        response = urequests.post(
            _url(path),
            data=ujson.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        return response.json()
    finally:
        if response is not None:
            response.close()


def _get_json(path):
    response = None
    try:
        response = urequests.get(
            _url(path),
        )
        return response.json()
    finally:
        if response is not None:
            response.close()


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


def get_next_command():
    return _get_json("/esp32/commands?device_id=" + _query_escape(DEVICE_ID))


def _query_escape(value):
    return str(value).replace(" ", "%20")
