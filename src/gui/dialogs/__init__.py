"""Dialog package — re-exports all dialog classes."""

from src.gui.dialogs.entry_dialog import EntryDialog
from src.gui.dialogs.password_generator_dialog import PasswordGeneratorDialog
from src.gui.dialogs.settings_dialog import SettingsDialog

__all__ = ["EntryDialog", "PasswordGeneratorDialog", "SettingsDialog"]
