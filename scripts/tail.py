"""
tail.py — stream events from a CMA session.

Usage:
    python scripts/tail.py                  # latest session for this agent
    python scripts/tail.py <session_id>     # specific session
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import get_anthropic_client, load_env, load_state  # noqa: E402


def main() -> int:
    load_env()
    client = get_anthropic_client()
    state = load_state()

    if len(sys.argv) >= 2 and sys.argv[1].startswith("ses_"):
        sid = sys.argv[1]
    else:
        agent_id = state.get("agent_id")
        if not agent_id:
            raise SystemExit("No agent_id in .deploy-state.json — pass a session ID.")
        # Most recent session for this agent
        page = client.beta.sessions.list(agent_id=agent_id, limit=1)
        sessions = list(page.data) if hasattr(page, "data") else list(page)
        if not sessions:
            raise SystemExit(f"No sessions found for agent {agent_id}.")
        sid = sessions[0].id
        print(f"Latest session: {sid}")

    print(f"Streaming {sid}...")
    print("=" * 70)
    stream = client.beta.sessions.events.stream(session_id=sid)
    for event in stream:
        evt = getattr(event, "type", "?")
        ts = getattr(event, "processed_at", "") or ""
        prefix = f"[{ts}] " if ts else ""

        if evt == "agent.message":
            text = ""
            for block in (getattr(event, "content", None) or []):
                if getattr(block, "type", None) == "text":
                    text = getattr(block, "text", "")
                    break
            if text:
                print(f"{prefix}💬 {text[:300]}")
        elif evt in ("agent.tool_use", "agent.mcp_tool_use"):
            name = getattr(event, "tool_name", None) or getattr(event, "name", "?")
            print(f"{prefix}🔧 {evt}: {name}")
        elif evt.startswith("session.status_"):
            print(f"{prefix}📊 {evt}")
            if evt in ("session.status_terminated",):
                break
            sr = getattr(event, "stop_reason", None)
            sr_type = getattr(sr, "type", None) if sr else None
            if evt == "session.status_idle" and sr_type and sr_type != "requires_action":
                break
        elif evt == "session.error":
            print(f"{prefix}⚠️ {getattr(event, 'error', None)}")
        else:
            print(f"{prefix}{evt}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
