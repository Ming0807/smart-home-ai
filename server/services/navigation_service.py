from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Literal

import requests
from requests.exceptions import RequestException, Timeout

from server.config import Settings, get_settings
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

OPENROUTESERVICE_DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/driving-car"
)
OPENROUTESERVICE_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving"
NAVIGATION_FALLBACK_REPLY = "ตอนนี้ยังดึงข้อมูลเส้นทางไม่ได้ ลองใหม่อีกครั้งได้ไหม"
NAVIGATION_UNKNOWN_PLACE_REPLY = (
    "ตอนนี้ยังหาต้นทางหรือปลายทางนี้ไม่เจอ ลองระบุชื่อสถานที่ให้ชัดขึ้นอีกนิดได้ไหม"
)


@dataclass(frozen=True)
class PlaceResolution:
    query_text: str
    display_name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteSummary:
    origin: str
    destination: str
    distance_km: float
    duration_minutes: int
    summary: str


@dataclass(frozen=True)
class NavigationAnswer:
    reply: str
    source: Literal["navigation_api", "fallback"]
    data: RouteSummary | None = None
    error: str | None = None


@dataclass(frozen=True)
class CachedRoute:
    summary: RouteSummary
    expires_at: datetime


@dataclass(frozen=True)
class NavigationQuery:
    origin_text: str
    destination_text: str
    response_focus: Literal["duration", "distance", "route"]


_DEMO_PLACE_ALIASES: tuple[tuple[str, PlaceResolution], ...] = (
    (
        "กรุงเทพฯ",
        PlaceResolution(
            query_text="Bangkok, Thailand",
            display_name="กรุงเทพฯ",
            latitude=13.7563,
            longitude=100.5018,
        ),
    ),
    (
        "กรุงเทพมหานคร",
        PlaceResolution(
            query_text="Bangkok, Thailand",
            display_name="กรุงเทพฯ",
            latitude=13.7563,
            longitude=100.5018,
        ),
    ),
    (
        "กรุงเทพ",
        PlaceResolution(
            query_text="Bangkok, Thailand",
            display_name="กรุงเทพฯ",
            latitude=13.7563,
            longitude=100.5018,
        ),
    ),
    (
        "bangkok",
        PlaceResolution(
            query_text="Bangkok, Thailand",
            display_name="กรุงเทพฯ",
            latitude=13.7563,
            longitude=100.5018,
        ),
    ),
    (
        "bkk",
        PlaceResolution(
            query_text="Bangkok, Thailand",
            display_name="กรุงเทพฯ",
            latitude=13.7563,
            longitude=100.5018,
        ),
    ),
    (
        "รามัน",
        PlaceResolution(
            query_text="Raman, Yala, Thailand",
            display_name="รามัน",
            latitude=6.4786,
            longitude=101.4333,
        ),
    ),
    (
        "raman",
        PlaceResolution(
            query_text="Raman, Yala, Thailand",
            display_name="รามัน",
            latitude=6.4786,
            longitude=101.4333,
        ),
    ),
    (
        "ยะลา",
        PlaceResolution(
            query_text="Yala, Thailand",
            display_name="ยะลา",
            latitude=6.5413,
            longitude=101.2804,
        ),
    ),
    (
        "yala",
        PlaceResolution(
            query_text="Yala, Thailand",
            display_name="ยะลา",
            latitude=6.5413,
            longitude=101.2804,
        ),
    ),
    (
        "หาดใหญ่",
        PlaceResolution(
            query_text="Hat Yai, Songkhla, Thailand",
            display_name="หาดใหญ่",
            latitude=7.0084,
            longitude=100.4747,
        ),
    ),
    (
        "hat yai",
        PlaceResolution(
            query_text="Hat Yai, Songkhla, Thailand",
            display_name="หาดใหญ่",
            latitude=7.0084,
            longitude=100.4747,
        ),
    ),
    (
        "สนามบินหาดใหญ่",
        PlaceResolution(
            query_text="Hat Yai International Airport, Thailand",
            display_name="สนามบินหาดใหญ่",
            latitude=6.9338,
            longitude=100.3926,
        ),
    ),
    (
        "hat yai airport",
        PlaceResolution(
            query_text="Hat Yai International Airport, Thailand",
            display_name="สนามบินหาดใหญ่",
            latitude=6.9338,
            longitude=100.3926,
        ),
    ),
    (
        "สนามบิน",
        PlaceResolution(
            query_text="Hat Yai International Airport, Thailand",
            display_name="สนามบินหาดใหญ่",
            latitude=6.9338,
            longitude=100.3926,
        ),
    ),
    (
        "airport",
        PlaceResolution(
            query_text="Hat Yai International Airport, Thailand",
            display_name="สนามบินหาดใหญ่",
            latitude=6.9338,
            longitude=100.3926,
        ),
    ),
    (
        "โรงพยาบาลยะลา",
        PlaceResolution(
            query_text="Yala Hospital, Yala, Thailand",
            display_name="โรงพยาบาลยะลา",
            latitude=6.5439,
            longitude=101.2818,
        ),
    ),
    (
        "hospital",
        PlaceResolution(
            query_text="Yala Hospital, Yala, Thailand",
            display_name="โรงพยาบาลยะลา",
            latitude=6.5439,
            longitude=101.2818,
        ),
    ),
    (
        "โรงพยาบาล",
        PlaceResolution(
            query_text="Yala Hospital, Yala, Thailand",
            display_name="โรงพยาบาลยะลา",
            latitude=6.5439,
            longitude=101.2818,
        ),
    ),
    (
        "มหาลัย",
        PlaceResolution(
            query_text="Yala Rajabhat University, Yala, Thailand",
            display_name="มหาวิทยาลัยราชภัฏยะลา",
            latitude=6.5168,
            longitude=101.2714,
        ),
    ),
    (
        "university",
        PlaceResolution(
            query_text="Yala Rajabhat University, Yala, Thailand",
            display_name="มหาวิทยาลัยราชภัฏยะลา",
            latitude=6.5168,
            longitude=101.2714,
        ),
    ),
    (
        "มหาวิทยาลัย",
        PlaceResolution(
            query_text="Yala Rajabhat University, Yala, Thailand",
            display_name="มหาวิทยาลัยราชภัฏยะลา",
            latitude=6.5168,
            longitude=101.2714,
        ),
    ),
    (
        "ตลาด",
        PlaceResolution(
            query_text="Yala Fresh Market, Yala, Thailand",
            display_name="ตลาดยะลา",
            latitude=6.5407,
            longitude=101.2827,
        ),
    ),
    (
        "market",
        PlaceResolution(
            query_text="Yala Fresh Market, Yala, Thailand",
            display_name="ตลาดยะลา",
            latitude=6.5407,
            longitude=101.2827,
        ),
    ),
)


