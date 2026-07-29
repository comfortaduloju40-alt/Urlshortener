"""
/about command handler.
"""

from telegram import Update
from telegram.ext import ContextTypes

ABOUT_TEXT = (
    "🔗 *URL Shortener Bot*\n\n"
    "A simple, fast link shortener built with python-telegram-bot, "
    "FastAPI, and SQLAlchemy — hosted on Railway.\n\n"
    "Features: custom aliases, click analytics, and unlimited links per user."
)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(ABOUT_TEXT, parse_mode="Markdown")
