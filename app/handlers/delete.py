"""
/delete command handler — deletes a short link, with an inline
confirmation step so accidental taps/typos don't destroy data instantly.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database import get_db_context
from app.logger import get_logger
from app.models import Link, User

logger = get_logger(__name__)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/delete <code>`\ne.g. `/delete abc123`", parse_mode="Markdown"
        )
        return

    code = args[0]
    tg_user = update.effective_user

    with get_db_context() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        link = None
        if user is not None:
            link = db.query(Link).filter(Link.short_code == code, Link.owner_id == user.id).first()

        if link is None:
            await update.message.reply_text(
                f"No link found with code `{code}` owned by you.", parse_mode="Markdown"
            )
            return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes, delete", callback_data=f"delete:confirm:{code}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"delete:cancel:{code}"),
            ]
        ]
    )
    await update.message.reply_text(
        f"Are you sure you want to delete `{code}`? This can't be undone.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, action, code = query.data.split(":")
    tg_user = query.from_user

    if action == "cancel":
        await query.edit_message_text(f"Cancelled. `{code}` was not deleted.", parse_mode="Markdown")
        return

    with get_db_context() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        link = None
        if user is not None:
            link = db.query(Link).filter(Link.short_code == code, Link.owner_id == user.id).first()

        if link is None:
            await query.edit_message_text(
                f"No link found with code `{code}` owned by you (already deleted?).",
                parse_mode="Markdown",
            )
            return

        db.delete(link)
        logger.info("Deleted link: %s (owner telegram_id=%d)", code, tg_user.id)

    await query.edit_message_text(f"🗑️ Deleted `{code}`.", parse_mode="Markdown")
