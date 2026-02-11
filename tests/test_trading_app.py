from pathlib import Path

import pandas as pd

from src.app.trading_app import load_config, pick_timeframes
from src.data.providers import YahooFinanceProvider


def test_load_config_reads_yaml():
    config = load_config(Path("config.yaml"))
    assert "styles" in config
    assert "risk" in config


def test_pick_timeframes_returns_primary_timeframes():
    config = load_config(Path("config.yaml"))
    htf, entry = pick_timeframes(config, "day")
    assert htf == "4H"
    assert entry == "15m"


def test_online_symbol_map_contains_xauusd():
    config = load_config(Path("config.yaml"))
    provider = YahooFinanceProvider(symbol_map=config["online_symbol_map"])
    assert provider._resolve_symbol("xauusd") == "GC=F"


def test_resample_4h_keeps_ohlcv_shape():
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=8, freq="h", tz="UTC"),
            "open": [1, 2, 3, 4, 5, 6, 7, 8],
            "high": [2, 3, 4, 5, 6, 7, 8, 9],
            "low": [0, 1, 2, 3, 4, 5, 6, 7],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5],
            "volume": [10] * 8,
        }
    )
    out = YahooFinanceProvider._resample_4h(df)
    assert list(out.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert len(out) == 2


def test_online_symbol_map_has_requested_forex_pairs():
    config = load_config(Path("config.yaml"))
    online = config["online_symbol_map"]
    expected = ["audusd", "nzdusd", "usdcad", "eurjpy", "gbpjpy"]
    for pair in expected:
        assert pair in online
