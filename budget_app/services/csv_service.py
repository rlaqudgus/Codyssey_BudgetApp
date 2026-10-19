"""CSV 가져오기/내보내기.

고정 스키마(UTF-8, 헤더 포함):
    date,type,category,amount,memo,tags
    - date     (필수) YYYY-MM-DD
    - type     (필수) income / expense
    - category (필수) 등록된 카테고리
    - amount   (필수) 양의 정수
    - memo     (선택) 문자열
    - tags     (선택) 쉼표(,)로 구분된 문자열 -> CSV에서는 따옴표로 감싼다. 예: "meal,team"
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from budget_app.decorators import timed
from budget_app.errors import AppError, NotFoundError, ValidationError
from budget_app.models import NewTransaction, Transaction
from budget_app.query import SearchCriteria
from budget_app.services.category_service import CategoryService
from budget_app.storage import TransactionRepository
from budget_app.storage.atomic import atomic_write
from budget_app.validators import (
    normalize_category,
    parse_amount,
    parse_date,
    parse_tags,
    parse_type,
)

CSV_COLUMNS: tuple[str, ...] = ("date", "type", "category", "amount", "memo", "tags")
REQUIRED_COLUMNS: tuple[str, ...] = ("date", "type", "category", "amount")


@dataclass(frozen=True)
class RowError:
    line: int  # CSV 파일 기준 줄 번호(헤더 = 1)
    reason: str


@dataclass
class ImportResult:
    imported: list[Transaction] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    created_categories: list[str] = field(default_factory=list)

    @property
    def skipped(self) -> int:
        return len(self.errors)


class CsvTransferService:
    def __init__(self, repo: TransactionRepository, categories: CategoryService) -> None:
        self.repo = repo
        self.categories = categories

    @timed
    def export(self, out: Path, criteria: SearchCriteria) -> int:
        """조건에 맞는 거래를 날짜 오름차순으로 CSV에 쓴다(임시 파일 후 교체)."""
        if criteria.is_empty:
            raise ValidationError(
                "내보낼 기간 조건이 없습니다.",
                "--month YYYY-MM 또는 --from YYYY-MM-DD --to YYYY-MM-DD 중 하나 이상을 지정하세요.",
            )
        rows = sorted(criteria.filter(self.repo.iter_all()), key=lambda tx: tx.sort_key)
        with atomic_write(out, newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for tx in rows:
                writer.writerow(
                    {
                        "date": tx.date.isoformat(),
                        "type": tx.type.value,
                        "category": tx.category,
                        "amount": tx.amount,
                        "memo": tx.memo,
                        "tags": ",".join(tx.tags),
                    }
                )
        return len(rows)

    @timed
    def import_csv(self, src: Path, *, create_categories: bool = False) -> ImportResult:
        """유효한 행만 일괄 등록하고, 잘못된 행은 사유와 함께 건너뛴다.

        행을 한 줄씩 검증하며 저장소에 흘려보내므로 큰 CSV도 메모리에 모두 올리지 않는다.
        저장은 임시 파일 + 원자적 교체라 도중에 실패하면 아무것도 반영되지 않는다.
        """
        if not src.is_file():
            raise NotFoundError(
                f"가져올 CSV 파일을 찾을 수 없습니다: {src}",
                "경로를 확인하세요. 예: import --from samples/import_sample.csv",
            )
        result = ImportResult()
        known = set(self.categories.names())
        try:
            with src.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                reader.fieldnames = self._check_header(reader.fieldnames)
                result.imported = self.repo.add_many(
                    self._valid_rows(reader, result, known, create_categories)
                )
        except UnicodeDecodeError:
            raise AppError(
                f"CSV 파일이 UTF-8 인코딩이 아닙니다: {src}",
                "엑셀에서 'CSV UTF-8(쉼표로 분리)' 형식으로 다시 저장하세요.",
            ) from None
        except csv.Error as exc:
            raise AppError(
                f"CSV 형식을 읽을 수 없습니다: {exc}",
                "따옴표/쉼표가 올바르게 짝지어졌는지 확인하세요.",
            ) from None
        return result

    def _valid_rows(
        self,
        reader: csv.DictReader[str],
        result: ImportResult,
        known: set[str],
        create_categories: bool,
    ) -> Iterator[NewTransaction]:
        for row in reader:
            line = reader.line_num
            if not any((value or "").strip() for value in row.values()):
                continue  # 빈 줄
            try:
                new = NewTransaction(
                    date=parse_date(row.get("date") or ""),
                    type=parse_type(row.get("type") or ""),
                    category=normalize_category(row.get("category") or ""),
                    amount=parse_amount(row.get("amount") or ""),
                    memo=(row.get("memo") or "").strip(),
                    tags=parse_tags(row.get("tags") or ""),
                )
                if new.category not in known:
                    if not create_categories:
                        raise ValidationError(f"등록되지 않은 카테고리 '{new.category}'")
                    # 거래보다 카테고리를 먼저 저장해 '없는 카테고리를 참조하는 거래'가 생기지 않게 한다.
                    self.categories.add(new.category)
                    known.add(new.category)
                    result.created_categories.append(new.category)
                yield new
            except ValidationError as exc:
                result.errors.append(RowError(line, exc.message))

    @staticmethod
    def _check_header(fieldnames: list[str] | None) -> list[str]:
        """헤더 이름의 공백/대소문자를 정규화해 반환한다. 필수 컬럼이 없으면 오류."""
        columns = [name.strip().lower() for name in fieldnames or []]
        missing = [col for col in REQUIRED_COLUMNS if col not in columns]
        if missing:
            raise ValidationError(
                f"CSV 헤더에 필수 컬럼이 없습니다: {', '.join(missing)}",
                f"첫 줄은 다음 헤더여야 합니다: {','.join(CSV_COLUMNS)}",
            )
        return columns
