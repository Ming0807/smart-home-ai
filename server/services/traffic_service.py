from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Literal

import requests
from requests.exceptions import RequestException, Timeout

from server.config import Settings, get_settings
from server.services.navigation_service import (
    NavigationQuery,
    NavigationService,
    PlaceResolution,
    get_navigation_service,
)
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

TOMTOM_ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute"
TOMTOM_FLOW_SEGMENT_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute"
TRAFFIC_FALLBACK_REPLY = "ตอนนี้ยังเช็กข้อมูลการจราจรสดไม่ได้ ลองใหม่อีกครั้งได้ไหม"
AREA_TRAFFIC_LOCATION_ALIASES = (
    "กรุงเทพมหานคร",
    "กรุงเทพฯ",
    "กรุงเทพ",
    "bangkok",
    "bkk",
    "ยะลา",
    "รามัน",
    "หาดใหญ่",
    "สนามบินหาดใหญ่",
    "สนามบิน",
    "ตลาด",
    "โรงพยาบาล",
)


@dataclass(frozen=True)
class RouteTrafficData:
    origin: str
    destination: str
    distance_km: float
    travel_minutes: int
    no_traffic_minutes: int | None
    delay_minutes: int
    traffic_length_km: float | None


@dataclass(frozen=True)
class AreaTrafficData:
    location: str
    current_speed_kmh: int
    free_flow_speed_kmh: int
    confidence: float | None
    road_closure: bool


@dataclass(frozen=True)
class TrafficAnswer:
    reply: str
    source: Literal["traffic_api", "fallback"]
    error: str | None = None


@dataclass(frozen=True)
class CachedTrafficAnswer:
    answer: TrafficAnswer
    expires_at: datetime


