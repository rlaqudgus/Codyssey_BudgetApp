"""콘솔 메시지 출력 규칙을 한 곳에 모은다."""

from __future__ import annotations

import sys


def print_error(message: str, hint: str | None = None) -> None:
    print(f"[오류] {message}", file=sys.stderr)
    if hint:
        print(f"[힌트] {hint}", file=sys.stderr)


def print_warning(message: str) -> None:
    print(f"[경고] {message}")


def print_info(message: str) -> None:
    print(f"[안내] {message}")


def print_done(message: str) -> None:
    print(f"[완료] {message}")


def print_saved(message: str) -> None:
    print(f"[저장 완료] {message}")
