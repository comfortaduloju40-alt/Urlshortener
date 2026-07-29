"""
SQLAlchemy ORM models: User, Link, Click.

Schema overview:
    User  (1) ──< (many) Link  (1) ──< (many) Click

- User: a Telegram user who has created at least one link.
- Link: a shortened URL, owned by a User.
- Click: one record per redirect, used to compute analytics without
  losing history (last_clicked/total_clicks are also denormalized
  onto Link for fast reads — see notes below).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """Timezone-aware UTC now, used as a default for timestamp columns."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Telegram's user ID — the actual identifier we look users up by.
    # BigInteger because Telegram user IDs can exceed 32-bit range.
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    links: Mapped[list["Link"]] = relationship(
        "Link", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} username={self.username!r}>"


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    short_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)

    is_custom_alias: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Denormalized for fast /mylinks and /stats reads without a COUNT(*) join.
    # The Click table below remains the source of truth for detailed history.
    total_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="links")
    clicks: Mapped[list["Click"]] = relationship(
        "Click", back_populates="link", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Link id={self.id} short_code={self.short_code!r} clicks={self.total_clicks}>"


class Click(Base):
    """
    One row per redirect event. Kept separate from Link so we can later
    support richer analytics (clicks over time, referrers, etc.) without
    schema changes to Link itself.
    """

    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    link_id: Mapped[int] = mapped_column(ForeignKey("links.id", ondelete="CASCADE"), nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Optional metadata, nullable since we may not always have it
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    link: Mapped["Link"] = relationship("Link", back_populates="clicks")

    def __repr__(self) -> str:
        return f"<Click id={self.id} link_id={self.link_id} at={self.clicked_at}>"
