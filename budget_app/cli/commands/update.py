"""update: 옵션 기반 거래 수정(안 A로 고정).

update --id <id> [--date ...] [--type ...] [--category ...] [--amount ...] [--memo ...] [--tags ...]
지정한 필드만 바뀌고 나머지는 유지된다. 파일은 임시 파일에 다시 쓴 뒤 원자적으로 교체한다.
"""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, arg_amount, arg_category, arg_date, arg_tags, arg_type
from budget_app.cli.views import format_transaction
from budget_app.console import print_done, print_info
from budget_app.context import AppContext
from budget_app.models import TransactionPatch

EPILOG = """\
지정한 옵션의 필드만 수정합니다. 빈 문자열("")을 주면 메모/태그를 비웁니다.

예시:
  python -m budget_app update --id TX-000012 --amount 18000
  python -m budget_app update --id TX-000012 --category food --memo "팀 점심" --tags "meal,team"
  python -m budget_app update --id TX-000012 --tags ""
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = add_command(subparsers, "update", help="거래 수정 (옵션 방식)", epilog=EPILOG, handler=run)
    parser.add_argument("--id", required=True, dest="tx_id", metavar="ID", help="수정할 거래 id")
    parser.add_argument("--date", type=arg_date, metavar="YYYY-MM-DD")
    parser.add_argument("--type", type=arg_type, metavar="{income,expense}")
    parser.add_argument("--category", type=arg_category)
    parser.add_argument("--amount", type=arg_amount, help="양의 정수")
    parser.add_argument("--memo")
    parser.add_argument("--tags", type=arg_tags, help="쉼표 구분 태그")


def run(args: argparse.Namespace, ctx: AppContext) -> int:
    patch = TransactionPatch(
        type=args.type,
        date=args.date,
        amount=args.amount,
        category=args.category,
        memo=args.memo.strip() if args.memo is not None else None,
        tags=args.tags,
    )
    before, after = ctx.transaction_service.update(args.tx_id, patch)
    if before == after:
        print_info(f"id={after.id} 변경된 내용이 없습니다.")
        return 0
    print(f"  수정 전: {format_transaction(before)}")
    print(f"  수정 후: {format_transaction(after)}")
    print_done(f"id={after.id} 수정 완료")
    return 0
