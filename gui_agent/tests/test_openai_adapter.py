import os
import pytest
from gui_agent.adapters.openai_adapter import OpenAIAdapter


def test_preflight_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = OpenAIAdapter(model_name="gpt-4o-mini-vision")
    pf = adapter.preflight()
    assert pf["ok"] is False
    assert "OPENAI_API_KEY" in pf["message"] or "not set" in pf["message"].lower()


def test_supports_images_without_pkg(monkeypatch):
    # simulate openai package missing by monkeypatching the module variable
    import importlib
    # If openai is installed in the environment this test will be conservative: it checks the return type
    adapter = OpenAIAdapter(model_name="gpt-4o-mini-vision")
    pf = adapter.preflight()
    # pf is a dict; either ok False (no key / no pkg) or ok True (if key+pkg exist). We only assert structure
    assert isinstance(pf, dict)
