from sqlalchemy.exc import SQLAlchemyError

from lc_agent.utils.error_text import safe_error_text, safe_traceback_text


class _ExplodingSqlError(SQLAlchemyError):
    """SQLAlchemy error whose __str__ would blow up on huge bound params."""

    def __init__(self):
        super().__init__("exploding")
        self.orig = RuntimeError("db down")

    def __str__(self):
        raise MemoryError("must not stringify the SQLAlchemy error")


def test_safe_error_text_empty_exception_falls_back_to_type():
    assert safe_error_text(RuntimeError()) == "RuntimeError"


def test_safe_error_text_never_stringifies_sqlalchemy_error():
    text = safe_error_text(_ExplodingSqlError())
    assert "db down" in text
    assert "MemoryError" not in text


def test_safe_error_text_truncates():
    assert len(safe_error_text(ValueError("x" * 100), limit=20)) <= 20


def test_safe_traceback_text_keeps_type_and_is_bounded():
    try:
        raise ValueError("boom")
    except ValueError as error:
        text = safe_traceback_text(error, limit=200)
    assert "ValueError" in text
    assert "boom" in text
    assert len(text) <= 200


def test_safe_traceback_text_never_stringifies_sqlalchemy_error():
    text = safe_traceback_text(_ExplodingSqlError(), limit=200)
    assert "db down" in text
    assert "MemoryError" not in text
