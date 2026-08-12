import os
import tempfile
import builtins
import pytest
from pathlib import Path
from guardrails import check_scope, require_confirmation, check_stop_file, write_audit_step, IterationCapReached

class DummyWindow:
    def __init__(self, title):
        self._title = title
    @property
    def title(self):
        return self._title
    def rect(self):
        return (0,0,100,100)

def test_check_scope_match():
    w = DummyWindow("MyTarget - App")
    assert check_scope(w, "mytarget")

def test_check_scope_no_match():
    w = DummyWindow("Other")
    assert not check_scope(w, "mytarget")

def test_require_confirmation_yes(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt="": "yes")
    action = {"description": "Dangerous action test"}
    assert require_confirmation(action) is True

def test_require_confirmation_no(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt="": "no")
    action = {"description": "Dangerous action test"}
    assert require_confirmation(action) is False

def test_check_stop_file(tmp_path):
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        assert not check_stop_file()
        Path("STOP").write_text("stop")
        assert check_stop_file()
    finally:
        os.chdir(cwd)

def test_write_audit_step(tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    screenshot = b"PNGDATA"
    write_audit_step(str(session_dir), 1, screenshot, {"note":"x"})
    step_dir = session_dir / "step_1"
    assert step_dir.exists()
    assert (step_dir / "screenshot.png").exists()
    assert (step_dir / "meta.json").exists()
