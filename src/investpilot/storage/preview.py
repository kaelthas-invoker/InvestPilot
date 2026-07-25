from __future__ import annotations


def first_line_preview(content: str, *, max_width: int = 60) -> str:
    """返回内容首行的预览（见 SPEC §9）。

    以 `\\n` 切出首行并 rstrip；按字符数（非显示宽度）截断，
    超长时保留 max_width-1 个字符并追加 `…`。
    """
    line = content.split("\n", 1)[0].rstrip()
    if len(line) <= max_width:
        return line
    return line[: max_width - 1] + "…"
