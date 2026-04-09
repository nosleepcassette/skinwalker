from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HistoryEntry:
    label: str
    state: dict[str, Any]


class DraftHistory:
    def __init__(self, *, max_entries: int = 300) -> None:
        self.max_entries = max(2, int(max_entries))
        self._entries: list[HistoryEntry] = []
        self._index = -1

    @property
    def current(self) -> HistoryEntry | None:
        if self._index < 0 or self._index >= len(self._entries):
            return None
        return self._entries[self._index]

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return 0 <= self._index < len(self._entries) - 1

    def reset(self, state: dict[str, Any], *, label: str) -> None:
        self._entries = [HistoryEntry(label=label, state=deepcopy(state))]
        self._index = 0

    def record(self, state: dict[str, Any], *, label: str) -> bool:
        snapshot = deepcopy(state)
        if self.current is not None and self.current.state == snapshot:
            return False

        if self.can_redo:
            self._entries = self._entries[: self._index + 1]

        self._entries.append(HistoryEntry(label=label, state=snapshot))

        if len(self._entries) > self.max_entries:
            overflow = len(self._entries) - self.max_entries
            self._entries = self._entries[overflow:]
            self._index = max(0, self._index - overflow)

        self._index = len(self._entries) - 1
        return True

    def undo(self) -> HistoryEntry | None:
        if not self.can_undo:
            return None
        self._index -= 1
        return self.current

    def redo(self) -> HistoryEntry | None:
        if not self.can_redo:
            return None
        self._index += 1
        return self.current
