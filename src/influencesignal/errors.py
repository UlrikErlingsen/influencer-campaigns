"""User-facing errors raised by InfluenceSignal."""

from __future__ import annotations


class DataProblem(ValueError):
    """Raised when supplied data cannot be accepted as it stands."""


class GateBlocked(DataProblem):
    """Raised when a pipeline move is refused because the compliance gate is not satisfied."""

    def __init__(self, message: str, reasons: list[str] | tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.reasons = tuple(reasons)


def friendly_message(exc: Exception) -> str:
    """Return a useful message without exposing an internal traceback by default."""
    if isinstance(exc, DataProblem):
        return str(exc)
    if isinstance(exc, ValueError):
        return f"InfluenceSignal could not complete that step: {exc}"
    return (
        "InfluenceSignal could not complete that step. Check the input and try again. "
        "Set INFLUENCESIGNAL_DEBUG=1 before launch if you need technical details."
    )
