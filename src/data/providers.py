from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Protocol

import pandas as pd
import yfinance as yf


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
class YahooFinanceProvider:
    symbol_map: Dict[str, str]

    _interval_map = {
        "1m": ("1m", "7d"),
        "5m": ("5m", "60d"),
        "15m": ("15m", "60d"),
        "1H": ("60m", "730d"),
        "4H": ("60m", "730d"),
        "4h": ("60m", "730d"),
        "1D": ("1d", "10y"),
    }

    def _resolve_symbol(self, symbol: str) -> str:
        resolved = self.symbol_map.get(symbol.lower())
        if resolved is None:
            raise KeyError(f"No online symbol mapping found for '{symbol}'")
        return resolved

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        ticker = self._resolve_symbol(symbol)
        interval, period = self._interval_map.get(timeframe, ("60m", "730d"))

        raw = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            actions=False,
        )
        if raw.empty:
            raise ValueError(f"No online market data returned for {symbol} ({ticker})")

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = raw.reset_index().rename(
            columns={
                "Datetime": "timestamp",
                "Date": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        if timeframe in ("4H", "4h"):
            df = self._resample_4h(df)

        required = ["timestamp", "open", "high", "low", "close", "volume"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required market columns: {missing}")

        df = df[required]
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df.tail(limit).reset_index(drop=True)

    @staticmethod
    def _resample_4h(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        temp = df.copy()
        temp["timestamp"] = pd.to_datetime(temp["timestamp"], utc=True)
        temp = temp.set_index("timestamp")
        out = temp.resample("4h").agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        out = out.dropna().reset_index()
        return out


@dataclass
class MT5Provider:
    symbol_map: Dict[str, List[str]]

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        raise NotImplementedError("MT5 provider stub - connect to MetaTrader5 here.")


@dataclass
class BinanceProvider:
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        raise NotImplementedError("Binance provider stub - connect to Binance API here.")
