"""Tests for src/generator.py — length, charset guarantees, CSPRNG usage."""

import pytest

from src.generator import entropy_bits, generate_password


def test_default_length() -> None:
    """Default password length should be 20."""
    raise NotImplementedError


def test_custom_length() -> None:
    """Password length should match the requested value within 16–64 bounds."""
    raise NotImplementedError


def test_contains_lowercase() -> None:
    """When lowercase is enabled, generated password must include a-z."""
    raise NotImplementedError


def test_contains_uppercase() -> None:
    """When uppercase is enabled, generated password must include A-Z."""
    raise NotImplementedError


def test_contains_digits() -> None:
    """When digits are enabled, generated password must include 0-9."""
    raise NotImplementedError


def test_contains_symbols() -> None:
    """When symbols are enabled, generated password must include a symbol."""
    raise NotImplementedError


def test_exclude_ambiguous() -> None:
    """When exclude_ambiguous is True, ambiguous characters must not appear."""
    raise NotImplementedError


def test_no_random_import() -> None:
    """The generator module must not import the random module."""
    raise NotImplementedError


def test_entropy_bits() -> None:
    """entropy_bits should return log2(alphabet) * length."""
    raise NotImplementedError
