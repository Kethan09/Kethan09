from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class PaperOrder:
    symbol: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    size: float
    created_at: datetime


class PaperExecution:
    def __init__(self) -> None:
        self.orders: List[PaperOrder] = []

    def place_bracket(self, symbol: str, direction: str, entry: float, stop_loss: float, take_profit: float, size: float) -> PaperOrder:
        order = PaperOrder(
            symbol=symbol,
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            size=size,
            created_at=datetime.utcnow(),
        )
        self.orders.append(order)
        return order
