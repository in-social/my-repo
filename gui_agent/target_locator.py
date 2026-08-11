"""
Locate target window/tab for desktop or browser modes.
Provides locate_target(target_spec: str, mode: str) -> WindowWrapper
WindowWrapper is a small object with:
  - rect() -> (left, top, right, bottom)
  - set_focus() / bring_to_front()
  - friendly_name / title
"""
from typing import Optional
from dataclasses import dataclass
import re
import time

from pywinauto import Desktop, findwindows

class TargetNotFoundError(Exception):
    pass

@dataclass
class WindowWrapper:
    element: object  # pywinauto window element

    @property
    def title(self) -> str:
        try:
            return self.element.window_text()
        except Exception:
            return ""

    def rect(self):
        r = self.element.rectangle()
        return (r.left, r.top, r.right, r.bottom)

    def bring_to_front(self):
        try:
            self.element.set_focus()
        except Exception:
            try:
                self.element.minimize()
                self.element.restore()
                self.element.set_focus()
            except Exception:
                pass

def locate_target(target_spec: str, mode: str, timeout: float = 3.0) -> WindowWrapper:
    d = Desktop(backend="uia")
    target_spec_low = target_spec.lower()
    if mode == "desktop":
        # find top-level windows whose title contains target_spec (case-insensitive)
        end_ts = time.time() + timeout
        while time.time() < end_ts:
            windows = d.windows()
            for w in windows:
                try:
                    title = (w.window_text() or "").strip()
                    if target_spec_low in title.lower():
                        return WindowWrapper(w)
                except Exception:
                    continue
            time.sleep(0.15)
        raise TargetNotFoundError(f"No top-level window with title containing '{target_spec}'")
    elif mode == "browser":
        # heuristics: find common browser processes
        browsers = []
        for w in d.windows():
            try:
                cls = w.class_name() or ""
                if any(k in cls.lower() for k in ("chrome", "edge", "mozilla", "browser", "applicationframewindow")):
                    browsers.append(w)
            except Exception:
                continue
        # Among found browser windows, check visible tab title in window_text
        for b in browsers:
            title = (b.window_text() or "")
            if target_spec_low in title.lower():
                return WindowWrapper(b)
        # If not found by visible title, return first browser as candidate (agent must verify via screenshot)
        if browsers:
            return WindowWrapper(browsers[0])
        raise TargetNotFoundError(f"No browser window found matching '{target_spec}'")
    else:
        raise ValueError("mode must be 'desktop' or 'browser'")
