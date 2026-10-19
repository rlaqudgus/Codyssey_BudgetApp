"""입력 문자열 -> 도메인 값 변환 및 검증.

대화형 입력, 옵션 인자, CSV import가 모두 같은 규칙을 공유하도록 한 곳에 모은다.
검증 실패 시 원인과 힌트를 담은 ValidationError를 던진다.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from budget_app.errors import ValidationError
from budget_app.models import TxType

_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CATEGORY_RE = re.compile(r"^[^\s,]{1,30}$")

_TYPE_ALIASES: dict[str, TxType] = {
    "income": TxType.INCOME,
    "수입": TxType.INCOME,
    "expense": TxType.EXPENSE,
    "지출": TxType.EXPENSE,
}


def parse_date(raw: str) -> date:
    text = raw.strip()
    if _DATE_RE.match(text):
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            pass
    raise ValidationError(
        f"날짜 형식이 올바르지 않습니다 (YYYY-MM-DD): {raw!r}",
        "예: 2024-01-15",
    )


def parse_month(raw: str) -> str:
    text = raw.strip()
    if _MONTH_RE.match(text):
        try:
            datetime.strptime(text, "%Y-%m")
            return text
        except ValueError:
            pass
    raise ValidationError(
        f"월 형식이 올바르지 않습니다 (YYYY-MM): {raw!r}",
        "예: 2024-01",
    )


def parse_type(raw: str) -> TxType:
    tx_type = _TYPE_ALIASES.get(raw.strip().lower())
    if tx_type is None:
        raise ValidationError(
            f"허용되지 않은 타입입니다: {raw!r}",
            "income 또는 expense 중 하나를 입력하세요.",
        )
    return tx_type


def parse_amount(raw: str | int) -> int:
    """양의 정수 금액. '15,000'처럼 천 단위 쉼표는 허용한다."""
    if isinstance(raw, int) and not isinstance(raw, bool):
        value = raw
    else:
        text = str(raw).strip().replace(",", "").replace("_", "")
        if not re.fullmatch(r"[+-]?\d+", text):
            raise ValidationError(
                f"금액은 정수여야 합니다: {raw!r}",
                "예: 15000 (소수점, 문자 없이 숫자만 입력)",
            )
        value = int(text)
    if value <= 0:
        raise ValidationError(
            f"금액은 0보다 커야 합니다: {raw!r}",
            "양수 금액을 입력하세요. 수입/지출 구분은 type으로 합니다.",
        )
    return value


def parse_tags(raw: str) -> tuple[str, ...]:
    """'meal, lunch,,meal' -> ('meal', 'lunch') : 공백 제거, 빈 값/중복 제거, 순서 유지."""
    seen: dict[str, None] = {}
    for part in raw.split(","):
        tag = part.strip()
        if tag:
            seen.setdefault(tag, None)
    return tuple(seen)


def normalize_category(raw: str) -> str:
    """카테고리명은 소문자로 정규화하고 공백/쉼표를 허용하지 않는다."""
    name = raw.strip().lower()
    if not _CATEGORY_RE.match(name):
        raise ValidationError(
            f"카테고리명이 올바르지 않습니다: {raw!r}",
            "공백과 쉼표 없이 1~30자로 입력하세요. 예: food",
        )
    return name


def parse_day(raw: str) -> int:
    text = raw.strip()
    if not text.isdigit() or not 1 <= int(text) <= 31:
        raise ValidationError(
            f"반복 날짜는 1~31 사이의 정수여야 합니다: {raw!r}",
            "예: 25 (해당 월에 없는 날짜면 말일에 생성됩니다)",
        )
    return int(text)


def parse_positive_int(raw: str, *, name: str = "값") -> int:
    text = raw.strip()
    if not text.isdigit() or int(text) <= 0:
        raise ValidationError(
            f"{name}은(는) 1 이상의 정수여야 합니다: {raw!r}",
            "예: 10",
        )
    return int(text)
