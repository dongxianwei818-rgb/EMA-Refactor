"""WeChat encryptedData AES decryption."""

import base64
import json
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def _pkcs7_unpad(data: bytes) -> bytes:
    pad = data[-1]
    if pad < 1 or pad > 32:
        raise ValueError("invalid padding")
    return data[:-pad]


def decrypt_wechat_data(encrypted_data: str, iv: str, session_key: str) -> dict[str, Any]:
    key = base64.b64decode(session_key)
    ciphertext = base64.b64decode(encrypted_data)
    iv_bytes = base64.b64decode(iv)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv_bytes), backend=default_backend())
    decryptor = cipher.decryptor()
    plain = decryptor.update(ciphertext) + decryptor.finalize()
    plain = _pkcs7_unpad(plain)
    return json.loads(plain.decode("utf-8"))
