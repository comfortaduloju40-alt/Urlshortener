"""
/help command handler.
"""

from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "*Available commands:*\n\n"
    "/shorten <url> [alias] — Shorten a URL, optionally with a custom alias\n"
    "  e.g. `/shorten https://example.com mylink`\n\n"
    "/mylinks — List all links you've created\n"
    "/stats <code> — View analytics for a specific short link\n"
    "/delete <code> — Delete one of your short links\n"
    "/about — About this bot\n"
    "/help — Show this message\n\n"
    "💡 Tip: you can also just paste a URL directly without a command "
    "and I'll shorten it automatically."
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
