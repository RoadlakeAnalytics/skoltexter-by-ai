"""Tests for menu label parsing variations in `src/setup/ui/menu.py`."""

from src.setup.ui import menu
from src.setup import i18n


def test_ui_items_handles_numeric_prefixes(monkeypatch):
    # Return labels with different prefixes to hit trimming logic
    def fake_translate(key):
        mapping = {
            "menu_option_1": "1. Manage Virtual",
            "menu_option_2": "2. View",
            "menu_option_3": "3. Run",
            "menu_option_4": "4. Logs",
            "menu_option_5": "5. Reset",
            "menu_option_6": "6. Exit",
        }
        return mapping.get(key, key)

    # Monkeypatch the translation used by the menu module itself
    monkeypatch.setattr(menu, "translate", fake_translate)
    items = menu._ui_items()
    assert items[0][1].startswith("Manage")
