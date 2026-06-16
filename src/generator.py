"""Password generator using the secrets CSPRNG."""

from __future__ import annotations


def generate_password(
    length: int = 20,
    use_lowercase: bool = True,
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """Generate a random password with at least one character from each enabled class."""
    raise NotImplementedError


def entropy_bits(alphabet_size: int, length: int) -> float:
    """Return log2(alphabet_size) * length as a float."""
    raise NotImplementedError
