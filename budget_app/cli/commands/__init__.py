"""명령 모듈 목록. 각 모듈은 register(subparsers) 함수를 제공한다."""

from __future__ import annotations

from types import ModuleType

from budget_app.cli.commands import (
    add,
    backup,
    budget,
    category,
    delete,
    listing,
    recurring,
    search,
    summary,
    transfer,
    update,
)

COMMAND_MODULES: tuple[ModuleType, ...] = (
    add,
    listing,
    search,
    update,
    delete,
    summary,
    budget,
    transfer,
    category,
    recurring,
    backup,
)
