"""A small, dependency-free HTTP client for statistical APIs.

Statistical agencies' APIs are free but flaky: the World Bank API occasionally
returns a 502 under load, and the IMF's edge rejects requests that do not ask
for JSON explicitly. This module wraps :mod:`urllib` with the three behaviours
every connector needs:

* **retries with exponential backoff** on transient failures (5xx, 429,
  timeouts, connection resets) — but not on 4xx, which will never succeed;
* **an identifying User-Agent**, which is basic API etiquette;
* **an injectable transport**, so tests replay recorded responses instead of
  touching the network (see ``backend/tests/fixtures/ingest``).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["FetchError", "HttpClient", "Transport", "urllib_transport"]

logger = logging.getLogger(__name__)

USER_AGENT = "RealGrowth-ingest/1.0 (+https://github.com/Iampranjaldubey/RealGrowth)"

#: HTTP status codes worth retrying: rate limiting and server-side failures.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

#: ``(url, headers, timeout) -> (status, body)``. The default implementation
#: uses urllib; tests substitute a dict-backed fake.
Transport = Callable[[str, dict[str, str], float], tuple[int, bytes]]


class FetchError(RuntimeError):
    """Raised when a request fails permanently or exhausts its retries."""


def urllib_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    """Perform one GET with urllib, returning the status even for HTTP errors."""
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return int(response.status), bytes(response.read())
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read() if exc.fp is not None else b""


@dataclass
class HttpClient:
    """GET with retries. Stateless apart from its configuration."""

    transport: Transport = urllib_transport
    timeout: float = 60.0
    max_attempts: int = 4
    backoff_seconds: float = 1.5
    #: Injected so tests do not actually sleep.
    sleep: Callable[[float], None] = time.sleep

    def get_bytes(self, url: str, *, accept: str = "*/*") -> bytes:
        headers = {"User-Agent": USER_AGENT, "Accept": accept}
        last_error = "no attempt made"
        for attempt in range(1, self.max_attempts + 1):
            try:
                status, body = self.transport(url, headers, self.timeout)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if 200 <= status < 300:
                    return body
                last_error = f"HTTP {status}"
                if status not in RETRYABLE_STATUS:
                    raise FetchError(f"GET {url} failed permanently: {last_error}")
            if attempt < self.max_attempts:
                delay = self.backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "GET %s failed (%s); retry %d/%d in %.1fs",
                    url,
                    last_error,
                    attempt,
                    self.max_attempts - 1,
                    delay,
                )
                self.sleep(delay)
        raise FetchError(f"GET {url} failed after {self.max_attempts} attempts: {last_error}")

    def get_json(self, url: str) -> Any:
        body = self.get_bytes(url, accept="application/json")
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FetchError(f"GET {url} returned invalid JSON: {exc}") from exc

    def get_text(self, url: str) -> str:
        return self.get_bytes(url, accept="text/csv, text/plain, */*").decode("utf-8-sig")
