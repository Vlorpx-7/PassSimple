"""Tests for src/generator.py — length bounds, charset guarantees, entropy."""

from __future__ import annotations

import inspect
import math

import pytest

import src.generator as generator_module
from src.generator import (
    _AMBIGUOUS,
    _DIGITS,
    _LOWER,
    _SYMBOLS,
    _UPPER,
    entropy_bits,
    generate_password,
)

# ---------------------------------------------------------------------------
# Length bounds
# ---------------------------------------------------------------------------


def test_default_length() -> None:
    """Default password must be exactly 20 characters."""
    assert len(generate_password()) == 20


def test_custom_length_in_range() -> None:
    """Passwords of any valid length must have exactly that many characters."""
    for length in (16, 20, 32, 50, 64):
        assert len(generate_password(length)) == length


def test_length_minimum_boundary_accepted() -> None:
    """Length 16 (minimum) must be accepted."""
    assert len(generate_password(16)) == 16


def test_length_maximum_boundary_accepted() -> None:
    """Length 64 (maximum) must be accepted."""
    assert len(generate_password(64)) == 64


def test_length_below_minimum_raises() -> None:
    """Length 15 (below minimum 16) must raise ValueError."""
    with pytest.raises(ValueError, match="length"):
        generate_password(15)


def test_length_above_maximum_raises() -> None:
    """Length 65 (above maximum 64) must raise ValueError."""
    with pytest.raises(ValueError, match="length"):
        generate_password(65)


# ---------------------------------------------------------------------------
# Empty charset
# ---------------------------------------------------------------------------


def test_all_charsets_disabled_raises() -> None:
    """Disabling every character class must raise ValueError."""
    with pytest.raises(ValueError, match="at least one character class required"):
        generate_password(lowercase=False, uppercase=False, digits=False, symbols=False)


# ---------------------------------------------------------------------------
# Charset guarantee — 100 iterations each for statistical confidence
# ---------------------------------------------------------------------------


def test_guarantee_lowercase_present() -> None:
    """Lowercase-only: every password must contain at least one a–z character."""
    for _ in range(100):
        pw = generate_password(lowercase=True, uppercase=False, digits=False, symbols=False)
        assert any(c in _LOWER for c in pw), f"missing lowercase in {pw!r}"


def test_guarantee_uppercase_present() -> None:
    """Uppercase-only: every password must contain at least one A–Z character."""
    for _ in range(100):
        pw = generate_password(lowercase=False, uppercase=True, digits=False, symbols=False)
        assert any(c in _UPPER for c in pw), f"missing uppercase in {pw!r}"


def test_guarantee_digits_present() -> None:
    """Digits-only: every password must contain at least one digit."""
    for _ in range(100):
        pw = generate_password(lowercase=False, uppercase=False, digits=True, symbols=False)
        assert any(c in _DIGITS for c in pw), f"missing digit in {pw!r}"


def test_guarantee_symbols_present() -> None:
    """Symbols-only: every password must contain at least one symbol."""
    for _ in range(100):
        pw = generate_password(lowercase=False, uppercase=False, digits=False, symbols=True)
        assert any(c in _SYMBOLS for c in pw), f"missing symbol in {pw!r}"


def test_guarantee_all_charsets_present() -> None:
    """All classes enabled: every password must have at least one char from each class."""
    for _ in range(100):
        pw = generate_password()
        assert any(c in _LOWER for c in pw), f"missing lowercase in {pw!r}"
        assert any(c in _UPPER for c in pw), f"missing uppercase in {pw!r}"
        assert any(c in _DIGITS for c in pw), f"missing digit in {pw!r}"
        assert any(c in _SYMBOLS for c in pw), f"missing symbol in {pw!r}"


# ---------------------------------------------------------------------------
# Ambiguous character exclusion
# ---------------------------------------------------------------------------


def test_exclude_ambiguous_removes_all_ambiguous_chars() -> None:
    """No character from _AMBIGUOUS must appear when exclude_ambiguous=True."""
    for _ in range(100):
        pw = generate_password(exclude_ambiguous=True)
        assert not any(c in _AMBIGUOUS for c in pw), f"ambiguous char in {pw!r}"


def test_exclude_ambiguous_false_may_include_ambiguous() -> None:
    """Without exclusion, ambiguous chars are part of the alphabet (statistical)."""
    # With 100 passwords of length 20 from digits only, '0' and '1' should appear.
    found = False
    for _ in range(100):
        pw = generate_password(lowercase=False, uppercase=False, digits=True, symbols=False)
        if any(c in _AMBIGUOUS for c in pw):
            found = True
            break
    assert found, "expected at least one ambiguous char across 100 digit-only passwords"


# ---------------------------------------------------------------------------
# CSPRNG purity: no 'random' module reference
# ---------------------------------------------------------------------------


def test_no_random_import() -> None:
    """The generator source must not contain the substring 'random'."""
    assert "random" not in inspect.getsource(generator_module)


# ---------------------------------------------------------------------------
# entropy_bits
# ---------------------------------------------------------------------------


def test_entropy_bits_exact_formula() -> None:
    """entropy_bits must equal log2(alphabet_size) * length exactly."""
    assert abs(entropy_bits(20, 26) - 20 * math.log2(26)) < 1e-10


def test_entropy_bits_known_value() -> None:
    """20 chars from a 26-char alphabet is approximately 94 bits."""
    assert abs(entropy_bits(20, 26) - 94.0) < 0.1  # actual: ~94.009 bits


def test_entropy_bits_increases_with_length() -> None:
    """Longer passwords must have strictly more entropy than shorter ones."""
    assert entropy_bits(30, 26) > entropy_bits(20, 26)


def test_entropy_bits_increases_with_alphabet_size() -> None:
    """A larger alphabet must produce strictly more entropy for the same length."""
    assert entropy_bits(20, 94) > entropy_bits(20, 26)
