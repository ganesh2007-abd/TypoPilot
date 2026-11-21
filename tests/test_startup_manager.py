"""Unit tests for Windows startup integration."""

from core.startup_manager import StartupManager


def test_startup_launcher_path():
    path = StartupManager.get_launcher_path()
    assert "main.py" in path
    assert "pythonw" in path.lower()


def test_startup_toggle(tmp_path, monkeypatch):
    # Test toggling safely with isolated directory to avoid OS permission boundaries in sandbox
    monkeypatch.setattr(StartupManager, "get_startup_folder", staticmethod(lambda: tmp_path))

    assert StartupManager.is_startup_enabled() is False

    # Toggle to True
    res = StartupManager.set_startup(True)
    assert res is True
    assert StartupManager.is_startup_enabled() is True
    assert (tmp_path / "TypoPilot.bat").exists()

    # Toggle to False
    res = StartupManager.set_startup(False)
    assert res is True
    assert StartupManager.is_startup_enabled() is False
    assert not (tmp_path / "TypoPilot.bat").exists()
