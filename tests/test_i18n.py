"""Tests for the Translator singleton and tr() convenience function."""

from __future__ import annotations

import pytest

from src.i18n import Translator, tr


@pytest.fixture(autouse=True)
def reset_translator():
    """Reset the Translator singleton to a clean state before every test."""
    # Force a fresh instance so language state from one test cannot bleed into the next.
    Translator._instance = None
    Translator._current_lang = "de"
    Translator._translations = {}
    yield
    # Teardown: reset again so subsequent test modules start clean.
    Translator._instance = None
    Translator._current_lang = "de"
    Translator._translations = {}


def test_translator_returns_key_when_missing():
    """A key present in neither DE nor EN is returned verbatim as the fallback."""
    t = Translator.instance()
    result = t.tr("no.such.key.anywhere")
    assert result == "no.such.key.anywhere"


def test_translator_falls_back_to_de_when_en_missing():
    """If a key exists only in DE, it is returned even when the active language is EN."""
    t = Translator.instance()
    # Inject a DE-only key directly into the loaded translations.
    t._translations["de"]["_test_de_only"] = "nur Deutsch"
    t._translations["en"].pop("_test_de_only", None)

    t.set_language("en")
    result = t.tr("_test_de_only")
    assert result == "nur Deutsch"


def test_translator_switches_language():
    """set_language('en') causes tr() to return the English value for known keys."""
    t = Translator.instance()
    t.set_language("en")
    assert t.tr("app.name") == "PassSimple"
    # A key that differs between DE and EN:
    assert t.tr("status.ready") == "Ready"


def test_translator_handles_nested_keys():
    """Dot-notation resolves arbitrarily deep nested keys in both languages."""
    t = Translator.instance()
    # DE
    assert t.tr("entry.field.title") == "Titel"
    assert t.tr("entry.button.new") == "+ Neuer Eintrag"
    # EN
    t.set_language("en")
    assert t.tr("entry.field.title") == "Title"
    assert t.tr("entry.button.new") == "+ New Entry"


def test_tr_shortcut_uses_active_language():
    """The module-level tr() shortcut delegates to the singleton correctly."""
    Translator.instance().set_language("en")
    assert tr("settings.title") == "Settings"
    Translator.instance().set_language("de")
    assert tr("settings.title") == "Einstellungen"


def test_current_language_property():
    """current_language reflects the active language after set_language()."""
    t = Translator.instance()
    assert t.current_language == "de"
    t.set_language("en")
    assert t.current_language == "en"


def test_set_language_ignores_unknown_codes():
    """An unsupported language code leaves the active language unchanged."""
    t = Translator.instance()
    t.set_language("en")
    t.set_language("xx")  # unsupported
    assert t.current_language == "en"
    assert t.tr("status.ready") == "Ready"
