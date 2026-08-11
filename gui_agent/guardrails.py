"""
Guardrail utilities required by spec.
Functions:
 - check_scope(current_window, target_spec) -> bool
 - require_confirmation(action) -> bool
 - write_audit_step(session_dir, step_n, screenshot_bytes, meta, suffix="")
 - check_stop_file() -> bool
 - IterationCapReached exception class
"""
import os
import json
from pathlib import Path
from datetime import datetime

STOP_FILENAME = "STOP"

class IterationCapReached(Exception):
    pass

def check_scope(window, target_spec: str) -> bool:
    """
    Verify target identity: foreground window title contains target_spec (case-insensitive).
    """
    try:
        title = window.title or ""
        return target_spec.lower() in title.lower()
    except Exception:
        return False

def require_confirmation(action: dict) -> bool:
    """
    If the action is potentially destructive, require typed 'yes' from human.
    action: dict with a readable description for the user.
    """
    desc = action.get("description") or json.dumps(action, ensure_ascii=False)
    print("HARD CONFIRMATION REQUIRED for the following action:")
    print(desc)
    print("Type 'yes' (without quotes) to confirm and proceed. Any other input will cancel.")
    try:
        resp = input("> ").strip().lower()
        return resp == "yes"
    except Exception:
        return False

def write_audit_step(session_dir: str, step_n: int, screenshot_bytes: bytes, meta: dict, suffix: str = ""):
    """
    Write screenshot and metadata to ./run_logs/<session>/step_<n>/
    """
    step_dir = Path(session_dir) / f"step_{step_n}{suffix}"
    step_dir.mkdir(parents=True, exist_ok=True)
    # screenshot
    try:
        with open(step_dir / "screenshot.png", "wb") as f:
            f.write(screenshot_bytes)
    except Exception:
        pass
    # meta json
    meta_out = meta.copy()
    meta_out["timestamp"] = datetime.utcnow().isoformat() + "Z"
    with open(step_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=2, ensure_ascii=False)

def check_stop_file() -> bool:
    return os.path.exists(STOP_FILENAME)
