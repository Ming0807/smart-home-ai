try:
    from machine import I2S, Pin
except ImportError:  # pragma: no cover - MicroPython only
    I2S = None
    Pin = None

from config import I2S_SCK_PIN, I2S_SD_PIN, I2S_WS_PIN


class MicReader:
    """Starter-only INMP441 helper for small buffer capture tests.

    This is intentionally not a production streaming pipeline yet.
    It is only used to verify wiring and basic I2S microphone readiness.
    """

    def __init__(
        self,
        ws_pin=I2S_WS_PIN,
        sck_pin=I2S_SCK_PIN,
        sd_pin=I2S_SD_PIN,
        sample_rate=16000,
        buffer_length=2048,
    ):
        if I2S is None or Pin is None:
            raise RuntimeError("I2S microphone support is not available in this firmware")

        self._buffer_length = buffer_length
        self._audio_in = I2S(
            0,
            sck=Pin(sck_pin),
            ws=Pin(ws_pin),
            sd=Pin(sd_pin),
            mode=I2S.RX,
            bits=16,
            format=I2S.MONO,
            rate=sample_rate,
            ibuf=buffer_length * 4,
        )

    def read_sample(self):
        buffer = bytearray(self._buffer_length)
        bytes_read = self._audio_in.readinto(buffer)
        if bytes_read is None:
            bytes_read = 0
        return buffer, bytes_read

    def deinit(self):
        self._audio_in.deinit()
