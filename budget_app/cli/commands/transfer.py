"""import / export (CSV)"""

from __future__ import annotations

import argparse
from pathlib import Path

from budget_app.cli.base import add_command, add_criteria_arguments
from budget_app.console import print_done, print_info, print_warning
from budget_app.context import AppContext
from budget_app.errors import ValidationError
from budget_app.query import SearchCriteria
from budget_app.services.csv_service import CSV_COLUMNS

MAX_ERRORS_SHOWN = 10

SCHEMA = f"""\
CSV 스키마 (UTF-8, 헤더 포함):
  {','.join(CSV_COLUMNS)}
  date(필수, YYYY-MM-DD) type(필수, income|expense) category(필수, 등록된 카테고리)
  amount(필수, 양의 정수) memo(선택) tags(선택, 쉼표 구분 -> 따옴표로 감싸기)
"""

IMPORT_EPILOG = SCHEMA + """
잘못된 행은 건너뛰고 줄 번호와 사유를 보여줍니다. 나머지 행은 한 번에(원자적으로) 저장됩니다.

예시:
  python -m budget_app import --from samples/import_sample.csv
  python -m budget_app import --from bank.csv --create-categories
"""

EXPORT_EPILOG = SCHEMA + """
--month 또는 --from/--to 중 하나 이상의 기간 조건이 필수입니다.

예시:
  python -m budget_app export --out export.csv --month 2024-01
  python -m budget_app export --out q1.csv --from 2024-01-01 --to 2024-03-31 --type expense
"""


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p_import = add_command(subparsers, "import", help="CSV에서 거래 일괄 등록",
                           epilog=IMPORT_EPILOG, handler=run_import)
    p_import.add_argument("--from", dest="src", type=Path, required=True, metavar="CSV",
                          help="가져올 CSV 파일 경로")
    p_import.add_argument("--create-categories", action="store_true",
                          help="등록되지 않은 카테고리를 자동으로 추가")

    p_export = add_command(subparsers, "export", help="조건에 맞는 거래를 CSV로 저장",
                           epilog=EXPORT_EPILOG, handler=run_export)
    p_export.add_argument("--out", type=Path, required=True, metavar="CSV", help="저장할 CSV 파일 경로")
    add_criteria_arguments(p_export)


def run_import(args: argparse.Namespace, ctx: AppContext) -> int:
    result = ctx.csv_service.import_csv(args.src, create_categories=args.create_categories)
    if result.created_categories:
        print_info(f"새 카테고리 추가: {', '.join(result.created_categories)}")
    for error in result.errors[:MAX_ERRORS_SHOWN]:
        print_warning(f"{error.line}행 건너뜀: {error.reason}")
    if result.skipped > MAX_ERRORS_SHOWN:
        print_warning(f"... 외 {result.skipped - MAX_ERRORS_SHOWN}행 더 건너뜀")
    if any("카테고리" in e.reason for e in result.errors):
        print_info("등록되지 않은 카테고리는 'category add' 로 등록하거나 --create-categories 를 사용하세요.")
    if result.imported:
        ids = result.imported
        id_range = ids[0].id if len(ids) == 1 else f"{ids[0].id} ~ {ids[-1].id}"
        print_info(f"등록된 id: {id_range}")
    print_done(f"imported={len(result.imported)}, skipped={result.skipped}")
    return 0


def run_export(args: argparse.Namespace, ctx: AppContext) -> int:
    if args.month is None and args.date_from is None and args.date_to is None:
        raise ValidationError(
            "export 에는 기간 조건이 필요합니다.",
            "--month YYYY-MM 또는 --from YYYY-MM-DD --to YYYY-MM-DD 를 지정하세요.",
        )
    criteria = SearchCriteria(
        date_from=args.date_from,
        date_to=args.date_to,
        month=args.month,
        category=args.category,
        type=args.type,
    )
    count = ctx.csv_service.export(args.out, criteria)
    if count == 0:
        print_info("조건에 맞는 거래가 없어 헤더만 저장했습니다.")
    print_done(f"{args.out} ({count} records)")
    return 0