class NavigationService:
    """Resolve demo-friendly route questions with ORS primary and OSRM fallback."""

    _ORIGIN_DESTINATION_PATTERN = re.compile(
        r"จาก\s*(?P<origin>.+?)\s*ไป\s*(?P<destination>.+)",
        re.IGNORECASE,
    )
    _DESTINATION_PATTERNS = (
        re.compile(r"เส้นทางไป\s*(?P<destination>.+)", re.IGNORECASE),
        re.compile(r"เดินทางไป\s*(?P<destination>.+)", re.IGNORECASE),
        re.compile(r"ไป\s*(?P<destination>.+)", re.IGNORECASE),
        re.compile(r"how long to\s*(?P<destination>.+)", re.IGNORECASE),
        re.compile(r"route to\s*(?P<destination>.+)", re.IGNORECASE),
        re.compile(r"directions(?:\s+to)?\s*(?P<destination>.+)", re.IGNORECASE),
    )
    _DESTINATION_SUFFIX_PATTERN = re.compile(
        r"(ใช้เวลากี่นาที|กี่นาที|กี่กิโล|กี่กิโลเมตร|ทางไหนดี|เส้นทางไหนดี|ยังไงดี|ได้ไหม|ไหม|$)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._cache: dict[str, CachedRoute] = {}
        self._lock = Lock()

    def answer_navigation_query(self, message: str) -> NavigationAnswer:
        navigation_query = self.parse_message(message)
        if navigation_query is None:
            return NavigationAnswer(
                reply=NAVIGATION_UNKNOWN_PLACE_REPLY,
                source="fallback",
                error="unable to parse route query",
            )

        route_summary = self.get_route(navigation_query)
        if route_summary is None:
            estimated_route = self._estimate_route(navigation_query)
            if estimated_route is not None:
                return NavigationAnswer(
                    reply=estimated_route.summary,
                    source="fallback",
                    data=estimated_route,
                    error="provider unavailable, returned estimated route",
                )
            return NavigationAnswer(
                reply=NAVIGATION_FALLBACK_REPLY,
                source="fallback",
                error="route unavailable",
            )

        return NavigationAnswer(
            reply=route_summary.summary,
            source="navigation_api",
            data=route_summary,
        )

    def get_route(self, navigation_query: NavigationQuery) -> RouteSummary | None:
        cache_key = self._cache_key(navigation_query)
        cached_summary = self._get_cached(cache_key)
        if cached_summary is not None:
            log_timing(
                logger,
                self._settings,
                "navigation.cache",
                0.0,
                key=cache_key,
            )
            return cached_summary

        origin = self._resolve_place(navigation_query.origin_text)
        destination = self._resolve_place(navigation_query.destination_text)
        if origin is None or destination is None:
            logger.warning(
                "Navigation could not resolve places origin=%s destination=%s",
                navigation_query.origin_text,
                navigation_query.destination_text,
            )
            return None

        timer = start_timer()
        provider_used = "osrm"
        try:
            route_data = None
            if self._normalize_provider(self._settings.nav_provider) == "openrouteservice":
                route_data = self._fetch_openrouteservice_route(origin, destination)
                if route_data is not None:
                    provider_used = "openrouteservice"

            if route_data is None:
                route_data = self._fetch_osrm_route(origin, destination)
                if route_data is None:
                    return None

            route_summary = self._build_summary(
                navigation_query,
                origin.display_name,
                destination.display_name,
                route_data["distance_km"],
                route_data["duration_minutes"],
            )
        except Timeout:
            logger.warning("Navigation provider request timed out")
            return None
        except RequestException as exc:
            logger.warning("Navigation provider request failed: %s", self._format_request_error(exc))
            return None
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid navigation response: %s", exc.__class__.__name__)
            return None

        self._set_cached(cache_key, route_summary)
        log_timing(
            logger,
            self._settings,
            "navigation.fetch",
            timer.elapsed_ms,
            provider=provider_used,
            key=cache_key,
        )
        return route_summary

    def _estimate_route(self, navigation_query: NavigationQuery) -> RouteSummary | None:
        origin = self._resolve_place(navigation_query.origin_text)
        destination = self._resolve_place(navigation_query.destination_text)
        if origin is None or destination is None:
            return None

        straight_distance_km = self._haversine_km(
            origin.latitude,
            origin.longitude,
            destination.latitude,
            destination.longitude,
        )
        if straight_distance_km <= 0:
            estimated_distance_km = 1.0
            estimated_duration_minutes = 3
        else:
            estimated_distance_km = max(1.0, round(straight_distance_km * 1.28, 1))
            average_speed_kmh = 55.0 if estimated_distance_km >= 20 else 28.0
            estimated_duration_minutes = max(
                3,
                round((estimated_distance_km / average_speed_kmh) * 60),
            )

        summary = self._build_summary(
            navigation_query,
            origin.display_name,
            destination.display_name,
            estimated_distance_km,
            estimated_duration_minutes,
        )
        log_timing(
            logger,
            self._settings,
            "navigation.estimate",
            0.0,
            origin=origin.display_name,
            destination=destination.display_name,
        )
        return summary

    def _fetch_openrouteservice_route(
        self,
        origin: PlaceResolution,
        destination: PlaceResolution,
    ) -> dict[str, float | int] | None:
        if not self._settings.openrouteservice_api_key:
            return None

        response = self._session.post(
            OPENROUTESERVICE_DIRECTIONS_URL,
            headers={
                "Authorization": self._settings.openrouteservice_api_key,
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
            json={
                "coordinates": [
                    [origin.longitude, origin.latitude],
                    [destination.longitude, destination.latitude],
                ],
                "instructions": False,
            },
            timeout=self._settings.nav_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        routes = payload.get("routes") or []
        if not routes:
            return None
        summary = routes[0].get("summary") or {}
        return {
            "distance_km": round(float(summary["distance"]) / 1000, 1),
            "duration_minutes": max(1, round(float(summary["duration"]) / 60)),
        }

    def _fetch_osrm_route(
        self,
        origin: PlaceResolution,
        destination: PlaceResolution,
    ) -> dict[str, float | int] | None:
        response = self._session.get(
            (
                f"{OSRM_ROUTE_URL}/"
                f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
            ),
            params={"overview": "false"},
            timeout=self._settings.nav_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != "Ok":
            return None
        routes = payload.get("routes") or []
        if not routes:
            return None
        route = routes[0]
        return {
            "distance_km": round(float(route["distance"]) / 1000, 1),
            "duration_minutes": max(1, round(float(route["duration"]) / 60)),
        }

    def _resolve_place(self, place_text: str) -> PlaceResolution | None:
        matched_alias = self._resolve_demo_alias(place_text)
        if matched_alias is not None:
            return matched_alias
        return self._geocode_with_openrouteservice(place_text)

    def resolve_place_text(self, place_text: str) -> PlaceResolution | None:
        return self._resolve_place(place_text)

    def parse_message(self, message: str) -> NavigationQuery | None:
        return self._parse_query(message)

    def _resolve_demo_alias(self, place_text: str) -> PlaceResolution | None:
        normalized_text = _normalize(place_text)
        for alias, place in _DEMO_PLACE_ALIASES:
            if _normalize(alias) in normalized_text:
                return place
        return None

    def _geocode_with_openrouteservice(self, place_text: str) -> PlaceResolution | None:
        if not self._settings.openrouteservice_api_key:
            return None

        response = self._session.get(
            OPENROUTESERVICE_GEOCODE_URL,
            params={
                "api_key": self._settings.openrouteservice_api_key,
                "text": place_text,
                "size": 1,
                "lang": self._settings.nav_default_language,
            },
            timeout=self._settings.nav_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features") or []
        if not features:
            return None
        feature = features[0]
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            return None

        properties = feature.get("properties") or {}
        label = str(
            properties.get("label")
            or properties.get("name")
            or place_text
        ).strip()
        return PlaceResolution(
            query_text=place_text,
            display_name=self._simplify_display_name(label, place_text),
            latitude=float(coordinates[1]),
            longitude=float(coordinates[0]),
        )

    def _parse_query(self, message: str) -> NavigationQuery | None:
        stripped_message = message.strip()
        if not stripped_message:
            return None

        origin_match = self._ORIGIN_DESTINATION_PATTERN.search(stripped_message)
        if origin_match is not None:
            origin_text = self._clean_place_text(origin_match.group("origin"))
            destination_text = self._clean_place_text(origin_match.group("destination"))
            if origin_text and destination_text:
                return NavigationQuery(
                    origin_text=origin_text,
                    destination_text=destination_text,
                    response_focus=self._detect_focus(stripped_message),
                )

        for pattern in self._DESTINATION_PATTERNS:
            match = pattern.search(stripped_message)
            if match is None:
                continue
            destination_text = self._clean_place_text(match.group("destination"))
            if destination_text:
                return NavigationQuery(
                    origin_text=self._settings.nav_default_origin,
                    destination_text=destination_text,
                    response_focus=self._detect_focus(stripped_message),
                )

        follow_up_destination = self._extract_follow_up_destination(stripped_message)
        if follow_up_destination:
            return NavigationQuery(
                origin_text=self._settings.nav_default_origin,
                destination_text=follow_up_destination,
                response_focus=self._detect_focus(stripped_message),
            )
        return None

    def _clean_place_text(self, value: str) -> str:
        cleaned = value.strip(" ?!.")
        if not cleaned:
            return ""
        cleaned = self._DESTINATION_SUFFIX_PATTERN.split(cleaned, maxsplit=1)[0]
        cleaned = re.sub(r"\b(using|take|takes)\b.*$", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip(" ,?.!")

    @staticmethod
    def _detect_focus(message: str) -> Literal["duration", "distance", "route"]:
        normalized_message = _normalize(message)
        if "กี่กิโล" in normalized_message or "kilometer" in normalized_message or "distance" in normalized_message:
            return "distance"
        if "กี่นาที" in normalized_message or "howlong" in normalized_message or "eta" in normalized_message:
            return "duration"
        if "เส้นทาง" in normalized_message or "route" in normalized_message or "directions" in normalized_message:
            return "route"
        return "duration"

    def _extract_follow_up_destination(self, message: str) -> str | None:
        cleaned = message.strip(" ?!.")
        if not cleaned:
            return None

        normalized_message = _normalize(cleaned)
        if any(token in normalized_message for token in ("จาก", "ไป", "route", "directions", "howlongto")):
            return None

        candidate = re.sub(r"(ล่ะ|ละ|ไหม|ครับ|คะ|ค่ะ|หน่อย|ที|ด้วย)$", "", cleaned).strip()
        if not candidate:
            return None

        if self._resolve_demo_alias(candidate) is not None:
            return candidate
        return None

    def _build_summary(
        self,
        navigation_query: NavigationQuery,
        origin_name: str,
        destination_name: str,
        distance_km: float,
        duration_minutes: int,
    ) -> RouteSummary:
        distance_text = self._format_distance(distance_km)
        duration_text = self._format_duration(duration_minutes)

        if navigation_query.response_focus == "distance":
            summary_text = (
                f"จาก{origin_name}ไป{destination_name}ประมาณ {distance_text} "
                f"ใช้เวลาราว {duration_text}"
            )
        else:
            summary_text = (
                f"จาก{origin_name}ไป{destination_name}ประมาณ {duration_text} "
                f"ระยะทางราว {distance_text}"
            )

        return RouteSummary(
            origin=origin_name,
            destination=destination_name,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            summary=summary_text,
        )

    @staticmethod
    def _format_duration(duration_minutes: int) -> str:
        hours, minutes = divmod(duration_minutes, 60)
        if hours <= 0:
            return f"{minutes} นาที"
        if minutes == 0:
            return f"{hours} ชั่วโมง"
        return f"{hours} ชั่วโมง {minutes} นาที"

    @staticmethod
    def _format_distance(distance_km: float) -> str:
        rounded_distance = round(distance_km, 1)
        if abs(rounded_distance - round(rounded_distance)) < 0.05:
            return f"{int(round(rounded_distance))} กิโลเมตร"
        return f"{rounded_distance:.1f} กิโลเมตร"

    def _get_cached(self, cache_key: str) -> RouteSummary | None:
        with self._lock:
            cached_route = self._cache.get(cache_key)
            if cached_route is None:
                return None
            if cached_route.expires_at <= self._now():
                self._cache.pop(cache_key, None)
                return None
            return cached_route.summary

    def _set_cached(self, cache_key: str, route_summary: RouteSummary) -> None:
        with self._lock:
            self._cache[cache_key] = CachedRoute(
                summary=route_summary,
                expires_at=self._now() + timedelta(seconds=self._settings.nav_cache_ttl_seconds),
            )

    @staticmethod
    def _cache_key(navigation_query: NavigationQuery) -> str:
        return "|".join(
            (
                _normalize(navigation_query.origin_text),
                _normalize(navigation_query.destination_text),
                navigation_query.response_focus,
            )
        )

    @staticmethod
    def _simplify_display_name(label: str, fallback: str) -> str:
        first_segment = label.split(",", maxsplit=1)[0].strip()
        return first_segment or fallback.strip()

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        return provider.strip().casefold()

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

    @staticmethod
    def _haversine_km(
        latitude_a: float,
        longitude_a: float,
        latitude_b: float,
        longitude_b: float,
    ) -> float:
        radius_km = 6371.0
        lat_a = math.radians(latitude_a)
        lat_b = math.radians(latitude_b)
        delta_lat = math.radians(latitude_b - latitude_a)
        delta_lon = math.radians(longitude_b - longitude_a)

        haversine = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
        )
        arc = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
        return radius_km * arc


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


_navigation_service = NavigationService(settings=get_settings())


def get_navigation_service() -> NavigationService:
    return _navigation_service
