from dataclasses import dataclass
from typing import Any, Optional, Tuple
from io import BytesIO

try:
    from pywinauto.keyboard import send_keys as _send_keys
    PYWIN_AVAILABLE = True
except Exception:
    PYWIN_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


class TargetNotFoundError(Exception):
    pass


@dataclass
class WindowWrapper:
    element: Any  # pywinauto WindowSpecification / Wrapper

    @property
    def title(self) -> str:
        try:
            return self.element.window_text()
        except Exception:
            return ""

    @property
    def friendly_name(self) -> str:
        return self.title

    @property
    def hwnd(self) -> Optional[int]:
        try:
            return int(getattr(self.element, "handle", None)
                       or getattr(self.element, "hwnd", None)
                       or (getattr(self.element, "element_info", None) and getattr(self.element.element_info, "handle", None)))
        except Exception:
            return None

    @property
    def pid(self) -> Optional[int]:
        try:
            return int(getattr(self.element, "process_id", None)
                       or (getattr(self.element, "element_info", None) and getattr(self.element.element_info, "process_id", None)))
        except Exception:
            return None

    def rect(self) -> Tuple[int, int, int, int]:
        try:
            r = self.element.rectangle()
            return (int(r.left), int(r.top), int(r.right), int(r.bottom))
        except Exception:
            return (0, 0, 0, 0)

    def set_focus(self) -> None:
        try:
            if hasattr(self.element, "set_focus"):
                self.element.set_focus()
                return
            if hasattr(self.element, "wrapper_object"):
                self.element.wrapper_object().set_focus()
                return
            raise RuntimeError("No focus API available on backend element")
        except Exception as e:
            raise RuntimeError(f"Failed to focus window: {e}")

    def bring_to_front(self) -> None:
        try:
            self.set_focus()
        except Exception:
            # best-effort fallback: try restore then focus
            try:
                if hasattr(self.element, "restore"):
                    self.element.restore()
                elif hasattr(self.element, "minimize") and hasattr(self.element, "maximize"):
                    try:
                        self.element.minimize()
                        self.element.restore()
                    except Exception:
                        pass
                if hasattr(self.element, "set_focus"):
                    self.element.set_focus()
            except Exception:
                pass

    def capture_screenshot(self) -> bytes:
        try:
            wrapper = self.element
            if hasattr(self.element, "wrapper_object"):
                wrapper = self.element.wrapper_object()
            if hasattr(wrapper, "capture_as_image"):
                img = wrapper.capture_as_image()
            else:
                raise RuntimeError("capture_as_image not available on backend wrapper")
            if not PIL_AVAILABLE:
                raise RuntimeError("Pillow is required to produce image bytes")
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            raise RuntimeError(f"Screenshot failed: {e}")

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        try:
            wrapper = self.element
            if hasattr(self.element, "wrapper_object"):
                wrapper = self.element.wrapper_object()
            if x is None or y is None:
                if hasattr(wrapper, "click_input"):
                    wrapper.click_input()
                    return
                raise RuntimeError("No click API available")
            left, top, _, _ = self.rect()
            abs_x, abs_y = left + x, top + y
            if hasattr(wrapper, "click_input"):
                wrapper.click_input(coords=(abs_x, abs_y))
                return
            raise RuntimeError("No click_input available on backend")
        except Exception as e:
            raise RuntimeError(f"Click failed: {e}")

    def type_text(self, text: str) -> None:
        try:
            wrapper = self.element
            if hasattr(self.element, "wrapper_object"):
                wrapper = self.element.wrapper_object()
            if hasattr(wrapper, "type_keys"):
                wrapper.type_keys(text, with_spaces=True)
                return
            if PYWIN_AVAILABLE:
                _send_keys(text)
                return
            raise RuntimeError("No typing backend available")
        except Exception as e:
            raise RuntimeError(f"type_text failed: {e}")

    def send_keys(self, keys: str) -> None:
        try:
            if PYWIN_AVAILABLE:
                _send_keys(keys)
                return
            raise RuntimeError("pywinauto.keyboard not available")
        except Exception as e:
            raise RuntimeError(f"send_keys failed: {e}")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "friendly_name": self.friendly_name,
            "hwnd": self.hwnd,
            "pid": self.pid,
            "rect": self.rect(),
        }
