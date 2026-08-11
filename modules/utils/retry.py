"""Smart retry with exponential backoff for transient translation failures.

A 429 from an API usually means "slow down" and a 5xx usually means the server
hiccupped — both can succeed on a second try. Credential, quota and
content-safety errors are permanent and are never retried.

The settings page can disable retries or tune the attempt cap and the base
delay. When the server sends a ``Retry-After`` header it wins over the
exponential backoff (clamped to the configured max delay).

Retrying lives *inside* the translation engines (``BaseLLMTranslation`` and
``UserTranslator``), so every call path — single image, batch, webtoon chunk,
single block — benefits without duplicating pipeline logic.
"""

from __future__ import annotations

import logging
import random
import re
import time
from typing import Any, Callable, Iterator

import requests

from modules.utils.exceptions import ContentFlaggedException, InsufficientCreditsException

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY_SECONDS = 2.0
DEFAULT_MAX_DELAY_SECONDS = 60.0

# Statuses worth retrying: the server is overloaded or we were rate-limited,
# not that the request itself is invalid.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Engines that do not keep the raw response embed the status code in their
# message ("Error 500: ...", "status code 429", "Server Error (503) ...").
_STATUS_IN_MESSAGE = re.compile(r"(?:status code|status|Error|Server Error)[^\d]*([1-5]\d{2})")

# Transport-level OS errors that mean "the connection died, try again".
_RETRYABLE_ERRNOS = {104, 32, 111, 110, 101, 113, -2}  # ECONNRESET, EPIPE, ECONNREFUSED, ...


def _walk(exc: BaseException) -> Iterator[BaseException]:
    """Yield *exc* and its ``__cause__``/``__context__`` chain, once each."""
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)


def status_code_of(exc: BaseException) -> int | None:
    """The HTTP status behind *exc*, if one can be recovered."""
    for e in _walk(exc):
        response = getattr(e, "response", None)
        if response is not None and hasattr(response, "status_code"):
            return response.status_code
    match = _STATUS_IN_MESSAGE.search(str(exc))
    if match:
        return int(match.group(1))
    return None


def retry_after_of(exc: BaseException) -> float | None:
    """Seconds suggested by a ``Retry-After`` header, if any."""
    for e in _walk(exc):
        response = getattr(e, "response", None)
        if response is None or not hasattr(response, "headers"):
            continue
        value = response.headers.get("Retry-After")
        if value is None:
            continue
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            # The HTTP-date form is rare; fall back to the configured base.
            return DEFAULT_BASE_DELAY_SECONDS
    return None


def backoff_delay(attempt: int, base: float, cap: float, rng=None) -> float:
    """Exponential backoff with full jitter, clamped to *cap*."""
    if attempt < 0:
        attempt = 0
    span = min(base * (2 ** attempt), cap)
    rng = rng or random
    if hasattr(rng, "uniform"):
        return rng.uniform(0.0, span)
    return rng() * span


def is_retryable(exc: BaseException) -> bool:
    """Whether a failed translation call is worth trying again."""
    if isinstance(exc, (InsufficientCreditsException, ContentFlaggedException)):
        return False
    code = status_code_of(exc)
    if code is not None:
        return code in RETRYABLE_STATUS
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(exc, OSError):
        return getattr(exc, "errno", None) in _RETRYABLE_ERRNOS
    # SDKs that wrap every failure in their own exception type still name
    # transient conditions clearly (e.g. the deepl client's
    # TooManyRequestsException / ServiceUnavailableException).
    name = type(exc).__name__.lower()
    if any(token in name for token in ("toomany", "ratelimit", "rate_limit", "serviceunavailable", "temporar")):
        return True
    return False


def read_retry_settings(settings: Any) -> dict:
    """Retry configuration, with defaults when absent or unavailable."""
    defaults = {
        "enabled": True,
        "max_attempts": DEFAULT_MAX_ATTEMPTS,
        "base_delay": DEFAULT_BASE_DELAY_SECONDS,
        "max_delay": DEFAULT_MAX_DELAY_SECONDS,
    }
    if settings is None:
        return defaults
    if isinstance(settings, dict):
        data = settings
    else:
        getter = getattr(settings, "get_retry_settings", None)
        if not callable(getter):
            return defaults
        try:
            data = getter() or {}
        except Exception:
            return defaults
    if not isinstance(data, dict):
        return defaults

    result = dict(defaults)
    if isinstance(data.get("enabled"), bool):
        result["enabled"] = data["enabled"]
    if isinstance(data.get("max_attempts"), int) and data["max_attempts"] >= 1:
        result["max_attempts"] = int(data["max_attempts"])
    if isinstance(data.get("base_delay"), (int, float)) and data["base_delay"] > 0:
        result["base_delay"] = float(data["base_delay"])
    if isinstance(data.get("max_delay"), (int, float)) and data["max_delay"] > 0:
        result["max_delay"] = float(data["max_delay"])
    return result


def with_retry(
    fn: Callable[[], Any],
    settings: Any = None,
    *,
    label: str = "request",
    log: logging.Logger | None = None,
) -> Any:
    """Run *fn* (a single API call) with exponential backoff.

    Permanent failures (invalid credentials, out of credits, flagged content,
    non-retryable 4xx) propagate immediately. Transient failures are retried up
    to the configured attempt cap, honouring ``Retry-After`` when present.
    When the cap is exhausted the last error is re-raised.
    """
    config = read_retry_settings(settings)
    if not config["enabled"]:
        return fn()

    attempts = max(1, config["max_attempts"])
    last_error: BaseException | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - every engine raises its own types
            last_error = exc
            if not is_retryable(exc):
                raise
            if attempt >= attempts - 1:
                if log:
                    log.warning(
                        "%s failed after %d attempt(s); last error: %s",
                        label, attempts, exc,
                    )
                raise
            delay = retry_after_of(exc)
            if delay is None:
                delay = backoff_delay(attempt, config["base_delay"], config["max_delay"])
            else:
                delay = min(delay, config["max_delay"])
            if log:
                log.warning(
                    "%s attempt %d/%d failed (%s); retrying in %.1fs",
                    label, attempt + 1, attempts, exc, delay,
                )
            time.sleep(delay)
    assert last_error is not None
    raise last_error
