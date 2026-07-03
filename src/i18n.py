"""Internationalisation: Translator singleton and tr() convenience shortcut."""

from __future__ import annotations

import json

from src.paths import resource_path


class Translator:
    """Singleton that loads JSON translation files and resolves dotted keys.

    Supported languages: "de" (default), "en".
    """

    _instance: Translator | None = None
    _current_lang: str = "de"
    _translations: dict[str, dict] = {}

    @classmethod
    def instance(cls) -> Translator:
        """Return the process-wide Translator, initialising it on first call."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Load all supported translation files into memory."""
        for lang in ("de", "en"):
            path = resource_path(f"src/translations/{lang}.json")
            with open(path, "r", encoding="utf-8") as f:
                self._translations[lang] = json.load(f)

    def set_language(self, lang: str) -> None:
        """Switch the active language. No-op for unsupported codes."""
        if lang in self._translations:
            self._current_lang = lang

    @property
    def current_language(self) -> str:
        """The currently active language code."""
        return self._current_lang

    def tr(self, key: str) -> str:
        """Resolve a dotted key against the active language.

        Fall-back chain: active language → German → key string itself.
        """
        def _lookup(lang: str) -> str | None:
            node: object = self._translations.get(lang, {})
            for part in key.split("."):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    return None
            return node if isinstance(node, str) else None

        result = _lookup(self._current_lang)
        if result is None:
            result = _lookup("de")
        return result if result is not None else key


def tr(key: str) -> str:
    """Module-level shortcut: ``tr("some.key")`` → translated string."""
    return Translator.instance().tr(key)
