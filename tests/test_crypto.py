"""Tests for src/crypto.py — AES-GCM roundtrip, DPAPI, tamper detection."""

from __future__ import annotations

import sys

import pytest
from cryptography.exceptions import InvalidTag

from src.crypto import (
    decrypt,
    encrypt,
    generate_master_key,
    protect_master_key,
    unprotect_master_key,
)


# ---------------------------------------------------------------------------
# AES-GCM tests — platform-independent
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_roundtrip() -> None:
    """Encrypt then decrypt should return the original plaintext."""
    key = generate_master_key()
    plaintext = "correct horse battery staple"
    assert decrypt(encrypt(plaintext, key), key) == plaintext


def test_roundtrip_unicode() -> None:
    """Unicode passwords (emoji, CJK, accents) must survive the roundtrip."""
    key = generate_master_key()
    plaintext = "P@ssw0rd! — Ünïcödé — 日本語"
    assert decrypt(encrypt(plaintext, key), key) == plaintext


def test_wrong_key_raises() -> None:
    """Decrypting with a different key must raise InvalidTag."""
    key_a = generate_master_key()
    key_b = generate_master_key()
    blob = encrypt("secret", key_a)
    with pytest.raises(InvalidTag):
        decrypt(blob, key_b)


def test_tampered_nonce_raises() -> None:
    """Flipping a byte inside the nonce must fail GCM authentication."""
    key = generate_master_key()
    blob = encrypt("secret", key)
    tampered = bytearray(blob)
    tampered[0] ^= 0xFF  # corrupt first byte of 12-byte nonce
    with pytest.raises(InvalidTag):
        decrypt(bytes(tampered), key)


def test_tampered_ciphertext_raises() -> None:
    """Flipping a byte in the ciphertext body must fail GCM authentication."""
    key = generate_master_key()
    blob = encrypt("secret", key)
    tampered = bytearray(blob)
    tampered[12] ^= 0xFF  # first byte after the nonce = start of ciphertext
    with pytest.raises(InvalidTag):
        decrypt(bytes(tampered), key)


def test_tampered_tag_raises() -> None:
    """Flipping a byte in the GCM tag must fail authentication."""
    key = generate_master_key()
    blob = encrypt("secret", key)
    tampered = bytearray(blob)
    tampered[-1] ^= 0xFF  # last byte = last byte of the 16-byte tag
    with pytest.raises(InvalidTag):
        decrypt(bytes(tampered), key)


def test_nonce_uniqueness() -> None:
    """Two encrypt() calls with the same key must produce different nonces."""
    key = generate_master_key()
    blob1 = encrypt("same plaintext", key)
    blob2 = encrypt("same plaintext", key)
    # Nonce is the first 12 bytes of the blob.
    assert blob1[:12] != blob2[:12], "Nonces must never repeat for the same key"
    # Full blobs must also differ (nonce difference cascades to ciphertext).
    assert blob1 != blob2


def test_generate_master_key_length() -> None:
    """Master key must be exactly 32 bytes (AES-256)."""
    assert len(generate_master_key()) == 32


def test_generate_master_key_is_random() -> None:
    """Two consecutive calls must not produce the same key."""
    assert generate_master_key() != generate_master_key()


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


def test_encrypt_wrong_key_length_raises() -> None:
    """encrypt() must raise ValueError for a key that is not 32 bytes."""
    with pytest.raises(ValueError, match="key must be 32 bytes"):
        encrypt("secret", b"tooshort")


def test_decrypt_wrong_key_length_raises() -> None:
    """decrypt() must raise ValueError for a key that is not 32 bytes."""
    key = generate_master_key()
    blob = encrypt("secret", key)
    with pytest.raises(ValueError, match="key must be 32 bytes"):
        decrypt(blob, b"x" * 31)


def test_decrypt_blob_too_short_raises() -> None:
    """decrypt() must raise ValueError when blob is shorter than 28 bytes."""
    key = generate_master_key()
    with pytest.raises(ValueError, match="blob too short"):
        decrypt(b"\x00" * 27, key)


def test_decrypt_blob_at_minimum_length_does_not_raise_value_error() -> None:
    """A 28-byte blob clears the length check; InvalidTag is the expected failure."""
    key = generate_master_key()
    with pytest.raises(InvalidTag):
        decrypt(b"\x00" * 28, key)


# ---------------------------------------------------------------------------
# DPAPI tests — Windows only
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_dpapi_roundtrip() -> None:
    """protect_master_key / unprotect_master_key must recover the original key."""
    key = generate_master_key()
    blob = protect_master_key(key)
    assert unprotect_master_key(blob) == key


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_dpapi_output_differs_from_key() -> None:
    """DPAPI ciphertext must not equal the plaintext key."""
    key = generate_master_key()
    blob = protect_master_key(key)
    assert blob != key


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_dpapi_two_calls_differ() -> None:
    """DPAPI uses internal randomness — two protect() calls must not be identical."""
    key = generate_master_key()
    assert protect_master_key(key) != protect_master_key(key)


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_dpapi_wrong_entropy_raises() -> None:
    """Decrypting with wrong optional_entropy must fail.

    This verifies that _DPAPI_ENTROPY actually participates in the DPAPI
    protection — a generic DPAPI unprotect call (no entropy) cannot recover
    the key even for the correct Windows user account.
    """
    import pywintypes
    import win32crypt

    key = generate_master_key()
    blob = protect_master_key(key)
    with pytest.raises(pywintypes.error):
        win32crypt.CryptUnprotectData(blob, b"wrong-entropy", None, None, 0)
