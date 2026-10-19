"""백업/복구: 저장 파일들을 타임스탬프 폴더로 복사하고, 필요하면 되돌린다."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from budget_app.decorators import timed
from budget_app.errors import NotFoundError

BACKUP_DIRNAME = "backups"
DATA_PATTERNS: tuple[str, ...] = ("*.jsonl", "*.seq")


@dataclass(frozen=True)
class BackupInfo:
    name: str
    path: Path
    files: tuple[str, ...]


class BackupService:
    def __init__(self, data_dir: Path, clock: Callable[[], datetime] = datetime.now) -> None:
        self.data_dir = data_dir
        self.root = data_dir / BACKUP_DIRNAME
        self.clock = clock

    @timed
    def create(self, label: str | None = None) -> BackupInfo:
        """data 폴더의 저장 파일을 backups/<YYYYMMDD-HHMMSS>[-label]/ 로 복사한다."""
        name = self.clock().strftime("%Y%m%d-%H%M%S") + (f"-{label}" if label else "")
        target = self._unique(self.root / name)
        target.mkdir(parents=True)
        copied = []
        for src in self._data_files(self.data_dir):
            shutil.copy2(src, target / src.name)
            copied.append(src.name)
        return BackupInfo(target.name, target, tuple(copied))

    def list(self) -> list[BackupInfo]:
        if not self.root.is_dir():
            return []
        backups = [
            BackupInfo(p.name, p, tuple(f.name for f in self._data_files(p)))
            for p in self.root.iterdir()
            if p.is_dir()
        ]
        return sorted(backups, key=lambda b: b.name, reverse=True)

    @timed
    def restore(self, name: str) -> tuple[BackupInfo, BackupInfo]:
        """백업을 현재 데이터로 되돌린다. 되돌리기 전 현재 상태를 자동 백업한다.

        반환: (복구한 백업, 복구 직전 자동 백업)
        """
        source = self.root / name
        if not source.is_dir() or source.parent != self.root:
            raise NotFoundError(
                f"백업을 찾을 수 없습니다: {name}",
                "'backup list' 로 백업 이름을 확인하세요.",
            )
        safety = self.create(label="before-restore")
        files = self._data_files(source)
        for src in files:
            _atomic_copy(src, self.data_dir / src.name)
        return BackupInfo(name, source, tuple(f.name for f in files)), safety

    @staticmethod
    def _data_files(folder: Path) -> list[Path]:
        found = {p for pattern in DATA_PATTERNS for p in folder.glob(pattern) if p.is_file()}
        return sorted(found)

    @staticmethod
    def _unique(path: Path) -> Path:
        candidate, n = path, 1
        while candidate.exists():
            candidate = path.with_name(f"{path.name}-{n}")
            n += 1
        return candidate


def _atomic_copy(src: Path, dest: Path) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{dest.name}.", suffix=".tmp", dir=dest.parent)
    os.close(fd)
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
