"""
Wrappers for pyautogui actions and window-scoped screenshot capture.
- capture_window_screenshot(window) -> bytes (PNG)
- focus_window(window)
- perform_action(window, decision)
"""
import io
import time
import json
from typing import Tuple
from PIL import Image
import pyautogui
import mss
from guardrails import write_audit_step

def focus_window(window):
    try:
        window.bring_to_front()
        time.sleep(0.25)
    except Exception:
        pass

def rect_from_window(window) -> Tuple[int,int,int,int]:
    left, top, right, bottom = window.rect()
    return (left, top, right, bottom)

def capture_window_screenshot(window) -> bytes:
    left, top, right, bottom = rect_from_window(window)
    width = max(1, right - left)
    height = max(1, bottom - top)
    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

def perform_action(window, decision: dict):
    """
    decision example:
      {"action":"click", "x": 100, "y": 200, "relative": true, "description": "..."}
      {"action":"type", "text":"hello"}
      {"action":"scroll", "direction":"down", "amount":3}
      {"action":"key", "key":"enter"}
    Coordinates are relative to window top-left if 'relative' true, otherwise absolute screen coords.
    Only one action executed per call.
    """
    action = decision.get("action")
    left, top, _, _ = rect_from_window(window)
    if action == "click":
        x = decision.get("x")
        y = decision.get("y")
        if decision.get("relative", True):
            pyautogui.click(left + x, top + y)
        else:
            pyautogui.click(x, y)
    elif action == "type":
        text = decision.get("text", "")
        interval = decision.get("interval", 0.02)
        pyautogui.typewrite(text, interval=interval)
    elif action == "scroll":
        direction = decision.get("direction", "down")
        amount = decision.get("amount", 1)
        amt = amount if direction == "down" else -amount
        pyautogui.scroll(-amt)  # pyautogui.scroll positive = up on Windows
    elif action == "move":
        x = decision.get("x"); y = decision.get("y")
        if decision.get("relative", True):
            pyautogui.moveTo(left + x, top + y)
        else:
            pyautogui.moveTo(x, y)
    elif action == "key":
        key = decision.get("key")
        pyautogui.press(key)
    else:
        raise ValueError(f"Unknown action: {action}")
