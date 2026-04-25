# 01 — Prerequisites

What you need to have before running anything in this repo.

## Accounts and access

### 1. Anthropic API account with Managed Agents enabled

- Sign up or log in at **https://console.anthropic.com**.
- Go to **Settings → Keys** and create an API key. Copy it somewhere safe
  — Anthropic shows it once. The key starts with `sk-ant-…`.
- Verify Managed Agents access:
  - Open **Settings → Beta features**.
  - Confirm **Managed Agents** is enabled. It should be on by default for
    new accounts. If not, click "Request access."
  - Confirm **Memory (research preview)** is enabled. This one usually
    needs an explicit request via the form Anthropic provides on that page.
    Without it, deployment will fail at the memory-store creation step.
- Anthropic billing: you'll be charged per-run for model tokens. Add a
  payment method if you haven't already.

### 2. Slack workspace admin (or someone who can install apps)

You need permission to:
- Create a Slack app in your workspace (https://api.slack.com/apps).
- Install the app (this requires either admin permission or admin
  approval, depending on your workspace's app-install policy).
- Invite the bot to the channel you want findings posted to.

If you're not an admin, walk your workspace admin through
`02-create-slack-bot.md` together — it takes 10 minutes.

### 3. Claude Code (for the cron routine)

You'll need an active Claude Code subscription with **Routines** enabled.
- Get Claude Code at **https://claude.com/claude-code** if you don't have
  it.
- Inside Claude Code, type `/schedule` — if it lists a help screen, you're
  good. If you get "command not found," update Claude Code to the latest
  version.

## Software

### 4. Python 3.12 or newer

VanguardCMA's deploy scripts are Python.

```bash
python --version    # should print 3.12.x or 3.13.x
# or:
python3 --version
```

Don't have it? Install from **https://www.python.org/downloads/** (Windows,
macOS) or `apt`/`brew`/`dnf` on Linux. **Tick "Add Python to PATH"** during
the Windows installer.

### 5. Git

To clone or pull updates to this repo:

```bash
git --version
```

If absent: **https://git-scm.com/downloads**.

### 6. A code editor (recommended, not strictly required)

VS Code, Sublime, Cursor — anything that handles YAML and Markdown. You'll
spend most of your time editing two files: `vanguard.yaml` and
`skills/custom/understanding-{your-company}/SKILL.md`. Plain Notepad will
work but won't catch YAML indentation mistakes early.

## Confirming everything works

In a terminal, in the `VanguardCMA/` directory, run:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux/Git-Bash:
source .venv/bin/activate

pip install -r scripts/requirements.txt
```

Expected: a wall of `pip` install logs ending with "Successfully installed
anthropic-… pyyaml-… python-dotenv-… slack-sdk-…". If you see errors,
re-check Python is 3.12+.

Then sanity-check the SDK:

```bash
python -c "import anthropic; print(anthropic.__version__)"
```

Expected: `0.97.0` or newer. If it prints `0.94.x` or older, run
`pip install --upgrade anthropic` — VanguardCMA needs the memory-store
SDK methods that landed in 0.95+.

## What you don't need

- **No AWS account.** None of this runs on AWS.
- **No Docker.** No images to build.
- **No PostgreSQL or any database.** Memory lives in Anthropic's memory
  store.
- **No DNS or domain.** Nothing public-facing.
- **No SSL certs.** Same.
- **No Terraform.** No infrastructure to provision.

## Next step

[`02-create-slack-bot.md`](02-create-slack-bot.md) — set up the Slack app
the agent posts as.
