from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from src.data.providers import CSVProvider
from src.execution.paper import PaperExecution
from src.risk.risk import AccountState, RiskLimits, can_trade, position_size
from src.strategy.scoring import score_setup
from src.strategy.smc import Setup, build_setup
from src.utils.time import market_open


logger = logging.getLogger(__name__)


@dataclass
class BotState:
    mode: str = "alerts"
    armed: bool = False


@dataclass
class BotConfig:
    data_dir: Path
    symbol_map: Dict[str, List[str]]
    styles: Dict[str, Dict[str, List[str]]]
    risk: Dict[str, float]
    spread_filter: Dict[str, float]
    broker_hours: Dict[str, Dict[str, str]]
    allowlist: List[str]
    account_balance: float


def load_config(path: Path) -> BotConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return BotConfig(
        data_dir=Path(raw["data_dir"]),
        symbol_map=raw["symbol_map"],
        styles=raw["styles"],
        risk=raw["risk"],
        spread_filter=raw["spread_filter"],
        broker_hours=raw["broker_hours"],
        allowlist=raw["allowlist"],
        account_balance=raw["account_balance"],
    )


def normalize_symbol(symbol: str, symbol_map: Dict[str, List[str]]) -> str:
    key = symbol.lower()
    for canonical, aliases in symbol_map.items():
        if key == canonical or key in [a.lower() for a in aliases]:
            return canonical
    return key


def format_setup_message(setup: Setup, score_points: int, grade: str) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    reasons = " | ".join(setup.reasons)
    return (
        f"{setup.symbol.upper()} {setup.style} {setup.direction.upper()}\n"
        f"Grade {grade} ({score_points}/10)\n"
        f"Entry: {setup.entry:.2f} | SL: {setup.stop_loss:.2f} | TP: {setup.take_profit:.2f} | RR: {setup.rr:.2f}\n"
        f"POI: {setup.poi}\n"
        f"Invalidation: {setup.invalidation}\n"
        f"Timeframes: HTF {', '.join(setup.htf_timeframes)} | Entry {', '.join(setup.entry_timeframes)}\n"
        f"Reasons: {reasons}\n"
        f"Timestamp: {now}\n"
    )


def score_from_setup(setup: Setup) -> Tuple[int, str, List[str]]:
    result = score_setup(
        htf_aligned=True,
        sweep_rejection=True,
        choch_bos=True,
        poi_quality=True,
        rr_ok=setup.rr >= 3,
        liquidity_target=True,
        spread_ok=True,
    )
    return result.points, result.grade, result.reasons


