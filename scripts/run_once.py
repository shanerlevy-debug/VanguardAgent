"""
run_once.py — manually trigger a single Vanguard run.

Reads .deploy-state.json for resource IDs, creates a session with:
  - the memory store attached (read_write)
  - the Slack token file mounted at /workspace/.slack-token
opens an SSE stream, and sends the kickoff. The session then runs
autonomously until idle with a terminal stop reason.

This is what the Claude Code routine calls on a cron, and what you can
run locally to trigger a manual run.

Usage:
    python scripts/run_once.py                 # standard kickoff
    python scripts/run_once.py --kickoff "..."  # custom kickoff message
    python scripts/run_once.py --dry-run        # tell agent to log, not post
    python scripts/run_once.py --no-stream      # send kickoff and exit
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import get_anthropic_client, load_env, load_state  # noqa: E402

DEFAULT_KICKOFF = (
    "Begin your scheduled competitive-intelligence run now. Follow the "
    "three-phase orchestration in your system prompt: process and score, "
    "post and persist (with memory writes), then post the run summary to "
    "Slack. Read the Slack bot token from /workspace/.slack-token before "
    "your first Slack call. Do not ask clarifying questions — execute."
)
DRY_RUN_ADDENDUM = (
    "\n\nDRY RUN: do NOT call Slack. Instead, write each intended Slack "
    "post to /tmp/dry-run-posts.json (append-mode). Continue all other "
    "steps normally including memory writes."
)

SLACK_TOKEN_MOUNT = "/workspace/.slack-token"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kickoff", default=DEFAULT_KICKOFF)
    ap.add_argument("--dry-run", action="store_true",
                    help="Tell agent to log Slack posts to a file, not post them")
    ap.add_argument("--no-stream", action="store_true",
                    help="Send kickoff and exit; agent keeps running on Anthropic")
    args = ap.parse_args()

    load_env()
    state = load_state()
    for key in ("agent_id", "environment_id", "memory_store_id", "slack_token_file_id"):
        if not state.get(key):
            raise SystemExit(
                f"{key} missing from .deploy-state.json — run scripts/deploy.py first."
            )

    client = get_anthropic_client()

    kickoff = args.kickoff
    if args.dry_run:
        kickoff += DRY_RUN_ADDENDUM

    print("Creating session...")
    session = client.beta.sessions.create(
        agent=state["agent_id"],
        environment_id=state["environment_id"],
        title=f"Vanguard run {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        resources=[
            {
                "type": "memory_store",
                "memory_store_id": state["memory_store_id"],
                "access": "read_write",
            },
            {
                "type": "file",
                "file_id": state["slack_token_file_id"],
                "mount_path": SLACK_TOKEN_MOUNT,
            },
        ],
    )
    print(f"  session: {session.id}")

    # Open stream BEFORE sending kickoff (per CMA event ordering)
    print("Opening SSE stream...")
    stream = client.beta.sessions.events.stream(session_id=session.id)

    print(f"Sending kickoff ({len(kickoff)} chars)...")
    client.beta.sessions.events.send(
        session.id,
        events=[
            {"type": "user.message",
             "content": [{"type": "text", "text": kickoff}]}
        ],
    )

    if args.no_stream:
        print(f"Kickoff sent. Stream with: python scripts/tail.py {session.id}")
        return 0

    print("Streaming events (Ctrl-C to detach; session keeps running)...")
    print("=" * 70)

    tool_calls = 0
    msg_count = 0
    for event in stream:
        evt = getattr(event, "type", "?")
        if evt == "agent.message":
            msg_count += 1
            text = ""
            for block in (getattr(event, "content", None) or []):
                if getattr(block, "type", None) == "text":
                    text = getattr(block, "text", "")
                    break
            if text:
                snippet = text[:240].replace("\n", " ")
                print(f"  💬 {snippet}{'…' if len(text) > 240 else ''}")
        elif evt in ("agent.tool_use", "agent.mcp_tool_use"):
            tool_calls += 1
            name = getattr(event, "tool_name", None) or getattr(event, "name", "?")
            print(f"  🔧 tool: {name}")
        elif evt == "session.status_idle":
            sr = getattr(event, "stop_reason", None)
            sr_type = getattr(sr, "type", None) if sr else None
            if sr_type and sr_type != "requires_action":
                print(f"  🏁 idle: {sr_type}")
                break
        elif evt == "session.status_terminated":
            print("  ❌ terminated")
            break
        elif evt == "session.error":
            err = getattr(event, "error", None)
            print(f"  ⚠️  error: {err}")

    print("=" * 70)
    print(f"Run complete: {msg_count} agent messages, {tool_calls} tool calls.")
    if tool_calls == 0:
        print("WARNING: zero tool calls — agent likely couldn't reach Slack/memory. "
              "Check session via: python scripts/tail.py " + session.id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
