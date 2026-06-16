"""Dataclasses for vault entries and tags."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Tag:
    """Represents a user-defined tag."""

    id: int | None
    name: str


@dataclass
class Entry:
    """Represents a single vault entry.

    password_ct always holds the encrypted blob (nonce + ciphertext + GCM tag).
    password is a transient plaintext field populated by Vault.get_entry; it is
    never written to the database and is excluded from __repr__ and equality
    comparisons to prevent accidental leakage.
    """

    id: int | None
    title: str
    username: str | None
    password_ct: bytes  # nonce + ciphertext + GCM tag — never plaintext on disk
    url: str | None
    notes: str | None
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    tags: list[Tag] = field(default_factory=list)
    # Decrypted password — populated by Vault.get_entry, None in list/search results.
    # compare=False: equality checks password_ct, not this derived field.
    password: str | None = field(default=None, compare=False)

    def __repr__(self) -> str:
        # password and password_ct are intentionally absent — safe for logging.
        return (
            f"Entry(id={self.id!r}, title={self.title!r}, "
            f"username={self.username!r}, url={self.url!r})"
        )