class TradingBot:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.state = BotState()
        self.provider = CSVProvider(config.data_dir)
        self.paper = PaperExecution()
        self.account = AccountState(
            balance=config.account_balance,
            equity=config.account_balance,
            open_trades=0,
            daily_pnl=0.0,
            weekly_pnl=0.0,
            last_loss_time=None,
        )
        self.risk_limits = RiskLimits(
            risk_per_trade=config.risk["risk_per_trade"],
            max_open_trades=int(config.risk["max_open_trades"]),
            max_daily_loss=config.risk["max_daily_loss"],
            max_weekly_loss=config.risk["max_weekly_loss"],
            cooldown_after_loss_minutes=int(config.risk["cooldown_after_loss_minutes"]),
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "/help, /status, /mode alerts|auto, /arm, /disarm, /scan <symbol> <style>"
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(f"Mode: {self.state.mode} | Armed: {self.state.armed}")

    async def mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not context.args:
            await update.message.reply_text("Usage: /mode alerts|auto")
            return
        mode = context.args[0].lower()
        if mode not in {"alerts", "auto"}:
            await update.message.reply_text("Mode must be alerts or auto")
            return
        self.state.mode = mode
        await update.message.reply_text(f"Mode set to {mode}")

    async def arm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.state.armed = True
        await update.message.reply_text("Auto trading armed.")

    async def disarm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.state.armed = False
        await update.message.reply_text("Auto trading disarmed.")

    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /scan <symbol> <style>")
            return
        symbol = normalize_symbol(context.args[0], self.config.symbol_map)
        style = context.args[1].lower()
        if style not in self.config.styles:
            await update.message.reply_text("Unknown style")
            return
        if not market_open(datetime.utcnow(), symbol, self.config.broker_hours):
            await update.message.reply_text("Market closed for symbol.")
            return

        try:
            htf_tf = self.config.styles[style]["htf"]
            entry_tf = self.config.styles[style]["entry"]
            htf_df = self.provider.get_ohlcv(symbol, htf_tf[0])
            entry_df = self.provider.get_ohlcv(symbol, entry_tf[0])
        except Exception as exc:
            logger.exception("Data error")
            await update.message.reply_text(f"Data error: {exc}")
            return

        setup = build_setup(
            symbol=symbol,
            style=style,
            htf_df=htf_df,
            entry_df=entry_df,
            lookback=int(self.config.risk["swing_lookback"]),
            sweep_lookahead=int(self.config.risk["sweep_lookahead"]),
            fvg_min=float(self.config.risk["fvg_min_size"]),
            displacement_threshold=float(self.config.risk["displacement_threshold"]),
        )

        if setup is None:
            await update.message.reply_text("No trade: no valid setup found.")
            return
        setup.htf_timeframes = htf_tf
        setup.entry_timeframes = entry_tf

        score_points, grade, reasons = score_from_setup(setup)
        if grade in {"C", "C+"}:
            await update.message.reply_text(f"No trade: best setup was {grade} ({', '.join(reasons)}).")
            return

        setup.reasons.extend(reasons)
        message = format_setup_message(setup, score_points, grade)
        await update.message.reply_text(message)

        if self.state.mode == "auto" and self.state.armed:
            if symbol not in self.config.allowlist:
                await update.message.reply_text("Auto trading disabled for this symbol.")
                return
            if not can_trade(self.account, self.risk_limits, datetime.utcnow()):
                await update.message.reply_text("Risk limits: trading blocked.")
                return
            size = position_size(self.account.balance, self.risk_limits.risk_per_trade, abs(setup.entry - setup.stop_loss))
            self.paper.place_bracket(symbol, setup.direction, setup.entry, setup.stop_loss, setup.take_profit, size)
            await update.message.reply_text("Paper order placed.")

    async def alias_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        command = update.message.text.lstrip("/").lower().split()[0]
        alias_map = {
            "xauswing": ("xauusd", "swing"),
            "xauday": ("xauusd", "day"),
            "xauscalp": ("xauusd", "scalp"),
            "eurusdday": ("eurusd", "day"),
            "gbpjpyswing": ("gbpjpy", "swing"),
            "nas100day": ("nas100", "day"),
            "us30scalp": ("us30", "scalp"),
        }
        if command not in alias_map:
            await update.message.reply_text("Unknown alias.")
            return
        symbol, style = alias_map[command]
        context.args = [symbol, style]
        await self.scan_command(update, context)


def build_app(config_path: Path):
    logging.basicConfig(
        filename="agent.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    config = load_config(config_path)
    bot = TradingBot(config)
    token = Path(".telegram_token").read_text(encoding="utf-8").strip()
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("help", bot.help_command))
    app.add_handler(CommandHandler("status", bot.status_command))
    app.add_handler(CommandHandler("mode", bot.mode_command))
    app.add_handler(CommandHandler("arm", bot.arm_command))
    app.add_handler(CommandHandler("disarm", bot.disarm_command))
    app.add_handler(CommandHandler("scan", bot.scan_command))
    app.add_handler(
        CommandHandler(
            ["xauswing", "xauday", "xauscalp", "eurusdday", "gbpjpyswing", "nas100day", "us30scalp"],
            bot.alias_command,
        )
    )
    return app


def main() -> None:
    app = build_app(Path("config.yaml"))
    app.run_polling()


if __name__ == "__main__":
    main()
