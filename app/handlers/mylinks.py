"""
/mylinks command handler — lists the user's short links with pagination.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database import get_db_context
from app.logger import get_logger
from app.models import Link, User
from app.shortener import build_short_url

logger = get_logger(__name__)

PAGE_SIZE = 5


def _format_page(links: list[Link], page: int, total: int) -> str:
    if not links:
        return "You haven't created any short links yet. Send me a URL to get started!"

    lines = [f"*Your links* (page {page + 1}, {total} total)\n"]
    for link in links:
        short_url = build_short_url(link.short_code)
        truncated = link.original_url[:60] + ("..." if len(link.original_url) > 60 else "")
        lines.append(
            f"🔗 `{link.short_code}`\n"
            f"   {short_url}\n"
            f"   → {truncated}\n"
            f"   👆 {link.total_clicks} clicks"
        )
    return "\n\n".join(lines)


def _build_keyboard(page: int, total: int) -> InlineKeyboardMarkup | None:
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    if total_pages <= 1:
        return None

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"mylinks:page:{page - 1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"mylinks:page:{page + 1}"))

    return InlineKeyboardMarkup([buttons]) if buttons else None


async def _render(tg_user_id: int, page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    with get_db_context() as db:
        user = db.query(User).filter(User.telegram_id == tg_user_id).first()
        if user is None:
            return "You haven't created any short links yet. Send me a URL to get started!", None

        total = db.query(Link).filter(Link.owner_id == user.id).count()
        links = (
            db.query(Link)
            .filter(Link.owner_id == user.id)
            .order_by(Link.created_at.desc())
            .offset(page * PAGE_SIZE)
            .limit(PAGE_SIZE)
            .all()
        )
        text = _format_page(links, page, total)
        keyboard = _build_keyboard(page, total)
        return text, keyboard


async def mylinks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, keyboard = await _render(update.effective_user.id, page=0)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def mylinks_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    page = int(query.data.split(":")[-1])
    text, keyboard = await _render(query.from_user.id, page=page)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
