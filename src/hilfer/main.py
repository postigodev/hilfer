from __future__ import annotations

import logging
import sys

from hilfer.config import ConfigError, load_settings
from hilfer.google_sheets import GoogleSheetsClient
from hilfer.market_data import FinnhubClient, utc_now_iso


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def run() -> int:
    logger = logging.getLogger("hilfer")

    try:
        settings = load_settings()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    logger.info(
        "Starting Hilfer market data refresh; google_sheet_id configured=%s, finnhub_api_key configured=%s",
        bool(settings.google_sheet_id),
        bool(settings.finnhub_api_key),
    )

    try:
        sheets = GoogleSheetsClient(
            service_account_info=settings.google_service_account_info,
            spreadsheet_id=settings.google_sheet_id,
        )
        tickers = sheets.read_tickers()
    except Exception:
        logger.exception("Failed to read tickers from Operaciones.")
        return 1

    logger.info("Read %s unique ticker(s) from Operaciones.", len(tickers))

    updated_at_utc = utc_now_iso()
    market_data = FinnhubClient(
        api_key=settings.finnhub_api_key,
        timeout_seconds=settings.http_timeout_seconds,
    )
    rows = [market_data.fetch_row(ticker, updated_at_utc=updated_at_utc) for ticker in tickers]

    for row in rows:
        if row.status == "ERROR":
            logger.warning("Ticker %s failed: %s", row.ticker, row.error)

    try:
        sheets.replace_market_data(rows)
    except Exception:
        logger.exception("Failed to replace Market_Data.")
        return 1

    ok_count = sum(1 for row in rows if row.status == "OK")
    error_count = len(rows) - ok_count
    logger.info("Finished Market_Data refresh: %s OK, %s ERROR.", ok_count, error_count)
    return 0


def main() -> None:
    configure_logging()
    sys.exit(run())


if __name__ == "__main__":
    main()

