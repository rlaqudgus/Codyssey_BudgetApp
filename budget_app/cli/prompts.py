"""대화형 입력 도우미: 검증에 실패하면 원인/힌트를 보여주고 다시 입력받는다."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from budget_app.console import print_error
from budget_app.errors import AppError, ValidationError

T = TypeVar("T")


def ask(prompt: str, parse: Callable[[str], T], *, default: str | None = None) -> T:
    """parse가 성공할 때까지 반복해서 입력받는다. 빈 입력이면 default를 사용."""
    while True:
        raw = read_line(prompt)
        if not raw.strip() and default is not None:
            raw = default
        try:
            return parse(raw)
        except ValidationError as exc:
            print_error(exc.message, exc.hint)


def ask_text(prompt: str) -> str:
    """선택 입력(빈 값 허용)."""
    return read_line(prompt).strip()


def confirm(prompt: str) -> bool:
    return read_line(f"{prompt} (y/N): ").strip().lower() in {"y", "yes", "예", "ㅛ"}


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        print()
        raise AppError(
            "입력이 끝나 작업을 취소했습니다.",
            "대화형 입력이 필요한 명령입니다. 터미널에서 직접 실행하거나 옵션으로 값을 지정하세요.",
        ) from None
