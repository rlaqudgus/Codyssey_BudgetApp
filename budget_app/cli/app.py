"""CLI 진입점: 파서 구성 -> 로깅 설정 -> 명령 디스패치."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from budget_app import __version__
from budget_app.cli.base import KoreanArgumentParser, Handler, add_common_options
from budget_app.cli.commands import COMMAND_MODULES
from budget_app.console import print_info
from budget_app.context import AppContext
from budget_app.decorators import handle_errors, log_execution, logger, timed

LOG_FILENAME = "app.log"

EPILOG = """\
예시:
  python -m budget_app add
  python -m budget_app list --limit 5
  python -m budget_app summary --month 2024-01 --top 3

각 명령의 자세한 사용법: python -m budget_app <command> --help
"""


def build_parser() -> KoreanArgumentParser:
    parser = KoreanArgumentParser(
        prog="python -m budget_app",
        description="파일 기반 콘솔 가계부",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_common_options(parser, top_level=True)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>", title="명령")
    subparsers.required = True
    for module in COMMAND_MODULES:
        module.register(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)
    _configure_logging(Path(args.data_dir), verbose=args.verbose)
    try:
        return run_command(args)
    finally:
        _close_logging()


@handle_errors
@log_execution
@timed
def run_command(args: argparse.Namespace) -> int:
    ctx = AppContext.open(Path(args.data_dir))
    for notice in ctx.notices:
        print_info(notice)
    handler: Handler = args.handler
    return handler(args, ctx)


def _configure_stdio() -> None:
    """콘솔 인코딩이 한글/특수문자를 표현하지 못해도 프로그램이 죽지 않게 한다."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def _configure_logging(data_dir: Path, *, verbose: bool) -> None:
    _close_logging()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(data_dir / LOG_FILENAME, encoding="utf-8")
    except OSError:
        file_handler = None  # 로그를 못 남겨도 본 기능은 계속 동작해야 한다.
    if file_handler is not None:
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(file_handler)
    if verbose:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter("[로그] %(message)s"))
        logger.addHandler(console)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())


def _close_logging() -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
