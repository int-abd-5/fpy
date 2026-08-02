from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Callable, Iterable
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from forecasting_assistant.domain.datasets import FetchResult


class UnsafeDatasetUrlError(ValueError):
    pass


class DatasetDownloadError(RuntimeError):
    pass


_CREDENTIAL_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "signature",
    "token",
    "x-amz-credential",
    "x-amz-signature",
}
_EXECUTABLE_SUFFIXES = {
    ".app",
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".dmg",
    ".exe",
    ".jar",
    ".msi",
    ".ps1",
    ".scr",
    ".sh",
}
_EXECUTABLE_CONTENT_TYPES = {
    "application/java-archive",
    "application/vnd.microsoft.portable-executable",
    "application/x-dosexec",
    "application/x-executable",
    "application/x-msdownload",
    "application/x-sh",
}


def _default_resolver(host: str, port: int) -> Iterable[str]:
    return {
        str(item[4][0])
        for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    }


def validate_public_https_url(
    url: str,
    *,
    resolver: Callable[[str, int], Iterable[str]] = _default_resolver,
) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise UnsafeDatasetUrlError("dataset URLs must use HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeDatasetUrlError("dataset URL has an invalid or credential-bearing authority")
    if any(key.casefold() in _CREDENTIAL_KEYS for key, _ in parse_qsl(parsed.query)):
        raise UnsafeDatasetUrlError("credentials must not be embedded in a dataset URL")
    lowered_path = parsed.path.casefold()
    if any(lowered_path.endswith(suffix) for suffix in _EXECUTABLE_SUFFIXES):
        raise UnsafeDatasetUrlError("executable dataset downloads are prohibited")
    try:
        addresses = list(resolver(parsed.hostname, parsed.port or 443))
    except OSError as error:
        raise UnsafeDatasetUrlError("dataset hostname could not be safely resolved") from error
    if not addresses:
        raise UnsafeDatasetUrlError("dataset hostname did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise UnsafeDatasetUrlError("dataset URLs must not resolve to private networks")


class _ValidatedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, validator: Callable[[str], None], max_redirects: int) -> None:
        super().__init__()
        self._validator = validator
        self._max_redirects = max_redirects
        self._redirects = 0

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        self._redirects += 1
        if self._redirects > self._max_redirects:
            raise DatasetDownloadError("dataset download exceeded the redirect limit")
        resolved = urljoin(req.full_url, newurl)
        self._validator(resolved)
        return super().redirect_request(req, fp, code, msg, headers, resolved)


class SecureHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20,
        max_bytes: int = 50 * 1024 * 1024,
        max_redirects: int = 3,
        resolver: Callable[[str, int], Iterable[str]] = _default_resolver,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects
        self._resolver = resolver

    def _validate(self, url: str) -> None:
        validate_public_https_url(url, resolver=self._resolver)

    def get_bytes(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResult:
        self._validate(url)
        request_headers = {"User-Agent": "forecasting-dataset-planner/0.1"}
        if headers:
            request_headers.update(headers)
        request = Request(url, headers=request_headers, method="GET")
        redirect_handler = _ValidatedRedirectHandler(self._validate, self._max_redirects)
        opener = build_opener(redirect_handler)
        try:
            with opener.open(request, timeout=self._timeout_seconds) as response:
                content_type = response.headers.get_content_type()
                if content_type.casefold() in _EXECUTABLE_CONTENT_TYPES:
                    raise DatasetDownloadError("executable response content is prohibited")
                declared_length = response.headers.get("content-length")
                if declared_length and int(declared_length) > self._max_bytes:
                    raise DatasetDownloadError("dataset exceeds the configured size limit")
                content = response.read(self._max_bytes + 1)
                if len(content) > self._max_bytes:
                    raise DatasetDownloadError("dataset exceeds the configured size limit")
                return FetchResult(
                    content=content,
                    content_type=content_type,
                    source_version=response.headers.get("etag")
                    or response.headers.get("last-modified"),
                    metadata={"final_url": response.geturl()},
                )
        except HTTPError as error:
            raise DatasetDownloadError(f"dataset source returned HTTP {error.code}") from error
        except OSError as error:
            raise DatasetDownloadError("dataset source could not be reached") from error

    def get_json(self, url: str, *, headers: dict[str, str] | None = None) -> Any:
        result = self.get_bytes(url, headers=headers)
        try:
            return json.loads(result.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DatasetDownloadError("dataset source returned malformed JSON") from error
