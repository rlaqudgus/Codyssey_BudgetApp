"""애플리케이션 조립(Composition Root).

데이터 폴더를 열고(없으면 초기화), 저장소와 서비스 객체를 연결한다.
CLI 명령은 AppContext만 받아서 필요한 서비스를 꺼내 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from budget_app.errors import StorageError
from budget_app.services.backup_service import BackupService
from budget_app.services.budget_service import BudgetService
from budget_app.services.category_service import CategoryService
from budget_app.services.csv_service import CsvTransferService
from budget_app.services.report_service import ReportService
from budget_app.services.transaction_service import TransactionService
from budget_app.storage import BudgetStore, CategoryStore, TransactionRepository


@dataclass
class AppContext:
    data_dir: Path
    transactions: TransactionRepository
    categories: CategoryStore
    budgets: BudgetStore
    notices: list[str] = field(default_factory=list)

    @classmethod
    def open(cls, data_dir: Path) -> AppContext:
        if data_dir.exists() and not data_dir.is_dir():
            raise StorageError(
                f"데이터 경로가 폴더가 아닙니다: {data_dir}",
                "--data-dir 로 다른 폴더를 지정하세요.",
            )
        data_dir.mkdir(parents=True, exist_ok=True)

        ctx = cls(
            data_dir=data_dir,
            transactions=TransactionRepository(data_dir),
            categories=CategoryStore(data_dir),
            budgets=BudgetStore(data_dir),
        )
        ctx._initialize()
        return ctx

    @cached_property
    def category_service(self) -> CategoryService:
        return CategoryService(self.categories, self.transactions)

    @cached_property
    def transaction_service(self) -> TransactionService:
        return TransactionService(self.transactions, self.category_service)

    @cached_property
    def report_service(self) -> ReportService:
        return ReportService(self.transactions, self.budgets)

    @cached_property
    def budget_service(self) -> BudgetService:
        return BudgetService(self.budgets)

    @cached_property
    def csv_service(self) -> CsvTransferService:
        return CsvTransferService(self.transactions, self.category_service)

    @cached_property
    def backup_service(self) -> BackupService:
        return BackupService(self.data_dir)

    def _initialize(self) -> None:
        created = [
            store.file.path.name
            for store in (self.transactions, self.categories, self.budgets)
            if store.ensure_exists()
        ]
        if created:
            self.notices.append(
                f"저장 파일을 새로 만들었습니다: {self.data_dir} ({', '.join(created)})"
            )
        seeded = self.categories.seed_defaults_if_empty()
        if seeded:
            self.notices.append(
                f"카테고리가 비어 있어 기본 카테고리를 생성했습니다: {', '.join(seeded)}"
            )
