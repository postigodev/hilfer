from __future__ import annotations

from dataclasses import dataclass


MARKET_DATA_HEADERS = [
    "Ticker",
    "Price",
    "Currency",
    "Change_Day",
    "Change_Day_Pct",
    "Previous_Close",
    "Market_Time",
    "Updated_At_UTC",
    "Source",
    "Status",
    "Error",
]


@dataclass(frozen=True)
class MarketDataRow:
    ticker: str
    price: float | str
    currency: str
    change_day: float | str
    change_day_pct: float | str
    previous_close: float | str
    market_time: str
    updated_at_utc: str
    source: str
    status: str
    error: str

    def to_sheet_row(self) -> list[str | float]:
        return [
            self.ticker,
            self.price,
            self.currency,
            self.change_day,
            self.change_day_pct,
            self.previous_close,
            self.market_time,
            self.updated_at_utc,
            self.source,
            self.status,
            self.error,
        ]

