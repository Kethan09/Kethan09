from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class RiskLimits:
    risk_per_trade: float
    max_open_trades: int
    max_daily_loss: float
    max_weekly_loss: float
    cooldown_after_loss_minutes: int


@dataclass
class AccountState:
    balance: float
    equity: float
    open_trades: int
    daily_pnl: float
    weekly_pnl: float
    last_loss_time: Optional[datetime]


def position_size(balance: float, risk_per_trade: float, stop_distance: float) -> float:
    if stop_distance <= 0:
        return 0.0
    return (balance * risk_per_trade) / stop_distance


def can_trade(state: AccountState, limits: RiskLimits, now: datetime) -> bool:
    if state.open_trades >= limits.max_open_trades:
        return False
    if state.daily_pnl <= -abs(limits.max_daily_loss):
        return False
    if state.weekly_pnl <= -abs(limits.max_weekly_loss):
        return False
    if state.last_loss_time:
        cooldown = state.last_loss_time + timedelta(minutes=limits.cooldown_after_loss_minutes)
        if now < cooldown:
            return False
    return True
