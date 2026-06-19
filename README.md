# Hilfer

Railway-compatible Python cron worker for refreshing market data in a Google Sheets investment ledger.

Hilfer reads tickers from a Hapi-based US stock/ETF portfolio ledger, fetches current quote data from Finnhub, and replaces the `Market_Data` worksheet with a clean machine-readable table for downstream analysis.

> [!IMPORTANT]
> Hilfer is intentionally narrow. It reads from `Operaciones`, writes only to `Market_Data`, preserves the worksheet itself, and exits after one run.

## Features

- Reads unique tickers from the `Operaciones` worksheet
- Detects the `Ticker` header even when the sheet has title or description rows above it
- Normalizes tickers by trimming whitespace and uppercasing
- Fetches US stock/ETF quote data from Finnhub
- Writes one `Market_Data` row per ticker with `OK` or `ERROR` status
- Builds the replacement table in memory before clearing `Market_Data`
- Uses Google service account authentication
- Runs once and exits for Railway cron jobs

## How It Works

```text
Google Sheets Operaciones
        |
        v
Read + normalize unique tickers
        |
        v
Finnhub /quote API
        |
        v
Replace Google Sheets Market_Data
```

The worker is safe by design: it never updates cells one by one across the ledger, and it never deletes or recreates worksheets.

## Spreadsheet Contract

Hilfer reads from the worksheet named `Operaciones`. That sheet must contain a column named exactly:

```text
Ticker
```

The header may appear below introductory title or description rows.

Hilfer replaces the contents of `Market_Data` with this exact header order:

```text
Ticker, Price, Currency, Change_Day, Change_Day_Pct, Previous_Close, Market_Time, Updated_At_UTC, Source, Status, Error
```

Rows with a valid Finnhub quote are written with `Status=OK`. Failed or invalid ticker lookups are still written as rows with `Status=ERROR` and an error message.

Hilfer must not mutate these worksheets:

- `Operaciones`
- `Movimientos_Dinero`
- `Tesis`
- `Portafolio`
- `Dashboard`
- `Snapshots`
- `Config`
- `Developer_Contract`

## Requirements

- Python 3.11+
- A Google Cloud service account with access to the target spreadsheet
- A Finnhub API key
- A Google Sheet with the expected worksheet names

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install Hilfer with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Create a local `.env` file:

```powershell
Copy-Item .env.example .env
```

Put your Google service account credentials at `./service_account.json`, then edit `.env`:

```env
FINNHUB_API_KEY=replace-with-your-finnhub-api-key
GOOGLE_SHEET_ID=replace-with-your-google-sheet-id
GOOGLE_SERVICE_ACCOUNT_PATH=./service_account.json
HTTP_TIMEOUT_SECONDS=10
```

Share the Google Sheet with the `client_email` from `service_account.json`.

Run the worker once:

```powershell
python -m hilfer.main
```

Or use the installed console script:

```powershell
hilfer
```

## Railway Deployment

Create a Railway service from this repository and configure it as a cron job.

Set these Railway environment variables:

```text
FINNHUB_API_KEY=...
GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_JSON=...
HTTP_TIMEOUT_SECONDS=10
```

For Railway, `GOOGLE_SERVICE_ACCOUNT_JSON` should contain the full service account JSON as a single environment variable value. Do not use `GOOGLE_SERVICE_ACCOUNT_PATH` unless you are also provisioning a credentials file in the runtime.

Use this start command:

```bash
python -m hilfer.main
```

The process logs progress, writes `Market_Data`, and exits.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `FINNHUB_API_KEY` | Yes | Finnhub API key. Sent via `X-Finnhub-Token` header. |
| `GOOGLE_SHEET_ID` | Yes | Target Google spreadsheet ID. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Either this or path | Full Google service account JSON string. Best for Railway. |
| `GOOGLE_SERVICE_ACCOUNT_PATH` | Either this or JSON | Path to a local service account JSON file. Best for local development. |
| `HTTP_TIMEOUT_SECONDS` | No | HTTP timeout for Finnhub calls. Defaults to `10`. |

> [!CAUTION]
> Never commit `.env`, `service_account.json`, exported ledgers, API keys, or Google credentials. The default `.gitignore` excludes the local credential files and `data/`.

## Market Data Mapping

Hilfer maps Finnhub quote fields into `Market_Data` as follows:

| Market_Data column | Finnhub field |
| --- | --- |
| `Price` | `c` |
| `Change_Day` | `d` |
| `Change_Day_Pct` | `dp` |
| `Previous_Close` | `pc` |
| `Market_Time` | `t` converted to UTC ISO timestamp |
| `Currency` | `USD` for v1 |
| `Source` | `Finnhub` |

A quote payload is treated as invalid when `c` is missing, null, non-numeric, or less than or equal to zero.

## Development

Run tests:

```powershell
python -m pytest
```

The test suite covers:

- Ticker normalization and deduplication
- Header detection below title rows
- Missing `Ticker` header errors
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
  market_data.py    Finnhub quote client and parsing
  models.py         Shared row models and headers
  main.py           Run-once cron worker entrypoint
tests/
  test_config.py
  test_google_sheets.py
  test_market_data.py
```
