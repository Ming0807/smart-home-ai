from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Literal

import requests
from requests.exceptions import RequestException, Timeout

from server.config import Settings, get_settings

logger = logging.getLogger(__name__)

OPENWEATHER_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
WEATHER_FALLBACK_REPLY = (
    "ตอนนี้ยังดึงข้อมูลอากาศข้างนอกไม่ได้ ลองใหม่อีกครั้งได้ไหม"
)


@dataclass(frozen=True)
class WeatherData:
    location: str
    temperature_c: float
    humidity: int
    condition: str
    rain_chance: int | None


@dataclass(frozen=True)
class WeatherAnswer:
    reply: str
    source: Literal["weather_api", "fallback"]
    data: WeatherData | None = None
    error: str | None = None


@dataclass(frozen=True)
class CachedWeather:
    data: WeatherData
    expires_at: datetime


class WeatherService:
    """Fetch and summarize OpenWeather data for chat responses."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._cache: dict[str, CachedWeather] = {}
        self._lock = Lock()

    def answer_weather_query(self, message: str) -> WeatherAnswer:
        location = self._detect_location(message) or self._settings.default_weather_location
        weather_data = self.get_weather(location)
        if weather_data is None:
            return WeatherAnswer(
                reply=WEATHER_FALLBACK_REPLY,
                source="fallback",
                error="weather unavailable",
            )
        return WeatherAnswer(
            reply=self._build_reply(message, weather_data),
            source="weather_api",
            data=weather_data,
        )

    def get_weather(self, location: str) -> WeatherData | None:
        cache_key = self._cache_key(location)
        cached_weather = self._get_cached(cache_key)
        if cached_weather is not None:
            return cached_weather

        if not self._settings.openweather_api_key:
            logger.warning("OPENWEATHER_API_KEY is not configured")
            return None

        try:
            current_payload = self._get_current_weather(location)
            rain_chance = self._get_rain_chance(location)
            weather_data = self._normalize_weather(current_payload, rain_chance)
        except Timeout:
            logger.warning("OpenWeather request timed out")
            return None
        except RequestException as exc:
            logger.warning("OpenWeather request failed: %s", self._format_request_error(exc))
            return None
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid OpenWeather response: %s", exc.__class__.__name__)
            return None

        self._set_cached(cache_key, weather_data)
        return weather_data

    def _get_current_weather(self, location: str) -> dict[str, Any]:
        response = self._session.get(
            OPENWEATHER_CURRENT_URL,
            params={
                "q": location,
                "appid": self._settings.openweather_api_key,
                "units": "metric",
                "lang": "th",
            },
            timeout=self._settings.weather_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _get_rain_chance(self, location: str) -> int | None:
        try:
            response = self._session.get(
                OPENWEATHER_FORECAST_URL,
                params={
                    "q": location,
                    "appid": self._settings.openweather_api_key,
                    "units": "metric",
                    "lang": "th",
                    "cnt": 1,
                },
                timeout=self._settings.weather_timeout_seconds,
            )
            response.raise_for_status()
            forecasts = response.json().get("list", [])
            if not forecasts:
                return None
            probability = forecasts[0].get("pop")
            if probability is None:
                return None
            return round(float(probability) * 100)
        except (RequestException, KeyError, TypeError, ValueError) as exc:
            logger.warning("OpenWeather forecast request failed: %s", exc.__class__.__name__)
            return None

    @staticmethod
    def _normalize_weather(
        payload: dict[str, Any],
        rain_chance: int | None,
    ) -> WeatherData:
        weather_items = payload.get("weather") or [{}]
        condition = str(
            weather_items[0].get("description")
            or weather_items[0].get("main")
            or "unknown"
        )
        return WeatherData(
            location=str(payload["name"]),
            temperature_c=round(float(payload["main"]["temp"]), 1),
            humidity=int(payload["main"]["humidity"]),
            condition=condition,
            rain_chance=rain_chance,
        )

    @staticmethod
    def _build_reply(message: str, weather_data: WeatherData) -> str:
        temperature = round(weather_data.temperature_c)
        display_location = WeatherService._display_location(weather_data.location)
        parts = [
            f"ตอนนี้ที่{display_location}ประมาณ {temperature} องศา",
            WeatherService._temperature_summary(temperature),
            f"สภาพอากาศ{weather_data.condition}",
        ]
        if weather_data.rain_chance is not None:
            parts.append(f"โอกาสฝนประมาณ {weather_data.rain_chance}%")
        elif "ฝน" in _normalize(message):
            parts.append("แต่ตอนนี้ยังไม่มีค่าประมาณโอกาสฝน")
        return " ".join(parts)

    @staticmethod
    def _temperature_summary(temperature: int) -> str:
        if temperature >= 35:
            return "ร้อนจัดเลยนะ"
        if temperature >= 32:
            return "ค่อนข้างร้อน"
        if temperature >= 28:
            return "อากาศอุ่น ๆ"
        if temperature >= 24:
            return "ค่อนข้างสบาย"
        return "ค่อนข้างเย็น"

    @staticmethod
    def _detect_location(message: str) -> str | None:
        normalized_message = _normalize(message)
        thai_location_map = {
            "ยะลา": "Yala,TH",
            "กรุงเทพ": "Bangkok,TH",
            "กรุงเทพฯ": "Bangkok,TH",
            "เชียงใหม่": "Chiang Mai,TH",
            "ภูเก็ต": "Phuket,TH",
            "สงขลา": "Songkhla,TH",
            "หาดใหญ่": "Hat Yai,TH",
            "ปัตตานี": "Pattani,TH",
            "นราธิวาส": "Narathiwat,TH",
        }
        for thai_name, query_location in thai_location_map.items():
            if _normalize(thai_name) in normalized_message:
                return query_location
        return None

    @staticmethod
    def _display_location(location: str) -> str:
        location_map = {
            "yala": "ยะลา",
            "bangkok": "กรุงเทพฯ",
            "chiang mai": "เชียงใหม่",
            "phuket": "ภูเก็ต",
            "songkhla": "สงขลา",
            "hat yai": "หาดใหญ่",
            "pattani": "ปัตตานี",
            "narathiwat": "นราธิวาส",
        }
        return location_map.get(location.casefold(), location)

    def _get_cached(self, cache_key: str) -> WeatherData | None:
        with self._lock:
            cached_weather = self._cache.get(cache_key)
            if cached_weather is None:
                return None
            if cached_weather.expires_at <= self._now():
                self._cache.pop(cache_key, None)
                return None
            return cached_weather.data

    def _set_cached(self, cache_key: str, weather_data: WeatherData) -> None:
        expires_at = self._now() + timedelta(
            seconds=self._settings.weather_cache_ttl_seconds,
        )
        with self._lock:
            self._cache[cache_key] = CachedWeather(
                data=weather_data,
                expires_at=expires_at,
            )

    @staticmethod
    def _cache_key(location: str) -> str:
        return _normalize(location)

    @staticmethod
    def _format_request_error(exc: RequestException) -> str:
        response = exc.response
        if response is None:
            return exc.__class__.__name__
        body = response.text[:300].replace("\n", " ")
        return f"{exc.__class__.__name__} status={response.status_code} body={body}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


_weather_service = WeatherService(settings=get_settings())


def get_weather_service() -> WeatherService:
    return _weather_service
