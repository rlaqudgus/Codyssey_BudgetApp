"""list: 최신순 거래 목록(스트리밍)."""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, arg_positive_int
from budget_app.cli.views import print_transactions
from budget_app.console import print_info
from budget_app.context import AppContext

DEFAULT_LIMIT = 10


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = add_command(
        subparsers,
        "list",
        help="거래 목록 (최신순)",
        epilog="예시:\n  python -m budget_app list\n  python -m budget_app list --limit 3",
        handler=run,
    )
    parser.add_argument(
        "--limit",
        type=arg_positive_int,
        default=DEFAULT_LIMIT,
        metavar="N",
        help=f"출력할 최대 건수 (기본: {DEFAULT_LIMIT})",
    )


def run(args: argparse.Namespace, ctx: AppContext) -> int:
    result = ctx.transaction_service.latest(args.limit)
    if not result.items:
        print_info("저장된 거래가 없습니다. 'add' 명령으로 거래를 추가하세요.")
        return 0
    print_transactions(result.items)
    print(f"(최신 {len(result.items)}건 / 전체 {result.total}건)")
    return 0
