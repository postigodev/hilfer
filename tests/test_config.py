from __future__ import annotations

import json

import pytest

from hilfer.config import ConfigError, load_settings


def test_load_settings_accepts_service_account_path(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    service_account_path = tmp_path / "service_account.json"
    service_account_info = {
        "type": "service_account",
        "project_id": "hilfer-test",
        "client_email": "hilfer@example.iam.gserviceaccount.com",
    }
    service_account_path.write_text(json.dumps(service_account_info), encoding="utf-8")

    monkeypatch.setenv("FINNHUB_API_KEY", "test-finnhub-key")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_PATH", str(service_account_path))
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "7")

    settings = load_settings(dotenv_path=None)

    assert settings.finnhub_api_key == "test-finnhub-key"
    assert settings.google_sheet_id == "test-sheet-id"
    assert settings.google_service_account_info == service_account_info
    assert settings.http_timeout_seconds == 7


def test_load_settings_accepts_service_account_json(monkeypatch: pytest.MonkeyPatch) -> None:
    service_account_info = {
        "type": "service_account",
        "project_id": "hilfer-test",
        "client_email": "hilfer@example.iam.gserviceaccount.com",
    }

    monkeypatch.setenv("FINNHUB_API_KEY", "test-finnhub-key")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", json.dumps(service_account_info))
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_PATH", raising=False)

    settings = load_settings(dotenv_path=None)

    assert settings.google_service_account_info == service_account_info


def test_dotenv_values_override_stale_shell_values(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    service_account_info = {
        "type": "service_account",
        "project_id": "hilfer-test",
        "client_email": "hilfer@example.iam.gserviceaccount.com",
    }
    service_account_path = tmp_path / "service_account.json"
    service_account_path.write_text(json.dumps(service_account_info), encoding="utf-8")
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "FINNHUB_API_KEY=fresh-key",
                "GOOGLE_SHEET_ID=fresh-sheet-id",
                f"GOOGLE_SERVICE_ACCOUNT_PATH={service_account_path}",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINNHUB_API_KEY", "stale-key")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "stale-sheet-id")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_PATH", raising=False)

    settings = load_settings(dotenv_path=dotenv_path)

    assert settings.finnhub_api_key == "fresh-key"
    assert settings.google_sheet_id == "fresh-sheet-id"


def test_load_settings_requires_a_service_account_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINNHUB_API_KEY", "test-finnhub-key")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_PATH", "")

    with pytest.raises(ConfigError, match="GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_PATH"):
        load_settings(dotenv_path=None)
