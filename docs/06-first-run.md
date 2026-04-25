# 06 — First run

The deploy created the agent. Now we'll trigger one session manually,
watch what happens, and verify Slack output.

This is also the verification step before scheduling — if the manual run
works, the cron will work.

## 1. Trigger a single run

```bash
./run_once.sh     # or .\run_once.ps1 on Windows
```

You'll see:

```
Creating session...
  session: ses_01ABC...
Opening SSE stream...
Sending kickoff (350 chars)...
Streaming events (Ctrl-C to detach; session keeps running)...
======================================================================
  💬 I'll begin the competitive-intelligence run for Acme Wines...
  🔧 tool: web_search
  🔧 tool: web_fetch
  💬 Found 3 candidate items for Kendall-Jackson...
  🔧 tool: memory_read
  🔧 tool: memory_write
  🔧 tool: bash
  ...
  🏁 idle: end_turn
======================================================================
Run complete: 14 agent messages, 22 tool calls.
```

The first run usually takes **3–8 minutes** (depends on competitor count
and how chatty the news is that day). Watching the live stream is
optional — the agent runs on Anthropic regardless of whether you stay
attached. Detach with **Ctrl-C** if you want; the session keeps going.

## 2. What to look for in the stream

| Pattern | What it means |
|---|---|
| `🔧 tool: web_search` early | Agent is querying news for each competitor — good. |
| `🔧 tool: memory_read` for each candidate | Dedupe is working — good. |
| `🔧 tool: memory_write` for new findings | Persistence is working — good. |
| `🔧 tool: bash` near end | Agent is calling Slack via curl — good. |
| `🏁 idle: end_turn` | Agent finished cleanly. |
| `🏁 idle: max_tokens` | Agent ran out of token budget. Usually means too many competitors or too verbose context. See troubleshooting. |
| `❌ terminated` | Hard error. Check `python scripts/tail.py <session_id>` for details. |
| **Zero `🔧 tool` lines** | Agent isn't using its skills — see troubleshooting. |

## 3. Check Slack

Open the channel you configured. You should see, in this order:

1. **Individual finding messages** — one per High/Medium finding. Each
   has a header (the title), 4 fields (competitor / category /
   importance / source), a body (summary + why-it-matters), and a context
   line (detection time + source link).
2. **A low-priority roundup** (only if there were Low findings) — single
   bulleted message.
3. **A run summary** (always last) — with `new_findings_count`,
   `duplicates_skipped`, and the list of competitors scanned.

If `new_findings_count == 0` and the summary still posts, **that's
correct**. Empty days are normal; the empty summary confirms the agent
ran.

## 4. Verify the memory store has entries

Open the Anthropic console → **Memory stores** → your store. You should
see one file per finding from this run, organized as:

```
findings/
  kendall-jackson/
    3a7bd3e2....md
    8b1c4d8f....md
  robert-mondavi/
    9e2af1bc....md
```

Each file's frontmatter has `competitor`, `category`, `importance`,
`title`, etc. These are what dedupe future runs against.

If the store is empty: the agent didn't write to memory. See
[troubleshooting](09-troubleshooting.md).

## 5. Run a second time — verify dedupe works

```bash
./run_once.sh     # or .\run_once.ps1 on Windows
```

Expected: a much faster run (most candidates dedupe via `memory_read`),
and a run summary with `duplicates_skipped > 0` and likely
`new_findings_count == 0` (unless brand-new news landed in the minutes
between runs).

If the second run posts the same findings as the first run — dedupe is
broken. See troubleshooting.

## 6. Detach a session you don't want to watch

If you triggered with `--no-stream`, or you Ctrl-C'd out of the stream,
the session is still running on Anthropic. You can:

- Re-attach: `python scripts/tail.py <session_id>` (or with no args for the
  latest session)
- Watch in the Anthropic console: **Sessions** → your session → live
  events tab

To explicitly stop a session that's misbehaving:

```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from common import get_anthropic_client, load_env
load_env()
c = get_anthropic_client()
c.beta.sessions.archive('ses_YOUR_SESSION_ID')
"
```

## 7. Dry-run mode (optional, for testing)

If you want to test the run flow without actually posting to Slack
(useful when iterating on prompts):

```bash
./run_once.sh --dry-run     # or .\run_once.ps1 on Windows
```

The agent will write each intended Slack post to `/tmp/dry-run-posts.json`
inside its container instead of calling Slack. Memory writes still
happen. Useful for "did the agent want to post X?" testing without
actually posting it. The file's contents aren't easy to retrieve from
outside the container — main use is "did the agent's tool-call stream
look right?"

## 8. Costs after first run

Open **https://console.anthropic.com → Usage**. Filter to today.

The first run is typically the most expensive (no memory hits — every
candidate is processed). Subsequent runs deduplicate aggressively and
cost a fraction.

If your first run cost more than a few dollars, that's notable but not
broken — adjust `model` to `claude-sonnet-4-6` in `vanguard.yaml` and
re-deploy if cost is a concern.

## You're done with manual verification

If steps 3 and 5 produced expected output, the agent is healthy. Move on.

## Next step

[`07-schedule-via-claude-code.md`](07-schedule-via-claude-code.md) — make
this run automatically every day.
