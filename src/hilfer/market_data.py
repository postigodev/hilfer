from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from hilfer.models import MarketDataRow

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
SOURCE = "Finnhub"
DEFAULT_CURRENCY = "USD"


class MarketDataError(ValueError):
    """Raised when a ticker quote cannot be fetched or parsed."""


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_finnhub_quote(ticker: str, payload: dict[str, Any], updated_at_utc: str, run_id: str) -> MarketDataRow:
    price = _required_positive_number(payload.get("c"), field_name="c")

    return MarketDataRow(
        ticker=ticker,
        name="",
        price=price,
        currency=DEFAULT_CURRENCY,
        change_day_pct=_optional_number(payload.get("dp")),
        previous_close=_optional_number(payload.get("pc")),
        market_time=_market_time_iso(payload.get("t")),
        updated_at_utc=updated_at_utc,
        source=SOURCE,
        status="OK",
        error="",
        provider_symbol=ticker,
        run_id=run_id,
    )


def error_row(ticker: str, error: str, updated_at_utc: str, run_id: str) -> MarketDataRow:
    return MarketDataRow(
        ticker=ticker,
        name="",
        price="",
        currency=DEFAULT_CURRENCY,
        change_day_pct="",
        previous_close="",
        market_time="",
        updated_at_utc=updated_at_utc,
        source=SOURCE,
        status="ERROR",
        error=error,
        provider_symbol=ticker,
        run_id=run_id,
    )


class FinnhubClient:
    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()

    def fetch_row(self, ticker: str, updated_at_utc: str, run_id: str) -> MarketDataRow:
        try:
            payload = self._fetch_payload(ticker)
            return parse_finnhub_quote(ticker=ticker, payload=payload, updated_at_utc=updated_at_utc, run_id=run_id)
        except Exception as exc:
            return error_row(ticker=ticker, error=str(exc), updated_at_utc=updated_at_utc, run_id=run_id)

    def _fetch_payload(self, ticker: str) -> dict[str, Any]:
        try:
            response = self._session.get(
                FINNHUB_QUOTE_URL,
                params={"symbol": ticker},
                headers={"X-Finnhub-Token": self._api_key},
                timeout=self._timeout_seconds,
            )
        except requests.Timeout as exc:
            raise MarketDataError(f"Finnhub request timed out for {ticker}.") from exc
        except requests.RequestException as exc:
            raise MarketDataError(f"Finnhub request failed for {ticker}: {exc}") from exc

        if not response.ok:
            reason = response.reason or "HTTP error"
            raise MarketDataError(f"Finnhub request failed for {ticker}: HTTP {response.status_code} {reason}.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise MarketDataError(f"Finnhub returned invalid JSON for {ticker}.") from exc

        if not isinstance(payload, dict):
            raise MarketDataError(f"Finnhub returned an invalid quote payload for {ticker}.")

        return payload


def _required_positive_number(value: Any, field_name: str) -> float:
    number = _to_number(value)
    if number is None:
        raise MarketDataError(f"Finnhub quote field {field_name} is missing or non-numeric.")
    if number <= 0:
        raise MarketDataError(f"Finnhub quote field {field_name} must be greater than 0.")
    return number


def _optional_number(value: Any) -> float | str:
    number = _to_number(value)
    return "" if number is None else number


def _to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _market_time_iso(value: Any) -> str:
    timestamp = _to_number(value)
    if timestamp is None or timestamp <= 0:
        return ""
    return datetime.fromtimestamp(timestamp, UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
