"""
/shorten command handler, plus a plain-text URL handler so users can
paste a link without a command.
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.database import get_db_context
from app.logger import get_logger
from app.models import User
from app.shortener import (
    AliasTakenError,
    InvalidAliasError,
    InvalidURLError,
    build_short_url,
    create_short_link,
    validate_url,
)

logger = get_logger(__name__)


def _get_or_create_user(db, tg_user) -> User:
    user = db.query(User).filter(User.telegram_id == tg_user.id).first()
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
        )
        db.add(user)
        db.flush()
    return user


async def _shorten_and_reply(update: Update, url: str, alias: str | None) -> None:
    tg_user = update.effective_user
    try:
        with get_db_context() as db:
            user = _get_or_create_user(db, tg_user)
            link = create_short_link(db, original_url=url, owner_id=user.id, custom_alias=alias)
            short_url = build_short_url(link.short_code)

        reply = f"✅ Shortened!\n\n{short_url}"
        if alias:
            reply += "\n\n_(custom alias)_"
        await update.message.reply_text(reply, parse_mode="Markdown")

    except (InvalidURLError, InvalidAliasError, AliasTakenError) as e:
        await update.message.reply_text(f"⚠️ {e}")
    except Exception:
        logger.exception("Unexpected error while shortening URL")
        await update.message.reply_text(
            "Something went wrong while shortening that link. Please try again."
        )


async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/shorten <url> [custom_alias]`\n"
            "e.g. `/shorten https://example.com mylink`",
            parse_mode="Markdown",
        )
        return

    url = args[0]
    alias = args[1] if len(args) > 1 else None
    await _shorten_and_reply(update, url, alias)


async def plain_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles plain-text messages that aren't commands. If the message
    looks like a URL, shorten it directly (no custom alias via this path —
    users who want an alias should use /shorten). Non-URL text is ignored
    silently rather than replying with an error on every random message.
    """
    text = (update.message.text or "").strip()
    if not text:
        return

    try:
        validate_url(text)
    except InvalidURLError:
        return  # not a URL — ignore silently

    await _shorten_and_reply(update, text, alias=None)
