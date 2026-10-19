"""도메인 모델(데이터 구조).

저장 포맷(JSONL)과의 변환(to_dict/from_dict)만 알고, 파일 I/O는 모른다.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date
from enum import Enum
from typing import Any


class TxType(str, Enum):
    """거래 타입."""

    INCOME = "income"
    EXPENSE = "expense"

    def __str__(self) -> str:
        return self.value


TX_ID_PREFIX = "TX-"


def format_tx_id(number: int) -> str:
    """정수 일련번호를 'TX-000012' 형태의 거래 id로 변환한다."""
    return f"{TX_ID_PREFIX}{number:06d}"


def parse_tx_number(tx_id: str) -> int | None:
    """'TX-000012' -> 12. 형식이 다르면 None."""
    if not tx_id.startswith(TX_ID_PREFIX):
        return None
    digits = tx_id[len(TX_ID_PREFIX):]
    return int(digits) if digits.isdigit() else None


@dataclass(frozen=True)
class NewTransaction:
    """id가 아직 부여되지 않은 거래(입력 단계의 데이터)."""

    type: TxType
    date: date
    amount: int
    category: str
    memo: str = ""
    tags: tuple[str, ...] = ()
    source: str | None = None  # 반복 규칙으로 생성된 경우 "RC-001@2024-01"

    def with_id(self, tx_id: str) -> Transaction:
        return Transaction(
            id=tx_id,
            type=self.type,
            date=self.date,
            amount=self.amount,
            category=self.category,
            memo=self.memo,
            tags=self.tags,
            source=self.source,
        )


@dataclass(frozen=True)
class Transaction:
    """저장된 거래 1건."""

    id: str
    type: TxType
    date: date
    amount: int
    category: str
    memo: str = ""
    tags: tuple[str, ...] = ()
    source: str | None = None  # 반복 규칙으로 생성된 경우 "RC-001@2024-01"

    @property
    def month(self) -> str:
        """'YYYY-MM'"""
        return self.date.strftime("%Y-%m")

    @property
    def sort_key(self) -> tuple[date, int]:
        """최신순 정렬 키: 날짜가 같으면 나중에 등록된(id가 큰) 거래가 더 최신."""
        return (self.date, parse_tx_number(self.id) or 0)

    def to_dict(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
            "date": self.date.isoformat(),
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": list(self.tags),
        }
        if self.source:
            record["source"] = self.source
        return record

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transaction:
        """저장 레코드 -> Transaction. 레코드가 손상되었으면 ValueError/KeyError/TypeError."""
        amount = data["amount"]
        if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
            raise ValueError(f"잘못된 금액: {amount!r}")
        return cls(
            id=str(data["id"]),
            type=TxType(data["type"]),
            date=date.fromisoformat(data["date"]),
            amount=amount,
            category=str(data["category"]),
            memo=str(data.get("memo") or ""),
            tags=tuple(str(t) for t in data.get("tags") or ()),
            source=data.get("source") or None,
        )


@dataclass(frozen=True)
class TransactionPatch:
    """update 시 변경할 필드만 담는다(None = 변경 안 함)."""

    type: TxType | None = None
    date: date | None = None
    amount: int | None = None
    category: str | None = None
    memo: str | None = None
    tags: tuple[str, ...] | None = None

    @property
    def is_empty(self) -> bool:
        return all(getattr(self, f.name) is None for f in fields(self))

    def apply(self, tx: Transaction) -> Transaction:
        changes = {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None}
        return replace(tx, **changes)


@dataclass(frozen=True)
class Budget:
    """월 예산."""

    month: str  # YYYY-MM
    amount: int

    def to_dict(self) -> dict[str, Any]:
        return {"month": self.month, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Budget:
        amount = data["amount"]
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError(f"잘못된 예산 금액: {amount!r}")
        return cls(month=str(data["month"]), amount=amount)


RC_ID_PREFIX = "RC-"


@dataclass(frozen=True)
class RecurringRule:
    """매달 반복되는 거래 규칙(월급, 월세 등)."""

    id: str  # RC-001
    day: int  # 1~31, 해당 월에 그 날짜가 없으면 말일로 생성
    type: TxType
    amount: int
    category: str
    memo: str = ""
    tags: tuple[str, ...] = ()

    def source_key(self, month: str) -> str:
        """같은 규칙이 같은 달에 두 번 생성되지 않도록 거래에 남기는 출처 키."""
        return f"{self.id}@{month}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "day": self.day,
            "type": self.type.value,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecurringRule:
        day, amount = data["day"], data["amount"]
        if not isinstance(day, int) or not 1 <= day <= 31:
            raise ValueError(f"잘못된 반복 날짜: {day!r}")
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError(f"잘못된 금액: {amount!r}")
        return cls(
            id=str(data["id"]),
            day=day,
            type=TxType(data["type"]),
            amount=amount,
            category=str(data["category"]),
            memo=str(data.get("memo") or ""),
            tags=tuple(str(t) for t in data.get("tags") or ()),
        )
