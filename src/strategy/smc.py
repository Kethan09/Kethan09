from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class SwingPoint:
    index: int
    kind: str  # "high" or "low"
    price: float


@dataclass
class StructureEvent:
    index: int
    kind: str  # "BOS" or "CHOCH"
    direction: str  # "bull" or "bear"
    level: float


@dataclass
class LiquiditySweep:
    index: int
    kind: str  # "sweep_high" or "sweep_low"
    level: float


@dataclass
class FairValueGap:
    index: int
    kind: str  # "bull" or "bear"
    upper: float
    lower: float
    size: float


@dataclass
class OrderBlock:
    index: int
    kind: str  # "bull" or "bear"
    upper: float
    lower: float
    mitigated: bool


@dataclass
class Setup:
    symbol: str
    style: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    rr: float
    poi: str
    invalidation: str
    htf_timeframes: List[str]
    entry_timeframes: List[str]
    reasons: List[str]


def find_swings(df: pd.DataFrame, lookback: int) -> List[SwingPoint]:
    swings: List[SwingPoint] = []
    if lookback < 1 or df.empty:
        return swings
    highs = df["high"].values
    lows = df["low"].values
    for i in range(lookback, len(df) - lookback):
        window_high = highs[i - lookback : i + lookback + 1]
        window_low = lows[i - lookback : i + lookback + 1]
        if highs[i] == window_high.max():
            swings.append(SwingPoint(index=i, kind="high", price=highs[i]))
        if lows[i] == window_low.min():
            swings.append(SwingPoint(index=i, kind="low", price=lows[i]))
    return sorted(swings, key=lambda s: s.index)


def detect_bos_choch(df: pd.DataFrame, swings: List[SwingPoint]) -> List[StructureEvent]:
    events: List[StructureEvent] = []
    trend: Optional[str] = None
    last_high = None
    last_low = None
    swing_map = {s.index: s for s in swings}
    for i in range(len(df)):
        if i in swing_map:
            swing = swing_map[i]
            if swing.kind == "high":
                last_high = swing.price
            else:
                last_low = swing.price
        close = df.loc[i, "close"]
        if last_high is not None and close > last_high:
            kind = "BOS" if trend in (None, "bull") else "CHOCH"
            events.append(StructureEvent(index=i, kind=kind, direction="bull", level=last_high))
            trend = "bull"
            last_high = close
        if last_low is not None and close < last_low:
            kind = "BOS" if trend in (None, "bear") else "CHOCH"
            events.append(StructureEvent(index=i, kind=kind, direction="bear", level=last_low))
            trend = "bear"
            last_low = close
    return events


def detect_liquidity_sweeps(
    df: pd.DataFrame, swings: List[SwingPoint], lookahead: int = 3
) -> List[LiquiditySweep]:
    sweeps: List[LiquiditySweep] = []
    for swing in swings:
        start = swing.index + 1
        end = min(len(df), swing.index + 1 + lookahead)
        for i in range(start, end):
            high = df.loc[i, "high"]
            low = df.loc[i, "low"]
            close = df.loc[i, "close"]
            if swing.kind == "high" and high > swing.price and close < swing.price:
                sweeps.append(LiquiditySweep(index=i, kind="sweep_high", level=swing.price))
                break
            if swing.kind == "low" and low < swing.price and close > swing.price:
                sweeps.append(LiquiditySweep(index=i, kind="sweep_low", level=swing.price))
                break
    return sweeps


def detect_fvg(df: pd.DataFrame, min_size: float = 0.0) -> List[FairValueGap]:
    gaps: List[FairValueGap] = []
    for i in range(2, len(df)):
        candle1 = df.loc[i - 2]
        candle3 = df.loc[i]
        if candle3["low"] > candle1["high"]:
            size = candle3["low"] - candle1["high"]
            if size >= min_size:
                gaps.append(
                    FairValueGap(index=i, kind="bull", upper=candle3["low"], lower=candle1["high"], size=size)
                )
        if candle3["high"] < candle1["low"]:
            size = candle1["low"] - candle3["high"]
            if size >= min_size:
                gaps.append(
                    FairValueGap(index=i, kind="bear", upper=candle1["low"], lower=candle3["high"], size=size)
                )
    return gaps


def detect_order_blocks(
    df: pd.DataFrame,
    displacement_threshold: float,
    mitigation_check: bool = True,
) -> List[OrderBlock]:
    blocks: List[OrderBlock] = []
    for i in range(1, len(df)):
        prev = df.loc[i - 1]
        curr = df.loc[i]
        if curr["close"] - curr["open"] >= displacement_threshold and curr["close"] > prev["high"]:
            if prev["close"] < prev["open"]:
                mitigated = False
                if mitigation_check:
                    future = df.loc[i + 1 :] if i + 1 < len(df) else pd.DataFrame()
                    mitigated = (future["low"] <= prev["high"]).any() if not future.empty else False
                blocks.append(
                    OrderBlock(index=i - 1, kind="bull", upper=prev["high"], lower=prev["low"], mitigated=mitigated)
                )
        if prev["open"] - prev["close"] >= displacement_threshold and curr["close"] < prev["low"]:
            if prev["close"] > prev["open"]:
                mitigated = False
                if mitigation_check:
                    future = df.loc[i + 1 :] if i + 1 < len(df) else pd.DataFrame()
                    mitigated = (future["high"] >= prev["low"]).any() if not future.empty else False
                blocks.append(
                    OrderBlock(index=i - 1, kind="bear", upper=prev["high"], lower=prev["low"], mitigated=mitigated)
                )
    return blocks


