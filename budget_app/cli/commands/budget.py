"""budget set / show / list"""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, add_group, arg_amount, arg_month
from budget_app.cli.views import print_budget_status, won
from budget_app.console import print_info, print_saved
from budget_app.context import AppContext

EPILOG = """\
예시:
  python -m budget_app budget set --month 2024-01 --amount 500000
  python -m budget_app budget show --month 2024-01
  python -m budget_app budget list

같은 달에 다시 set 하면 기존 예산을 덮어씁니다.
summary 실행 시 예산 사용률과 초과 경고가 함께 출력됩니다.
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = add_group(subparsers, "budget", help="월 예산 설정/조회 (set/show/list)", epilog=EPILOG)

    p_set = add_command(group, "set", help="월 예산 설정", handler=run_set)
    p_set.add_argument("--month", type=arg_month, required=True, metavar="YYYY-MM")
    p_set.add_argument("--amount", type=arg_amount, required=True, help="예산 금액(양의 정수)")

    p_show = add_command(group, "show", help="월 예산과 사용률 조회", handler=run_show)
    p_show.add_argument("--month", type=arg_month, required=True, metavar="YYYY-MM")

    add_command(group, "list", help="설정된 모든 월 예산", handler=run_list)


def run_set(args: argparse.Namespace, ctx: AppContext) -> int:
    budget = ctx.budget_service.set(args.month, args.amount)
    print_saved(f"{budget.month} 예산 {won(budget.amount)}")
    return 0


def run_show(args: argparse.Namespace, ctx: AppContext) -> int:
    status = ctx.report_service.budget_status(args.month)
    if status is None:
        print_info(f"{args.month} 예산이 설정되어 있지 않습니다. 'budget set' 으로 설정하세요.")
        return 0
    print(f"=== {status.month} 예산 ===")
    print(f"지출: {won(status.spent)}")
    print_budget_status(status)
    return 0


def run_list(args: argparse.Namespace, ctx: AppContext) -> int:
    budgets = ctx.budget_service.all()
    if not budgets:
        print_info("설정된 예산이 없습니다.")
        return 0
    for budget in budgets:
        print(f"- {budget.month}: {won(budget.amount)}")
    return 0
