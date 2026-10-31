import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.schemas.encoding import base64_length

GCM_TAG_BYTES = 16
GCM_NONCE_BYTES = 12
MAX_CIPHERTEXT_BYTES = 64 * 1024

Algorithm = Literal["AES-256-GCM"]

Ciphertext = Annotated[
    str,
    Field(max_length=(MAX_CIPHERTEXT_BYTES // 3 + 1) * 4),
    AfterValidator(
        base64_length(min_bytes=GCM_TAG_BYTES, max_bytes=MAX_CIPHERTEXT_BYTES)
    ),
]
Nonce = Annotated[
    str,
    Field(max_length=32),
    AfterValidator(base64_length(min_bytes=GCM_NONCE_BYTES, max_bytes=GCM_NONCE_BYTES)),
]


class VaultEntryWrite(BaseModel):
    # Un champ en clair envoyé par erreur doit être refusé, pas ignoré en silence.
    model_config = ConfigDict(extra="forbid")

    ciphertext: Ciphertext
    nonce: Nonce
    algorithm: Algorithm = "AES-256-GCM"


class VaultEntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ciphertext: str
    nonce: str
    algorithm: str
    created_at: datetime
    updated_at: datetime


class VaultEntriesPublic(BaseModel):
    data: list[VaultEntryPublic]
    count: int
