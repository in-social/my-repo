# GUI Agent (Kimi-like) — Generalized Vision-Driven UI Automation

Overview
- This project implements a generalized perceive→reason→act→verify loop to automate interactions with chatbot UIs (browser tabs or desktop apps).
- Safety-first: hard confirmation gate, stop file, audit logs, iteration cap, no handling of credentials.

Model choice (my decision)
- Default recommendation: OpenAI multimodal model (e.g. `gpt-4o-mini-vision` / `gpt-4v`) if you have API access.
- The code is pluggable: implement a new Reasoner class in `reasoners.py` for other providers.
- A `mock` reasoner is provided for safe dry runs.

Preflight checklist (run locally)
1. Ensure you run the script with native Windows Python (not WSL python), as described in the spec.
2. Install dependencies:
   pip install -r requirements.txt
3. If you plan to use OpenAIReasoner: set `OPENAI_API_KEY` in the environment.
4. Run a preflight: the main script writes preflight.json in `run_logs/<session>/preflight.json`.

Usage examples
- Dry-run against a desktop target (safe):
  python gui_agent.py --target "MyThrowawayChat" --mode desktop --task "open new chat and type a test message, halt before sending" --reasoner mock --dry-run

- Real run (requires vision-capable reasoner configured):
  python gui_agent.py --target "chat.example.com" --mode browser --task "open a new chat and send greeting" --reasoner openai

Security & ToS notes
- Many chatbots disallow automated/unsupervised access in their terms; run this tool only in supervised opt-in sessions.
- This tool does not bypass authentication and will halt if login/payment screens are detected.
- It logs every message/action to `run_logs/<session>/` for audit.

Dry-run proof
- Use the `mock` reasoner and `--dry-run` to validate the perceive→reason→act→verify loop. The mock reasoner will not perform destructive actions.

Tests
- Unit tests for guardrails are in `tests/test_guardrails.py`.
  Run: `pytest tests/ -v`

Important
- Do not run unattended. The tool expects an unlocked foreground Windows desktop session.
