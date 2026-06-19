from __future__ import annotations

import pytest

from hilfer.google_sheets import SpreadsheetContractError, normalize_tickers_from_rows


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


def test_missing_ticker_header_raises_clear_error() -> None:
    rows = [["Date", "Symbol"], ["2026-01-01", "AAPL"]]

    with pytest.raises(SpreadsheetContractError, match="Ticker column"):
        normalize_tickers_from_rows(rows)
