"""
teardown.py — remove every Anthropic resource this deployment created.

Reads .deploy-state.json. Archives the agent + environment, deletes the
memory store, archives every skill. Idempotent — run twice, second run
is a no-op.

Usage:
    python scripts/teardown.py            # asks for confirmation
    python scripts/teardown.py --yes      # skip confirmation
    python scripts/teardown.py --keep-memory  # keep the memory store

The memory store contains your run history — once deleted, the dedupe
table is gone and the next run will re-process everything in the recency
window. Use --keep-memory if you plan to redeploy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import STATE_PATH, get_anthropic_client, load_env, load_state, save_state  # noqa: E402


def confirm(prompt: str) -> bool:
    try:
        return input(f"{prompt} [y/N] ").strip().lower() == "y"
    except (EOFError, KeyboardInterrupt):
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="Skip confirmation")
    ap.add_argument("--keep-memory", action="store_true",
                    help="Keep the memory store (delete other resources)")
    args = ap.parse_args()

    load_env()
    state = load_state()
    if not state:
        print("No .deploy-state.json — nothing to tear down.")
        return 0

    print("Will remove:")
    if state.get("agent_id"):
        print(f"  Agent:       {state['agent_id']}")
    if state.get("environment_id"):
        print(f"  Environment: {state['environment_id']}")
    skills = state.get("skills") or {}
    if skills:
        print(f"  Skills:      {len(skills)} (will be archived)")
    if state.get("memory_store_id") and not args.keep_memory:
        print(f"  Memory:      {state['memory_store_id']} (DELETED — run history lost)")
    elif state.get("memory_store_id"):
        print(f"  Memory:      {state['memory_store_id']} (kept)")

    if not args.yes and not confirm("Proceed?"):
        print("Aborted.")
        return 1

    client = get_anthropic_client()

    if state.get("agent_id"):
        try:
            client.beta.agents.archive(state["agent_id"])
            print(f"archived agent {state['agent_id']}")
        except Exception as e:
            print(f"  agent archive failed: {e}")
        state.pop("agent_id", None)

    if skills:
        for name, info in list(skills.items()):
            sid = info.get("id")
            if not sid:
                continue
            try:
                client.beta.skills.archive(sid)
                print(f"archived skill {name} ({sid})")
            except Exception as e:
                print(f"  skill archive failed for {name}: {e}")
        state["skills"] = {}

    if state.get("environment_id"):
        try:
            # Archive first to prevent new sessions, then delete if no sessions
            client.beta.environments.archive(state["environment_id"])
            print(f"archived environment {state['environment_id']}")
        except Exception as e:
            print(f"  environment archive failed: {e}")
        state.pop("environment_id", None)

    if state.get("memory_store_id") and not args.keep_memory:
        try:
            client.beta.memory_stores.delete(state["memory_store_id"])
            print(f"deleted memory store {state['memory_store_id']}")
        except Exception as e:
            print(f"  memory delete failed: {e}")
        state.pop("memory_store_id", None)

    save_state(state)
    if not state:
        STATE_PATH.unlink(missing_ok=True)
        print(".deploy-state.json removed.")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
