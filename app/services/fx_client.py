import json
import time
from datetime import date
from pathlib import Path

import httpx

from app.config import (
    CACHE_TTL_SECONDS,
    DEFAULT_FROM,
    DEFAULT_TO,
    FRANKFURTER_BASE,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
    SAMPLE_FX_PATH,
)

_cache: dict[str, tuple[float, dict]] = {}


def _cache_key(start: date, end: date, from_currency: str, to_currency: str) -> str:
    return f"{from_currency}:{to_currency}:{start.isoformat()}:{end.isoformat()}"


def _read_from_cache(key: str) -> dict | None:
    entry = _cache.get(key)
    if not entry:
        return None
    expires_at, payload = entry
    if time.time() > expires_at:
        _cache.pop(key, None)
        return None
    return payload


def _write_to_cache(key: str, payload: dict) -> None:
    _cache[key] = (time.time() + CACHE_TTL_SECONDS, payload)


def _parse_rates_payload(payload: dict, to_currency: str) -> dict[date, float]:
    rates_block = payload.get("rates", {})
    daily: dict[date, float] = {}

    if not rates_block:
        raise ValueError("FX payload did not include any rates.")

    first_key = next(iter(rates_block))
    if isinstance(rates_block[first_key], dict):
        for day_str, quote_rates in rates_block.items():
            daily[date.fromisoformat(day_str)] = float(quote_rates[to_currency])
    else:
        day_str = payload.get("date") or payload.get("start_date")
        if not day_str:
            raise ValueError("FX payload missing date information.")
        daily[date.fromisoformat(day_str)] = float(rates_block[to_currency])

    return daily


def _load_sample_file() -> dict[date, float]:
    with Path(SAMPLE_FX_PATH).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return _parse_rates_payload(payload, DEFAULT_TO)


def _request_with_retry(url: str) -> dict:
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 404:
                raise httpx.HTTPStatusError(
                    "Not found", request=response.request, response=response
                )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS * (2**attempt))

    raise RuntimeError(f"Frankfurter request failed after retries: {last_error}")


def _build_urls(start: date, end: date, from_currency: str, to_currency: str) -> list[str]:
    start_str = start.isoformat()
    end_str = end.isoformat()

    if start == end:
        return [
            f"{FRANKFURTER_BASE}/latest?from={from_currency}&to={to_currency}",
            f"{FRANKFURTER_BASE}/v1/{start_str}?base={from_currency}&symbols={to_currency}",
        ]

    return [
        (
            f"{FRANKFURTER_BASE}/{start_str}..{end_str}"
            f"?from={from_currency}&to={to_currency}"
        ),
        (
            f"{FRANKFURTER_BASE}/v1/{start_str}..{end_str}"
            f"?base={from_currency}&symbols={to_currency}"
        ),
    ]


def fetch_rates(
    start: date,
    end: date,
    from_currency: str = DEFAULT_FROM,
    to_currency: str = DEFAULT_TO,
) -> tuple[dict[date, float], str]:
    if end < start:
        raise ValueError("End date must be on or after start date.")

    if (end - start).days > 366:
        raise ValueError("Date range cannot exceed one year.")

    cache_key = _cache_key(start, end, from_currency, to_currency)
    cached = _read_from_cache(cache_key)
    if cached:
        return _parse_rates_payload(cached, to_currency), "cache"

    urls = _build_urls(start, end, from_currency, to_currency)
    errors: list[str] = []

    for url in urls:
        try:
            payload = _request_with_retry(url)
            daily = _parse_rates_payload(payload, to_currency)
            daily = {
                day: rate for day, rate in daily.items() if start <= day <= end
            }

            if not daily:
                raise ValueError("No exchange rates returned for the requested range.")

            _write_to_cache(cache_key, payload)
            return daily, "live"
        except Exception as exc:  # noqa: BLE001 - collect and fall through
            errors.append(f"{url} -> {exc}")

    try:
        sample = _load_sample_file()
        filtered = {
            day: rate for day, rate in sample.items() if start <= day <= end
        }
        if not filtered:
            raise ValueError("Offline sample data does not cover requested dates.")
        return filtered, "offline_fallback"
    except Exception as fallback_exc:
        detail = "; ".join(errors)
        raise RuntimeError(
            f"Network and offline fallback both failed. {detail}; fallback: {fallback_exc}"
        ) from fallback_exc