class TrafficService:
    """Traffic-aware summaries powered by TomTom routing and flow APIs."""

    def __init__(
        self,
        settings: Settings,
        navigation_service: NavigationService,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._navigation_service = navigation_service
        self._session = session or requests.Session()
        self._cache: dict[str, CachedTrafficAnswer] = {}
        self._lock = Lock()

    def answer_traffic_query(self, message: str) -> TrafficAnswer:
        cache_key = self._cache_key(message)
        cached_answer = self._get_cached(cache_key)
        if cached_answer is not None:
            log_timing(logger, self._settings, "traffic.cache", 0.0, key=cache_key)
            return cached_answer

        if not self._settings.tomtom_api_key:
            logger.warning("TOMTOM_API_KEY is not configured")
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="tomtom api key missing",
            )

        if self._should_use_route_traffic(message):
            route_query = self._navigation_service.parse_message(message)
        else:
            route_query = None

        if route_query is not None:
            answer = self._answer_route_traffic(route_query)
        else:
            answer = self._answer_area_traffic(message)

        self._set_cached(cache_key, answer)
        return answer

    def _answer_route_traffic(self, route_query: NavigationQuery) -> TrafficAnswer:
        origin = self._navigation_service.resolve_place_text(route_query.origin_text)
        destination = self._navigation_service.resolve_place_text(route_query.destination_text)
        if origin is None or destination is None:
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="unable to resolve route places",
            )

        timer = start_timer()
        try:
            route_data = self._fetch_route_traffic(origin, destination)
        except Timeout:
            logger.warning("TomTom route traffic request timed out")
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="route traffic timeout",
            )
        except RequestException as exc:
            logger.warning("TomTom route traffic request failed: %s", self._format_request_error(exc))
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="route traffic request failed",
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid TomTom route traffic response: %s", exc.__class__.__name__)
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="invalid route traffic response",
            )

        log_timing(
            logger,
            self._settings,
            "traffic.route",
            timer.elapsed_ms,
            origin=route_data.origin,
            destination=route_data.destination,
            delay_minutes=route_data.delay_minutes,
        )
        return TrafficAnswer(
            reply=self._build_route_reply(route_data),
            source="traffic_api",
        )

    def _answer_area_traffic(self, message: str) -> TrafficAnswer:
        location_text = self._detect_location_text(message)
        place = self._navigation_service.resolve_place_text(location_text)
        if place is None:
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="unable to resolve area traffic location",
            )

        timer = start_timer()
        try:
            area_data = self._fetch_area_traffic(place)
        except Timeout:
            logger.warning("TomTom area traffic request timed out")
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="area traffic timeout",
            )
        except RequestException as exc:
            logger.warning("TomTom area traffic request failed: %s", self._format_request_error(exc))
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="area traffic request failed",
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid TomTom area traffic response: %s", exc.__class__.__name__)
            return TrafficAnswer(
                reply=TRAFFIC_FALLBACK_REPLY,
                source="fallback",
                error="invalid area traffic response",
            )

        log_timing(
            logger,
            self._settings,
            "traffic.area",
            timer.elapsed_ms,
            location=area_data.location,
            current_speed=area_data.current_speed_kmh,
            free_flow_speed=area_data.free_flow_speed_kmh,
        )
        return TrafficAnswer(
            reply=self._build_area_reply(area_data),
            source="traffic_api",
        )

    def _fetch_route_traffic(
        self,
        origin: PlaceResolution,
        destination: PlaceResolution,
    ) -> RouteTrafficData:
        response = self._session.get(
            (
                f"{TOMTOM_ROUTE_URL}/"
                f"{origin.latitude},{origin.longitude}:"
                f"{destination.latitude},{destination.longitude}/json"
            ),
            params={
                "key": self._settings.tomtom_api_key,
                "traffic": "true",
                "routeType": "fastest",
                "computeTravelTimeFor": "all",
                "instructionsType": "text",
                "language": "th-TH",
            },
            timeout=self._settings.traffic_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        routes = payload.get("routes") or []
        if not routes:
            raise ValueError("TomTom route response missing routes")

        summary = routes[0].get("summary") or {}
        travel_seconds = int(summary["travelTimeInSeconds"])
        no_traffic_seconds_raw = summary.get("noTrafficTravelTimeInSeconds")
        traffic_delay_seconds = int(summary.get("trafficDelayInSeconds") or 0)
        traffic_length_meters = summary.get("trafficLengthInMeters")
        return RouteTrafficData(
            origin=origin.display_name,
            destination=destination.display_name,
            distance_km=round(float(summary["lengthInMeters"]) / 1000, 1),
            travel_minutes=max(1, round(travel_seconds / 60)),
            no_traffic_minutes=(
                max(1, round(float(no_traffic_seconds_raw) / 60))
                if no_traffic_seconds_raw is not None
                else None
            ),
            delay_minutes=max(0, round(traffic_delay_seconds / 60)),
            traffic_length_km=(
                round(float(traffic_length_meters) / 1000, 1)
                if traffic_length_meters is not None
                else None
            ),
        )

    def _fetch_area_traffic(self, place: PlaceResolution) -> AreaTrafficData:
        response = self._session.get(
            f"{TOMTOM_FLOW_SEGMENT_URL}/{self._settings.traffic_flow_zoom}/json",
            params={
                "key": self._settings.tomtom_api_key,
                "point": f"{place.latitude},{place.longitude}",
                "unit": "kmph",
            },
            timeout=self._settings.traffic_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        flow_data = payload.get("flowSegmentData") or payload
        return AreaTrafficData(
            location=place.display_name,
            current_speed_kmh=int(flow_data["currentSpeed"]),
            free_flow_speed_kmh=int(flow_data["freeFlowSpeed"]),
            confidence=(
                float(flow_data["confidence"])
                if flow_data.get("confidence") is not None
                else None
            ),
            road_closure=bool(flow_data.get("roadClosure", False)),
        )

    def _build_route_reply(self, data: RouteTrafficData) -> str:
        traffic_state = self._classify_route_delay(data.delay_minutes, data.no_traffic_minutes)
        parts = [
            f"ตอนนี้จาก{data.origin}ไป{data.destination}ใช้เวลาประมาณ {self._format_minutes(data.travel_minutes)}",
            f"ระยะทางราว {self._format_distance(data.distance_km)}",
            traffic_state,
        ]
        if data.delay_minutes > 0:
            parts.append(f"ช้ากว่าช่วงรถโล่งประมาณ {self._format_minutes(data.delay_minutes)}")
        elif data.no_traffic_minutes is not None:
            parts.append("เวลาตอนนี้ใกล้เคียงช่วงรถโล่ง")
        if data.traffic_length_km:
            parts.append(f"ช่วงที่ได้รับผลจากการจราจรราว {self._format_distance(data.traffic_length_km)}")
        return " ".join(parts)

    def _build_area_reply(self, data: AreaTrafficData) -> str:
        traffic_state = self._classify_area_flow(data.current_speed_kmh, data.free_flow_speed_kmh)
        parts = [
            f"ตอนนี้ใน{data.location}การจราจร{traffic_state}",
            f"ความเร็วเฉลี่ยบนถนนหลักแถวนี้ประมาณ {data.current_speed_kmh} กม./ชม.",
        ]
        if data.free_flow_speed_kmh > 0:
            parts.append(f"เทียบกับช่วงรถโล่งที่ราว {data.free_flow_speed_kmh} กม./ชม.")
        if data.road_closure:
            parts.append("และมีสัญญาณว่ามีจุดปิดถนนใกล้เคียง")
        return " ".join(parts)

    def _detect_location_text(self, message: str) -> str:
        normalized_message = _normalize(message)
        for candidate in AREA_TRAFFIC_LOCATION_ALIASES:
            if _normalize(candidate) in normalized_message:
                return candidate
        return self._settings.traffic_default_location

    def _should_use_route_traffic(self, message: str) -> bool:
        normalized_message = _normalize(message)
        if normalized_message.startswith("ใน") and not any(
            token in normalized_message for token in ("จาก", "ไป")
        ):
            return False

        return any(
            token in normalized_message
            for token in (
                "จาก",
                "ไป",
                "สนามบิน",
                "ตลาด",
                "โรงพยาบาล",
                "มหาลัย",
                "มหาวิทยาลัย",
                "หาดใหญ่",
                "raman",
                "รามัน",
            )
        )

    @staticmethod
    def _classify_route_delay(delay_minutes: int, no_traffic_minutes: int | None) -> str:
        if delay_minutes >= 15:
            return "การจราจรค่อนข้างติด"
        if delay_minutes >= 5:
            return "การจราจรเริ่มหนาแน่น"
        if no_traffic_minutes is not None and no_traffic_minutes > 0:
            return "การจราจรยังค่อนข้างคล่อง"
        return "การจราจรยังปกติ"

    @staticmethod
    def _classify_area_flow(current_speed_kmh: int, free_flow_speed_kmh: int) -> str:
        if free_flow_speed_kmh <= 0:
            return "ยังประเมินได้ไม่ชัด"
        ratio = current_speed_kmh / free_flow_speed_kmh
        if ratio <= 0.55:
            return "ค่อนข้างติด"
        if ratio <= 0.75:
            return "เริ่มหนาแน่น"
        return "ยังค่อนข้างคล่อง"

    def _get_cached(self, cache_key: str) -> TrafficAnswer | None:
        with self._lock:
            cached_item = self._cache.get(cache_key)
            if cached_item is None:
                return None
            if cached_item.expires_at <= self._now():
                self._cache.pop(cache_key, None)
                return None
            return cached_item.answer

    def _set_cached(self, cache_key: str, answer: TrafficAnswer) -> None:
        with self._lock:
            self._cache[cache_key] = CachedTrafficAnswer(
                answer=answer,
                expires_at=self._now()
                + timedelta(seconds=self._settings.traffic_cache_ttl_seconds),
            )

    @staticmethod
    def _cache_key(message: str) -> str:
        return _normalize(message)

    @staticmethod
    def _format_request_error(exc: RequestException) -> str:
        response = exc.response
        if response is None:
            return exc.__class__.__name__
        body = response.text[:300].replace("\n", " ")
        return f"{exc.__class__.__name__} status={response.status_code} body={body}"

    @staticmethod
    def _format_minutes(total_minutes: int) -> str:
        hours, minutes = divmod(total_minutes, 60)
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

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


_traffic_service = TrafficService(
    settings=get_settings(),
    navigation_service=get_navigation_service(),
)


def get_traffic_service() -> TrafficService:
    return _traffic_service
