"""Extra tests for the venv manager covering recreate error handling."""

from types import SimpleNamespace
from pathlib import Path
import os

import src.setup.venv_manager as vm


def test_manage_virtual_environment_recreate_permission_error(
    monkeypatch, tmp_path: Path
):
    """When safe_rmtree raises PermissionError the manager logs and returns."""
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()

    # Build a minimal UI adapter expected by the function
    captured = {"msgs": []}

    class UI:
        def __init__(self):
            self.logger = SimpleNamespace(
                error=lambda *a, **k: captured["msgs"].append(str(a))
            )

        ask_text = staticmethod(lambda prompt, default=None: "y")
        rprint = staticmethod(lambda *a, **k: None)
        ui_info = staticmethod(lambda *a, **k: None)
        _ = staticmethod(lambda k: k)
        subprocess = None

    ui = UI()

    # Simulate existing venv and recreate chosen; safe_rmtree raises PermissionError
    monkeypatch.setattr(vm.venvmod, "is_venv_active", lambda: False)
    monkeypatch.setattr(vm, "create_safe_path", lambda p: p)
    monkeypatch.setattr(
        vm, "safe_rmtree", lambda p: (_ for _ in ()).throw(PermissionError("denied"))
    )

    # Run the manager; it should handle the PermissionError and return
    vm.manage_virtual_environment(Path("/tmp"), venv_dir, Path("r1"), Path("r2"), ui)
    assert any("denied" in s for s in " ".join(captured["msgs"])) or captured["msgs"]
