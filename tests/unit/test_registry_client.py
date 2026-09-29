from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from forecasting_assistant.infrastructure.datasets.registry_client import (
    RegistryApiError,
    RegistryClient,
    RegistryResponse,
)


@dataclass
class FakeTransport:
    responses: list[Any]

    def __post_init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> RegistryResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "payload": payload,
                "headers": headers,
                "timeout_seconds": timeout_seconds,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def test_resolve_posts_explicit_registry_payload_without_empty_optional_values() -> None:
    transport = FakeTransport(
        [
            RegistryResponse(
                200,
                {
                    "target_sources": [],
                    "companion_sources": [],
                    "lineage": [],
                    "warnings": [],
                },
            )
        ]
    )
    client = RegistryClient("https://registry.example.com", transport=transport)

    client.resolve(
        {
            "prompt": "Forecast Bitcoin price",
            "target": None,
            "fields": [],
            "domains": [],
            "geo": None,
            "frequency": None,
            "min_relevance": 0.80,
            "min_companion_strength": 0.60,
            "max_dependency_depth": 2,
            "max_sources": 12,
            "include_pending": False,
        }
    )

    call = transport.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://registry.example.com/resolve"
    assert call["payload"] == {
        "prompt": "Forecast Bitcoin price",
        "min_relevance": 0.80,
        "min_companion_strength": 0.60,
        "max_dependency_depth": 2,
        "max_sources": 12,
        "include_pending": False,
    }


def test_health_requires_status_ok_and_db_ok() -> None:
    unhealthy = FakeTransport([RegistryResponse(200, {"status": "ok", "db_ok": False})])
    client = RegistryClient("https://registry.example.com", transport=unhealthy)

    with pytest.raises(RegistryApiError, match="database is not ready"):
        client.health()


def test_transient_failures_retry_but_client_errors_do_not() -> None:
    transport = FakeTransport(
        [
            TimeoutError("temporary timeout"),
            RegistryResponse(200, {"status": "ok", "db_ok": True}),
        ]
    )
    sleeps: list[float] = []
    client = RegistryClient(
        "https://registry.example.com",
        transport=transport,
        max_retries=1,
        sleeper=sleeps.append,
    )

    assert client.health() == {"status": "ok", "db_ok": True}
    assert len(transport.calls) == 2
    assert sleeps == [1.0]

    bad_request = FakeTransport([RegistryResponse(400, {"detail": "invalid request"})])
    client = RegistryClient("https://registry.example.com", transport=bad_request, max_retries=3)

    with pytest.raises(RegistryApiError, match="HTTP 400"):
        client.resolve({"prompt": "bad"})
    assert len(bad_request.calls) == 1


def test_malformed_json_and_response_shape_raise_registry_api_error() -> None:
    transport = FakeTransport([RegistryResponse(200, {"unexpected": []})])
    client = RegistryClient("https://registry.example.com", transport=transport)

    with pytest.raises(RegistryApiError, match="health response"):
        client.health()

    malformed = FakeTransport([RegistryResponse(200, "not an object")])
    client = RegistryClient("https://registry.example.com", transport=malformed)

    with pytest.raises(RegistryApiError, match="JSON object"):
        client.resolve({"prompt": "anything"})


def test_registry_api_key_is_sent_as_bearer_without_being_exposed_in_errors() -> None:
    secret = "registry-secret-value"
    transport = FakeTransport([RegistryResponse(401, {"detail": "unauthorized"})])
    client = RegistryClient(
        "https://registry.example.com",
        api_key=secret,
        transport=transport,
    )

    with pytest.raises(RegistryApiError) as error:
        client.health()

    assert transport.calls[0]["headers"]["Authorization"] == f"Bearer {secret}"
    assert secret not in str(error.value)
