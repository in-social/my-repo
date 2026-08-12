"""
OpenAI adapter for the GUI agent.
Provides a small wrapper with safe preflight checks and a minimal decide/verify API.
This adapter never stores credentials; it reads OPENAI_API_KEY from the environment at call time.
"""
import os
import json
from typing import Optional, Any, Dict

try:
    import openai
    OPENAI_PKG_AVAILABLE = True
except Exception:
    openai = None
    OPENAI_PKG_AVAILABLE = False


class OpenAIAdapter:
    def __init__(self, model_name: str = "gpt-4o-mini-vision"):
        self.model_name = model_name

    def preflight(self) -> Dict[str, Any]:
        """
        Perform best-effort preflight checks for OpenAI access and model availability.
        Returns a dict with keys: ok(bool), message(str), details(dict)
        """
        details = {}
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"ok": False, "message": "OPENAI_API_KEY not set in environment", "details": details}
        details["api_key_present"] = True

        if not OPENAI_PKG_AVAILABLE:
            return {"ok": False, "message": "openai package not installed", "details": details}

        # Conservative preflight: do NOT call Model.retrieve (can trigger unsupported parameter errors).
        # Only check that API key exists and openai package is importable. A deeper runtime check may be
        # enabled by setting OPENAI_PING=true in env, which will attempt a lightweight API call.
        details["api_key_present"] = True
        details["openai_pkg_importable"] = True

        # Optional runtime ping (disabled by default)
        if os.environ.get("OPENAI_PING", "false").lower() in ("1", "true", "yes"):
            try:
                # Minimal ChatCompletion probe with no image and tiny max_tokens
                openai.api_key = os.environ.get("OPENAI_API_KEY")
                resp = openai.ChatCompletion.create(model=self.model_name, messages=[{"role":"system","content":"ping"}], max_tokens=1, temperature=0)
                details["ping_ok"] = True
            except Exception as e:
                return {"ok": False, "message": f"OpenAI ping failed: {e}", "details": details}

        # Heuristic for vision support: derive from model name or environment override
        model_lower = (self.model_name or "").lower()
        supports_images = False
        if any(k in model_lower for k in ("vision", "v", "multimodal")) or os.environ.get("FORCE_OPENAI_VISION", "false").lower() in ("1","true","yes"):
            supports_images = True
        details["supports_images_heuristic"] = supports_images
        return {"ok": True, "message": "OpenAI preflight ok (lightweight)", "details": details}

    def supports_images(self) -> bool:
        # Conservative: rely on preflight heuristic only
        pf = self.preflight()
        return bool(pf.get("details", {}).get("supports_images_heuristic", False))

    def decide(self, image_bytes: Optional[bytes], context: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Calls OpenAI multimodal model to obtain a single JSON decision.
        This implementation expects the OpenAI SDK to be installed and OPENAI_API_KEY set.
        It is intentionally conservative: if any error occurs, it raises an exception to let caller handle it.
        """
        if not OPENAI_PKG_AVAILABLE:
            raise RuntimeError("openai package not installed")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        openai.api_key = api_key

        # Build a minimal prompt that asks for STRICT JSON only
        prompt = {
            "task": context.get("task"),
            "notes": "Return a single JSON object with keys: action, description and any action params.\nOnly JSON, no markdown."
        }

        # Use a simple Chat API call; actual multimodal payloads differ per SDK. We include image as base64 if provided.
        try:
            import base64
            messages = [
                {"role": "system", "content": "You are a vision-enabled UI assistant. Return EXACT JSON in your reply."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}
            ]
            if image_bytes:
                b64 = base64.b64encode(image_bytes).decode("ascii")
                # attach image in a second user message to avoid inline binary in the prompt
                messages.append({"role": "user", "content": json.dumps({"image_b64": b64})})

            resp = openai.ChatCompletion.create(model=self.model_name, messages=messages, temperature=0)
            text = resp.choices[0].message["content"]
            # parse JSON
            data = json.loads(text)
            return data
        except Exception as e:
            raise RuntimeError(f"OpenAIAdapter decide failed: {e}")

    def verify(self, image_bytes: Optional[bytes], context: Dict[str, Any], last_decision: Dict[str, Any]) -> Dict[str, Any]:
        # For now, delegate to decide with a verification prompt or return conservative default
        try:
            # A simple heuristic: if last_decision was 'halt', return ok True
            if last_decision.get("action") == "halt":
                return {"ok": True, "notes": "halted - nothing to verify"}
            # Otherwise, return not implemented to force conservative behavior
            return {"ok": False, "notes": "verification not implemented for OpenAIAdapter; be conservative"}
        except Exception as e:
            return {"ok": False, "notes": f"verify failed: {e}"}
