"""Vault package — re-exports for backward-compatible imports."""

from src.db.schema import _DDL, _SCHEMA_VERSION
from src.db.vault import Vault

__all__ = ["Vault", "_DDL", "_SCHEMA_VERSION"]
