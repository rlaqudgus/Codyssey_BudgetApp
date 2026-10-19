"""명령 등록 공통 도구: 파서 클래스, 공통 옵션, 인자 타입 변환기."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import NoReturn, TypeVar

from budget_app.console import print_error
from budget_app.context import AppContext
from budget_app.errors import ValidationError
from budget_app import validators

Handler = Callable[[argparse.Namespace, AppContext], int]

DEFAULT_DATA_DIR = "data"
EXIT_USAGE = 2

T = TypeVar("T")


class KoreanArgumentParser(argparse.ArgumentParser):
    """인자 오류를 '[오류] 원인 / [힌트] 해결 방법' 형식으로 출력한다."""

    def error(self, message: str) -> NoReturn:
        print_error(
            f"명령 인자가 올바르지 않습니다: {message}",
            f"'{self.prog} --help' 로 사용법을 확인하세요.",
        )
        sys.exit(EXIT_USAGE)


def add_common_options(parser: argparse.ArgumentParser, *, top_level: bool) -> None:
    """--data-dir, --verbose 는 명령 앞/뒤 어디에 써도 동작하게 한다.

    하위 명령에서는 기본값을 SUPPRESS 로 두어 최상위에서 지정한 값을 덮어쓰지 않는다.
    """
    default_dir = DEFAULT_DATA_DIR if top_level else argparse.SUPPRESS
    default_flag = False if top_level else argparse.SUPPRESS
    parser.add_argument(
        "--data-dir",
        default=default_dir,
        metavar="PATH",
        help=f"저장 폴더 경로 (기본: ./{DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=default_flag,
        help="실행 로그/실행 시간을 콘솔(stderr)에도 출력",
    )


def add_command(
    subparsers: argparse._SubParsersAction,  # type: ignore[type-arg]
    name: str,
    *,
    help: str,
    epilog: str | None = None,
    handler: Handler | None = None,
) -> KoreanArgumentParser:
    parser: KoreanArgumentParser = subparsers.add_parser(
        name,
        help=help,
        description=help,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_options(parser, top_level=False)
    if handler is not None:
        parser.set_defaults(handler=handler)
    return parser


def add_group(
    subparsers: argparse._SubParsersAction,  # type: ignore[type-arg]
    name: str,
    *,
    help: str,
    epilog: str | None = None,
) -> argparse._SubParsersAction:  # type: ignore[type-arg]
    """'category add' 처럼 하위 명령을 가지는 명령 그룹."""
    parser = add_command(subparsers, name, help=help, epilog=epilog)
    group = parser.add_subparsers(dest="action", metavar="<action>", title="하위 명령")
    group.required = True
    return group


def add_criteria_arguments(parser: argparse.ArgumentParser) -> None:
    """search / export 가 공유하는 기간·카테고리·타입 옵션."""
    parser.add_argument("--from", dest="date_from", type=arg_date, metavar="YYYY-MM-DD", help="시작일(포함)")
    parser.add_argument("--to", dest="date_to", type=arg_date, metavar="YYYY-MM-DD", help="종료일(포함)")
    parser.add_argument("--month", type=arg_month, metavar="YYYY-MM", help="해당 월")
    parser.add_argument("--category", type=arg_category, help="카테고리")
    parser.add_argument("--type", type=arg_type, metavar="{income,expense}", help="거래 타입")


def _argtype(parse: Callable[[str], T], label: str) -> Callable[[str], T]:
    """ValidationError -> argparse.ArgumentTypeError 로 바꿔 argparse가 오류를 보고하게 한다."""

    def convert(raw: str) -> T:
        try:
            return parse(raw)
        except ValidationError as exc:
            hint = f" ({exc.hint})" if exc.hint else ""
            raise argparse.ArgumentTypeError(f"{exc.message}{hint}") from None

    convert.__name__ = label
    return convert


arg_date = _argtype(validators.parse_date, "date")
arg_month = _argtype(validators.parse_month, "month")
arg_type = _argtype(validators.parse_type, "type")
arg_amount = _argtype(validators.parse_amount, "amount")
arg_tags = _argtype(validators.parse_tags, "tags")
arg_category = _argtype(validators.normalize_category, "category")
arg_positive_int = _argtype(validators.parse_positive_int, "positive int")
