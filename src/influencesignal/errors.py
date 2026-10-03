"""User-facing errors raised by Influence Signal."""

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
    if isinstance(exc, MemoryError):  # includes pyarrow's ArrowMemoryError
        return (
            "There is not enough memory on this computer for this file or step. Close other programs, or split the "
            "file and import it in parts."
        )
    if isinstance(exc, ValueError):
        return f"Influence Signal could not complete that step: {exc}"
    return (
        "Influence Signal could not complete that step. Check the input and try again. "
        "Set INFLUENCESIGNAL_DEBUG=1 before launch if you need technical details."
    )
