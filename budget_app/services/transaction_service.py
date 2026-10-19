"""거래 추가/조회/수정/삭제 규칙."""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from budget_app.errors import NotFoundError, ValidationError
from budget_app.models import NewTransaction, Transaction, TransactionPatch
from budget_app.query import SearchCriteria
from budget_app.services.category_service import CategoryService
from budget_app.storage import TransactionRepository


@dataclass(frozen=True)
class ListResult:
    items: list[Transaction]  # 최신순
    total: int  # 조건에 맞는 전체 건수


def latest_first(stream: Iterable[Transaction], limit: int | None) -> ListResult:
    """스트림을 한 번만 순회하며 최신순 상위 limit건만 메모리에 유지한다.

    heapq.nlargest는 크기 limit의 힙만 유지하므로 파일이 아무리 커도
    메모리 사용량은 O(limit)이다. limit이 None이면 조건에 맞는 건만 정렬한다.
    """
    total = 0

    def counted() -> Iterator[Transaction]:
        nonlocal total
        for tx in stream:
            total += 1
            yield tx

    if limit is None:
        items = sorted(counted(), key=lambda tx: tx.sort_key, reverse=True)
    else:
        items = heapq.nlargest(limit, counted(), key=lambda tx: tx.sort_key)
    return ListResult(items=items, total=total)


class TransactionService:
    def __init__(self, repo: TransactionRepository, categories: CategoryService) -> None:
        self.repo = repo
        self.categories = categories

    def add(self, new: NewTransaction) -> Transaction:
        self.categories.require(new.category)
        return self.repo.add(new)

    def latest(self, limit: int) -> ListResult:
        return latest_first(self.repo.iter_all(), limit)

    def search(self, criteria: SearchCriteria, limit: int | None = None) -> ListResult:
        return latest_first(criteria.filter(self.repo.iter_all()), limit)

    def get(self, tx_id: str) -> Transaction:
        normalized = tx_id.strip().upper()
        tx = self.repo.get(normalized)
        if tx is None:
            raise NotFoundError(
                f"id={normalized} 거래가 없습니다 (없는 데이터).",
                "'list' 또는 'search' 로 정확한 거래 id를 확인하세요. 예: TX-000012",
            )
        return tx

    def update(self, tx_id: str, patch: TransactionPatch) -> tuple[Transaction, Transaction]:
        """(수정 전, 수정 후)를 반환한다."""
        if patch.is_empty:
            raise ValidationError(
                "수정할 항목이 없습니다.",
                "--date/--type/--category/--amount/--memo/--tags 중 하나 이상을 지정하세요.",
            )
        before = self.get(tx_id)
        if patch.category is not None:
            self.categories.require(patch.category)
        after = patch.apply(before)
        if after != before:
            self.repo.replace(after)
        return before, after

    def delete(self, tx_id: str) -> Transaction:
        tx = self.get(tx_id)
        self.repo.delete(tx.id)
        return tx
