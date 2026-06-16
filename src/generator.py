"""Password generator backed exclusively by the secrets module (CSPRNG)."""

from __future__ import annotations

import math
import secrets

_LOWER: str = "abcdefghijklmnopqrstuvwxyz"
_UPPER: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_DIGITS: str = "0123456789"
_SYMBOLS: str = "!@#$%^&*()-_=+[]{};:,.<>?"
# Characters excluded when exclude_ambiguous=True:
# visually similar glyphs that cause transcription errors.
_AMBIGUOUS: str = "0Oo1lI|`"

_MIN_LENGTH: int = 16
_MAX_LENGTH: int = 64


def generate_password(
    length: int = 20,
    *,
    lowercase: bool = True,
    uppercase: bool = True,
    digits: bool = True,
    symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """Generate a password with at least one character from each enabled class.

    Strategy:
    1. Pick one character per active charset with secrets.choice — guarantees coverage.
    2. Fill remaining positions from the union of all active charsets.
    3. Shuffle with secrets.SystemRandom().shuffle() so the guaranteed characters
       are not always at fixed positions.

    Raises ValueError for out-of-range length or if no charset is enabled.
    """
    if not (_MIN_LENGTH <= length <= _MAX_LENGTH):
        raise ValueError(
            f"length must be between {_MIN_LENGTH} and {_MAX_LENGTH}, got {length}"
        )

    # Build the filtered charset for each enabled class.
    active: list[str] = []
    for enabled, base in [
        (lowercase, _LOWER),
        (uppercase, _UPPER),
        (digits, _DIGITS),
        (symbols, _SYMBOLS),
    ]:
        if enabled:
            charset = (
                "".join(c for c in base if c not in _AMBIGUOUS)
                if exclude_ambiguous
                else base
            )
            active.append(charset)

    if not active:
        raise ValueError("at least one character class required")

    # Step 1: one guaranteed character per active class.
    chars: list[str] = [secrets.choice(charset) for charset in active]

    # Step 2: fill remaining slots from the union of all active charsets.
    # The charsets are pairwise disjoint by construction so simple join = union.
    alphabet = "".join(active)
    chars.extend(secrets.choice(alphabet) for _ in range(length - len(active)))

    # Step 3: shuffle so guaranteed chars don't cluster at the front.
    secrets.SystemRandom().shuffle(chars)

    return "".join(chars)


def entropy_bits(length: int, alphabet_size: int) -> float:
    """Return the theoretical entropy of a password in bits: log2(alphabet_size) * length."""
    return math.log2(alphabet_size) * length
