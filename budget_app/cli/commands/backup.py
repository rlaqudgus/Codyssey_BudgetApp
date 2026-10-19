"""backup create / list / restore"""

from __future__ import annotations

import argparse

from budget_app.cli.base import add_command, add_group
from budget_app.cli.prompts import confirm
from budget_app.console import print_done, print_info
from budget_app.context import AppContext
from budget_app.errors import AppError

EPILOG = """\
백업 위치: <data-dir>/backups/<YYYYMMDD-HHMMSS>/

예시:
  python -m budget_app backup create
  python -m budget_app backup list
  python -m budget_app backup restore --name 20240131-235959 --yes

restore 는 실행 직전 상태를 '...-before-restore' 백업으로 자동 보관한 뒤 되돌립니다.
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    group = add_group(subparsers, "backup", help="데이터 백업/복구 (create/list/restore)", epilog=EPILOG)
    add_command(group, "create", help="타임스탬프 백업 생성", handler=run_create)
    add_command(group, "list", help="백업 목록", handler=run_list)
    p_restore = add_command(group, "restore", help="백업으로 복구", handler=run_restore)
    p_restore.add_argument("--name", required=True, help="복구할 백업 이름(backup list 참고)")
    p_restore.add_argument("--yes", action="store_true", help="확인 질문 없이 진행")


def run_create(args: argparse.Namespace, ctx: AppContext) -> int:
    info = ctx.backup_service.create()
    print_done(f"백업 생성: {info.path} ({len(info.files)}개 파일)")
    return 0


def run_list(args: argparse.Namespace, ctx: AppContext) -> int:
    backups = ctx.backup_service.list()
    if not backups:
        print_info("백업이 없습니다. 'backup create' 로 생성하세요.")
        return 0
    for info in backups:
        print(f"- {info.name}  ({', '.join(info.files) or '파일 없음'})")
    return 0


def run_restore(args: argparse.Namespace, ctx: AppContext) -> int:
    if not args.yes and not confirm(f"현재 데이터를 백업 '{args.name}' 으로 되돌릴까요?"):
        raise AppError("복구를 취소했습니다.", "진행하려면 y 를 입력하거나 --yes 옵션을 사용하세요.")
    restored, safety = ctx.backup_service.restore(args.name)
    print_info(f"복구 전 상태를 자동 백업했습니다: {safety.name}")
    print_done(f"백업 '{restored.name}' 복구 ({len(restored.files)}개 파일)")
    return 0
