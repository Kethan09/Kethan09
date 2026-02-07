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

5. **Provide CSV data**
   - Create a `data/` folder in the repo root.
   - Add files like `xauusd_1H.csv`, `xauusd_15m.csv` (headers: `timestamp,open,high,low,close,volume`).

6. **Run the bot**
   ```powershell
   python -m src.bot.telegram_bot
   ```

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
