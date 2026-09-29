from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, build_opener


class RegistryApiError(RuntimeError):
    """The registry returned an invalid or non-successful API response."""


class RegistryUnavailableError(RegistryApiError):
    """The registry could not be reached after bounded retries."""


@dataclass(frozen=True)
class RegistryResponse:
    status_code: int
    payload: Any


class RegistryTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> RegistryResponse:
        raise NotImplementedError


def _is_local_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    return hostname.casefold() in {"localhost", "127.0.0.1", "::1"}


def _normalize_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("registry API URL must be an HTTP(S) URL with a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("registry API URL must not contain credentials or query parameters")
    if parsed.scheme != "https" and not _is_local_host(parsed.hostname):
        raise ValueError("non-local registry API URLs must use HTTPS")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


class _UrllibRegistryTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> RegistryResponse:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with build_opener().open(request, timeout=timeout_seconds) as response:
                raw = response.read()
                try:
                    decoded = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise RegistryApiError("registry returned malformed JSON") from error
                return RegistryResponse(response.status, decoded)
        except HTTPError as error:
            return RegistryResponse(error.code, None)
        except (OSError, URLError, TimeoutError) as error:
            raise RegistryUnavailableError("registry API could not be reached") from error


class RegistryClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str = "",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        transport: RegistryTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = _normalize_base_url(base_url)
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._transport = transport or _UrllibRegistryTransport()
        self._sleeper = sleeper

    def health(self, *, timeout_seconds: float | None = None) -> dict[str, Any]:
        payload = self._request("GET", "/healthz", timeout_seconds=timeout_seconds)
        if "status" not in payload or "db_ok" not in payload:
            raise RegistryApiError("registry health response has an invalid shape")
        if payload.get("status") != "ok":
            raise RegistryApiError("registry health check is not ok")
        if payload.get("db_ok") is not True:
            raise RegistryApiError("registry database is not ready")
        return payload

    def resolve(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._request("POST", "/resolve", payload=payload)
        required = {"target_sources", "companion_sources", "lineage", "warnings"}
        if not required.issubset(result) or any(not isinstance(result[key], list) for key in required):
            raise RegistryApiError("registry resolve response has an invalid shape")
        return result

    def get_source(self, slug: str) -> dict[str, Any]:
        if not slug.strip():
            raise ValueError("registry source slug is required")
        return self._request("GET", f"/sources/{quote(slug, safe='')}")

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        request_payload = None if payload is None else _clean_payload(payload)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        timeout = timeout_seconds or self._timeout_seconds
        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.request(
                    method,
                    f"{self._base_url}{path}",
                    payload=request_payload,
                    headers=headers,
                    timeout_seconds=timeout,
                )
            except (RegistryUnavailableError, OSError, TimeoutError) as error:
                if attempt < self._max_retries:
                    self._sleeper(2.0**attempt)
                    continue
                raise RegistryUnavailableError("registry API could not be reached") from error
            if response.status_code >= 500:
                if attempt < self._max_retries:
                    self._sleeper(2.0**attempt)
                    continue
                raise RegistryUnavailableError(
                    f"registry API returned HTTP {response.status_code}"
                )
            if response.status_code >= 400:
                raise RegistryApiError(f"registry API returned HTTP {response.status_code}")
            if not isinstance(response.payload, Mapping):
                raise RegistryApiError("registry response must be a JSON object")
            return dict(response.payload)
        raise RegistryUnavailableError("registry API request exhausted retries")


def _clean_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        if isinstance(value, str) and not value.strip() and key != "prompt":
            continue
        cleaned[key] = value
    return cleaned
