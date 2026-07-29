
"""
Registers all Telegram command/message/callback handlers on the
python-telegram-bot Application instance.
"""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.handlers.about import about_command
from app.handlers.delete import delete_command, delete_confirm_callback
from app.handlers.help import help_command
from app.handlers.mylinks import mylinks_command, mylinks_page_callback
from app.handlers.shorten import plain_url_message, shorten_command
from app.handlers.start import start_command
from app.handlers.stats import stats_command


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("shorten", shorten_command))
    application.add_handler(CommandHandler("mylinks", mylinks_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("delete", delete_command))

    application.add_handler(CallbackQueryHandler(mylinks_page_callback, pattern=r"^mylinks:page:\d+$"))
    application.add_handler(CallbackQueryHandler(delete_confirm_callback, pattern=r"^delete:(confirm|cancel):"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_url_message))
