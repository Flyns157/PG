import base64
import os
from typing import Any


def entry_payload(plaintext_size: int = 32, **overrides: Any) -> dict[str, Any]:
    return {
        "ciphertext": base64.b64encode(os.urandom(plaintext_size + 16)).decode(),
        "nonce": base64.b64encode(os.urandom(12)).decode(),
        "algorithm": "AES-256-GCM",
    } | overrides
