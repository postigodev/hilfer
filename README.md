<p align="center">
  <img src="assets/hilfer.jpg" alt="Hilfer logo" width="180">
</p>

<h1 align="center">Hilfer</h1>

<p align="center">
  A run-once Python cron worker that refreshes Google Sheets market data for a personal US stock/ETF portfolio ledger.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-blue"></a>
  <img alt="Tests" src="https://img.shields.io/badge/tests-pytest-green">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-black">
</p>

## Overview

Hilfer is the market-data ingestion layer for a Hapi-based investment control system. It treats Google Sheets as the ledger, Finnhub as the quote provider, and scheduled infrastructure such as Railway Cron as the automation layer.

The current MVP has one job:

1. Read unique tickers from the operations ledger.
2. Fetch current US stock/ETF quote data from Finnhub.
3. Replace the `Market_Data` worksheet with a fresh table.
4. Exit.

> [!IMPORTANT]
> Hilfer is intentionally conservative. It writes only to `Market_Data`, preserves the worksheet itself, and never mutates the rest of the investment workbook.

## Why This Exists

Personal investment tracking often ends up split across brokerage exports, hand-maintained spreadsheets, and ad hoc analysis. Hilfer keeps the system simple and auditable:

- Google Sheets remains the source of truth for transactions and portfolio structure.
- The worker refreshes market data without touching thesis, dashboard, or portfolio formulas.
- ChatGPT Project sources or other analysis tools can consume the updated workbook without needing API credentials.

This repository is small on purpose: it is easier to review, deploy, and trust.

## Features

- Run-once cron worker designed for Railway.
- Google service account authentication.
- Batch-style read/write flow through `gspread`.
- Finnhub quote integration using `X-Finnhub-Token`.
- Per-ticker `OK` / `ERROR` rows.
- Invalid quote handling for missing, null, non-numeric, or non-positive prices.
- API keys and Google credentials kept out of logs and Git.
- English and Spanish/spanglish ledger compatibility for the source operations sheet.
- Focused pytest coverage for parsing, config, spreadsheet contracts, and error rows.

## Data Flow

```text
Google Sheets operations ledger
        |
        v
Read ticker column + normalize symbols
        |
        v
Finnhub /quote
        |
        v
Build replacement Market_Data table in memory
        |
        v
Clear + update Market_Data
```

## Spreadsheet Contract

Hilfer reads tickers from the first matching source worksheet:

| Language style | Worksheet name |
| --- | --- |
| Spanish | `Operaciones` |
| English | `Operations` |

The source worksheet must contain one of these ticker columns:

| Preferred | Also supported |
| --- | --- |
| `Ticker` | `Symbol` |

The header row may appear below title or description rows.

Hilfer writes only to:

```text
Market_Data
```

`Market_Data` is replaced with this exact header order:

```text
Ticker, Price, Currency, Change_Day, Change_Day_Pct, Previous_Close, Market_Time, Updated_At_UTC, Source, Status, Error
```

Rows with valid quote data are written with `Status=OK`. Failed or invalid tickers are still written with `Status=ERROR` and a concise error message.

Hilfer must not mutate:

- `Operaciones`
- `Operations`
- `Movimientos_Dinero`
- `Money_Movements`
- `Tesis`
- `Theses`
- `Portafolio`
- `Portfolio`
- `Dashboard`
- `Snapshots`
- `Config`
- `Developer_Contract`

## Market Data Mapping

| `Market_Data` column | Source |
| --- | --- |
| `Ticker` | Normalized ticker from the ledger |
| `Price` | Finnhub `c` |
| `Currency` | `USD` for v1 |
| `Change_Day` | Finnhub `d` |
| `Change_Day_Pct` | Finnhub `dp` |
| `Previous_Close` | Finnhub `pc` |
| `Market_Time` | Finnhub `t`, converted to UTC ISO timestamp |
| `Updated_At_UTC` | Worker execution timestamp |
| `Source` | `Finnhub` |
| `Status` | `OK` or `ERROR` |
| `Error` | Empty on success; concise message on failure |

## Requirements

- Python 3.11+
- Google Cloud service account with access to the target spreadsheet
- Finnhub API key
- Google Sheet matching the spreadsheet contract above

## Local Development

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the package with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Create a local `.env`:

```powershell
Copy-Item .env.example .env
```

Place your Google service account file at `./service_account.json`, then configure:

```env
FINNHUB_API_KEY=replace-with-your-finnhub-api-key
GOOGLE_SHEET_ID=replace-with-your-google-sheet-id
GOOGLE_SERVICE_ACCOUNT_PATH=./service_account.json
HTTP_TIMEOUT_SECONDS=10
```

Share the target Google Sheet with the `client_email` from `service_account.json`.

Run the worker:

```powershell
python -m hilfer.main
```

Or use the installed console script:

```powershell
hilfer
```

## Railway Deployment

Create a Railway service from this repository and configure it as a cron job.

Set the following environment variables:

```text
FINNHUB_API_KEY=...
GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_JSON=...
HTTP_TIMEOUT_SECONDS=10
```

Use this start command:

```bash
python -m hilfer.main
```

The repository also includes `railpack.json`, which sets the same command through Railpack's `deploy.startCommand` field so Railway can build the worker without framework auto-detection.

For Railway, prefer `GOOGLE_SERVICE_ACCOUNT_JSON` as a single environment variable containing the full service account JSON. `GOOGLE_SERVICE_ACCOUNT_PATH` is intended for local development unless you explicitly provision a credentials file in the runtime.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `FINNHUB_API_KEY` | Yes | Finnhub API key. Sent via `X-Finnhub-Token`. |
| `GOOGLE_SHEET_ID` | Yes | Target Google spreadsheet ID. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Either this or path | Full Google service account JSON string. Best for Railway. |
| `GOOGLE_SERVICE_ACCOUNT_PATH` | Either this or JSON | Local path to a service account JSON file. Best for development. |
| `HTTP_TIMEOUT_SECONDS` | No | HTTP timeout for Finnhub requests. Defaults to `10`. |

> [!CAUTION]
> Do not commit `.env`, `service_account.json`, exported ledgers, API keys, or Google credentials. The default `.gitignore` excludes the local credential files and `data/`.

## Development Workflow

Run tests:

```powershell
python -m pytest
```

The test suite covers:

- Ticker normalization and deduplication
- Header detection below title rows
- English and Spanish/spanglish spreadsheet aliases
- Missing ticker header errors
- Service account configuration loading
- Finnhub quote parsing
- Invalid quote handling
- Per-ticker error rows
- API key redaction in HTTP errors

## Project Structure

```text
src/hilfer/
  config.py         Environment and credential loading
  google_sheets.py  Google Sheets read/write contract
  market_data.py    Finnhub quote client and quote parsing
  models.py         Shared row models and headers
  main.py           Run-once cron worker entrypoint
tests/
  test_config.py
  test_google_sheets.py
  test_market_data.py
```

## Security Notes

- Finnhub credentials are sent in an HTTP header, not in query strings.
- HTTP errors are sanitized so API keys are not written to logs.
- The worker builds the full replacement table before clearing `Market_Data`.
- The worker does not delete or recreate worksheets.
- Configuration supports local file-based credentials and Railway-friendly JSON-string credentials.
