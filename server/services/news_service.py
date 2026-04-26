from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Literal

import requests
from requests.exceptions import RequestException, Timeout

from server.config import Settings, get_settings
from server.utils.observability import log_timing, start_timer

logger = logging.getLogger(__name__)

CURRENTS_LATEST_NEWS_URL = "https://api.currentsapi.services/v1/latest-news"
CURRENTS_SEARCH_URL = "https://api.currentsapi.services/v1/search"
NEWS_FALLBACK_REPLY = "ตอนนี้ยังดึงข่าวล่าสุดไม่ได้ ลองใหม่อีกครั้งได้ไหม"
NEWS_EMPTY_REPLY = "ตอนนี้ยังไม่พบข่าวที่ตรงกับคำถามนี้ ลองถามหัวข้ออื่นได้เลย"


@dataclass(frozen=True)
class NewsItem:
    title: str
    description: str
    url: str
    published: str
    source: str


@dataclass(frozen=True)
class NewsAnswer:
    reply: str
    source: Literal["currents_api", "fallback"]
    items: tuple[NewsItem, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class CachedNews:
    items: tuple[NewsItem, ...]
    expires_at: datetime


@dataclass(frozen=True)
class NewsQuery:
    category: str | None = None
    keywords: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class NewsRequestVariant:
    language: str | None
    country: str | None


@dataclass(frozen=True)
class RecentNewsState:
    items: tuple[NewsItem, ...]
    label: str
    updated_at: datetime


class NewsService:
    """Fetch and summarize news for concise Thai replies."""

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._cache: dict[str, CachedNews] = {}
        self._lock = Lock()
        self._recent_news: RecentNewsState | None = None

    def answer_news_query(self, message: str) -> NewsAnswer:
        news_query = self._build_query(message)
        items = self.get_news(news_query)
        if items is None:
            return NewsAnswer(
                reply=NEWS_FALLBACK_REPLY,
                source="fallback",
                error="news unavailable",
            )
        if not items:
            return NewsAnswer(
                reply=NEWS_EMPTY_REPLY,
                source="fallback",
                error="news not found",
            )
        self._store_recent_news(news_query, items)
        return NewsAnswer(
            reply=self._build_reply(news_query, items),
            source="currents_api",
            items=items,
        )

    def answer_news_detail_query(self, message: str) -> NewsAnswer:
        requested_index = self._extract_requested_index(message)
        if requested_index is None:
            return NewsAnswer(
                reply="ถ้าอยากฟังต่อ บอกได้เลยว่าเอาข้อไหน เช่น ข้อ 1 หรือ ข่าวข้อ 2",
                source="fallback",
                error="missing news index",
            )

        recent_news = self._get_recent_news()
        if recent_news is None:
            return NewsAnswer(
                reply="ยังไม่มีรายการข่าวล่าสุดให้อ่านต่อ ลองถามก่อนว่าวันนี้มีข่าวอะไรบ้าง",
                source="fallback",
                error="recent news unavailable",
            )

        if requested_index < 1 or requested_index > len(recent_news.items):
            return NewsAnswer(
                reply=(
                    f"ตอนนี้มีข่าวล่าสุดอยู่ {len(recent_news.items)} เรื่อง "
                    "ลองเลือกข้อที่อยู่ในรายการล่าสุดได้เลย"
                ),
                source="fallback",
                error="news index out of range",
            )

        item = recent_news.items[requested_index - 1]
        return NewsAnswer(
            reply=self._build_detail_reply(requested_index, item),
            source="currents_api",
            items=(item,),
        )

    def get_news(self, news_query: NewsQuery) -> tuple[NewsItem, ...] | None:
        cache_key = self._cache_key(news_query)
        cached_items = self._get_cached(cache_key)
        if cached_items is not None:
            log_timing(
                logger,
                self._settings,
                "news.cache",
                0.0,
                key=cache_key,
            )
            return cached_items

        if not self._settings.currents_api_key:
            logger.warning("CURRENTS_API_KEY is not configured")
            return None

        timer = start_timer()
        try:
            items = self._fetch_news_with_fallback(news_query)
        except Timeout:
            logger.warning("Currents API request timed out")
            return None
        except RequestException as exc:
            logger.warning("Currents API request failed: %s", self._format_request_error(exc))
            return None
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid Currents API response: %s", exc.__class__.__name__)
            return None

        self._set_cached(cache_key, items)
        log_timing(
            logger,
            self._settings,
            "news.fetch",
            timer.elapsed_ms,
            key=cache_key,
        )
        return items

    def _fetch_news_with_fallback(self, news_query: NewsQuery) -> tuple[NewsItem, ...]:
        last_items: tuple[NewsItem, ...] = ()
        for variant in self._build_request_variants():
            payload = self._fetch_news_payload(news_query, variant)
            items = self._normalize_items(payload)
            if items:
                return items
            last_items = items
        return last_items

    def _fetch_news_payload(
        self,
        news_query: NewsQuery,
        variant: NewsRequestVariant,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "apiKey": self._settings.currents_api_key,
            "page_number": 1,
            "page_size": self._settings.news_max_items,
        }
        if variant.language:
            params["language"] = variant.language
        if variant.country:
            params["country"] = variant.country

        endpoint = CURRENTS_LATEST_NEWS_URL
        if news_query.keywords:
            endpoint = CURRENTS_SEARCH_URL
            params["keywords"] = news_query.keywords
        if news_query.category:
            params["category"] = news_query.category

        response = self._session.get(
            endpoint,
            params=params,
            timeout=self._settings.news_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "ok":
            raise ValueError(f"unexpected currents status: {payload.get('status')}")
        return payload

    def _normalize_items(self, payload: dict[str, Any]) -> tuple[NewsItem, ...]:
        raw_items = payload.get("news") or []
        normalized_items: list[NewsItem] = []
        for item in raw_items[: self._settings.news_max_items]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url:
                continue

            normalized_items.append(
                NewsItem(
                    title=title,
                    description=str(item.get("description") or "").strip(),
                    url=url,
                    published=str(item.get("published") or "").strip(),
                    source=self._extract_source(item),
                )
            )
        return tuple(normalized_items)

    @staticmethod
    def _extract_source(item: dict[str, Any]) -> str:
        author = str(item.get("author") or "").strip()
        if author:
            return author
        return "Currents"

    def _build_query(self, message: str) -> NewsQuery:
        normalized_message = _normalize(message)
        if "ai" in normalized_message:
            return NewsQuery(
                keywords="AI",
                category="science_technology",
                label="ข่าว AI ล่าสุด",
            )
        if "เทคโนโลยี" in normalized_message or "technology" in normalized_message:
            return NewsQuery(
                category="science_technology",
                label="ข่าวเทคโนโลยีวันนี้",
            )
        return NewsQuery(label="ข่าวล่าสุดวันนี้")

    @staticmethod
    def _build_reply(news_query: NewsQuery, items: tuple[NewsItem, ...]) -> str:
        headline_count = min(len(items), 5)
        topic_label = news_query.label or "ข่าวล่าสุด"
        headline_summary = " | ".join(
            f"{index}. {item.title}"
            for index, item in enumerate(items[:headline_count], start=1)
        )
        return (
            f"{topic_label}ที่น่าสนใจมี {headline_count} เรื่อง: {headline_summary} "
            "ถ้าอยากฟังต่อ บอกได้เลยว่าเอาข้อไหน"
        )

    @staticmethod
    def _build_detail_reply(index: int, item: NewsItem) -> str:
        detail = item.description or "ตอนนี้มีข้อมูลย่อเท่านี้จากรายการข่าวล่าสุด"
        return (
            f"ข่าวข้อ {index}: {item.title} "
            f"{detail} แหล่งข่าว {item.source}"
        )

    def _build_request_variants(self) -> tuple[NewsRequestVariant, ...]:
        default_language = self._clean_optional(self._settings.news_default_language)
        default_country = self._clean_optional(self._settings.news_default_country)
        variants = (
            NewsRequestVariant(language=default_language, country=default_country),
            NewsRequestVariant(language=default_language, country=None),
            NewsRequestVariant(language=None, country=default_country),
            NewsRequestVariant(language=None, country=None),
        )

        unique_variants: list[NewsRequestVariant] = []
        for variant in variants:
            if variant not in unique_variants:
                unique_variants.append(variant)
        return tuple(unique_variants)

    def _get_cached(self, cache_key: str) -> tuple[NewsItem, ...] | None:
        with self._lock:
            cached_news = self._cache.get(cache_key)
            if cached_news is None:
                return None
            if cached_news.expires_at <= self._now():
                self._cache.pop(cache_key, None)
                return None
            return cached_news.items

    def _set_cached(self, cache_key: str, items: tuple[NewsItem, ...]) -> None:
        with self._lock:
            self._cache[cache_key] = CachedNews(
                items=items,
                expires_at=self._now()
                + timedelta(seconds=self._settings.news_cache_ttl_seconds),
            )

    def _cache_key(self, news_query: NewsQuery) -> str:
        return "|".join(
            (
                _normalize(news_query.category or ""),
                _normalize(news_query.keywords or ""),
                _normalize(self._settings.news_default_language),
                _normalize(self._settings.news_default_country),
                str(self._settings.news_max_items),
            )
        )

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
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _store_recent_news(
        self,
        news_query: NewsQuery,
        items: tuple[NewsItem, ...],
    ) -> None:
        with self._lock:
            self._recent_news = RecentNewsState(
                items=items,
                label=news_query.label or "ข่าวล่าสุด",
                updated_at=self._now(),
            )

    def _get_recent_news(self) -> RecentNewsState | None:
        with self._lock:
            recent_news = self._recent_news
        if recent_news is None:
            return None
        age_seconds = (self._now() - recent_news.updated_at).total_seconds()
        if age_seconds > self._settings.news_cache_ttl_seconds:
            return None
        return recent_news

    @staticmethod
    def _extract_requested_index(message: str) -> int | None:
        match = re.search(r"ข้อ\s*([1-9])", message.casefold())
        if match is None:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None


def _normalize(text: str) -> str:
    return "".join(text.casefold().split())


_news_service = NewsService(settings=get_settings())


def get_news_service() -> NewsService:
    return _news_service
