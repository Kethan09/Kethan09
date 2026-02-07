import pandas as pd

from src.strategy.smc import (
    detect_bos_choch,
    detect_fvg,
    detect_order_blocks,
    find_swings,
)


def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [10, 11, 12, 11, 13, 14, 15],
            "high": [11, 12, 13, 12, 14, 15, 16],
            "low": [9, 10, 11, 10, 12, 13, 14],
            "close": [11, 12, 11, 13, 14, 15, 16],
        }
    )


def test_find_swings():
    df = sample_df()
    swings = find_swings(df, lookback=1)
    assert any(s.kind == "high" for s in swings)
    assert any(s.kind == "low" for s in swings)


def test_detect_bos_choch():
    df = sample_df()
    swings = find_swings(df, lookback=1)
    events = detect_bos_choch(df, swings)
    assert events
    assert events[-1].direction in {"bull", "bear"}


def test_detect_fvg():
    df = pd.DataFrame(
        {
            "open": [10, 10, 12],
            "high": [11, 11, 13],
            "low": [9, 9, 12.5],
            "close": [10.5, 10.5, 13],
        }
    )
    gaps = detect_fvg(df, min_size=0.5)
    assert gaps
    assert gaps[0].kind == "bull"


def test_detect_order_blocks():
    df = pd.DataFrame(
        {
            "open": [10, 9, 11],
            "high": [10.5, 9.5, 12],
            "low": [9.5, 8.5, 10.5],
            "close": [9, 11, 11.8],
        }
    )
    blocks = detect_order_blocks(df, displacement_threshold=1.0)
    assert blocks
    assert blocks[0].kind == "bull"
