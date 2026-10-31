import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.vault_entry import (
    VaultEntriesPublic,
    VaultEntryPublic,
    VaultEntryWrite,
)
from app.services import vault_entry_service

router = APIRouter(prefix="/vault-entries", tags=["vault-entries"])


@router.get("/", response_model=VaultEntriesPublic)
def read_entries(
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> Any:
    """
    Entrées chiffrées de l'utilisateur. La recherche se fait côté client.
    """
    entries, count = vault_entry_service.list_entries(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return VaultEntriesPublic(
        data=[VaultEntryPublic.model_validate(entry) for entry in entries],
        count=count,
    )


@router.post("/", response_model=VaultEntryPublic, status_code=status.HTTP_201_CREATED)
def create_entry(
    session: SessionDep, current_user: CurrentUser, entry_in: VaultEntryWrite
) -> Any:
    """
    Enregistre une entrée déjà chiffrée par le client.
    """
    return vault_entry_service.create_entry(
        session=session, user_id=current_user.id, entry_in=entry_in
    )


@router.get("/{entry_id}", response_model=VaultEntryPublic)
def read_entry(
    session: SessionDep, current_user: CurrentUser, entry_id: uuid.UUID
) -> Any:
    """
    Une entrée chiffrée.
    """
    return vault_entry_service.get_entry(
        session=session, user_id=current_user.id, entry_id=entry_id
    )


@router.put("/{entry_id}", response_model=VaultEntryPublic)
def replace_entry(
    session: SessionDep,
    current_user: CurrentUser,
    entry_id: uuid.UUID,
    entry_in: VaultEntryWrite,
) -> Any:
    """
    Remplace le contenu chiffré d'une entrée.
    """
    return vault_entry_service.replace_entry(
        session=session, user_id=current_user.id, entry_id=entry_id, entry_in=entry_in
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    session: SessionDep, current_user: CurrentUser, entry_id: uuid.UUID
) -> None:
    """
    Supprime une entrée.
    """
    vault_entry_service.delete_entry(
        session=session, user_id=current_user.id, entry_id=entry_id
    )
