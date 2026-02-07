from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ScoreResult:
    points: int
    grade: str
    reasons: List[str]


def grade_from_points(points: int) -> str:
    if points >= 9:
        return "A+"
    if points == 8:
        return "A"
    if points == 7:
        return "B+"
    if points == 6:
        return "B"
    if points == 5:
        return "C+"
    return "C"


def score_setup(
    htf_aligned: bool,
    sweep_rejection: bool,
    choch_bos: bool,
    poi_quality: bool,
    rr_ok: bool,
    liquidity_target: bool,
    spread_ok: bool,
) -> ScoreResult:
    points = 0
    reasons: List[str] = []
    if htf_aligned:
        points += 2
        reasons.append("HTF bias aligned")
    if sweep_rejection:
        points += 2
        reasons.append("Sweep + rejection")
    if choch_bos:
        points += 2
        reasons.append("CHOCH then BOS")
    if poi_quality:
        points += 2
        reasons.append("POI quality + premium/discount")
    if rr_ok and liquidity_target:
        points += 1
        reasons.append("RR >= 3 with liquidity target")
    if spread_ok:
        points += 1
        reasons.append("Spread/volatility OK")
    return ScoreResult(points=points, grade=grade_from_points(points), reasons=reasons)
