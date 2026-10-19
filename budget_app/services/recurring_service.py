"""반복 거래: 규칙 등록 후 특정 월에 실제 거래를 자동 생성한다."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from budget_app.errors import NotFoundError
from budget_app.models import NewTransaction, RecurringRule, Transaction, TxType
from budget_app.services.category_service import CategoryService
from budget_app.storage import TransactionRepository
from budget_app.storage.recurring import RecurringStore


@dataclass(frozen=True)
class ApplyResult:
    month: str
    created: list[Transaction]
    already_applied: list[RecurringRule]


class RecurringService:
    def __init__(
        self,
        store: RecurringStore,
        transactions: TransactionRepository,
        categories: CategoryService,
    ) -> None:
        self.store = store
        self.transactions = transactions
        self.categories = categories

    def add(
        self,
        *,
        day: int,
        type: TxType,
        amount: int,
        category: str,
        memo: str = "",
        tags: tuple[str, ...] = (),
    ) -> RecurringRule:
        rule = RecurringRule(
            id=self.store.next_id(),
            day=day,
            type=type,
            amount=amount,
            category=self.categories.require(category),
            memo=memo,
            tags=tags,
        )
        self.store.add(rule)
        return rule

    def rules(self) -> list[RecurringRule]:
        return list(self.store.iter_all())

    def remove(self, rule_id: str) -> RecurringRule:
        normalized = rule_id.strip().upper()
        rule = self.store.get(normalized)
        if rule is None:
            raise NotFoundError(
                f"id={normalized} 반복 규칙이 없습니다.",
                "'recurring list' 로 규칙 id를 확인하세요. 예: RC-001",
            )
        self.store.remove(rule.id)
        return rule

    def apply(self, month: str) -> ApplyResult:
        """month 에 아직 생성되지 않은 규칙만 거래로 생성한다(여러 번 실행해도 중복 없음)."""
        rules = self.rules()
        keys = {rule.source_key(month) for rule in rules}
        applied = {tx.source for tx in self.transactions.iter_all() if tx.source in keys}
        pending = [r for r in rules if r.source_key(month) not in applied]
        done = [r for r in rules if r.source_key(month) in applied]
        for rule in pending:
            self.categories.require(rule.category)  # 규칙 등록 후 카테고리가 바뀐 경우 방어
        created = self.transactions.add_many(
            NewTransaction(
                type=rule.type,
                date=_day_in_month(month, rule.day),
                amount=rule.amount,
                category=rule.category,
                memo=rule.memo,
                tags=rule.tags,
                source=rule.source_key(month),
            )
            for rule in pending
        ) if pending else []
        return ApplyResult(month, created, done)


def _day_in_month(month: str, day: int) -> date:
    """2024-02 + 31일 -> 2024-02-29 (말일 보정)."""
    year, mon = (int(part) for part in month.split("-"))
    last = calendar.monthrange(year, mon)[1]
    return date(year, mon, min(day, last))
