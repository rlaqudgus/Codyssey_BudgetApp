"""add: 대화형으로 거래 1건을 추가한다."""

from __future__ import annotations

import argparse
from datetime import date

from budget_app.cli.base import add_command
from budget_app.cli.prompts import ask, ask_text
from budget_app.console import print_saved, print_warning
from budget_app.context import AppContext
from budget_app.models import NewTransaction, TxType
from budget_app.validators import parse_amount, parse_date, parse_tags, parse_type

EPILOG = """\
입력 항목(순서대로 대화형 입력):
  날짜(YYYY-MM-DD, 엔터=오늘) / 타입(income|expense) / 카테고리(등록된 것만)
  금액(양의 정수) / 메모(선택) / 태그(쉼표 구분, 선택)

잘못 입력하면 원인과 힌트를 보여주고 같은 항목을 다시 묻습니다.
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    add_command(subparsers, "add", help="거래 추가 (대화형 입력)", epilog=EPILOG, handler=run)


def run(args: argparse.Namespace, ctx: AppContext) -> int:
    categories = ctx.category_service
    new = NewTransaction(
        date=ask("날짜(YYYY-MM-DD, 엔터=오늘): ", parse_date, default=date.today().isoformat()),
        type=ask("타입(income/expense): ", parse_type),
        category=ask(f"카테고리 [{', '.join(categories.names())}]: ", categories.require),
        amount=ask("금액(양수): ", parse_amount),
        memo=ask_text("메모(선택): "),
        tags=parse_tags(ask_text("태그(쉼표로 구분, 없으면 엔터): ")),
    )
    tx = ctx.transaction_service.add(new)
    print_saved(f"id={tx.id}")
    if tx.type is TxType.EXPENSE:
        status = ctx.report_service.budget_status(tx.month)
        if status and status.exceeded:
            print_warning(
                f"{status.month} 지출 {status.spent:,}원이 예산 {status.budget:,}원을 초과했습니다 "
                f"(사용률 {status.usage_rate:.1f}%)."
            )
    return 0
