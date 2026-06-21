from __future__ import annotations

import pytest
import gspread

from hilfer.models import MARKET_DATA_CONTRACT_NOTE, MARKET_DATA_HEADERS, MARKET_DATA_TITLE, MarketDataRow
from hilfer.google_sheets import GoogleSheetsClient, SpreadsheetContractError, normalize_tickers_from_rows


def test_normalize_tickers_ignores_blanks_uppercases_dedupes_and_sorts() -> None:
    rows = [
        ["Date", "Ticker", "Qty"],
        ["2026-01-01", " aapl ", "1"],
        ["2026-01-02", "", "2"],
        ["2026-01-03", "MSFT", "3"],
        ["2026-01-04", "aapl", "4"],
        ["2026-01-05"],
    ]

    assert normalize_tickers_from_rows(rows) == ["AAPL", "MSFT"]


def test_normalize_tickers_finds_header_below_title_rows() -> None:
    rows = [
        ["Operaciones"],
        ["Ledger de compras, ventas y eventos dentro de Hapi."],
        ["ID operación", "Fecha", "Broker", "Tipo", "Ticker"],
        ["OP-0001", "2026-06-17", "Hapi", "Compra", " vug "],
        ["OP-0002", "2026-06-17", "Hapi", "Compra", "SCHB"],
    ]

    assert normalize_tickers_from_rows(rows) == ["SCHB", "VUG"]


def test_normalize_tickers_accepts_english_symbol_header() -> None:
    rows = [
        ["Operations"],
        ["Trade ledger for the portfolio."],
        ["Operation ID", "Date", "Broker", "Type", "Symbol"],
        ["OP-0001", "2026-06-17", "Hapi", "Buy", " vug "],
        ["OP-0002", "2026-06-17", "Hapi", "Buy", "SCHB"],
    ]

    assert normalize_tickers_from_rows(rows) == ["SCHB", "VUG"]


def test_missing_ticker_header_raises_clear_error() -> None:
    rows = [["Date", "Asset"], ["2026-01-01", "AAPL"]]

    with pytest.raises(SpreadsheetContractError, match="Ticker, Symbol"):
        normalize_tickers_from_rows(rows)


class FakeWorksheet:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows
        self.row_count = 25
        self.batch_clear_ranges: list[list[str]] = []
        self.updated_values: list[list[str | float]] | None = None
        self.updated_range: str | None = None
        self.clear_called = False

    def get_all_values(self) -> list[list[str]]:
        return self._rows

    def clear(self) -> None:
        self.clear_called = True

    def batch_clear(self, ranges: list[str]) -> None:
        self.batch_clear_ranges.append(ranges)

    def update(self, values: list[list[str | float]], range_name: str) -> None:
        self.updated_values = values
        self.updated_range = range_name


class FakeSpreadsheet:
    def __init__(self) -> None:
        self.requested_names: list[str] = []
        self.market_data_worksheet = FakeWorksheet([])

    def worksheet(self, name: str) -> FakeWorksheet:
        self.requested_names.append(name)
        if name == "Operaciones":
            raise gspread.WorksheetNotFound("missing")
        if name == "Operations":
            return FakeWorksheet(
                [
                    ["Operations"],
                    ["Operation ID", "Symbol"],
                    ["OP-0001", "SCHB"],
                    ["OP-0002", "VUG"],
                ]
            )
        if name == "Market_Data":
            return self.market_data_worksheet
        raise AssertionError(f"Unexpected worksheet request: {name}")


def test_google_sheets_client_falls_back_to_english_operations_sheet() -> None:
    spreadsheet = FakeSpreadsheet()
    client = GoogleSheetsClient.__new__(GoogleSheetsClient)
    client._spreadsheet = spreadsheet

    assert client.read_tickers() == ["SCHB", "VUG"]
    assert spreadsheet.requested_names == ["Operaciones", "Operations"]


def test_replace_market_data_writes_actual_sheet_contract_without_whole_sheet_clear() -> None:
    spreadsheet = FakeSpreadsheet()
    client = GoogleSheetsClient.__new__(GoogleSheetsClient)
    client._spreadsheet = spreadsheet
    row = MarketDataRow(
        ticker="VUG",
        name="",
        price=86.98,
        currency="USD",
        change_day_pct=1.6003,
        previous_close=85.61,
        market_time="2026-06-18T20:00:00Z",
        updated_at_utc="2026-06-21T03:00:39Z",
        source="Finnhub",
        status="OK",
        error="",
        provider_symbol="VUG",
        run_id="run-20260621T030039Z",
    )

    client.replace_market_data([row])

    worksheet = spreadsheet.market_data_worksheet
    assert worksheet.clear_called is False
    assert worksheet.batch_clear_ranges == [["A1:M25"]]
    assert worksheet.updated_range == "A1"
    assert worksheet.updated_values == [
        [MARKET_DATA_TITLE, "", "", "", "", "", "", "", "", "", "", "", ""],
        [MARKET_DATA_CONTRACT_NOTE, "", "", "", "", "", "", "", "", "", "", "", ""],
        MARKET_DATA_HEADERS,
        [
            "VUG",
            "",
            86.98,
            "USD",
            1.6003,
            85.61,
            "2026-06-18T20:00:00Z",
            "2026-06-21T03:00:39Z",
            "Finnhub",
            "OK",
            "",
            "VUG",
            "run-20260621T030039Z",
        ],
    ]
