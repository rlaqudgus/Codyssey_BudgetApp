"""명령 모듈 목록. 각 모듈은 register(subparsers) 함수를 제공한다."""

from __future__ import annotations

from types import ModuleType

from budget_app.cli.commands import add, category, delete, listing, search, update

COMMAND_MODULES: tuple[ModuleType, ...] = (
    add,
    listing,
    search,
    update,
    delete,
    category,
)
