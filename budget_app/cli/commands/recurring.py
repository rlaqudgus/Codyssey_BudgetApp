"""recurring add / list / remove / apply"""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, add_group, arg_month
from budget_app.cli.prompts import ask, ask_text
from budget_app.cli.views import print_transactions
from budget_app.console import print_done, print_info, print_saved
from budget_app.context import AppContext
from budget_app.formatting import render_table
from budget_app.validators import parse_amount, parse_day, parse_tags, parse_type

EPILOG = """\
월급/월세처럼 매달 반복되는 거래를 규칙으로 등록하고, apply 로 특정 월의 거래를 생성합니다.
같은 달에 apply 를 여러 번 실행해도 이미 생성된 규칙은 건너뜁니다.

예시:
  python -m budget_app recurring add          (대화형: 날짜(일)/타입/카테고리/금액/메모/태그)
  python -m budget_app recurring list
  python -m budget_app recurring apply --month 2024-02
  python -m budget_app recurring remove --id RC-001
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = add_group(subparsers, "recurring", help="반복 거래 관리 (add/list/remove/apply)", epilog=EPILOG)
    add_command(group, "add", help="반복 규칙 추가 (대화형)", handler=run_add)
    add_command(group, "list", help="반복 규칙 목록", handler=run_list)
    p_rm = add_command(group, "remove", help="반복 규칙 삭제", handler=run_remove)
    p_rm.add_argument("--id", required=True, dest="rule_id", metavar="ID", help="규칙 id (예: RC-001)")
    p_apply = add_command(group, "apply", help="해당 월의 반복 거래 생성", handler=run_apply)
    p_apply.add_argument("--month", type=arg_month, required=True, metavar="YYYY-MM")


def run_add(args: argparse.Namespace, ctx: AppContext) -> int:
    categories = ctx.category_service
    rule = ctx.recurring_service.add(
        day=ask("매월 날짜(1~31): ", parse_day),
        type=ask("타입(income/expense): ", parse_type),
        category=ask(f"카테고리 [{', '.join(categories.names())}]: ", categories.require),
        amount=ask("금액(양수): ", parse_amount),
        memo=ask_text("메모(선택): "),
        tags=parse_tags(ask_text("태그(쉼표로 구분, 없으면 엔터): ")),
    )
    print_saved(f"id={rule.id} (매월 {rule.day}일 {rule.category} {rule.amount:,}원)")
    return 0


def run_list(args: argparse.Namespace, ctx: AppContext) -> int:
    rules = ctx.recurring_service.rules()
    if not rules:
        print_info("등록된 반복 규칙이 없습니다. 'recurring add' 로 추가하세요.")
        return 0
    rows = [
        [r.id, f"매월 {r.day}일", r.type.value, r.category, f"{r.amount:,}", r.memo]
        for r in rules
    ]
    print(render_table(("ID", "주기", "타입", "카테고리", "금액", "메모"), rows,
                       ("left", "left", "left", "left", "right", "left")))
    return 0


def run_remove(args: argparse.Namespace, ctx: AppContext) -> int:
    rule = ctx.recurring_service.remove(args.rule_id)
    print_done(f"반복 규칙 {rule.id} 삭제 (이미 생성된 거래는 유지됩니다)")
    return 0


def run_apply(args: argparse.Namespace, ctx: AppContext) -> int:
    result = ctx.recurring_service.apply(args.month)
    if result.created:
        print_transactions(result.created)
    if result.already_applied:
        skipped = ", ".join(r.id for r in result.already_applied)
        print_info(f"{result.month} 에 이미 생성된 규칙은 건너뜀: {skipped}")
    print_done(f"{result.month} 반복 거래 created={len(result.created)}, skipped={len(result.already_applied)}")
    return 0
