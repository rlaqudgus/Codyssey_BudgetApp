"""거래 출력 형식."""

from __future__ import annotations

from collections.abc import Sequence

from budget_app.console import print_warning
from budget_app.models import Transaction
from budget_app.services.report_service import BudgetStatus


def format_transaction(tx: Transaction) -> str:
    return " | ".join(
        [
            tx.id,
            tx.date.isoformat(),
            f"{tx.type.value:<7}",
            tx.category,
            str(tx.amount),
            tx.memo,
            ",".join(f"#{t}" for t in tx.tags),
        ]
    ).rstrip(" |")


def print_transactions(items: Sequence[Transaction]) -> None:
    for tx in items:
        print(format_transaction(tx))


def won(amount: int) -> str:
    return f"{amount:,}원"


def print_budget_status(status: BudgetStatus) -> None:
    print(f"예산: {won(status.budget)} (사용률 {status.usage_rate:.1f}%)")
    if status.exceeded:
        print_warning(f"{status.month} 예산을 {won(-status.remaining)} 초과했습니다!")
    elif status.near_limit:
        print(f"[주의] 예산의 {status.usage_rate:.1f}%를 사용했습니다. 남은 예산 {won(status.remaining)}")
    else:
        print(f"남은 예산: {won(status.remaining)}")
