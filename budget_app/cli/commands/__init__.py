"""명령 모듈 목록. 각 모듈은 register(subparsers) 함수를 제공한다."""

from __future__ import annotations

from types import ModuleType

COMMAND_MODULES: tuple[ModuleType, ...] = ()
