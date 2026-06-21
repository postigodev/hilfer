from __future__ import annotations

from dataclasses import dataclass


MARKET_DATA_HEADERS = [
    "Ticker",
    "Nombre",
    "Precio USD",
    "Moneda",
    "Cambio % día",
    "Prev Close",
    "Market Time",
    "Updated At",
    "Fuente",
    "Status",
    "Error",
    "Provider Symbol",
    "Run ID",
]

MARKET_DATA_TITLE = "Market_Data"
MARKET_DATA_CONTRACT_NOTE = (
    "Contrato para el script Railway. El script debe sobrescribir/actualizar esta hoja en batch; "
    "no debe tocar Portafolio."
)


@dataclass(frozen=True)
class MarketDataRow:
    ticker: str
    name: str
    price: float | str
    currency: str
    change_day_pct: float | str
    previous_close: float | str
    market_time: str
    updated_at_utc: str
    source: str
    status: str
    error: str
    provider_symbol: str
    run_id: str

    def to_sheet_row(self) -> list[str | float]:
        return [
            self.ticker,
            self.name,
            self.price,
            self.currency,
            self.change_day_pct,
            self.previous_close,
            self.market_time,
            self.updated_at_utc,
            self.source,
            self.status,
            self.error,
            self.provider_symbol,
            self.run_id,
        ]