def premium_discount_zone(htf_swings: List[SwingPoint]) -> Optional[Tuple[float, float, float]]:
    highs = [s for s in htf_swings if s.kind == "high"]
    lows = [s for s in htf_swings if s.kind == "low"]
    if not highs or not lows:
        return None
    last_high = max(highs, key=lambda s: s.index).price
    last_low = max(lows, key=lambda s: s.index).price
    equilibrium = (last_high + last_low) / 2
    return last_low, equilibrium, last_high


def select_poi(
    direction: str,
    fvg: List[FairValueGap],
    obs: List[OrderBlock],
    zone: Optional[Tuple[float, float, float]],
) -> Optional[Tuple[str, float, float]]:
    if zone is None:
        return None
    low, eq, high = zone
    if direction == "bull":
        candidates = [
            ("OB", ob.lower, ob.upper)
            for ob in obs
            if ob.kind == "bull" and ob.lower <= eq
        ] + [
            ("FVG", gap.lower, gap.upper)
            for gap in fvg
            if gap.kind == "bull" and gap.lower <= eq
        ]
    else:
        candidates = [
            ("OB", ob.lower, ob.upper)
            for ob in obs
            if ob.kind == "bear" and ob.upper >= eq
        ] + [
            ("FVG", gap.lower, gap.upper)
            for gap in fvg
            if gap.kind == "bear" and gap.upper >= eq
        ]
    if not candidates:
        return None
    return candidates[-1]


def build_setup(
    symbol: str,
    style: str,
    htf_df: pd.DataFrame,
    entry_df: pd.DataFrame,
    lookback: int,
    sweep_lookahead: int,
    fvg_min: float,
    displacement_threshold: float,
) -> Optional[Setup]:
    htf_swings = find_swings(htf_df, lookback)
    htf_structure = detect_bos_choch(htf_df, htf_swings)
    if not htf_structure:
        return None
    bias_event = htf_structure[-1]
    direction = bias_event.direction

    entry_swings = find_swings(entry_df, lookback)
    sweeps = detect_liquidity_sweeps(entry_df, entry_swings, lookahead=sweep_lookahead)
    if not sweeps:
        return None
    last_sweep = sweeps[-1]
    if direction == "bull" and last_sweep.kind != "sweep_low":
        return None
    if direction == "bear" and last_sweep.kind != "sweep_high":
        return None

    entry_structure = detect_bos_choch(entry_df, entry_swings)
    confirmation = [e for e in entry_structure if e.index > last_sweep.index and e.direction == direction]
    if len(confirmation) < 2:
        return None

    fvgs = detect_fvg(entry_df, min_size=fvg_min)
    obs = detect_order_blocks(entry_df, displacement_threshold=displacement_threshold)
    zone = premium_discount_zone(htf_swings)
    poi = select_poi(direction, fvgs, obs, zone)
    if poi is None:
        return None
    poi_name, poi_low, poi_high = poi
    entry = (poi_low + poi_high) / 2

    if direction == "bull":
        stop_loss = min(entry_df.loc[last_sweep.index, "low"], poi_low)
        target_level = max([s.price for s in entry_swings if s.kind == "high"], default=entry * 1.03)
    else:
        stop_loss = max(entry_df.loc[last_sweep.index, "high"], poi_high)
        target_level = min([s.price for s in entry_swings if s.kind == "low"], default=entry * 0.97)

    risk = abs(entry - stop_loss)
    if risk == 0:
        return None
    rr_target = entry + 3 * risk if direction == "bull" else entry - 3 * risk
    take_profit = rr_target if direction == "bull" else rr_target
    if direction == "bull" and target_level < rr_target:
        take_profit = target_level
    if direction == "bear" and target_level > rr_target:
        take_profit = target_level

    rr = abs(take_profit - entry) / risk
    if rr < 3:
        return None

    invalidation = f"Close beyond {stop_loss:.2f}"
    return Setup(
        symbol=symbol,
        style=style,
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        rr=rr,
        poi=poi_name,
        invalidation=invalidation,
        htf_timeframes=[],
        entry_timeframes=[],
        reasons=[
            f"HTF bias {direction}",
            f"Liquidity sweep {last_sweep.kind}",
            "CHOCH then BOS confirmation",
            f"POI: {poi_name}",
        ],
    )
