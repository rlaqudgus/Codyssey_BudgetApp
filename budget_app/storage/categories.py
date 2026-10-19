"""카테고리 저장소(categories.jsonl). 레코드: {"name": "food"}"""

from __future__ import annotations

from pathlib import Path

from budget_app.storage.jsonl import JsonlFile

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "food",
    "transport",
    "rent",
    "shopping",
    "salary",
    "etc",
)


class CategoryStore:
    FILENAME = "categories.jsonl"

    def __init__(self, data_dir: Path) -> None:
        self.file = JsonlFile(data_dir / self.FILENAME)

    def ensure_exists(self) -> bool:
        return self.file.ensure_exists()

    def names(self) -> list[str]:
        return list(self.file.load(_category_name))

    def exists(self, name: str) -> bool:
        return any(n == name for n in self.file.load(_category_name))

    def add(self, name: str) -> None:
        self.file.append({"name": name})

    def remove(self, name: str) -> None:
        self.file.rewrite({"name": n} for n in self.names() if n != name)

    def seed_defaults_if_empty(self) -> tuple[str, ...]:
        """(정책 A) 카테고리가 하나도 없으면 기본 카테고리를 생성하고 생성된 목록을 반환."""
        if self.names():
            return ()
        self.file.rewrite({"name": n} for n in DEFAULT_CATEGORIES)
        return DEFAULT_CATEGORIES


def _category_name(record: dict[str, object]) -> str:
    name = record["name"]
    if not isinstance(name, str) or not name:
        raise ValueError(f"잘못된 카테고리 이름: {name!r}")
    return name
