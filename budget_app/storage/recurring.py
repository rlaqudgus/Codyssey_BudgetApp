"""반복 거래 규칙 저장소(recurring.jsonl)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

from budget_app.models import RC_ID_PREFIX, RecurringRule
from budget_app.storage.jsonl import JsonlFile


class RecurringStore:
    FILENAME = "recurring.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.file = JsonlFile(data_dir / self.FILENAME)

    def ensure_exists(self) -> bool:
        return self.file.ensure_exists()

    def iter_all(self) -> Iterator[RecurringRule]:
        for record in self.file.stream():
            try:
                yield RecurringRule.from_dict(record)
            except (KeyError, ValueError, TypeError) as exc:
                raise self.file.corrupted(None, f"반복 규칙 {record.get('id', '?')}: {exc}") from None

    def get(self, rule_id: str) -> RecurringRule | None:
        return next((r for r in self.iter_all() if r.id == rule_id), None)

    def next_id(self) -> str:
        numbers = (
            int(r.id[len(RC_ID_PREFIX):])
            for r in self.iter_all()
            if r.id.startswith(RC_ID_PREFIX) and r.id[len(RC_ID_PREFIX):].isdigit()
        )
        return f"{RC_ID_PREFIX}{max(numbers, default=0) + 1:03d}"

    def add(self, rule: RecurringRule) -> None:
        self.file.append(rule.to_dict())

    def remove(self, rule_id: str) -> None:
        self.file.rewrite(r.to_dict() for r in list(self.iter_all()) if r.id != rule_id)

    def count_by_category(self, category: str) -> int:
        return sum(1 for r in self.iter_all() if r.category == category)

    def recategorize(self, old: str, new: str) -> int:
        rules = list(self.iter_all())
        changed = sum(1 for r in rules if r.category == old)
        if changed:
            self.file.rewrite(
                (replace(r, category=new) if r.category == old else r).to_dict() for r in rules
            )
        return changed
