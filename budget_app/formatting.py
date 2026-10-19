"""외부 라이브러리 없이 콘솔 표를 정렬하는 포매터.

한글/한자 등 전각 문자는 터미널에서 2칸을 차지하므로 len() 대신
unicodedata.east_asian_width 로 '표시 폭'을 계산해 열을 맞춘다.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from typing import Literal

Align = Literal["left", "right"]

ELLIPSIS = "…"


def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def truncate(text: str, max_width: int) -> str:
    """표시 폭이 max_width를 넘으면 잘라내고 말줄임표를 붙인다."""
    if display_width(text) <= max_width:
        return text
    out: list[str] = []
    width = 0
    for ch in text:
        w = display_width(ch)
        if width + w > max_width - 1:
            break
        out.append(ch)
        width += w
    return "".join(out) + ELLIPSIS


def pad(text: str, width: int, align: Align = "left") -> str:
    gap = " " * max(0, width - display_width(text))
    return gap + text if align == "right" else text + gap


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    aligns: Sequence[Align] | None = None,
    *,
    sep: str = " | ",
) -> str:
    aligns = aligns or ["left"] * len(headers)
    widths = [display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], display_width(cell))

    def line(cells: Sequence[str]) -> str:
        return sep.join(pad(c, widths[i], aligns[i]) for i, c in enumerate(cells)).rstrip()

    rule = "-+-".join("-" * w for w in widths)
    return "\n".join([line(headers), rule, *(line(r) for r in rows)])
