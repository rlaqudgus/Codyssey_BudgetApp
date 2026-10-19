"""거래 출력 형식."""

from __future__ import annotations

from collections.abc import Sequence

from budget_app.models import Transaction


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
