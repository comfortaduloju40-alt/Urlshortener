# Telegram URL Shortener Bot

A production-ready Telegram bot that shortens URLs, tracks click
analytics, and supports custom aliases. Built with python-telegram-bot,
FastAPI (webhook mode), and SQLAlchemy. Deployed on Railway.

## Commands

- `/start` — welcome message, registers you as a user
- `/help` — list all commands
- `/shorten <url> [alias]` — shorten a URL, optional custom alias
- `/mylinks` — paginated list of your links
- `/stats [code]` — analytics for one link, or a summary of all your links
- `/delete <code>` — delete a link (asks for confirmation)
- `/about` — about this bot

You can also just paste a URL with no command and it'll shorten automatically.

## Local development

1. Clone the repo and create a virtualenv:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
