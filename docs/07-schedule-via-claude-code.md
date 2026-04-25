# 07 — Schedule via Claude Code routine

The agent is healthy on manual triggers. Now we make it run on a cron
without you doing anything.

We'll use a **Claude Code Routine** — a scheduled remote agent that fires
the run for us. No GitHub Actions, no AWS Lambda, no cron on your laptop.
Anthropic's side of the wire handles it.

## What a routine is, in 30 seconds

A Claude Code routine is a remote Claude session that runs on a cron
schedule. You give it a prompt; it fires that prompt at the scheduled
time. The remote session can run any Claude Code-able command — including
running our Python script.

For Vanguard, our routine prompt is essentially: "Open the VanguardCMA
project and run `python scripts/run_once.py --no-stream`." The
`--no-stream` flag matters — it sends the kickoff and exits, letting the
CMA session continue independently. The routine doesn't need to wait for
the run to finish; it just needs to start it.

## 1. Make sure your routine can reach the project

The Claude Code routine runs in a remote sandbox. It clones from your git
remote (GitHub, GitLab, etc.). So the routine needs:

- **A git remote** with your VanguardCMA repo (private is fine).
- **Your `secrets.env` available somehow**. Two options:
  - **Recommended:** Use Claude Code's secret-storage feature. In Claude
    Code, run `/schedule secrets` to add `ANTHROPIC_API_KEY` and
    `SLACK_BOT_TOKEN` as routine-scoped secrets. The routine writes them
    to `secrets.env` at startup.
  - **Alternative:** Bake the env vars into the routine prompt itself
    (less secure; visible in the routine listing).

If you don't have your VanguardCMA in a git remote yet, do that now:

```bash
git init
git add .
git commit -m "Initial VanguardCMA deployment"
# Then push to a private GitHub/GitLab/Bitbucket repo
git remote add origin git@github.com:your-org/vanguard-cma.git
git push -u origin main
```

The repo can be private; the routine will use your Claude Code GitHub
authorization to clone.

## 2. Create the routine

In Claude Code, run:

```
/schedule create
```

Claude Code will walk you through the routine creation interview. Answer
as follows:

| Question | Answer |
|---|---|
| **Schedule** | `0 9 * * *` (every day at 9 AM UTC) — adjust to your team's morning |
| **Timezone** | Your business timezone, e.g. `America/Los_Angeles` |
| **Repo** | Your VanguardCMA git remote URL |
| **Branch** | `main` |
| **Prompt** | (see below) |
| **Title** | `Vanguard daily run` |

### The routine prompt (paste this verbatim, edit the parts in `<...>`)

```
You're firing a scheduled Vanguard run.

Steps:
1. Confirm you're in the VanguardCMA directory: `ls vanguard.yaml && ls scripts/run_once.py`. If either is missing, abort with a clear error.
2. Write secrets.env from the routine's secrets:
   - ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
   - SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN
   (these come from /schedule secrets)
3. Make sure deps are installed: `python -m venv .venv && source .venv/bin/activate && pip install -r scripts/requirements.txt --quiet`
4. Trigger the run with --no-stream: `python scripts/run_once.py --no-stream`
5. Confirm the session ID printed. If not, exit with an error.

Do not edit any project file. Do not commit anything. The CMA session continues running on Anthropic after step 4 — your job is just to fire it. Total runtime should be under 60 seconds.
```

### Cron schedule examples

| You want | Cron |
|---|---|
| Daily at 9 AM in your timezone | `0 9 * * *` (set timezone) |
| Twice daily (9 AM, 4 PM) | `0 9,16 * * *` |
| Weekdays only at 8 AM | `0 8 * * 1-5` |
| Every 4 hours | `0 */4 * * *` |
| Once a week, Monday 7 AM | `0 7 * * 1` |

Daily is the standard; pick the time when your team would naturally check
overnight news.

## 3. Test the routine

`/schedule create` will offer to run the routine immediately as a test.
Accept. You should see Claude Code:

1. Clone the repo
2. Set up the venv
3. Print "session: ses_01..."
4. Exit cleanly

Then check Slack — you should see a fresh run summary appear within ~5
minutes (the CMA session takes a couple of minutes after the routine
fires it).

If the test fails, see [troubleshooting](09-troubleshooting.md).

## 4. Confirm the routine is enabled

```
/schedule list
```

You should see your routine listed with **Enabled: yes** and the next
fire time. That's it — Anthropic's side runs the routine on schedule
forever (until you disable or delete it).

## 5. Daily operations

Once running, you have nothing to do unless you want to:

- **Pause:** `/schedule disable <routine-id>`
- **Change schedule:** `/schedule update <routine-id> --cron "..."`
- **See last run:** `/schedule history <routine-id>`
- **Delete entirely:** `/schedule delete <routine-id>`

The routine itself is a stable trigger — the actual agent behavior
(competitors, scoring, channel) is controlled by `vanguard.yaml` and the
skills, which you re-deploy via `python scripts/deploy.py` whenever you
change them.

## How the routine fits with manual triggers

The routine and manual `./run_once.sh` (or `.\run_once.ps1`) triggers can
**coexist**. You can fire a manual run anytime — for example, after
deploying a context-skill update — and the next scheduled run will
proceed normally. Memory dedupe handles overlap correctly: a manual run
just before the scheduled one means the scheduled one finds nothing new.

## Time-zone gotcha

Cron strings are always UTC unless you set a timezone in the routine
configuration. `0 9 * * *` without a timezone fires at **9 AM UTC**, which
is the middle of the night for most US teams. Set your business timezone
in `/schedule create` to avoid this.

## You're done

If you got here and the routine ran successfully, VanguardCMA is fully
deployed and operating on autopilot. Findings will land in your Slack
channel on schedule until you disable it.

## Next steps (only as needed)

- [`08-customization.md`](08-customization.md) — adding a competitor,
  tweaking scoring, editing the context skill mid-deployment.
- [`09-troubleshooting.md`](09-troubleshooting.md) — when something
  breaks.
- [`10-teardown.md`](10-teardown.md) — clean removal.
