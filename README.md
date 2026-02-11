# Telegram SMC/ICT Trading Bot (Alerts + Paper Trading)

A modular Python 3.10+ trading bot for Telegram-driven SMC/ICT-style scanning, grading, and optional auto-execution. Default mode runs alerts + paper trading. Auto execution is protected behind `/mode auto` and `/arm` safety toggles.

## Features

- Multi-timeframe SMC/ICT scanning (swing/day/scalp)
- BOS/CHOCH, liquidity sweep, FVG, and order block detection
- Premium/discount filtering
- Setup grading (A+ to C)
- Risk and trading limit enforcement
- CSV-based data provider (MVP)
- Paper trading execution (always available)
- MT5 live execution stub (behind toggles)
- Telegram bot commands and aliases

## Project Structure

```
src/
  bot/telegram_bot.py
  strategy/smc.py
  strategy/scoring.py
  risk/risk.py
  data/providers.py
  execution/paper.py
  execution/live_mt5.py
  utils/time.py
config.yaml
```

## Setup (Windows)

1. **Install Python 3.10+**
   - Download from https://www.python.org/downloads/windows/

2. **Create a virtual environment**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Add your Telegram bot token**
   - Save your bot token to a file named `.telegram_token` in the repo root.

5. **Run the bot**
   ```powershell
   python -m src.bot.telegram_bot
   ```


## App Mode (AI Trading Assistant - Live Data)

You can run a Streamlit app with online market data (no CSV files needed):

```powershell
streamlit run src/app/trading_app.py
```

What the app does:
- Select symbol + style from your config
- Pull online OHLCV market candles from Yahoo Finance
- Run the same SMC/ICT setup builder used by the bot
- Show AI-style suggestion with entry, SL, TP, RR, grade, and risk-based position sizing

### Android / APK path

This app is built in Streamlit (web app). To use on phone:

1. Deploy Streamlit app (Render/Railway/VM).
2. Open from mobile browser and install as web app (PWA style).
3. If you need an `.apk`, wrap the deployed URL using an Android WebView wrapper (for example Android Studio `WebView` shell or trusted web activity toolchain).



## Trading Rules Used by the App

The app uses the same SMC/ICT rule pipeline as the strategy module:

1. Detect HTF structure (BOS/CHOCH) and set directional bias.
2. Require a liquidity sweep on entry timeframe in the opposite side of liquidity.
3. Require post-sweep confirmation (CHOCH + BOS in bias direction).
4. Select POI from order block / fair value gap with premium-discount filter.
5. Build setup with entry, stop, target, and enforce minimum RR >= 3.
6. Grade setup quality (A+ to C) with the scoring model and show reasons.
7. Position size is computed from account balance, risk per trade, and stop distance.

Forex pairs now mapped online include: EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD, EURJPY, GBPJPY.

## Telegram Commands

- `/help`
- `/status`
- `/mode alerts` or `/mode auto`
- `/arm` / `/disarm`
- `/scan <symbol> <style>` (example: `/scan xauusd day`)

### Aliases
- `/xauswing`, `/xauday`, `/xauscalp`
- `/eurusdday`
- `/gbpjpyswing`
- `/nas100day`
- `/us30scalp`

## Notes

- Default mode is alerts + paper trading.
- Live execution requires `/mode auto` and `/arm`, and the symbol must be allowlisted.
- CSV provider is the MVP; add MT5/OANDA/Binance data providers as needed.

## Tests

```powershell
pytest
```
