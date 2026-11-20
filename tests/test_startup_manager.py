"""Unit tests for Windows startup integration."""

from core.startup_manager import StartupManager


def test_startup_launcher_path():
    path = StartupManager.get_launcher_path()
    assert "main.py" in path
    assert "pythonw" in path.lower()


def test_startup_toggle():
    # Test toggling without crashing
    current = StartupManager.is_startup_enabled()

    # Toggle to False
    res = StartupManager.set_startup(False)
    assert res is True
    assert StartupManager.is_startup_enabled() is False

    # Restore initial state
    StartupManager.set_startup(current)
