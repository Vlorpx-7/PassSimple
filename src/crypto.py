"""DPAPI master-key management and AES-GCM per-entry encryption."""

from __future__ import annotations


def protect_master_key(key: bytes) -> bytes:
    """Encrypt a 32-byte master key with DPAPI (user scope). Returns opaque blob."""
    raise NotImplementedError


def unprotect_master_key(blob: bytes) -> bytes:
    """Decrypt a DPAPI blob back to the 32-byte master key."""
    raise NotImplementedError


def generate_master_key() -> bytes:
    """Generate a cryptographically random 32-byte master key."""
    raise NotImplementedError


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt plaintext with AES-256-GCM. Returns nonce + ciphertext + tag."""
    raise NotImplementedError


def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt an AES-256-GCM blob produced by encrypt(). Raises on auth failure."""
    raise NotImplementedError
