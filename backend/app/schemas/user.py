import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.core.security import KDF_SALT_BYTES, MAX_VERIFIER_LENGTH
from app.schemas.encoding import base64_length

MIN_KDF_N = 2**15
MAX_KDF_N = 2**24

KdfSalt = Annotated[
    str,
    Field(max_length=64),
    AfterValidator(base64_length(min_bytes=KDF_SALT_BYTES, max_bytes=32)),
]


class KdfParameters(BaseModel):
    """Paramètres de dérivation dont le client a besoin pour retrouver sa clé."""

    algorithm: Literal["scrypt"] = "scrypt"
    salt: KdfSalt
    n: int = Field(default=MIN_KDF_N, ge=MIN_KDF_N, le=MAX_KDF_N)
    r: int = Field(default=8, ge=8, le=32)
    p: int = Field(default=1, ge=1, le=16)

    @field_validator("n")
    @classmethod
    def _n_is_power_of_two(cls, value: int) -> int:
        if value & (value - 1):
            raise ValueError("n doit être une puissance de deux")
        return value


class KdfParametersRequest(BaseModel):
    email: EmailStr = Field(max_length=255)


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=255)
    auth_verifier: str = Field(min_length=32, max_length=MAX_VERIFIER_LENGTH)
    kdf: KdfParameters


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
