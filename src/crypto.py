"""DPAPI master-key management and AES-GCM per-entry encryption."""

from __future__ import annotations

import os

import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# GCM nonce must be exactly 12 bytes — the NIST-recommended size for AESGCM.
# Shorter nonces reduce the security margin; longer ones are hashed down anyway.
_NONCE_SIZE = 12
_TAG_SIZE = 16   # AES-GCM authentication tag is always 16 bytes
_KEY_SIZE = 32   # AES-256 requires a 32-byte key
_MIN_BLOB = _NONCE_SIZE + _TAG_SIZE  # 28 — minimum valid blob (empty plaintext)

# Application-specific entropy mixed into DPAPI as a second factor.
# DPAPI already binds blobs to the current Windows user account; adding this
# entropy means a *different application* running under the same user cannot
# decrypt PassSimple's master-key blob even if it calls CryptUnprotectData —
# it would need to supply the identical entropy bytes. Defense-in-depth only:
# an attacker with full code-execution as this user can still read the constant,
# but it raises the bar against generic DPAPI-dumping tools and other apps.
# The string is versioned ("v1") so we can rotate it in a future migration.
_DPAPI_ENTROPY = b"PassSimple/v1/master-key"


def generate_master_key() -> bytes:
    """Generate a cryptographically random 32-byte master key."""
    return os.urandom(_KEY_SIZE)


def protect_master_key(key: bytes) -> bytes:
    """Encrypt key with DPAPI (current user scope). Returns an opaque blob.

    Flags=0 is deliberate: it means DPAPI binds the blob to the *current user*
    account only. CRYPTPROTECT_LOCAL_MACHINE (flag 4) would allow any user on
    the same machine to decrypt it — that would be wrong for a personal vault.

    _DPAPI_ENTROPY is passed as optional_entropy for defense-in-depth: another
    application running under the same user account cannot decrypt this blob
    unless it also knows the entropy value. See the constant's comment for
    the full threat model.
    """
    return win32crypt.CryptProtectData(key, None, _DPAPI_ENTROPY, None, None, 0)


def unprotect_master_key(blob: bytes) -> bytes:
    """Decrypt a DPAPI blob produced by protect_master_key(). Returns the raw key.

    Raises pywintypes.error if the blob is corrupted, the entropy is wrong, or
    the blob was encrypted by a different Windows user account — do not catch
    this silently.
    """
    # CryptUnprotectData returns (description_str, data_bytes); we only need data.
    _description, key = win32crypt.CryptUnprotectData(blob, _DPAPI_ENTROPY, None, None, 0)
    return key


def encrypt(plaintext: str, key: bytes) -> bytes:
    """Encrypt a plaintext string with AES-256-GCM.

    A fresh 12-byte nonce is drawn from os.urandom on every call.
    Reusing a nonce with the same key breaks GCM's confidentiality and
    authentication guarantees completely — hence always random, never a counter.

    The cryptography library appends the 16-byte authentication tag to the
    ciphertext automatically. Layout of the returned blob:
        bytes  0 –  11 : nonce  (12 bytes, random, not secret)
        bytes 12 – end : ciphertext + GCM tag  (len(plaintext_utf8) + 16 bytes)
    """
    if len(key) != _KEY_SIZE:
        raise ValueError(f"key must be {_KEY_SIZE} bytes, got {len(key)}")
    nonce = os.urandom(_NONCE_SIZE)
    ct_and_tag = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ct_and_tag


def decrypt(blob: bytes, key: bytes) -> str:
    """Decrypt an AES-256-GCM blob produced by encrypt().

    Raises cryptography.exceptions.InvalidTag if the key is wrong or any byte
    of the blob was modified. AESGCM.decrypt() verifies the authentication tag
    before returning any plaintext — there is no partially-authenticated output.
    Do not catch InvalidTag silently; let it propagate to the caller.
    """
    if len(key) != _KEY_SIZE:
        raise ValueError(f"key must be {_KEY_SIZE} bytes, got {len(key)}")
    if len(blob) < _MIN_BLOB:
        raise ValueError(f"blob too short: need at least {_MIN_BLOB} bytes, got {len(blob)}")
    nonce = blob[:_NONCE_SIZE]
    ct_and_tag = blob[_NONCE_SIZE:]
    # AESGCM.decrypt raises InvalidTag on any mismatch — no need to check manually.
    plaintext_bytes = AESGCM(key).decrypt(nonce, ct_and_tag, None)
    return plaintext_bytes.decode("utf-8")
