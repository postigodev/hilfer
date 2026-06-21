from __future__ import annotations

import pytest

from hilfer.models import MARKET_DATA_HEADERS
from hilfer.market_data import FinnhubClient, error_row, parse_finnhub_quote


def test_parse_finnhub_quote_maps_successful_payload() -> None:
    row = parse_finnhub_quote(
        ticker="AAPL",
        payload={"c": 200.5, "d": 1.25, "dp": 0.63, "pc": 199.25, "t": 1_735_689_600},
        updated_at_utc="2026-06-19T00:00:00Z",
        run_id="run-20260619T000000Z",
    )

    assert row.ticker == "AAPL"
    assert row.name == ""
    assert row.price == 200.5
    assert row.currency == "USD"
    assert row.change_day_pct == 0.63
    assert row.previous_close == 199.25
    assert row.market_time == "2025-01-01T00:00:00Z"
    assert row.updated_at_utc == "2026-06-19T00:00:00Z"
    assert row.source == "Finnhub"
    assert row.status == "OK"
    assert row.error == ""
    assert row.provider_symbol == "AAPL"
    assert row.run_id == "run-20260619T000000Z"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"d": 1.25, "dp": 0.63, "pc": 199.25, "t": 1_735_689_600}, "c"),
        ({"c": None, "d": 0, "dp": 0, "pc": 199.25, "t": 1_735_689_600}, "c"),
        ({"c": "not-a-number", "d": 0, "dp": 0, "pc": 199.25, "t": 1_735_689_600}, "c"),
        ({"c": 0, "d": 0, "dp": 0, "pc": 199.25, "t": 1_735_689_600}, "greater than 0"),
        ({"c": -1, "d": 0, "dp": 0, "pc": 199.25, "t": 1_735_689_600}, "greater than 0"),
    ],
)
def test_invalid_quote_current_price_raises(payload: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_finnhub_quote(
            ticker="AAPL",
            payload=payload,
            updated_at_utc="2026-06-19T00:00:00Z",
            run_id="run-20260619T000000Z",
        )


def test_per_ticker_error_row_shape() -> None:
    row = error_row("BAD", "Finnhub failed", "2026-06-19T00:00:00Z", "run-20260619T000000Z")

    assert row.to_sheet_row() == [
        "BAD",
        "",
        "",
        "USD",
        "",
        "",
        "",
        "2026-06-19T00:00:00Z",
        "Finnhub",
        "ERROR",
        "Finnhub failed",
        "BAD",
        "run-20260619T000000Z",
    ]
    assert len(row.to_sheet_row()) == len(MARKET_DATA_HEADERS)


class FakeResponse:
    ok = False
    status_code = 401
    reason = "Unauthorized"


def test_finnhub_http_error_does_not_include_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FinnhubClient(api_key="secret-token", timeout_seconds=10)

    def fake_get(*args: object, **kwargs: object) -> FakeResponse:
        assert kwargs["params"] == {"symbol": "SCHB"}
        assert kwargs["headers"] == {"X-Finnhub-Token": "secret-token"}
        return FakeResponse()

    monkeypatch.setattr(client._session, "get", fake_get)

    row = client.fetch_row("SCHB", updated_at_utc="2026-06-19T00:00:00Z", run_id="run-20260619T000000Z")

    assert row.status == "ERROR"
    assert "HTTP 401 Unauthorized" in row.error
    assert "secret-token" not in row.error
