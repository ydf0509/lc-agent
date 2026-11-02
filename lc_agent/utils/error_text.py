"""Exception formatting helpers that never materialize huge SQL payloads."""

import traceback
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

DEFAULT_ERROR_LIMIT = 2000
DEFAULT_TRACE_LIMIT = 4000


def _safe_str(value: Any) -> str:
    try:
        return str(value)
    except BaseException:
        return ""


def safe_error_text(error: BaseException, limit: int = DEFAULT_ERROR_LIMIT) -> str:
    """Return a bounded, human-readable error message.

    SQLAlchemy ``StatementError`` includes every bound parameter in ``str()``;
    with large batches this can allocate hundreds of KB and has been observed
    to raise ``MemoryError``. Use ``.orig`` (usually the small DBAPI error)
    instead of stringifying the statement wrapper.
    """
    if isinstance(error, SQLAlchemyError):
        orig = getattr(error, "orig", None)
        if orig is not None:
            text = f"{type(error).__name__}: {type(orig).__name__}: {_safe_str(orig)}"
        elif type(error).__name__ == "StatementError":
            text = type(error).__name__
        else:
            text = _safe_str(error)
    else:
        text = _safe_str(error)

    text = text.strip() or type(error).__name__
    if limit > 0:
        text = text[:limit]
    return text


def safe_traceback_text(error: BaseException, limit: int = DEFAULT_TRACE_LIMIT) -> str:
    """Return a bounded traceback that keeps the exception type/message tail."""
    try:
        frames = "".join(traceback.format_tb(error.__traceback__, limit=20))
    except BaseException:
        frames = ""

    tail = f"{type(error).__name__}: {safe_error_text(error, limit=max(100, limit // 2))}"
    if limit <= 0:
        return frames + tail
    if len(frames) + len(tail) > limit:
        keep = max(0, limit - len(tail))
        # Keep the frames nearest the failure; the tail keeps type + message.
        frames = frames[-keep:] if keep else ""
    return (frames + tail)[:limit]
