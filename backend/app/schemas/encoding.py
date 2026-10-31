import base64
import binascii
from collections.abc import Callable


def base64_length(*, min_bytes: int, max_bytes: int) -> Callable[[str], str]:
    """Valide du base64 strict dont la taille décodée reste dans les bornes."""

    def validate(value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except binascii.Error:
            raise ValueError("base64 invalide") from None
        if not min_bytes <= len(decoded) <= max_bytes:
            raise ValueError(f"taille attendue : {min_bytes} à {max_bytes} octets")
        return value

    return validate
