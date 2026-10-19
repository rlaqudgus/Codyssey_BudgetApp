"""search: 조건 검색(최신순, 스트리밍)."""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, add_criteria_arguments, arg_positive_int
from budget_app.cli.views import print_transactions
from budget_app.console import print_info
from budget_app.context import AppContext
from budget_app.query import SearchCriteria

EPILOG = """\
조건은 모두 AND 로 결합됩니다. 조건이 없으면 전체 거래를 최신순으로 출력합니다.

예시:
  python -m budget_app search --from 2024-01-01 --to 2024-01-31
  python -m budget_app search --category food --type expense
  python -m budget_app search --q 점심 --tag meal --limit 5
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = add_command(subparsers, "search", help="조건 검색 (최신순)", epilog=EPILOG, handler=run)
    add_criteria_arguments(parser)
    parser.add_argument("--q", metavar="KEYWORD", help="메모 키워드(부분 일치, 대소문자 무시)")
    parser.add_argument("--tag", help="태그(정확히 일치)")
    parser.add_argument("--limit", type=arg_positive_int, metavar="N", help="최대 출력 건수 (기본: 전체)")


def run(args: argparse.Namespace, ctx: AppContext) -> int:
    criteria = SearchCriteria(
        date_from=args.date_from,
        date_to=args.date_to,
        month=args.month,
        category=args.category,
        type=args.type,
        keyword=args.q,
        tag=args.tag,
    )
    result = ctx.transaction_service.search(criteria, args.limit)
    if not result.items:
        print_info("조건에 맞는 거래가 없습니다.")
        return 0
    print_transactions(result.items)
    shown = f"{len(result.items)}건 표시 / " if len(result.items) != result.total else ""
    print(f"(검색 결과 {shown}총 {result.total}건)")
    return 0
