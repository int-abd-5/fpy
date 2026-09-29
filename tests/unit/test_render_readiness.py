from __future__ import annotations

import json
from http import HTTPStatus

import pytest

from forecasting_assistant.config import Settings
from forecasting_assistant.infrastructure.datasets.adapters import LocalUploadAdapter
from forecasting_assistant.infrastructure.datasets.registry_client import RegistryUnavailableError
from forecasting_assistant.interfaces import cli, web


class HealthyRegistryClient:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def health(self, *, timeout_seconds: float | None = None) -> dict[str, object]:
        return {"status": "ok", "db_ok": True}


class UnavailableRegistryClient(HealthyRegistryClient):
    def health(self, *, timeout_seconds: float | None = None) -> dict[str, object]:
        raise RegistryUnavailableError("registry API could not be reached")


def _settings(tmp_path, **overrides) -> Settings:
    return Settings(
        _env_file=None,
        openai_api_key="openai-secret",
        registry_api_key="registry-secret",
        elicitation_db_path=str(tmp_path / "dialogue.db"),
        elicitation_log_path=str(tmp_path / "logs" / "pipeline.jsonl"),
        dataset_store_path=str(tmp_path / "datasets"),
        **overrides,
    )


def test_cli_dataset_service_passes_settings_to_adapter_factory(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path, registry_api_url="https://registry.example.com")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    def fake_factory(http, *, settings):
        captured["settings"] = settings
        return [LocalUploadAdapter()]

    monkeypatch.setattr(cli, "build_default_adapters", fake_factory)

    service, _ = cli.build_dataset_service()

    assert service is not None
    assert captured["settings"] is settings


def test_web_dashboard_uses_registry_configured_adapters(monkeypatch, tmp_path) -> None:
    settings = _settings(tmp_path, registry_api_url="https://registry.example.com")
    captured: dict[str, object] = {}
    monkeypatch.setattr(web, "get_settings", lambda: settings)
    monkeypatch.setattr(web, "RegistryClient", HealthyRegistryClient)

    def fake_factory(http, *, settings):
        captured["settings"] = settings
        return [LocalUploadAdapter()]

    monkeypatch.setattr(web, "build_default_adapters", fake_factory)

    server = web.DashboardServer("127.0.0.1", 0)
    try:
        assert captured["settings"] is settings
        assert server.registry_client is not None
    finally:
        server.server.server_close()


def test_healthz_reports_app_and_registry_status_without_secrets(monkeypatch, tmp_path) -> None:
    settings = _settings(
        tmp_path,
        registry_api_url="https://registry.example.com",
        registry_required=True,
    )
    monkeypatch.setattr(web, "get_settings", lambda: settings)
    monkeypatch.setattr(web, "RegistryClient", HealthyRegistryClient)
    monkeypatch.setattr(web, "build_default_adapters", lambda http, *, settings: [LocalUploadAdapter()])

    server = web.DashboardServer("127.0.0.1", 0)
    try:
        payload, status = server.health_payload()
    finally:
        server.server.server_close()

    assert status == HTTPStatus.OK
    assert payload["status"] == "ok"
    assert payload["registry"] == {
        "configured": True,
        "required": True,
        "status": "ok",
    }
    assert "openai-secret" not in json.dumps(payload)
    assert "registry-secret" not in json.dumps(payload)


def test_required_registry_failure_returns_service_unavailable(monkeypatch, tmp_path) -> None:
    settings = _settings(
        tmp_path,
        registry_api_url="https://registry.example.com",
        registry_required=True,
    )
    monkeypatch.setattr(web, "get_settings", lambda: settings)
    monkeypatch.setattr(web, "RegistryClient", UnavailableRegistryClient)
    monkeypatch.setattr(web, "build_default_adapters", lambda http, *, settings: [LocalUploadAdapter()])

    server = web.DashboardServer("127.0.0.1", 0)
    try:
        payload, status = server.health_payload()
    finally:
        server.server.server_close()

    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert payload["status"] == "unavailable"
    assert payload["registry"]["status"] == "unavailable"


def test_web_server_start_command_accepts_render_host_and_port(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "9100")
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        cli,
        "run_web_server",
        lambda **kwargs: calls.append(kwargs),
        raising=False,
    )

    # The command imports the runner from the web module at call time.
    monkeypatch.setattr(web, "run_web_server", lambda **kwargs: calls.append(kwargs))
    cli.web(host=None, port=None, open_browser=False)

    assert calls == [{"host": "127.0.0.1", "port": 9100, "open_browser": False}]
