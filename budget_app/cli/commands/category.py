"""category add / list / remove"""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, add_group, arg_category
from budget_app.cli.prompts import ask, ask_text
from budget_app.console import print_done, print_info, print_saved
from budget_app.context import AppContext
from budget_app.errors import AppError
from budget_app.validators import normalize_category

EPILOG = """\
예시:
  python -m budget_app category add                 (대화형으로 이름 입력)
  python -m budget_app category add --name coffee
  python -m budget_app category list
  python -m budget_app category remove --name coffee --replace food

사용 중인 카테고리를 삭제하려면 --replace 로 대체 카테고리를 지정해야 합니다.
(옵션이 없으면 대화형으로 대체 카테고리를 묻고, 빈 입력이면 삭제를 취소합니다.)
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = add_group(subparsers, "category", help="카테고리 관리 (add/list/remove)", epilog=EPILOG)

    p_add = add_command(group, "add", help="카테고리 추가", handler=run_add)
    p_add.add_argument("--name", type=arg_category, help="카테고리명 (생략 시 대화형 입력)")

    add_command(group, "list", help="카테고리 목록과 사용 건수", handler=run_list)

    p_rm = add_command(group, "remove", help="카테고리 삭제", handler=run_remove)
    p_rm.add_argument("--name", type=arg_category, help="삭제할 카테고리 (생략 시 대화형 입력)")
    p_rm.add_argument("--replace", type=arg_category, metavar="CATEGORY",
                      help="사용 중인 거래를 옮길 대체 카테고리")


def run_add(args: argparse.Namespace, ctx: AppContext) -> int:
    raw = args.name or ask("카테고리명: ", normalize_category)
    name = ctx.category_service.add(raw)
    print_saved(f"category={name}")
    return 0


def run_list(args: argparse.Namespace, ctx: AppContext) -> int:
    rows = ctx.category_service.list_with_usage()
    if not rows:
        print_info("등록된 카테고리가 없습니다. 'category add' 로 추가하세요.")
        return 0
    width = max(len(name) for name, _ in rows)
    for name, used in rows:
        print(f"- {name:<{width}}  (사용 {used}건)")
    return 0


def run_remove(args: argparse.Namespace, ctx: AppContext) -> int:
    service = ctx.category_service
    name: str = args.name or ask("삭제할 카테고리명: ", normalize_category)
    replacement: str | None = args.replace
    used = service.usage_count(name)
    if used and replacement is None:
        print_info(f"'{name}' 카테고리를 사용하는 거래가 {used}건 있습니다.")
        replacement = ask_text("거래를 옮길 대체 카테고리 (취소하려면 엔터): ") or None
        if replacement is None:
            raise AppError(
                "카테고리 삭제를 취소했습니다.",
                f"category remove --name {name} --replace <대체카테고리> 로 다시 실행하세요.",
            )
    moved = service.remove(name, replacement)
    if moved:
        print_done(f"category={name} 삭제 (거래 {moved}건 -> {replacement} 로 이동)")
    else:
        print_done(f"category={name} 삭제")
    return 0
