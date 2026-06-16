"""Tests for src/crypto.py — AES-GCM roundtrip, DPAPI, tamper detection."""

import pytest

from src.crypto import decrypt, encrypt, generate_master_key, protect_master_key, unprotect_master_key


def test_encrypt_decrypt_roundtrip() -> None:
    """Encrypt then decrypt should return the original plaintext."""
    raise NotImplementedError


def test_wrong_key_raises() -> None:
    """Decrypting with a different key must raise an exception."""
    raise NotImplementedError


def test_tampered_ciphertext_raises() -> None:
    """Flipping a byte in the ciphertext must fail GCM authentication."""
    raise NotImplementedError


def test_nonce_uniqueness() -> None:
    """Two calls to encrypt() with the same key must produce different nonces."""
    raise NotImplementedError


def test_dpapi_roundtrip() -> None:
    """protect_master_key / unprotect_master_key roundtrip."""
    raise NotImplementedError


def test_generate_master_key_length() -> None:
    """Master key must be exactly 32 bytes."""
    raise NotImplementedError
