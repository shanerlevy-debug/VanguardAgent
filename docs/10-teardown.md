# 10 — Teardown

When you're decommissioning the deployment — say, sunsetting the project
or migrating to a different architecture — this is how to remove every
trace from Anthropic and Slack.

## What teardown removes

| Resource | What happens |
|---|---|
| **Agent** | Archived (read-only; existing sessions complete). Can be unarchived later. |
| **Environment** | Archived. |
| **Skills** | Archived. Custom skill source code stays in your repo unaffected. |
| **Memory store** | **Deleted** — all your finding history is permanently gone. Use `--keep-memory` to retain. |
| **Slack token file** | Deleted from Files API. |
| **`.deploy-state.json`** | Removed locally. |

What teardown does **NOT** touch:

- Your Slack app or bot — those live in Slack, not Anthropic.
- Your repository, `vanguard.yaml`, `secrets.env`, or any local files.
- Your Claude Code routine — disable/delete that separately.
- Anthropic billing history or usage logs.

## 1. Disable the cron first

Before tearing down, stop the cron so a routine doesn't fire mid-teardown:

```
# In Claude Code:
/schedule disable <routine-id>
# or to remove entirely:
/schedule delete <routine-id>
```

If you skip this and a routine fires after teardown, it will fail with
"agent not found" — harmless but generates an error in your routine
history.

## 2. Run teardown

```bash
python scripts/teardown.py
```

You'll see a confirmation prompt:

```
Will remove:
  Agent:       agent_01ABC...
  Environment: env_01DEF...
  Skills:      8 (will be archived)
  Memory:      memstore_01GHI... (DELETED — run history lost)
Proceed? [y/N]
```

Type `y` and Enter.

The script archives each resource, deletes the memory store, and clears
local state. Output:

```
archived agent agent_01ABC...
archived skill processing-sources (skill_01...)
archived skill scoring-findings (skill_01...)
... (8 skills total)
archived environment env_01DEF...
deleted memory store memstore_01GHI...
deleted slack-token file file_01XXX...
.deploy-state.json removed.
Done.
```

### Skip the prompt for scripted teardown

```bash
python scripts/teardown.py --yes
```

### Keep the memory store

If you might redeploy and want to preserve dedupe history:

```bash
python scripts/teardown.py --keep-memory
```

The memory store stays. Future re-deploys can reattach by setting the
same `memory.store_name` in `vanguard.yaml` — but the deploy script will
create a new one (it doesn't search by name). To re-use, you'd need to
manually paste the old store ID into a fresh `.deploy-state.json` before
running deploy.

## 3. (Optional) Revoke the Slack bot

If you're done forever:

1. Open **https://api.slack.com/apps** → your Vanguard app.
2. **Manage Distribution** (left sidebar) — for completeness.
3. **Settings → Basic Information → Delete App** (scroll to the bottom).

This invalidates the bot token on Slack's side. Already-deleted from
Anthropic's Files API in step 2 above, but this also closes the loop on
Slack's side.

If you want to keep the bot for a future redeployment, leave it alone.
Tokens don't expire.

## 4. (Optional) Delete the project directory

Once teardown completes, the local files are no longer doing anything.

```bash
# From the parent directory:
rm -rf VanguardCMA/
# (Windows)
Remove-Item -Recurse VanguardCMA
```

Or just leave it on your machine for reference. There's no ongoing cost
or activity once `.deploy-state.json` is gone.

## 5. Verify in the Anthropic console

Open https://console.anthropic.com:

- **Agents** — your agent should be in **Archived** state (filter the
  list to see archived items).
- **Environments** — same.
- **Skills** — your 8 skills archived.
- **Memory stores** — your store should be **gone** (unless
  `--keep-memory`).
- **Files** — the slack-token file should be gone.

If anything's still active, run `python scripts/teardown.py --yes` again
— it's idempotent.

## Re-deploying later

If you tore down but later want to redeploy:

1. Pull or re-clone the repo (if deleted).
2. Re-do `02-create-slack-bot.md` if you deleted the Slack app.
3. Re-fill `vanguard.yaml` and `secrets.env`.
4. (Optional) Re-author `skills/custom/understanding-{slug}` from the
   template — or restore it from git history if you'd committed it
   privately.
5. `python scripts/deploy.py`.

This creates a new agent, new memory store, etc. The old archived
resources can stay archived forever or be unarchived from the Anthropic
console if you specifically want to revive them.

## Cost after teardown

Zero ongoing cost. CMA only bills for active sessions; archived agents
don't run sessions; the deleted memory store isn't billable. Your
account's overall billing posture (active subscriptions, etc.) is
unaffected.

## You're done

The agent is fully decommissioned. If you tear down then redeploy, the
process is the same as a first-time setup — start at
[`05-deploy.md`](05-deploy.md).
