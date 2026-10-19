"""거래 추가/조회/수정/삭제 규칙."""

from __future__ import annotations

from budget_app.models import NewTransaction, Transaction
from budget_app.services.category_service import CategoryService
from budget_app.storage import TransactionRepository


class TransactionService:
    def __init__(self, repo: TransactionRepository, categories: CategoryService) -> None:
        self.repo = repo
        self.categories = categories

    def add(self, new: NewTransaction) -> Transaction:
        self.categories.require(new.category)
        return self.repo.add(new)
