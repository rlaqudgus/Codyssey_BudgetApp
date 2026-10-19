"""월 예산 설정/조회."""

from __future__ import annotations

from budget_app.models import Budget
from budget_app.storage import BudgetStore


class BudgetService:
    def __init__(self, store: BudgetStore) -> None:
        self.store = store

    def set(self, month: str, amount: int) -> Budget:
        budget = Budget(month=month, amount=amount)
        self.store.upsert(budget)
        return budget

    def get(self, month: str) -> Budget | None:
        return self.store.get(month)

    def all(self) -> list[Budget]:
        return list(self.store.iter_all())
