"""
Pluggable reasoners abstraction.
Provides:
 - build_reasoner(name) -> instance with methods:
     supports_images() -> bool
     decide(image_bytes, context, dry_run=False) -> dict
     verify(image_bytes, context, last_decision) -> dict ({"ok": True/False, "notes":...})
Implementations:
 - MockReasoner: safe, returns halt or simple typing plans for dry-run.
 - OpenAIReasoner: example implementation calling OpenAI Vision-capable model (requires env var OPENAI_API_KEY).
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Any

class ReasonerError(Exception):
    pass

class BaseReasoner(ABC):
    @abstractmethod
    def supports_images(self) -> bool:
        pass

    @abstractmethod
    def decide(self, image_bytes: bytes, context: dict, dry_run: bool = False) -> dict:
        pass

    @abstractmethod
    def verify(self, image_bytes: bytes, context: dict, last_decision: dict) -> dict:
        pass

class MockReasoner(BaseReasoner):
    def supports_images(self) -> bool:
        return True

    def decide(self, image_bytes: bytes, context: dict, dry_run: bool = False) -> dict:
        """
        Very conservative mock decision:
          - If task mentions 'type' or 'message', return a 'type' action with a test message but mark as dangerous to trigger confirmation.
          - Otherwise, halt.
        """
        task = context.get("task", "").lower()
        if "type" in task or "message" in task:
            decision = {
                "action": "type",
                "text": "[TEST MESSAGE] This is a dry-run. HALT BEFORE SENDING.",
                "description": "Type a test message into the message input (dry-run).",
                "dangerous": True
            }
            # In dry_run mode we will not perform actual send; the main loop will require confirmation.
            return decision
        return {"action": "halt", "reason": "Mock reasoner: nothing to do."}

    def verify(self, image_bytes: bytes, context: dict, last_decision: dict) -> dict:
        # Mock verification always returns ok=True for demo
        return {"ok": True, "notes": "mock verification OK"}

class OpenAIReasoner(BaseReasoner):
    def __init__(self, model_name="gpt-4o-mini-vision"):
        try:
            import openai
        except Exception as e:
            raise ReasonerError("openai package not installed or import failed") from e
        self.model_name = model_name
        self._supports = True

    def supports_images(self) -> bool:
        return self._supports

    def decide(self, image_bytes: bytes, context: dict, dry_run: bool = False) -> dict:
        """
        Example decision flow: send image + task + history to OpenAI multimodal model and expect strict JSON back.
        The caller must set OPENAI_API_KEY in env.
        """
        import base64
        import openai
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ReasonerError("OPENAI_API_KEY not set")
        openai.api_key = api_key

        prompt = {
            "task": context.get("task"),
            "action_history": context.get("action_history", []),
            "instructions": (
                "Return a single JSON object POJO with keys: action, description, and depending on action additional params. "
                "Possible actions: click, type, scroll, key, halt. Use coordinates relative to window top-left (relative: true)."
            )
        }
        # Here we show a conceptual example; actual OpenAI multimodal API call depends on provider SDK & format.
        # We'll send base64 image plus prompt as a text message and expect JSON in assistant response.
        b64 = base64.b64encode(image_bytes).decode("ascii")
        messages = [
            {"role": "system", "content": "You are a vision-enabled UI assistant that returns EXACT JSON (no markdown)."},
            {"role": "user", "content": json.dumps({"prompt": prompt, "image_b64": b64})}
        ]
        try:
            resp = openai.ChatCompletion.create(model=self.model_name, messages=messages, temperature=0)
            text = resp.choices[0].message["content"]
            # parse JSON out of text
            data = json.loads(text)
            return data
        except Exception as e:
            raise ReasonerError(f"OpenAI reasoner failed: {e}")

    def verify(self, image_bytes: bytes, context: dict, last_decision: dict) -> dict:
        # naive verification could re-run a classification; here we return ok=False to be conservative
        return {"ok": False, "notes": "OpenAIReasoner: verification not implemented; be conservative."}

def build_reasoner(name: str):
    name = (name or "mock").lower()
    if name in ("mock", "default-mock"):
        return MockReasoner()
    if name in ("openai", "gpt-4v", "gpt-4o-mini-vision"):
        return OpenAIReasoner(model_name="gpt-4o-mini-vision")
    raise ReasonerError(f"Unknown reasoner: {name}")
