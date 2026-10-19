"""카테고리 관리 규칙."""

from __future__ import annotations

from collections import Counter

from budget_app.errors import ConflictError, NotFoundError, ValidationError
from budget_app.storage import CategoryStore, TransactionRepository
from budget_app.validators import normalize_category


class CategoryService:
    def __init__(self, store: CategoryStore, transactions: TransactionRepository) -> None:
        self.store = store
        self.transactions = transactions

    def names(self) -> list[str]:
        return self.store.names()

    def list_with_usage(self) -> list[tuple[str, int]]:
        """(카테고리, 사용 중인 거래 수). 거래 파일은 한 번만 스트리밍한다."""
        usage = Counter(tx.category for tx in self.transactions.iter_all())
        return [(name, usage.get(name, 0)) for name in self.store.names()]

    def require(self, raw: str) -> str:
        """등록된 카테고리면 정규화된 이름을, 아니면 ValidationError."""
        name = normalize_category(raw)
        if not self.store.exists(name):
            raise ValidationError(
                f"등록되지 않은 카테고리입니다: {name}",
                f"등록된 카테고리: {', '.join(self.store.names()) or '(없음)'}"
                " / 새 카테고리는 'category add' 로 등록하세요.",
            )
        return name

    def add(self, raw: str) -> str:
        name = normalize_category(raw)
        if self.store.exists(name):
            raise ConflictError(
                f"이미 등록된 카테고리입니다: {name}",
                "'category list' 로 등록된 카테고리를 확인하세요.",
            )
        self.store.add(name)
        return name

    def usage_count(self, raw: str) -> int:
        name = self._existing(raw)
        return self.transactions.count_by_category(name)

    def remove(self, raw: str, replacement: str | None = None) -> int:
        """카테고리를 삭제하고 대체 카테고리로 옮긴 거래 수를 반환한다.

        사용 중인 거래가 있는데 대체 카테고리가 없으면 삭제를 막는다(데이터 보호).
        """
        name = self._existing(raw)
        used = self.transactions.count_by_category(name)
        moved = 0
        if used:
            if replacement is None:
                raise ConflictError(
                    f"'{name}' 카테고리를 사용하는 거래가 {used}건 있어 삭제할 수 없습니다.",
                    f"대체 카테고리를 지정하세요. 예: category remove --name {name} --replace etc",
                )
            target = self.require(replacement)
            if target == name:
                raise ValidationError(
                    "삭제할 카테고리와 대체 카테고리가 같습니다.",
                    "다른 카테고리를 대체 카테고리로 지정하세요.",
                )
            moved = self.transactions.recategorize(name, target)
        self.store.remove(name)
        return moved

    def _existing(self, raw: str) -> str:
        name = normalize_category(raw)
        if not self.store.exists(name):
            raise NotFoundError(
                f"존재하지 않는 카테고리입니다: {name}",
                "'category list' 로 등록된 카테고리를 확인하세요.",
            )
        return name
