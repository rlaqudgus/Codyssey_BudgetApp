"""거래 출력 형식."""

from __future__ import annotations

from collections.abc import Sequence

from budget_app.models import Transaction


def print_transactions(items: Sequence[Transaction]) -> None:
    for tx in items:
        print(
            " | ".join(
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
        )
