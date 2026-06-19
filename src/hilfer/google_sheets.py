from __future__ import annotations

from typing import Any

import gspread

from hilfer.models import MARKET_DATA_HEADERS, MarketDataRow

SOURCE_SHEET_NAMES = ("Operaciones", "Operations")
MARKET_DATA_SHEET = "Market_Data"
TICKER_HEADERS = ("Ticker", "Symbol")


class SpreadsheetContractError(ValueError):
    """Raised when the Google Sheet does not match Hilfer's expected contract."""


def normalize_tickers_from_rows(rows: list[list[str]]) -> list[str]:
    if not rows:
        raise SpreadsheetContractError("Source operations sheet is empty; expected a Ticker or Symbol header.")

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
        for ticker_header in TICKER_HEADERS:
            try:
                return row_index, headers.index(ticker_header)
            except ValueError:
                continue

    accepted_headers = ", ".join(TICKER_HEADERS)
    raise SpreadsheetContractError(f"Source operations sheet must contain one of these columns: {accepted_headers}.")


class GoogleSheetsClient:
    def __init__(self, service_account_info: dict[str, Any], spreadsheet_id: str) -> None:
        self._client = gspread.service_account_from_dict(service_account_info)
        self._spreadsheet = self._client.open_by_key(spreadsheet_id)

    def read_tickers(self) -> list[str]:
        worksheet = self._worksheet_by_alias(SOURCE_SHEET_NAMES)
        rows = worksheet.get_all_values()
        return normalize_tickers_from_rows(rows)

    def replace_market_data(self, rows: list[MarketDataRow]) -> None:
        table: list[list[str | float]] = [MARKET_DATA_HEADERS]
        table.extend(row.to_sheet_row() for row in rows)

        worksheet = self._spreadsheet.worksheet(MARKET_DATA_SHEET)
        worksheet.clear()
        worksheet.update(values=table, range_name="A1")

    def _worksheet_by_alias(self, names: tuple[str, ...]) -> gspread.Worksheet:
        last_error: Exception | None = None
        for name in names:
            try:
                return self._spreadsheet.worksheet(name)
            except gspread.WorksheetNotFound as exc:
                last_error = exc

        accepted_names = ", ".join(names)
        raise SpreadsheetContractError(f"Spreadsheet must contain one of these source worksheets: {accepted_names}.") from last_error
