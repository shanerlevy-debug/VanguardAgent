# 09 — Troubleshooting

Symptoms first; remediation second. Search this doc by symptom (Ctrl-F).

## Symptom: nothing posted to Slack

### 1. Did the agent run at all?

Check the latest session:

```bash
python scripts/tail.py
```

If you see `❌ terminated` or `⚠️ error: ...`, that's the cause — read the
error.

If you see normal-looking output but **zero `🔧 tool: bash` lines**, the
agent ran but never tried to post. That points at the system prompt,
context skill, or kickoff.

### 2. The agent posted but Slack rejected it

`python scripts/tail.py <session_id>` and look for `bash` tool outputs
that contain `"ok":false`. Common Slack errors:

| `error` | Fix |
|---|---|
| `not_in_channel` | Bot wasn't invited to the channel. Invite it (Slack: `/invite @vanguard`). |
| `channel_not_found` | Channel ID wrong in `vanguard.yaml`. |
| `invalid_auth` | Slack token expired/revoked. Re-do `02-create-slack-bot.md` step 7, then `python scripts/deploy.py --force-recreate slack-token`. |
| `missing_scope` | Forgot `chat:write` or `chat:write.public` when creating the Slack app. |
| `ratelimited` | Slack throttled the bot. Wait 1 minute, re-run; if persistent, the agent is posting too aggressively (rare — investigate). |

### 3. The agent thinks it posted but nothing appears

Trick: the agent is in `--dry-run` mode. Check the kickoff in the session
events — does it contain "DRY RUN"? If yes, you accidentally triggered
with `--dry-run`. Re-trigger without it.

## Symptom: same finding posted twice

Memory dedupe is failing. Possible causes:

### Memory store not attached

Verify the session resources include the memory store:

```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from common import get_anthropic_client, load_env, load_state
load_env(); state = load_state()
c = get_anthropic_client()
sess = c.beta.sessions.list(agent_id=state['agent_id'], limit=1).data[0]
print('resources:', list(sess.resources or []))
"
```

You should see one entry with `type: memory_store` and your store ID. If
not, `run_once.py` isn't attaching it — check the script wasn't modified.

### Memory writes are silently failing

Check session events for `memory_write` calls and any error responses
following them.

### Same content, slightly different URL

Two outlets republished the same press release with different URLs. The
exact `memory_read` check won't catch this — that's what the fuzzy dedupe
in `scoring-findings` is for. If it's not catching it either, the
similarity threshold may need tuning. Add a rule to `overriding-scoring`:

```
Press release content from PRNewswire, BusinessWire, or competitor's own newsroom is highly likely to be republished. If a finding's title matches a finding from the past 24h with edit distance < 10, suppress as a duplicate.
```

## Symptom: zero findings every run, even on news days

Possible causes in order of likelihood:

### 1. Sources globally disabled in `vanguard.yaml`

Open `vanguard.yaml`. Confirm `sources.news.enabled: true` (and other
sources you expect).

### 2. Per-competitor source list is empty

Each competitor needs `sources: [...]` populated.

### 3. Network policy blocking sources

If `environment.networking == "limited"` and `allowed_hosts` doesn't
include the source you need (e.g., `news.google.com` or
`www.businesswire.com`), the agent can fetch nothing. Add the host and
`python scripts/deploy.py --force-recreate environment`.

### 4. Aliases are too restrictive

If your competitor is "OpenAI" with no aliases, queries miss
`Open AI` (with space) and similar. Add to `aliases:`.

### 5. Recency window too tight

`scoring.recency_cap_days: 7` only affects scoring (older findings score
Low). The agent's actual lookback is governed in the source playbooks at
~24h. If your competitors don't make news daily, you'll see frequent
empty days. Normal — see the run summary post.

## Symptom: too noisy / too many findings

### 1. Add anti-priorities

Edit `skills/custom/understanding-{slug}/SKILL.md` § 4. Be specific:

```
- Hiring announcements unless C-level (CEO/CFO/CRO)
- Conference speaking announcements (the talk content might be a finding; the announcement isn't)
- Generic "AI is the future" thought-leadership pieces
```

Re-upload: `python scripts/deploy.py --skill understanding-{slug}`.

### 2. Use overriding-scoring to force categories Low

```
Hiring findings are always Low unless title contains "Chief" or "VP".
Marketing Positioning findings from analyst-firm sources only are always Low.
```

Re-upload: `python scripts/deploy.py --skill overriding-scoring`.

### 3. Set `low_priority_strategy: drop`

If Lows aren't valuable to you at all, drop them entirely:

```yaml
slack:
  low_priority_strategy: "drop"
```

Findings still get recorded to memory; they just don't post. (Useful if
you're using the memory store for downstream reporting.)

## Symptom: deploy.py fails

### `Skill upload failed: 400 invalid file path`

