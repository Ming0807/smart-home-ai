import machine
import time

from api_client import (
    get_next_command,
    send_capabilities,
    send_command_result,
    send_heartbeat,
    send_motion_event,
    send_sensor_reading,
)
from config import (
    CAPABILITIES_INTERVAL_SECONDS,
    COMMAND_POLL_INTERVAL_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    MOTION_ENABLED,
    RELAY_ACTIVE_HIGH,
    RELAY_PIN,
    RELAY_PINS,
    SENSOR_INTERVAL_SECONDS,
)
from motion_reader import MotionReader
from sensor_reader import Dht22Reader
from wifi_manager import ensure_wifi


class RelayChannel:
    def __init__(self, pin_number, active_high=RELAY_ACTIVE_HIGH):
        self._pin_number = pin_number
        self._pin = machine.Pin(pin_number, machine.Pin.OUT)
        self._active_high = active_high
        self.off()

    def on(self):
        self._pin.value(1 if self._active_high else 0)

    def off(self):
        self._pin.value(0 if self._active_high else 1)


class RelayController:
    def __init__(self, relay_pins=None, active_high=RELAY_ACTIVE_HIGH):
        pins = relay_pins or {1: RELAY_PIN}
        self._channels = {}
        for channel, pin_number in pins.items():
            self._channels[int(channel)] = RelayChannel(
                pin_number=int(pin_number),
                active_high=active_high,
            )

    def apply(self, command):
        if command.get("type") != "relay":
            return {
                "status": "failed",
                "state": None,
                "error": "unsupported command",
            }
        channel = int(command.get("channel") or 1)
        relay = self._channels.get(channel)
        if relay is None:
            return {
                "status": "failed",
                "state": None,
                "error": "unsupported relay channel",
            }
        action = command.get("action")
        print("Relay command received:", command)
        if action == "on":
            relay.on()
            return {"status": "applied", "state": "on", "error": None}
        elif action == "off":
            relay.off()
            return {"status": "applied", "state": "off", "error": None}
        return {
            "status": "failed",
            "state": None,
            "error": "unsupported relay action",
        }


def _due(now, last_run, interval):
    return last_run is None or now - last_run >= interval


def main():
    wlan = None
    sensor = Dht22Reader()
    motion_reader = MotionReader() if MOTION_ENABLED else None
    relay = RelayController(RELAY_PINS)

    last_heartbeat = None
    last_capabilities = None
    last_sensor = None
    last_command_poll = None

    while True:
        try:
            wlan = ensure_wifi(wlan)
            now = time.time()

            if _due(now, last_heartbeat, HEARTBEAT_INTERVAL_SECONDS):
                last_heartbeat = now
                print("Heartbeat:", send_heartbeat())

            if _due(now, last_capabilities, CAPABILITIES_INTERVAL_SECONDS):
                last_capabilities = now
                print("Capabilities:", send_capabilities())

            if _due(now, last_sensor, SENSOR_INTERVAL_SECONDS):
                last_sensor = now
                try:
                    reading = sensor.read()
                    print("Sensor:", reading, send_sensor_reading(reading))
                except Exception as e:
                    print("Sensor error:", e)

            if _due(now, last_command_poll, COMMAND_POLL_INTERVAL_SECONDS):
                last_command_poll = now
                response = get_next_command()
                command = response.get("command") if response else None
                if command:
                    result = relay.apply(command)
                    print("Command result:", result, send_command_result(command, result))

            if motion_reader is not None:
                motion_event = motion_reader.poll(now)
                if motion_event is not None:
                    print("Motion:", motion_event, send_motion_event(motion_event))

        except Exception as exc:
            print("Loop error:", exc)
            if _should_reset_wifi(exc):
                wlan = None
            time.sleep(5)

        time.sleep(1)


def _should_reset_wifi(exc):
    if isinstance(exc, OSError):
        error_number = getattr(exc, "errno", None)
        if error_number in (103, 104, 110, 113, 116):
            return True

    message = str(exc).upper()
    return (
        "ECONNABORTED" in message
        or "TIMED OUT" in message
        or "ECONNRESET" in message
        or "ENOTCONN" in message
    )


main()
