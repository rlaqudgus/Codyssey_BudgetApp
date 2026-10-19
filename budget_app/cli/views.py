"""출력 형식(뷰). 데이터 -> 문자열 변환만 담당하고, 정렬 규칙은 formatting 모듈에 위임한다."""

from __future__ import annotations

from collections.abc import Sequence

from budget_app.console import print_warning
from budget_app.formatting import Align, render_table, truncate
from budget_app.models import Transaction
from budget_app.services.report_service import BudgetStatus

MEMO_MAX_WIDTH = 24

TX_HEADERS = ("ID", "날짜", "타입", "카테고리", "금액", "메모", "태그")
TX_ALIGNS: tuple[Align, ...] = ("left", "left", "left", "left", "right", "left", "left")


def transaction_cells(tx: Transaction) -> list[str]:
    return [
        tx.id,
        tx.date.isoformat(),
        tx.type.value,
        tx.category,
        f"{tx.amount:,}",
        truncate(tx.memo, MEMO_MAX_WIDTH),
        ",".join(f"#{t}" for t in tx.tags),
    ]


def format_transaction(tx: Transaction) -> str:
    """한 줄 요약(수정/삭제 결과 표시용)."""
    return " | ".join(cell for cell in transaction_cells(tx) if cell)


def print_transactions(items: Sequence[Transaction]) -> None:
    print(render_table(TX_HEADERS, [transaction_cells(tx) for tx in items], TX_ALIGNS))


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
