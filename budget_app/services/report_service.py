"""월별 요약/리포트 집계."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from budget_app.decorators import timed
from budget_app.models import TxType
from budget_app.query import SearchCriteria
from budget_app.storage import TransactionRepository


@dataclass(frozen=True)
class MonthlySummary:
    month: str
    count: int
    income: int
    expense: int
    top_expenses: list[tuple[str, int]]  # (카테고리, 합계) 지출 내림차순

    @property
    def balance(self) -> int:
        return self.income - self.expense

    @property
    def has_data(self) -> bool:
        return self.count > 0


class ReportService:
    def __init__(self, transactions: TransactionRepository) -> None:
        self.transactions = transactions

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
        return MonthlySummary(month, count, income, expense, top_expenses)
