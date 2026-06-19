from __future__ import annotations

import pytest
import gspread

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

    def get_all_values(self) -> list[list[str]]:
        return self._rows


class FakeSpreadsheet:
    def __init__(self) -> None:
        self.requested_names: list[str] = []

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
        raise AssertionError(f"Unexpected worksheet request: {name}")


def test_google_sheets_client_falls_back_to_english_operations_sheet() -> None:
    spreadsheet = FakeSpreadsheet()
    client = GoogleSheetsClient.__new__(GoogleSheetsClient)
    client._spreadsheet = spreadsheet

    assert client.read_tickers() == ["SCHB", "VUG"]
    assert spreadsheet.requested_names == ["Operaciones", "Operations"]
