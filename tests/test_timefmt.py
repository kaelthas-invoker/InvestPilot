from __future__ import annotations

from datetime import timedelta

import pytest

from investpilot.utils import format_age


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0s"),
        (59, "59s"),
        (60, "1m"),
        (3599, "59m"),
        (3600, "1h"),
        (86399, "23h"),
        (86400, "1d"),
    ],
)
def test_format_age_boundaries(seconds: int, expected: str) -> None:
    assert format_age(timedelta(seconds=seconds)) == expected


def test_format_age_future_time_clamped_to_zero() -> None:
    assert format_age(timedelta(seconds=-30)) == "0s"
