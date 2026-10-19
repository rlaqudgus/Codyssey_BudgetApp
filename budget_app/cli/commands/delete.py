"""delete: 거래 삭제(임시 파일 + 원자적 교체)."""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command
from budget_app.cli.views import format_transaction
from budget_app.console import print_done
from budget_app.context import AppContext


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = add_command(
        subparsers,
        "delete",
        help="거래 삭제",
        epilog="예시:\n  python -m budget_app delete --id TX-000012",
        handler=run,
    )
    parser.add_argument("--id", required=True, dest="tx_id", metavar="ID", help="삭제할 거래 id")


def run(args: argparse.Namespace, ctx: AppContext) -> int:
    tx = ctx.transaction_service.delete(args.tx_id)
    print(f"  삭제됨: {format_transaction(tx)}")
    print_done(f"id={tx.id} 삭제 완료")
    return 0
