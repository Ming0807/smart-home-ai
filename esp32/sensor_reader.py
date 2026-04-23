import dht
import machine
import time

from config import DHT22_PIN


class Dht22Reader:
    def __init__(self, pin_number=DHT22_PIN):
        self._sensor = dht.DHT22(machine.Pin(pin_number))

    def read(self):
        self._sensor.measure()
        return {
            "temperature": float(self._sensor.temperature()),
            "humidity": float(self._sensor.humidity()),
            "timestamp": _timestamp(),
        }


def _timestamp():
    year, month, day, hour, minute, second, _, _ = time.localtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
        year,
        month,
        day,
        hour,
        minute,
        second,
    )
