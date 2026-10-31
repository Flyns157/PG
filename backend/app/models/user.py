import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.vault_entry import VaultEntry


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Haché du vérificateur dérivé côté client, jamais du mot de passe maître.
    hashed_verifier: Mapped[str] = mapped_column(String(255))
    kdf_algorithm: Mapped[str] = mapped_column(String(32))
    kdf_salt: Mapped[str] = mapped_column(String(64))
    kdf_n: Mapped[int]
    kdf_r: Mapped[int]
    kdf_p: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    vault_entries: Mapped[list["VaultEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
