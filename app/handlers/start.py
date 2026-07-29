"""
/start command handler.
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.database import get_db_context
from app.logger import get_logger
from app.models import User

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    if tg_user is None:
        return

    with get_db_context() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        if user is None:
            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
            )
            db.add(user)
            logger.info("Registered new user: telegram_id=%d username=%s", tg_user.id, tg_user.username)

    text = (
        f"👋 Hi {tg_user.first_name or 'there'}!\n\n"
        "I'm a URL Shortener bot. Send me any link and I'll shorten it for you.\n\n"
        "*Quick start:*\n"
        "• Just paste a URL to shorten it instantly\n"
        "• `/shorten <url> [custom_alias]` — shorten with an optional custom alias\n"
        "• `/mylinks` — view all your links\n"
        "• `/stats <code>` — see click analytics for a link\n"
        "• `/delete <code>` — delete a link\n\n"
        "Type /help for the full command list."
    )
    await update.message.reply_text(text, parse_mode="Markdown")
