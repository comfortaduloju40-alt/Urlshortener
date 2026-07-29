"""
FastAPI application entrypoint.

Runs the Telegram bot in webhook mode (not polling): Telegram POSTs
updates to /webhook/<secret>, which this app forwards to
python-telegram-bot's Application for processing. Also serves the
short-link redirect route and a /health endpoint for Railway.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import Application

from app.config import settings
from app.database import get_db, init_db
from app.handlers import register_handlers
from app.logger import get_logger
from app.models import Click, Link
from app.models import utcnow as model_utcnow

logger = get_logger(__name__)

telegram_app: Application = Application.builder().token(settings.BOT_TOKEN).build()
register_handlers(telegram_app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    init_db()
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(
        url=settings.full_webhook_url,
        allowed_updates=Update.ALL_TYPES,
    )
    await telegram_app.start()
    logger.info("Bot started. Webhook set to %s", settings.full_webhook_url)

    yield

    # --- Shutdown ---
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("Bot shut down cleanly.")


app = FastAPI(title="Telegram URL Shortener Bot", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    """Railway health check endpoint."""
    return {"status": "ok"}


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request) -> Response:
    """Receives updates from Telegram and hands them to python-telegram-bot."""
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return Response(status_code=200)


# NOTE: this catch-all route must stay LAST in the file. FastAPI matches
# routes in declaration order, and /{short_code} would otherwise shadow
# /health and /webhook/... if declared above them.
@app.get("/{short_code}")
async def redirect_short_link(short_code: str, request: Request, db: Session = Depends(get_db)):
    link = (
        db.query(Link)
        .filter(Link.short_code == short_code, Link.is_active == True)  # noqa: E712
        .first()
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Short link not found")

    click = Click(
        link_id=link.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(click)
    link.total_clicks += 1
    link.last_clicked_at = model_utcnow()
    db.commit()

    return RedirectResponse(url=link.original_url, status_code=307)