Some skill directory has a non-Markdown file or the SKILL.md isn't at the
root. Check:

```bash
ls skills/core/*/SKILL.md skills/custom/*/SKILL.md
```

Each skill directory must have a `SKILL.md` directly inside it.

### `Memory store creation failed: 403 / feature not enabled`

Your Anthropic account doesn't have memory access. Settings → Beta
features → request access. Wait for approval.

### `Agent update failed: ...version conflict...`

Someone else updated the agent in the Anthropic console (or a parallel
deploy ran). Clear the cached agent ID and re-deploy:

```bash
python -c "
import json
state = json.load(open('.deploy-state.json'))
state.pop('agent_id', None)
json.dump(state, open('.deploy-state.json','w'), indent=2)
"
python scripts/deploy.py
```

This creates a new agent version. The old one is still archivable via
the console.

### `ANTHROPIC_API_KEY missing in secrets.env`

Check that `secrets.env` (not `secrets.env.example`) exists in the
project root and contains a non-blank value. The script looks for
`secrets.env`; the example file is just a template.

## Symptom: routine fired but no run happened

### Routine logs show success but Slack is silent

Check the session that the routine started:

```bash
# In Claude Code:
/schedule history <routine-id>
# Find the latest invocation; copy the printed session_id (ses_...)
# Then locally:
python scripts/tail.py ses_01XXX...
```

The session may have errored after the routine exited. The tail will
show what happened.

### Routine logs show error during clone or pip install

The routine sandbox can't reach your repo or PyPI. Causes:

- Repo is private and Claude Code's git auth isn't configured.
  Re-authenticate via Claude Code's settings.
- The routine prompt has a typo in the repo URL.
- Your `secrets.env` write step in the prompt has a bash error. Test the
  routine prompt as a one-off Claude Code task first to debug.

### Time zone confusion

If your routine is firing at the wrong time, double-check the `--cron`
and the timezone you set when creating the routine. Cron without a
timezone defaults to UTC.

## Symptom: agent posts but the formatting is broken

### Block Kit error in Slack ("an attachment was sent with malformed JSON")

The agent's curl post had a JSON syntax error. Look at the bash tool's
output in the session events. Likely cause: a `'` (apostrophe) or `"` in
the title or summary that wasn't escaped.

The skill `posting-to-slack` uses `cat > /tmp/finding.json <<'EOF'`
heredoc precisely to avoid this. If the agent generated something
different, it deviated from the skill — usually a sign the system prompt
or skill needs to be more explicit.

Update `posting-to-slack` to add an example showing the EOF heredoc with
problematic characters in the body.

### Wrong channel

The agent posted to the default channel when it should have used an
override (or vice versa). Check `vanguard.yaml` → `slack.channel_overrides`
matches the categories you expect, then `python scripts/deploy.py`.

## Symptom: cost is higher than expected

### High input tokens

The agent is reading large amounts of context per run. Causes:

- Memory store is huge — but memory tools only retrieve relevant
  entries; this should be self-limiting. Verify the memory tools are
  being used (you should see `memory_search` not `memory_list` for
  dedupe).
- Many sources × many competitors × full-fetch (deep web_fetch on every
  result). The agent should use snippets when sufficient. If you see
  many `web_fetch` calls per finding in events, something pushed it into
  full-fetch mode — likely the system prompt or a skill change.

### Many output tokens

The agent is producing long messages internally. Causes:

- Verbose `summary` or `why_it_matters` — your context skill might be
  asking for more detail than necessary. Tighten § 5 (Voice) toward
  "terse, no hedging."
- Too many findings per run — split competitors across two daily
  routines (morning + evening) so each session handles fewer.

### Quick diagnostic

Open `https://console.anthropic.com → Usage`, filter to today, click a
session row to see per-session token breakdown.

## Symptom: I broke something and want to start over

```bash
python scripts/teardown.py
python scripts/deploy.py
```

`teardown.py` archives the agent + skills + environment, deletes the
memory store (unless `--keep-memory`) and the Slack token file. Then
`deploy.py` rebuilds from your current `vanguard.yaml` + skills.

If you want to keep your finding history through the rebuild:

```bash
python scripts/teardown.py --keep-memory
python scripts/deploy.py
```

The new agent will reattach to the same memory store on its first
session.

## When to ask for help

If you've tried the relevant section here and the issue persists:

1. Capture a session ID and its events: `python scripts/tail.py ses_XXX > tail.log`
2. Capture your `vanguard.yaml` (redact channel IDs if sensitive)
3. Capture the relevant `SKILL.md` if a skill is suspect
4. Open an issue on the VanguardCMA repo with these attached

Don't paste your `secrets.env` or any token. The maintainer doesn't need
those to debug.

## Next step

[`10-teardown.md`](10-teardown.md) — clean removal when you're done with
this deployment.
