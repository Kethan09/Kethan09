from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Protocol

import pandas as pd


class DataProvider(Protocol):
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        ...


@dataclass
class CSVProvider:
    data_dir: Path

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        normalized = symbol.lower()
        file_candidates = [
            self.data_dir / f"{normalized}_{timeframe}.csv",
            self.data_dir / f"{symbol}_{timeframe}.csv",
        ]
        for path in file_candidates:
            if path.exists():
                df = pd.read_csv(path)
                df.columns = [c.lower() for c in df.columns]
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                return df.tail(limit).reset_index(drop=True)
        raise FileNotFoundError(f"CSV not found for {symbol} {timeframe} in {self.data_dir}")


@dataclass
class MT5Provider:
    symbol_map: Dict[str, List[str]]

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        raise NotImplementedError("MT5 provider stub - connect to MetaTrader5 here.")


@dataclass
class BinanceProvider:
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        raise NotImplementedError("Binance provider stub - connect to Binance API here.")
