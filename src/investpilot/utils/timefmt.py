from __future__ import annotations

from datetime import timedelta


def format_age(delta: timedelta) -> str:
    """把时间差格式化为 k8s 风格的紧凑年龄字符串（见 SPEC §10）。

    未来时间（负 delta）被钳位为 0s。边界：
    0s->"0s", 59s->"59s", 60s->"1m", 3599s->"59m", 3600s->"1h",
    86399s->"23h", 86400s->"1d"。
    """
    s = max(0, int(delta.total_seconds()))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"
