"""원자적 파일 쓰기.

같은 폴더의 임시 파일에 먼저 모두 쓴 뒤 fsync -> os.replace(rename)로 교체한다.
쓰는 도중 예외/전원 차단이 나도 원본 파일은 '이전 상태 그대로' 남는다.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TextIO


@contextmanager
def atomic_write(path: Path, *, newline: str | None = "\n") -> Iterator[TextIO]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as fh:
            yield fh
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        with suppress(FileNotFoundError):
            tmp_path.unlink()
        raise
