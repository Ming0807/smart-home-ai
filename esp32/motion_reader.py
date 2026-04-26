import machine
import time

from config import MOTION_EVENT_COOLDOWN_SECONDS, PIR_PIN


class MotionReader:
    def __init__(
        self,
        pin_number=PIR_PIN,
        cooldown_seconds=MOTION_EVENT_COOLDOWN_SECONDS,
    ):
        self._pin = machine.Pin(pin_number, machine.Pin.IN)
        self._cooldown_seconds = cooldown_seconds
        self._last_state = bool(self._pin.value())
        self._last_motion_sent_at = None

    def poll(self, now=None):
        if now is None:
            now = time.time()

        current_state = bool(self._pin.value())
        event = None

        if current_state and not self._last_state:
            if self._last_motion_sent_at is None:
                event = True
            elif now - self._last_motion_sent_at >= self._cooldown_seconds:
                event = True

            if event is True:
                self._last_motion_sent_at = now
        elif not current_state and self._last_state:
            event = False

        self._last_state = current_state
        return event

