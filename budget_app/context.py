"""애플리케이션 조립(Composition Root).

데이터 폴더를 열고(없으면 초기화), 저장소와 서비스 객체를 연결한다.
CLI 명령은 AppContext만 받아서 필요한 서비스를 꺼내 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from budget_app.errors import StorageError
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
