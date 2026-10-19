"""summary: 월별 요약(총수입/총지출/잔액 + 카테고리별 지출 TOP N)."""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, arg_month, arg_positive_int
from budget_app.cli.views import print_budget_status, won
from budget_app.context import AppContext
from budget_app.formatting import display_width, pad

DEFAULT_TOP = 3

EPILOG = """\
예시:
  python -m budget_app summary --month 2024-01
  python -m budget_app summary --month 2024-01 --top 5
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = add_command(subparsers, "summary", help="월별 요약", epilog=EPILOG, handler=run)
    parser.add_argument("--month", type=arg_month, required=True, metavar="YYYY-MM", help="요약할 월")
    parser.add_argument("--top", type=arg_positive_int, default=DEFAULT_TOP, metavar="N",
                        help=f"카테고리별 지출 상위 N개 (기본: {DEFAULT_TOP})")


def run(args: argparse.Namespace, ctx: AppContext) -> int:
    summary = ctx.report_service.monthly_summary(args.month, args.top)
    print(f"=== {summary.month} 요약 ===")
    if not summary.has_data:
        print(f"[데이터 없음] {summary.month} 에 해당하는 거래가 없습니다.")
        if summary.budget:
            print_budget_status(summary.budget)
        return 0

    print(f"총 수입: {won(summary.income)}")
    print(f"총 지출: {won(summary.expense)}")
    print(f"잔액: {won(summary.balance)}")
    if summary.budget:
        print_budget_status(summary.budget)
    else:
        print("예산: 미설정 (budget set --month YYYY-MM --amount 금액)")
    print()
    if summary.top_expenses:
        print(f"지출 TOP {args.top}")
        name_width = max(display_width(c) for c, _ in summary.top_expenses)
        amount_width = max(display_width(won(t)) for _, t in summary.top_expenses)
        for rank, (category, total) in enumerate(summary.top_expenses, start=1):
            print(f"{rank}) {pad(category, name_width)}  {pad(won(total), amount_width, 'right')}")
    else:
        print("지출 내역이 없습니다.")
    return 0
