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
    """Represents a single vault entry. Password field is always encrypted bytes."""

    id: int | None
    title: str
    username: str | None
    password_ct: bytes  # nonce + ciphertext + GCM tag — never plaintext
    url: str | None
    notes: str | None
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    tags: list[Tag] = field(default_factory=list)

    def __repr__(self) -> str:
        # Intentionally omit password_ct from repr to avoid accidental logging.
        return (
            f"Entry(id={self.id!r}, title={self.title!r}, "
            f"username={self.username!r}, url={self.url!r})"
        )
