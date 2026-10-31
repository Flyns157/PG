import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import VaultEntryNotFoundError
from app.models import VaultEntry
from app.schemas.vault_entry import VaultEntryWrite


def list_entries(
    *, session: Session, user_id: uuid.UUID, skip: int, limit: int
) -> tuple[Sequence[VaultEntry], int]:
    owned = VaultEntry.user_id == user_id
    count = session.scalar(select(func.count()).select_from(VaultEntry).where(owned))
    entries = session.scalars(
        select(VaultEntry)
        .where(owned)
        .order_by(VaultEntry.created_at.desc(), VaultEntry.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return entries, count or 0


def get_entry(
    *, session: Session, user_id: uuid.UUID, entry_id: uuid.UUID
) -> VaultEntry:
    # Filtrer sur le propriétaire : une entrée d'autrui reste indiscernable d'un 404.
    entry = session.scalar(
        select(VaultEntry).where(
            VaultEntry.id == entry_id, VaultEntry.user_id == user_id
        )
    )
    if entry is None:
        raise VaultEntryNotFoundError
    return entry


def create_entry(
    *, session: Session, user_id: uuid.UUID, entry_in: VaultEntryWrite
) -> VaultEntry:
    entry = VaultEntry(user_id=user_id, **entry_in.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def replace_entry(
    *,
    session: Session,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    entry_in: VaultEntryWrite,
) -> VaultEntry:
    entry = get_entry(session=session, user_id=user_id, entry_id=entry_id)
    # Le nonce est lié au texte chiffré : les deux sont toujours remplacés ensemble.
    entry.ciphertext = entry_in.ciphertext
    entry.nonce = entry_in.nonce
    entry.algorithm = entry_in.algorithm
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry(*, session: Session, user_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    entry = get_entry(session=session, user_id=user_id, entry_id=entry_id)
    session.delete(entry)
    session.commit()
