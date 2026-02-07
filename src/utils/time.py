from __future__ import annotations

from datetime import datetime, time
from typing import Dict


def is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5


def market_open(dt: datetime, symbol: str, hours: Dict[str, Dict[str, str]]) -> bool:
    if symbol.lower() == "btcusd":
        return True
    if is_weekend(dt):
        return False
    session = hours.get("forex", {"open": "00:00", "close": "23:59"})
    open_time = time.fromisoformat(session["open"])
    close_time = time.fromisoformat(session["close"])
    return open_time <= dt.time() <= close_time
