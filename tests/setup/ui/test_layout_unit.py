"""Tests for the lightweight layout helpers. (unique name)"""

from src.setup.ui.layout import _Slot, build_dashboard_layout


def test_slot_update():
    s = _Slot("init")
    assert s.value == "init"
    s.update("next")
    assert s.value == "next"


def test_build_dashboard_layout_old_and_new_signatures():
    def tr(x):
        return x

    layout_old = build_dashboard_layout(tr, "welcome", None, "en")
    assert "header" in layout_old
    assert layout_old["header"].value == "welcome"

    layout_new = build_dashboard_layout("welcome2")
    assert layout_new["header"].value == "welcome2"
