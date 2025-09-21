"""Tests for the ``manage_virtual_environment`` wrapper in ``src.setup.app``.

These ensure the function delegates to the refactored venv manager when
available and is inert when the manager module is absent.
"""

import sys

import src.setup.app_venv as app


def test_manage_virtual_environment_delegates(monkeypatch) -> None:
    """When a venv manager is present, ``manage_virtual_environment`` calls it.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to install a fake venv_manager module.

    Returns
    -------
    None
    """
    called = {}

    fake_vm = type(sys)("src.setup.venv_manager")

    def _manage(*a, **k):
        called["ok"] = True

    fake_vm.manage_virtual_environment = _manage
    monkeypatch.setitem(sys.modules, "src.setup.venv_manager", fake_vm)
    if "src.setup" in sys.modules:
        monkeypatch.setattr(sys.modules["src.setup"], "venv_manager", fake_vm, raising=False)

    app.manage_virtual_environment()
    assert called.get("ok", False) is True


def test_manage_virtual_environment_no_manager_is_noop(monkeypatch) -> None:
    """If no venv_manager is importable the wrapper does nothing.

    The test simply ensures no exception is raised when the module is
    absent.
    """
    # Ensure module is not present
    monkeypatch.delitem(sys.modules, "src.setup.venv_manager", raising=False)
    app.manage_virtual_environment()  # should not raise
