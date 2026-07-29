"""
Core shortening logic: URL validation and short code generation.

Kept separate from the Telegram handlers so it's independently testable
and reusable (e.g. if you ever add a REST API for shortening later).
"""

import re
import secrets
import string

import validators
from sqlalchemy.orm import Session

from app.config import settings
from app.logger import get_logger
from app.models import Link

logger = get_logger(__name__)

# Characters used for randomly generated short codes.
# Excludes visually ambiguous characters (0/O, 1/l/I) to avoid confusion
# when someone reads a code aloud or retypes it.
_ALPHABET = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"

# Custom aliases are restricted to this pattern: letters, digits,
# hyphens, underscores. Keeps them URL-safe with no encoding needed.
_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")

# Reserved words that can't be used as custom aliases because they'd
# collide with real routes in main.py (e.g. /health, /webhook/...).
_RESERVED_ALIASES = {"start", "help", "health", "webhook", "api", "admin", "stats"}


class ShortenerError(Exception):
    """Base exception for shortener-related failures. Handlers catch
    this and turn it into a user-friendly Telegram message."""


class InvalidURLError(ShortenerError):
    pass


class InvalidAliasError(ShortenerError):
    pass


class AliasTakenError(ShortenerError):
    pass


def validate_url(url: str) -> str:
    """
    Validates a URL and returns it normalized (stripped whitespace).
    Raises InvalidURLError with a user-facing message if invalid.
    """
    url = url.strip()

    if not url:
        raise InvalidURLError("The URL can't be empty.")

    # `validators.url` requires a scheme; if the user pasted something
    # like "example.com" without http(s)://, prepend it before validating
    # so we don't reject perfectly reasonable input.
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = f"https://{url}"

    if not validators.url(url):
        raise InvalidURLError(
            "That doesn't look like a valid URL. Make sure it looks like "
            "https://example.com/page"
        )

    if len(url) > 2048:
        raise InvalidURLError("That URL is too long (max 2048 characters).")

    return url


def validate_alias(alias: str) -> str:
    """
    Validates a custom alias and returns it normalized.
    Raises InvalidAliasError with a user-facing message if invalid.
    """
    alias = alias.strip()

    if not _ALIAS_PATTERN.match(alias):
        raise InvalidAliasError(
            "Custom aliases must be 3-32 characters long and contain only "
            "letters, numbers, hyphens, and underscores."
        )

    if alias.lower() in _RESERVED_ALIASES:
        raise InvalidAliasError(
            f"'{alias}' is a reserved word and can't be used as an alias."
        )

    return alias


def _generate_random_code(db: Session, length: int | None = None) -> str:
    """
    Generates a random short code guaranteed to be unique in the DB.
    Retries on the rare collision rather than failing outright.
    """
    length = length or settings.SHORT_CODE_LENGTH
    max_attempts = 10

    for attempt in range(max_attempts):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        exists = db.query(Link.id).filter(Link.short_code == code).first()
        if not exists:
            return code
        logger.warning("Short code collision on attempt %d: %s", attempt + 1, code)

    # Extremely unlikely with a 6+ char alphabet of ~55 chars, but if we
    # somehow exhaust attempts, widen the search space rather than fail.
    logger.error("Exhausted %d attempts generating unique short code; increasing length", max_attempts)
    return _generate_random_code(db, length=length + 1)


def create_short_link(
    db: Session,
    original_url: str,
    owner_id: int,
    custom_alias: str | None = None,
) -> Link:
    """
    Validates input and creates a new Link row.

    Raises InvalidURLError, InvalidAliasError, or AliasTakenError on bad input.
    Does NOT commit — caller controls the transaction (use get_db_context()).
    """
    clean_url = validate_url(original_url)

    if custom_alias:
        clean_alias = validate_alias(custom_alias)
        existing = db.query(Link.id).filter(Link.short_code == clean_alias).first()
        if existing:
            raise AliasTakenError(f"The alias '{clean_alias}' is already taken. Try another one.")
        short_code = clean_alias
        is_custom = True
    else:
        short_code = _generate_random_code(db)
        is_custom = False

    link = Link(
        short_code=short_code,
        original_url=clean_url,
        owner_id=owner_id,
        is_custom_alias=is_custom,
    )
    db.add(link)
    db.flush()  # populates link.id without committing yet

    logger.info("Created short link: %s -> %s (owner_id=%d)", short_code, clean_url, owner_id)
    return link


def build_short_url(short_code: str) -> str:
    """Builds the full user-facing short URL from a short code."""
    return f"{settings.SHORT_DOMAIN.rstrip('/')}/{short_code}"
