from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import streamlit as st
import yaml

from src.data.providers import YahooFinanceProvider
from src.risk.risk import position_size
from src.strategy.scoring import score_setup
from src.strategy.smc import build_setup


CONFIG_PATH = Path("config.yaml")


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def pick_timeframes(config: Dict[str, Any], style: str) -> Tuple[str, str]:
    style_cfg = config["styles"][style]
    htf = style_cfg["htf"][0]
    entry = style_cfg["entry"][0]
    return htf, entry


def run() -> None:
    st.set_page_config(page_title="AI Trading Assistant", layout="wide")
    st.title("📈 AI Trading Assistant App")
    st.caption("Runs your strategy rules on live online market data.")

    config = load_config()
    provider = YahooFinanceProvider(symbol_map=config.get("online_symbol_map", {}))

    symbols = list(config.get("online_symbol_map", {}).keys())
    styles = list(config.get("styles", {}).keys())

    with st.sidebar:
        st.header("Strategy controls")
        symbol = st.selectbox("Symbol", symbols, index=0)
        style = st.selectbox("Style", styles, index=0)
        balance = st.number_input(
            "Account balance",
            min_value=100.0,
            value=float(config.get("account_balance", 10000.0)),
            step=100.0,
        )
        run_scan = st.button("Analyze live market", type="primary")

    if not run_scan:
        st.info("Choose symbol/style and press **Analyze live market**.")
        return

    htf_tf, entry_tf = pick_timeframes(config, style)

    try:
        htf_df = provider.get_ohlcv(symbol=symbol, timeframe=htf_tf, limit=500)
        entry_df = provider.get_ohlcv(symbol=symbol, timeframe=entry_tf, limit=500)
    except (ValueError, KeyError) as exc:
        st.error(str(exc))
        st.stop()

    risk_cfg = config["risk"]
    setup = build_setup(
        symbol=symbol,
        style=style,
        htf_df=htf_df,
        entry_df=entry_df,
        lookback=int(risk_cfg["swing_lookback"]),
        sweep_lookahead=int(risk_cfg["sweep_lookahead"]),
        fvg_min=float(risk_cfg["fvg_min_size"]),
        displacement_threshold=float(risk_cfg["displacement_threshold"]),
    )

    left, right = st.columns([2, 1])

    with left:
        chart_df = entry_df.copy().set_index("timestamp")
        st.subheader(f"{symbol.upper()} {entry_tf} live price")
        st.line_chart(chart_df["close"])

    with right:
        st.subheader("AI suggestion")
        if setup is None:
            st.warning("No valid setup found right now. Wait for cleaner structure.")
            st.markdown(
                """
                **Next action**
                - Stay flat and keep risk protected.
                - Wait for liquidity sweep + CHOCH/BOS confirmation.
                - Re-scan on the next candle close.
                """
            )
            return

        stop_distance = abs(setup.entry - setup.stop_loss)
        units = position_size(
            balance=balance,
            risk_per_trade=float(risk_cfg["risk_per_trade"]),
            stop_distance=stop_distance,
        )

        score = score_setup(
            htf_aligned=True,
            sweep_rejection=True,
            choch_bos=True,
            poi_quality=True,
            rr_ok=setup.rr >= 3,
            liquidity_target=True,
            spread_ok=True,
        )

        st.success(f"{setup.direction.upper()} setup detected")
        st.metric("Grade", score.grade)
        st.metric("Entry", f"{setup.entry:.2f}")
        st.metric("Stop Loss", f"{setup.stop_loss:.2f}")
        st.metric("Take Profit", f"{setup.take_profit:.2f}")
        st.metric("Risk:Reward", f"{setup.rr:.2f}")
        st.metric("Suggested size", f"{units:.2f} units")

        st.markdown("**Reasoning**")
        for reason in setup.reasons:
            st.write(f"- {reason}")

        st.markdown("**Risk note**")
        st.write("Educational only. Not financial advice.")


if __name__ == "__main__":
    run()
