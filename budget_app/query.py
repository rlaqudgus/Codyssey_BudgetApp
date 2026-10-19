"""거래 검색 조건. search / export / summary 가 같은 조건 객체를 공유한다."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date

from budget_app.errors import ValidationError
from budget_app.models import Transaction, TxType


@dataclass(frozen=True)
class SearchCriteria:
    date_from: date | None = None
    date_to: date | None = None
    month: str | None = None  # YYYY-MM
    category: str | None = None
    type: TxType | None = None
    keyword: str | None = None  # 메모 부분 일치(대소문자 무시)
    tag: str | None = None  # 태그 정확히 일치(대소문자 무시)

    def __post_init__(self) -> None:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(
                f"시작일({self.date_from})이 종료일({self.date_to})보다 늦습니다.",
                "--from 은 --to 보다 같거나 이른 날짜여야 합니다.",
            )

    @property
    def is_empty(self) -> bool:
        return all(value is None for value in vars(self).values())

    def matches(self, tx: Transaction) -> bool:
        if self.date_from and tx.date < self.date_from:
            return False
        if self.date_to and tx.date > self.date_to:
            return False
        if self.month and tx.month != self.month:
            return False
        if self.category and tx.category != self.category:
            return False
        if self.type and tx.type is not self.type:
            return False
        if self.keyword and self.keyword.casefold() not in tx.memo.casefold():
            return False
        if self.tag and self.tag.casefold() not in (t.casefold() for t in tx.tags):
            return False
        return True

    def filter(self, stream: Iterable[Transaction]) -> Iterator[Transaction]:
        """조건에 맞는 거래만 흘려보내는 제너레이터(스트리밍 유지)."""
        return (tx for tx in stream if self.matches(tx))
