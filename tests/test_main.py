from __future__ import annotations

from hilfer.main import run_id_from_updated_at


def test_run_id_from_updated_at() -> None:
    assert run_id_from_updated_at("2026-06-21T03:00:39Z") == "run-20260621T030039Z"
