"""
/stats command handler — shows analytics for a specific link, or a
summary across all of the user's links if no code is given.
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.database import get_db_context
from app.logger import get_logger
from app.models import Link, User
from app.shortener import build_short_url

logger = get_logger(__name__)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    args = context.args

    with get_db_context() as db:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        if user is None:
            await update.message.reply_text("You haven't created any short links yet.")
            return

        if args:
            code = args[0]
            link = (
                db.query(Link)
                .filter(Link.short_code == code, Link.owner_id == user.id)
                .first()
            )
            if link is None:
                await update.message.reply_text(
                    f"No link found with code `{code}` owned by you.", parse_mode="Markdown"
                )
                return

            last_clicked = (
                link.last_clicked_at.strftime("%Y-%m-%d %H:%M UTC")
                if link.last_clicked_at
                else "Never"
            )
            text = (
                f"📊 *Stats for* `{link.short_code}`\n\n"
                f"🔗 Short URL: {build_short_url(link.short_code)}\n"
                f"🌐 Original: {link.original_url}\n"
                f"👆 Total clicks: {link.total_clicks}\n"
                f"📅 Created: {link.created_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"🕐 Last clicked: {last_clicked}"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            all_links = db.query(Link).filter(Link.owner_id == user.id).all()
            total_links = len(all_links)
            total_clicks = sum(l.total_clicks for l in all_links)
            text = (
                f"📊 *Your overall stats*\n\n"
                f"🔗 Total links: {total_links}\n"
                f"👆 Total clicks across all links: {total_clicks}\n\n"
                f"Use `/stats <code>` for details on a specific link."
            )
            await update.message.reply_text(text, parse_mode="Markdown")
