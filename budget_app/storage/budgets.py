"""월 예산 저장소(budgets.jsonl). 레코드: {"month": "2024-01", "amount": 500000}"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from budget_app.models import Budget
from budget_app.storage.jsonl import JsonlFile, Record


class BudgetStore:
    FILENAME = "budgets.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.file = JsonlFile(data_dir / self.FILENAME)

    def ensure_exists(self) -> bool:
        return self.file.ensure_exists()

    def iter_all(self) -> Iterator[Budget]:
        for record in self.file.stream():
            try:
                yield Budget.from_dict(record)
            except (KeyError, ValueError, TypeError) as exc:
                raise self.file.corrupted(None, f"예산 레코드 {record}: {exc}") from None

    def get(self, month: str) -> Budget | None:
        return next((b for b in self.iter_all() if b.month == month), None)

    def upsert(self, budget: Budget) -> None:
        """같은 월이 있으면 교체, 없으면 추가(월 오름차순 유지)."""

        def records() -> Iterator[Record]:
            others = [b for b in self.iter_all() if b.month != budget.month]
            for b in sorted([*others, budget], key=lambda item: item.month):
                yield b.to_dict()

        self.file.rewrite(records())
