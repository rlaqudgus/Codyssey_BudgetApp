"""JSONL(한 줄 = JSON 객체 1개) 파일 접근 계층.

- stream(): 파일을 한 줄씩 읽어 yield 하는 제너레이터. 파일 전체를 메모리에 올리지 않는다.
- append(): 끝에 한 줄 추가(add 시 기존 데이터를 다시 쓰지 않음).
- rewrite(): 레코드 이터러블을 임시 파일에 쓰고 원자적으로 교체(update/delete/import).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from budget_app.decorators import timed
from budget_app.errors import StorageError
from budget_app.storage.atomic import atomic_write

Record = dict[str, Any]


class JsonlFile:
    def __init__(self, path: Path) -> None:
        self.path = path

    def ensure_exists(self) -> bool:
        """파일이 없으면 빈 파일을 만든다. 새로 만들었으면 True."""
        if self.path.exists():
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()
        return True

    def stream(self) -> Iterator[Record]:
        """레코드를 한 줄씩 지연 로딩한다. 빈 줄은 건너뛴다."""
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise self.corrupted(line_no, exc.msg) from None
                if not isinstance(record, dict):
                    raise self.corrupted(line_no, "JSON 객체가 아닙니다")
                yield record

    def append(self, record: Record) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(_dumps(record))
            fh.flush()
            os.fsync(fh.fileno())

    @timed
    def rewrite(self, records: Iterable[Record]) -> int:
        """records로 파일 전체를 원자적으로 교체한다. records가 self.stream()을
        소비하는 제너레이터여도 안전하다(임시 파일에 쓰고 마지막에 교체하므로)."""
        count = 0
        with atomic_write(self.path) as fh:
            for record in records:
                fh.write(_dumps(record))
                count += 1
        return count

    def corrupted(self, line_no: int | None, reason: str) -> StorageError:
        where = f"{self.path} {line_no}번째 줄" if line_no else str(self.path)
        return StorageError(
            f"저장 파일이 손상되었습니다: {where} ({reason})",
            "backup restore 로 백업을 복구하거나, 해당 줄을 직접 수정/삭제한 뒤 다시 실행하세요.",
        )


def _dumps(record: Record) -> str:
    return json.dumps(record, ensure_ascii=False) + "\n"
