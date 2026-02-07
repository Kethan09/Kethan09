import io
import os
from datetime import datetime

import mss
import pytesseract
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes


def capture_screen() -> Image.Image:
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return image


def extract_text(image: Image.Image) -> str:
    return pytesseract.image_to_string(image)


def analyze_question(ocr_text: str) -> str:
    if not ocr_text.strip():
        return "No readable text found on screen."
    return ocr_text


def render_report(analysis: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Scan time: {timestamp}\n\n{analysis}"


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return

    image = capture_screen()
    text = extract_text(image)
    analysis = analyze_question(text)
    report = render_report(analysis)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    await update.effective_message.reply_photo(photo=buffer, caption=report[:1024])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "Send /scan to capture the screen and run OCR."
    )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("scan", scan_command))

    application.run_polling()


if __name__ == "__main__":
    main()
