from __future__ import annotations

import re
import unicodedata
from typing import Any

MAX_ERROR_BYTES = 4096


class FairyError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        from astrofairy._contracts import canonical  # noqa: PLC0415 - error construction must avoid import cycles.

        fallback = {
            "error": "invalid_diagnostic",
            "message": "Operation failed without a usable public diagnostic",
        }
        result: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.details is not None:
            result["details"] = self.details
        try:
            if (
                type(self.code) is not str
                or type(self.message) is not str
                or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,79}", self.code)
                or not self.message.strip()
            ):
                return fallback
            pending: list[Any] = [result]
            visited = 0
            while pending:
                value = pending.pop()
                visited += 1
                if visited > MAX_ERROR_BYTES:
                    return fallback
                if type(value) is dict:
                    if len(value) > MAX_ERROR_BYTES or any(type(key) is not str for key in value):
                        return fallback
                    pending.extend(value.keys())
                    pending.extend(value.values())
                elif type(value) is list:
                    if len(value) > MAX_ERROR_BYTES:
                        return fallback
                    pending.extend(value)
                elif type(value) is str:
                    if any(unicodedata.category(char).startswith("C") for char in value):
                        return fallback
                elif type(value) not in {int, float, bool, type(None)}:
                    return fallback
            return result if len(canonical(result)) <= MAX_ERROR_BYTES else fallback
        except (TypeError, ValueError, UnicodeError, RecursionError, FairyError):
            return fallback
