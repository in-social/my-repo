#!/usr/bin/env python3
"""
Main CLI entrypoint: perceive -> reason -> act -> verify loop.
Usage examples:
  python gui_agent.py --target "Windsurf" --mode desktop --task "open a new chat and type a test message, halt before sending"
  python gui_agent.py --target "chat.example.com" --mode browser --task "..."
"""
import argparse
import os
import sys
import time
import uuid
import json
from datetime import datetime

from target_locator import locate_target, TargetNotFoundError
from guardrails import (
    check_scope, require_confirmation, write_audit_step, check_stop_file, IterationCapReached
)
from ui_control import focus_window, perform_action
from reasoners import build_reasoner, ReasonerError

RUN_LOGS_DIR = "run_logs"


def preflight_checks(reasoner_name: str):
    """
    Perform the mandatory pre-flight dependency checks described in the spec.
    Return dict of checks (bool + message).
    """
    checks = {}
    # 1) Vision model availability: reasoner reports capability
    try:
        reasoner = build_reasoner(reasoner_name)
        checks['vision_supported'] = (reasoner.supports_images(), "Reasoner reports support for images." if reasoner.supports_images() else "Reasoner reports NO image support.")
    except Exception as e:
        checks['vision_supported'] = (False, f"Error instantiating reasoner '{reasoner_name}': {e}")

    # 2) Python reachable (we assume running under native Python); just report sys.executable
    py_exec = sys.executable
    checks['python_executable'] = (os.path.exists(py_exec), f"python executable: {py_exec}")

    # 3) Required packages - best-effort import check
    pkgs = {}
    for pkg in ("pyautogui", "pywinauto", "mss", "PIL"):
        try:
            __import__(pkg)
            pkgs[pkg] = (True, "")
        except Exception as e:
            pkgs[pkg] = (False, str(e))
    checks['packages'] = pkgs

    # 4) pywinauto Desktop enumerability (best-effort)
    try:
        from pywinauto import Desktop
        d = Desktop(backend="uia")
        # don't enumerate windows here; just successful import/construct
        checks['pywinauto_desktop'] = (True, "pywinauto Desktop created.")
    except Exception as e:
        checks['pywinauto_desktop'] = (False, str(e))

    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Window title substring or browser tab URL/title substring")
    parser.add_argument("--mode", choices=("desktop", "browser"), required=True)
    parser.add_argument("--task", required=True, help="Task goal")
    parser.add_argument("--reasoner", default="mock", help="Reasoner to use (e.g., openai, mock). See reasoners.py")
    parser.add_argument("--max-iterations", type=int, default=25)
    parser.add_argument("--dry-run", action="store_true", help="Do not perform destructive actions; prefer safe decisions")
    args = parser.parse_args()

    session_id = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    session_dir = os.path.join(RUN_LOGS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Preflight
    checks = preflight_checks(args.reasoner)
    with open(os.path.join(session_dir, "preflight.json"), "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=2, ensure_ascii=False)
    # If reasoner lacks image support -> warn and stop (per spec)
    if not checks.get('vision_supported', (False,))[0]:
        print("Preflight failed: chosen reasoner does not support image input. Aborting. See run_logs preflight.json")
        return

    reasoner = build_reasoner(args.reasoner)
    action_history = []

    # main loop
    iteration = 0
    try:
        while True:
            iteration += 1
            if iteration > args.max_iterations:
                raise IterationCapReached(f"Reached max iterations ({args.max_iterations})")

            if check_stop_file():
                print("STOP file detected; halting.")
                break

            # Locate and focus target
            try:
                window = locate_target(args.target, args.mode)
            except TargetNotFoundError as e:
                print(f"Target not found: {e}")
                break

            # Ensure scope lock
            if not check_scope(window, args.target):
                print("Scope check failed: target identity mismatch. Halting.")
                break

            # Bring to foreground
            focus_window(window)

            # Capture screenshot scoped to window rect (reasoner will receive bytes)
            from ui_control import capture_window_screenshot
            img_bytes = capture_window_screenshot(window)

            # Build reasoner prompt context
            context = {
                "task": args.task,
                "action_history": action_history[-10:],  # recent history
                "iteration": iteration,
                "session_id": session_id,
            }

            # Call reasoner
            try:
                decision = reasoner.decide(img_bytes, context, dry_run=args.dry_run)
            except ReasonerError as e:
                print(f"Reasoner error: {e}")
                break

            # Audit log step (before action)
            step_meta = {
                "iteration": iteration,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "target": args.target,
                "mode": args.mode,
                "decision": decision,
            }
            write_audit_step(session_dir, iteration, img_bytes, step_meta)

            # If decision asks to halt, stop
            if decision.get("action") == "halt":
                print(f"Halt decision from reasoner: {decision.get('reason')}")
                break

            # If destructive, require confirmation
            if decision.get("dangerous", False):
                confirmed = require_confirmation(decision)
                if not confirmed:
                    print("Action not confirmed by human; halting.")
                    break

            # Execute the single action
            try:
                perform_action(window, decision)
            except Exception as e:
                print(f"Action execution error: {e}")
                break

            action_history.append({
                "iteration": iteration,
                "decision": decision,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

            # Post-action verification: re-screenshot and let reasoner verify
            post_img_bytes = capture_window_screenshot(window)
            verify_result = reasoner.verify(post_img_bytes, context, decision)
            write_audit_step(session_dir, iteration, post_img_bytes, {"verify": verify_result}, suffix="_post")
            if not verify_result.get("ok", False):
                print("Verification failed: expected effect not observed; halting.")
                break

            print(f"Iteration {iteration} completed; action: {decision.get('action')}")
    except IterationCapReached as e:
        print(str(e))
    finally:
        print(f"Session logs stored in: {session_dir}")
        print("Exiting.")


if __name__ == "__main__":
    main()
