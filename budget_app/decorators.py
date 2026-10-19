"""공통 관심사(예외 처리 / 실행 로그 / 실행 시간 측정) 데코레이터.

비즈니스 로직 함수에는 try/except, 로그, 시간 측정 코드를 넣지 않고
데코레이터로 감싸서 '무엇을 하는가'와 '어떻게 감시/보호하는가'를 분리한다.

    @handle_errors      # 가장 바깥: 모든 예외를 원인+힌트 메시지와 종료 코드로 변환
    @log_execution      # 시작/종료/실패를 로그 파일에 기록
    @timed              # 실행 시간을 로그에 기록
    def run_command(args) -> int: ...
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from budget_app.console import print_error
from budget_app.errors import AppError

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger("budget_app")
# 핸들러가 하나도 없으면 logging 의 lastResort 핸들러가 스택트레이스를 stderr 로 출력한다.
# 항상 NullHandler 를 두고 상위 로거로 전파하지 않아, 로그는 명시적으로 설정한 곳에만 남게 한다.
logger.addHandler(logging.NullHandler())
logger.propagate = False

EXIT_INTERRUPTED = 130
EXIT_UNEXPECTED = 1


def handle_errors(func: Callable[P, int]) -> Callable[P, int]:
    """예외를 스택트레이스 대신 '원인 + 해결 힌트'로 출력하고 종료 코드를 반환한다."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        try:
            return func(*args, **kwargs)
        except AppError as exc:
            print_error(exc.message, exc.hint)
            return exc.exit_code
        except KeyboardInterrupt:
            print_error("사용자에 의해 작업이 취소되었습니다.")
            return EXIT_INTERRUPTED
        except PermissionError as exc:
            print_error(
                f"파일 접근 권한이 없습니다: {exc.filename}",
                "다른 프로그램이 파일을 열고 있는지, 폴더 쓰기 권한이 있는지 확인하세요.",
            )
            return EXIT_UNEXPECTED
        except OSError as exc:
            print_error(
                f"파일 처리 중 문제가 발생했습니다: {exc.strerror or exc} ({exc.filename})",
                "경로가 올바른지, 디스크 공간이 충분한지 확인하세요.",
            )
            return EXIT_UNEXPECTED
        except Exception as exc:  # noqa: BLE001 - 최후의 안전망
            # 상세 스택트레이스는 로그 파일에만 남기고 콘솔에는 요약만 보여준다.
            logger.exception("예상하지 못한 오류")
            print_error(
                f"예상하지 못한 오류가 발생했습니다: {type(exc).__name__}: {exc}",
                "--verbose 옵션으로 다시 실행하거나 데이터 폴더의 app.log 를 확인하세요.",
            )
            return EXIT_UNEXPECTED

    return wrapper


def log_execution(func: Callable[P, R]) -> Callable[P, R]:
    """함수의 시작/정상 종료/실패를 로그로 남긴다."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        name = func.__qualname__
        logger.info("시작: %s %s", name, _describe(args))
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            logger.warning("실패: %s (%s: %s)", name, type(exc).__name__, exc)
            raise
        logger.info("종료: %s -> %r", name, result if _is_simple(result) else type(result).__name__)
        return result

    return wrapper


def timed(func: Callable[P, R]) -> Callable[P, R]:
    """실행 시간을 측정해 로그로 남긴다(실패해도 측정)."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info("실행 시간: %s %.2fms", func.__qualname__, elapsed_ms)

    return wrapper


def _describe(args: tuple[object, ...]) -> str:
    """로그에 남길 인자 요약(argparse.Namespace면 명령/옵션을 보여준다)."""
    if not args:
        return ""
    first = args[0]
    if hasattr(first, "__dict__") and hasattr(first, "command"):
        options = {k: v for k, v in vars(first).items() if k != "handler" and v is not None}
        return repr(options)
    return ""


def _is_simple(value: object) -> bool:
    return value is None or isinstance(value, (int, float, str, bool))
