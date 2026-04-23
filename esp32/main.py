import machine
import time

from api_client import get_next_command, send_heartbeat, send_sensor_reading
from config import (
    COMMAND_POLL_INTERVAL_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    RELAY_ACTIVE_HIGH,
    RELAY_PIN,
    SENSOR_INTERVAL_SECONDS,
)
from sensor_reader import Dht22Reader
from wifi_manager import ensure_wifi


class RelayChannel:
    def __init__(self, pin_number=RELAY_PIN, active_high=RELAY_ACTIVE_HIGH):
        self._pin = machine.Pin(pin_number, machine.Pin.OUT)
        self._active_high = active_high
        self.off()

    def on(self):
        self._pin.value(1 if self._active_high else 0)

    def off(self):
        self._pin.value(0 if self._active_high else 1)

    def apply(self, command):
        if command.get("type") != "relay" or command.get("channel") != 1:
            return
        action = command.get("action")
        print("Relay command received:", command)
        if action == "on":
            self.on()
        elif action == "off":
            self.off()


def _due(now, last_run, interval):
    return last_run is None or now - last_run >= interval


def main():
    wlan = None
    sensor = Dht22Reader()
    relay = RelayChannel()

    last_heartbeat = None
    last_sensor = None
    last_command_poll = None

    while True:
        try:
            wlan = ensure_wifi(wlan)
            now = time.time()

            if _due(now, last_heartbeat, HEARTBEAT_INTERVAL_SECONDS):
                print("Heartbeat:", send_heartbeat())
                last_heartbeat = now

            if _due(now, last_sensor, SENSOR_INTERVAL_SECONDS):
                reading = sensor.read()
                print("Sensor:", reading, send_sensor_reading(reading))
                last_sensor = now

            if _due(now, last_command_poll, COMMAND_POLL_INTERVAL_SECONDS):
                response = get_next_command()
                command = response.get("command") if response else None
                if command:
                    relay.apply(command)
                last_command_poll = now

        except Exception as exc:
            print("Loop error:", exc)
            time.sleep(5)

        time.sleep(1)


main()
