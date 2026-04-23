import network
import time

from config import WIFI_PASSWORD, WIFI_SSID


def connect_wifi(timeout_seconds=20):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    print("Connecting to Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    started_at = time.time()
    while not wlan.isconnected():
        if time.time() - started_at > timeout_seconds:
            raise RuntimeError("Wi-Fi connection timed out")
        time.sleep(1)

    print("Wi-Fi connected:", wlan.ifconfig())
    return wlan


def ensure_wifi(wlan):
    if wlan is None or not wlan.isconnected():
        return connect_wifi()
    return wlan
