"""거래 저장소(transactions.jsonl)."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from budget_app.models import NewTransaction, Transaction, format_tx_id, parse_tx_number
from budget_app.storage.atomic import atomic_write
from budget_app.storage.jsonl import JsonlFile, Record


class TransactionRepository:
    FILENAME = "transactions.jsonl"
    SEQUENCE_FILENAME = "transactions.seq"

    def __init__(self, data_dir: Path) -> None:
        self.file = JsonlFile(data_dir / self.FILENAME)
        # 마지막으로 발급한 일련번호. 삭제된 id가 재사용되지 않도록 별도로 기록한다.
        self.sequence_path = data_dir / self.SEQUENCE_FILENAME

    def ensure_exists(self) -> bool:
        return self.file.ensure_exists()

    def iter_all(self) -> Iterator[Transaction]:
        """저장 순서대로 거래를 하나씩 yield 한다(스트리밍)."""
        yield from self.file.load(Transaction.from_dict)

    def get(self, tx_id: str) -> Transaction | None:
        return next((tx for tx in self.iter_all() if tx.id == tx_id), None)

    def next_id(self) -> str:
        """현재까지의 최대 일련번호 + 1. 메모리에는 최대값 하나만 유지한다."""
        return format_tx_id(self._max_number() + 1)

    def add(self, new: NewTransaction) -> Transaction:
        tx = new.with_id(self.next_id())
        self.file.append(tx.to_dict())
        self._save_sequence(parse_tx_number(tx.id) or 0)
        return tx

    def add_many(self, items: Iterable[NewTransaction]) -> list[Transaction]:
        """여러 건을 한 번에 추가한다. 중간에 실패하면 아무것도 반영되지 않는다(원자적)."""
        number = self._max_number()
        added: list[Transaction] = []

        def records() -> Iterator[Record]:
            nonlocal number
            yield from self.file.stream()
            for new in items:
                number += 1
                tx = new.with_id(format_tx_id(number))
                added.append(tx)
                yield tx.to_dict()

        self.file.rewrite(records())
        self._save_sequence(number)
        return added

    def replace(self, updated: Transaction) -> None:
        """같은 id의 거래를 updated로 교체한다(임시 파일 + 원자적 교체)."""

        def records() -> Iterator[Record]:
            for tx in self.iter_all():
                yield (updated if tx.id == updated.id else tx).to_dict()

        self.file.rewrite(records())

    def delete(self, tx_id: str) -> None:
        def records() -> Iterator[Record]:
            for tx in self.iter_all():
                if tx.id != tx_id:
                    yield tx.to_dict()

        self.file.rewrite(records())

    def count_by_category(self, category: str) -> int:
        return sum(1 for tx in self.iter_all() if tx.category == category)

    def recategorize(self, old: str, new: str) -> int:
        """old 카테고리를 쓰는 모든 거래를 new로 변경하고 변경 건수를 반환한다."""
        changed = 0

        def records() -> Iterator[Record]:
            nonlocal changed
            for tx in self.iter_all():
                if tx.category == old:
                    changed += 1
                    record = tx.to_dict()
                    record["category"] = new
                    yield record
                else:
                    yield tx.to_dict()

        self.file.rewrite(records())
        return changed

    def _max_number(self) -> int:
        """발급 기록과 실제 파일의 최대 번호 중 큰 값(시퀀스 파일이 없어도 안전)."""
        in_file = max((parse_tx_number(tx.id) or 0 for tx in self.iter_all()), default=0)
        return max(in_file, self._load_sequence())

    def _load_sequence(self) -> int:
        try:
            value = json.loads(self.sequence_path.read_text(encoding="utf-8")).get("last", 0)
        except (FileNotFoundError, ValueError, AttributeError):
            return 0
        return value if isinstance(value, int) else 0

    def _save_sequence(self, number: int) -> None:
        with atomic_write(self.sequence_path) as fh:
            fh.write(json.dumps({"last": number}))
