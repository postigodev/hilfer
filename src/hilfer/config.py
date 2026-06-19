from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    finnhub_api_key: str
    google_sheet_id: str
    google_service_account_info: dict[str, Any]
    http_timeout_seconds: float = 10.0


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


def load_settings(dotenv_path: str | Path | None = ".env") -> Settings:
    if dotenv_path is not None:
        load_dotenv(dotenv_path=dotenv_path, override=True)

    finnhub_api_key = _required_env("FINNHUB_API_KEY")
    google_sheet_id = _required_env("GOOGLE_SHEET_ID")
    service_account_info = _load_service_account_info()
    timeout_seconds = _load_timeout()

    return Settings(
        finnhub_api_key=finnhub_api_key,
        google_sheet_id=google_sheet_id,
        google_service_account_info=service_account_info,
        http_timeout_seconds=timeout_seconds,
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigError(f"{name} is required.")
    return value.strip()


def _load_service_account_info() -> dict[str, Any]:
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")

    if raw_json and raw_json.strip():
        return _parse_service_account_json(
            raw_json.strip(),
            source="GOOGLE_SERVICE_ACCOUNT_JSON",
        )

    if path and path.strip():
        service_account_path = Path(path.strip()).expanduser()
        try:
            raw_file = service_account_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"GOOGLE_SERVICE_ACCOUNT_PATH could not be read: {service_account_path}") from exc

        return _parse_service_account_json(
            raw_file,
            source="GOOGLE_SERVICE_ACCOUNT_PATH",
        )

    raise ConfigError("GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_PATH is required.")


def _parse_service_account_json(raw_json: str, source: str) -> dict[str, Any]:
    try:
        service_account_info = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{source} must contain valid JSON.") from exc

    if not isinstance(service_account_info, dict):
        raise ConfigError(f"{source} must decode to a JSON object.")

    return service_account_info


def _load_timeout() -> float:
    raw_timeout = os.getenv("HTTP_TIMEOUT_SECONDS", "10").strip()
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise ConfigError("HTTP_TIMEOUT_SECONDS must be numeric.") from exc

    if timeout <= 0:
        raise ConfigError("HTTP_TIMEOUT_SECONDS must be greater than 0.")

    return timeout
