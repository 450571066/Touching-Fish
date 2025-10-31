"""Minimal subset of the :mod:`requests` API used by the travel agent example.

This module provides a tiny compatibility layer so that the project can run in
restricted environments where the third-party ``requests`` package is not
available. Only the features exercised by the project are implemented; the
module should not be considered a drop-in replacement for the real library.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

__all__ = [
    "RequestException",
    "HTTPError",
    "Session",
]


class RequestException(Exception):
    """Base class for errors raised by this shim."""


class HTTPError(RequestException):
    """Raised when an HTTP response signals an error status code."""

    def __init__(self, status_code: int, message: str, url: str) -> None:
        super().__init__(f"HTTP {status_code} Error for url: {url} :: {message}")
        self.response: Response | None = None
        self.status_code = status_code
        self.url = url


@dataclass
class Response:
    """Lightweight representation of an HTTP response."""

    url: str
    status_code: int
    headers: MutableMapping[str, str]
    _body: bytes

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if 400 <= self.status_code:
            raise HTTPError(self.status_code, self.text, self.url)


class Session:
    """Extremely small subset of :class:`requests.Session`."""

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | bytes | bytearray | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        query = ""
        if params:
            serialised = {
                key: _stringify(value)
                for key, value in params.items()
                if value is not None
            }
            query = urllib.parse.urlencode(serialised)
        target = f"{url}?{query}" if query else url

        body: bytes | None
        if isinstance(data, (bytes, bytearray)):
            body = bytes(data)
        elif isinstance(data, Mapping):
            serialised_data = {
                key: _stringify(value)
                for key, value in data.items()
                if value is not None
            }
            body = urllib.parse.urlencode(serialised_data).encode("utf-8")
        elif data is None:
            body = None
        else:
            body = _stringify(data).encode("utf-8")

        request = urllib.request.Request(
            target,
            data=body,
            headers=dict(headers or {}),
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body_bytes = response.read()
                status = response.getcode()
                header_map = {key: value for key, value in response.getheaders()}
                final_url = response.geturl()
        except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in example run
            body_bytes = exc.read()
            status = exc.code
            header_map = dict(exc.headers.items()) if exc.headers else {}
            final_url = exc.geturl()
            raise HTTPError(status, body_bytes.decode("utf-8", errors="replace"), final_url) from exc
        except urllib.error.URLError as exc:  # pragma: no cover - exercised in example run
            raise RequestException(str(exc)) from exc

        return Response(final_url, status, header_map, body_bytes)

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        return self.request("GET", url, params=params, headers=headers, timeout=timeout)

    def post(
        self,
        url: str,
        *,
        data: Mapping[str, Any] | bytes | bytearray | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        return self.request("POST", url, data=data, headers=headers, timeout=timeout)


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
