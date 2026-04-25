# 05 — Deploy

You've configured `vanguard.yaml`, authored your context skill, and your
dry-run passes. Time to push to Anthropic.

## 1. Set your secrets

Copy the example and fill in your two API keys:

```bash
cp secrets.env.example secrets.env
```

Open `secrets.env` and replace the placeholders:

```bash
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SLACK_BOT_TOKEN=xoxb-XXXXXXXXXXX-XXXXXXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXX
```

> ⚠️ `secrets.env` is in `.gitignore`. Never commit it. Rotate either
> token if you suspect it leaked.

## 2. Run the deploy

The recommended path uses the wrapper script — it creates the venv,
installs dependencies the first time, and runs the deploy:

```bash
# macOS / Linux / Git-Bash:
./deploy.sh

# Windows PowerShell:
.\deploy.ps1
```

(If PowerShell refuses to run the script with "running scripts is
disabled," run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
once, then retry.)

The wrapper forwards all arguments to `scripts/deploy.py`, so anything
shown later in this doc as `python scripts/deploy.py ...` works
identically as `./deploy.sh ...` (or `.\deploy.ps1 ...`).

If you'd rather manage the venv yourself:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux/Git-Bash
source .venv/bin/activate

python scripts/deploy.py
```

Expected output (≈30 seconds total):

```
[1/8] Validating config...
  ok
[2/8] Validating Slack token via auth.test...
  ok — bot user 'vanguard' in workspace 'AcmeWines'
[3/8] Setting up memory store...
  created: memstore_01ABC... (vanguard-acme-wines)
[4/8] Uploading Slack token as a session-mountable file...
  uploaded: file_01DEF...
[5/8] Uploading skills...
  created processing-sources: skill_01GHI... v...
  created scoring-findings: skill_01JKL... v...
  created formatting-slack-posts: skill_01MNO... v...
  created formatting-run-log: skill_01PQR... v...
  created posting-to-slack: skill_01STU... v...
  created overriding-scoring: skill_01VWX... v...
  created writing-why-it-matters: skill_01YZA... v...
  created understanding-acme-wines: skill_01BCD... v...
[6/8] Setting up environment...
  created: env_01EFG... (vanguard-acme-wines-prod)
[7/8] Setting up agent...
  created: agent_01HIJ... v1
[8/8] Saved state to .deploy-state.json

Done. Resource IDs:
  Memory:           memstore_01ABC...
  Slack token file: file_01DEF...
  Environment:      env_01EFG...
  Agent:            agent_01HIJ...
  Skills:           8 uploaded

Next: ./run_once.sh    (macOS/Linux/Git-Bash)
      .\run_once.ps1   (Windows PowerShell)
```

## What just happened

The deploy script created **5 things in your Anthropic workspace**:

1. **Memory store** — where the agent will write findings to dedupe.
2. **Slack token file** (Files API) — the bot token, mounted into every
   session at `/workspace/.slack-token`.
3. **8 skills** — uploaded as immutable versioned objects.
4. **Environment** — the container template (network policy, allowed
   hosts) sessions launch from.
5. **Agent** — bundles the model, system prompt, tools, and skill
   pinned-versions into a single reusable definition.

Each resource ID is saved to `.deploy-state.json` (also in `.gitignore`).
Re-running deploy is **idempotent** — it'll detect the existing IDs,
re-fetch them, and either skip or update as appropriate. It won't
duplicate.

The deploy also writes a file called **`agent.yaml`** to the project root.
This is the **CMA-native agent manifest** — the exact YAML body the
Anthropic API received when creating/updating your agent. Its shape
matches the "Create agent" YAML editor in the Anthropic console. You can:

- Read it to see exactly what's in production (system prompt, skill ID
  pins, tools, model).
- Paste it into the console's **Create agent → YAML** tab to manually
  recreate the agent in another workspace (you'd need to re-create the
  skills there too).
- Diff it across deploys to see what changed.

`agent.yaml` is **regenerated** every time you run deploy, so don't edit
it by hand — your edits will be overwritten. Edit `vanguard.yaml`
instead; the deploy script renders `agent.yaml` from it.

## 3. Verify in the Anthropic console

Open **https://console.anthropic.com** and confirm:

- **Agents:** Vanguard — Acme Wines (latest version pinned to your skills)
- **Environments:** vanguard-acme-wines-prod
- **Memory stores:** vanguard-acme-wines (empty for now)
- **Skills:** 8 entries with names matching your skills/ directories

If anything's missing or named wrong, [09-troubleshooting.md](09-troubleshooting.md) has remediation steps.

## Common errors and fixes

### `ANTHROPIC_API_KEY missing`

You didn't fill in `secrets.env`, or the file isn't where the script is
looking. Make sure `secrets.env` is in the `VanguardCMA/` root (same
folder as `vanguard.yaml`).

### `Slack token rejected: invalid_auth`

The `xoxb-…` token is wrong, was revoked, or you accidentally pasted the
`xoxp-…` user token. Re-do `02-create-slack-bot.md` step 7.

### `slack.default_channel must be a channel ID (starts with 'C')`

You put a channel name (e.g., `"#vanguard-intel"`) instead of an ID.
Replace with the `C09…` ID from `02-create-slack-bot.md` step 6.

### `company.context_skill_name = '...' but skills/custom/.../SKILL.md does not exist`

You skipped or forgot to copy the template in `04-fill-company-context.md`.
Do that step first.

### Memory store creation fails with `403` or `feature not enabled`

Memory is a research-preview feature. Go to Anthropic console → Settings
→ Beta features and request access. Wait for approval, then re-run.

### Skill upload fails with `400 invalid file path`

Some skill directory has a non-Markdown file or an oddly-named one. Check
that every file under `skills/` is `.md` and the directory has a
`SKILL.md` at its root.

## Re-runs

After your first successful deploy, re-running `python scripts/deploy.py`
is safe. It will:

- Reuse the same memory store (your finding history is preserved).
- Reuse the same environment if config hasn't changed.
- Re-upload **only changed skills** (compares against state file).
- Update the agent's pinned skill versions if any changed.

If you want to force a fresh deploy of one piece:

```bash
python scripts/deploy.py --force-recreate slack-token   # rotated bot token
python scripts/deploy.py --force-recreate environment   # added allowed_hosts
python scripts/deploy.py --force-recreate skills        # re-upload all skills
python scripts/deploy.py --skill understanding-acme-wines  # one skill
```

## Next step

[`06-first-run.md`](06-first-run.md) — fire a manual session and verify
findings land in Slack.
