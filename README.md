# Laptop Screen Monitor Agent (Telegram)

This project is a minimal starter agent that:

1. Captures your laptop screen.
2. Extracts text from the screenshot (OCR).
3. Sends the extracted text to Telegram.

It also provides a hook where you can add AI analysis so the agent can answer questions found on-screen and send responses to Telegram.

## Features

- Telegram bot with `/scan` command.
- Full-screen capture using `mss`.
- OCR via `pytesseract`.
- Pluggable `analyze_question()` function for AI-based answers.

## Requirements

- Python 3.10+
- Tesseract installed locally (for OCR). Example (Ubuntu):
  ```bash
  sudo apt-get install tesseract-ocr
  ```
- Telegram bot token and chat ID.

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   export TELEGRAM_CHAT_ID="your-chat-id"
   ```
3. Run the bot:
   ```bash
   python -m src.agent
   ```

## Usage

In Telegram, open your bot and run:

```
/scan
```

The bot will capture your current screen, run OCR, and return the extracted text. You can then implement `analyze_question()` to use an AI model and respond with the answer instead of raw OCR.

## Adding AI Analysis

Update `analyze_question()` in `src/agent.py` to call your preferred model (OpenAI, local LLM, etc.). The function currently returns the raw OCR text to keep the project dependency-light.

## Notes

- For WhatsApp support, use the WhatsApp Business API or a provider like Twilio. This repository focuses on Telegram for a clean baseline.
- You should secure access to your bot token and avoid exposing it in code or logs.
