from __future__ import annotations

from typing import Any

import gspread

from hilfer.models import MARKET_DATA_HEADERS, MarketDataRow

OPERACIONES_SHEET = "Operaciones"
MARKET_DATA_SHEET = "Market_Data"
TICKER_HEADER = "Ticker"


class SpreadsheetContractError(ValueError):
    """Raised when the Google Sheet does not match Hilfer's expected contract."""


def normalize_tickers_from_rows(rows: list[list[str]]) -> list[str]:
    if not rows:
        raise SpreadsheetContractError("Operaciones sheet is empty; expected a Ticker header.")

    header_row_index, ticker_index = _find_ticker_header(rows)

    tickers: set[str] = set()
    for row in rows[header_row_index + 1 :]:
        if ticker_index >= len(row):
            continue
        ticker = row[ticker_index].strip().upper()
        if ticker:
            tickers.add(ticker)

    return sorted(tickers)


def _find_ticker_header(rows: list[list[str]]) -> tuple[int, int]:
    for row_index, row in enumerate(rows):
        headers = [header.strip() for header in row]
        try:
            return row_index, headers.index(TICKER_HEADER)
        except ValueError:
            continue

    raise SpreadsheetContractError("Operaciones sheet must contain a Ticker column.")


class GoogleSheetsClient:
    def __init__(self, service_account_info: dict[str, Any], spreadsheet_id: str) -> None:
        self._client = gspread.service_account_from_dict(service_account_info)
        self._spreadsheet = self._client.open_by_key(spreadsheet_id)

    def read_tickers(self) -> list[str]:
        worksheet = self._spreadsheet.worksheet(OPERACIONES_SHEET)
        rows = worksheet.get_all_values()
        return normalize_tickers_from_rows(rows)

    def replace_market_data(self, rows: list[MarketDataRow]) -> None:
        table: list[list[str | float]] = [MARKET_DATA_HEADERS]
        table.extend(row.to_sheet_row() for row in rows)

        worksheet = self._spreadsheet.worksheet(MARKET_DATA_SHEET)
        worksheet.clear()
        worksheet.update(values=table, range_name="A1")
