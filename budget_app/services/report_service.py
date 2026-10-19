"""월별 요약/리포트 집계."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from budget_app.decorators import timed
from budget_app.models import TxType
from budget_app.query import SearchCriteria
from budget_app.storage import BudgetStore, TransactionRepository

WARNING_RATE = 80.0  # 사용률이 이 값(%) 이상이면 주의 문구


@dataclass(frozen=True)
class BudgetStatus:
    month: str
    budget: int
    spent: int

    @property
    def usage_rate(self) -> float:
        return self.spent / self.budget * 100

    @property
    def remaining(self) -> int:
        return self.budget - self.spent

    @property
    def exceeded(self) -> bool:
        return self.spent > self.budget

    @property
    def near_limit(self) -> bool:
        return not self.exceeded and self.usage_rate >= WARNING_RATE


@dataclass(frozen=True)
class MonthlySummary:
    month: str
    count: int
    income: int
    expense: int
    top_expenses: list[tuple[str, int]]  # (카테고리, 합계) 지출 내림차순
    budget: BudgetStatus | None = None  # 예산 미설정이면 None

    @property
    def balance(self) -> int:
        return self.income - self.expense

    @property
    def has_data(self) -> bool:
        return self.count > 0


class ReportService:
    def __init__(self, transactions: TransactionRepository, budgets: BudgetStore) -> None:
        self.transactions = transactions
        self.budgets = budgets

    @timed
    def monthly_summary(self, month: str, top: int) -> MonthlySummary:
        """해당 월 거래를 스트리밍하며 합계만 누적한다(거래 목록을 메모리에 쌓지 않음)."""
        count = income = expense = 0
        by_category: Counter[str] = Counter()
        for tx in SearchCriteria(month=month).filter(self.transactions.iter_all()):
            count += 1
            if tx.type is TxType.INCOME:
                income += tx.amount
            else:
                expense += tx.amount
                by_category[tx.category] += tx.amount
        top_expenses = sorted(by_category.items(), key=lambda item: (-item[1], item[0]))[:top]
        return MonthlySummary(
            month, count, income, expense, top_expenses, self._status(month, expense)
        )

    def budget_status(self, month: str) -> BudgetStatus | None:
        """예산이 설정된 달이면 해당 월 지출 합계와 함께 반환한다."""
        budget = self.budgets.get(month)
        if budget is None:
            return None
        criteria = SearchCriteria(month=month, type=TxType.EXPENSE)
        spent = sum(tx.amount for tx in criteria.filter(self.transactions.iter_all()))
        return BudgetStatus(month, budget.amount, spent)

    def _status(self, month: str, spent: int) -> BudgetStatus | None:
        budget = self.budgets.get(month)
        return BudgetStatus(month, budget.amount, spent) if budget else None
