import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


class ChaCha20Cipher:
    """Symmetric cipher used to encrypt/decrypt the auth cookies.

    The same key must be shared by every client that needs to read the
    cookies (dashboard, mobile app, ...). Key is read from settings/env,
    never hard-coded.
    """

    def __init__(self, key: str):
        raw_key = key.encode('utf-8')
        if len(raw_key) != 32:
            raise ValueError('ChaCha20Cipher key must be exactly 32 bytes long')
        self._aead = ChaCha20Poly1305(raw_key)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self._aead.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt(self, token: str) -> str | None:
        try:
            raw = base64.urlsafe_b64decode(token.encode('utf-8'))
            nonce, ciphertext = raw[:12], raw[12:]
            return self._aead.decrypt(nonce, ciphertext, None).decode('utf-8')
        except Exception:
            return None
