# 08 — Customization

What to edit, when, and how to push changes safely. This is the doc you'll
return to most often after the initial deploy.

## The two-tier model

VanguardCMA's skills split into two tiers:

| Tier | What | When to edit |
|---|---|---|
| **Core** (`skills/core/`) | The framework: how to fetch sources, score findings, format Slack posts, write run logs, post to Slack | Only when upgrading to a new VanguardCMA version |
| **Custom** (`skills/custom/`) | Your company's voice and tuning: `understanding-{slug}`, `writing-why-it-matters`, `overriding-scoring` | Edit freely; this is yours |

If you find yourself wanting to change a core skill, ask first whether
the same effect can be achieved by editing your context skill, scoring
overrides, or `vanguard.yaml`. Almost always: yes.

## Common customizations

### Add a new competitor

1. Edit `vanguard.yaml`:

   ```yaml
   competitors:
     # …existing entries…
     - name: "New Competitor Co"
       aliases: ["NewCo", "New Co"]
       sources: ["news", "blog", "press_release"]
   ```

2. Edit `skills/custom/understanding-{slug}/SKILL.md` § 7 (Competitor-
   specific notes) — add a paragraph explaining what to watch for with the
   new competitor, if there's anything special.

3. (Optional) If the competitor has a public newsroom you want to scrape,
   add the host to `vanguard.yaml` → `environment.allowed_hosts`.

4. Push:

   ```bash
   python scripts/deploy.py
   ```

   The script detects only the changed pieces (agent system prompt,
   possibly your context skill) and updates them. Memory and other skills
   are reused.

5. Either wait for the next scheduled run or trigger manually:

   ```bash
   ./run_once.sh     # or .\run_once.ps1 on Windows
   ```

### Remove a competitor

1. Delete the entry from `vanguard.yaml` `competitors:`.
2. Optionally remove the competitor's notes from your context skill.
3. `python scripts/deploy.py`.

The competitor's old findings stay in the memory store for audit. If you
want them deleted, see "Clean memory of an old competitor" below.

### Add a new source type for an existing competitor

Two-step:

1. Make sure the source is **globally enabled** in `vanguard.yaml` →
   `sources:`:

   ```yaml
   sources:
     youtube: { enabled: true, competitor_channels: { "OpenAI": "UCXuq..." } }
   ```

2. Add the source to that competitor's list:

   ```yaml
   competitors:
     - name: "OpenAI"
       aliases: [...]
       sources: ["news", "blog", "press_release", "youtube"]   # added
   ```

3. `python scripts/deploy.py`.

The agent picks up the new source on the next run.

### Tune scoring keywords

Edit `vanguard.yaml` → `scoring.high_keywords`:

```yaml
scoring:
  high_keywords:
    - "acquires"
    - "acquisition"
    - "vintage"            # added — wine industry signal
    - "harvest"            # added
    - "appellation"        # added
```

`python scripts/deploy.py` and you're done.

### Make a category always-High or always-Low

Don't edit `scoring-findings`. Use `overriding-scoring`:

1. Open `skills/custom/overriding-scoring/SKILL.md`.

2. Add rules at the bottom under "Your rules":

   ```
   1. Security/Incidents findings are always High, regardless of source or recency. We're in a regulated industry.
   2. Hiring findings are always Low unless the title contains VP, Chief, or "head of".
   ```

3. Re-upload just that skill:

   ```bash
   python scripts/deploy.py --skill overriding-scoring
   ```

   The agent picks up the new rules on the next run.

### Tune voice / priorities / anti-priorities

Edit `skills/custom/understanding-{slug}/SKILL.md`. Re-upload:

```bash
python scripts/deploy.py --skill understanding-{slug}
```

Tip: tune iteratively. After each Slack post that's wrong (too noisy /
missed an important signal / wrong tone), update one section of the
context skill, re-upload, and let the next run validate the change. Don't
try to nail it in one giant edit.

### Add a category-specific channel

```yaml
slack:
  default_channel: "C09GENERAL01"
  channel_overrides:
    "Funding/M&A": "C09FUNDING01"
    "Security/Incidents": "C09SECURITY1"
```

Make sure the bot is invited to each override channel (or that they're
public if you're using `chat:write.public`).

`python scripts/deploy.py`.

### Switch model for cost savings

Edit `vanguard.yaml`:

```yaml
agent:
  model: "claude-sonnet-4-6"   # was: "claude-opus-4-7"
```

`python scripts/deploy.py`. About 5× cheaper per run; quality difference
is small but real. Run for a week and read the output — if findings get
noticeably less sharp, switch back.

### Change the run cadence

Edit your routine in Claude Code:

```
/schedule update <routine-id> --cron "0 7,15 * * *"   # 7 AM and 3 PM
```

No re-deploy needed — cron is on Claude Code's side, not Anthropic's.

### Add a new noise pattern

Whenever you notice the agent posting the same kind of junk twice, add it
to your context skill § 6 (Known noise patterns):

```markdown
## 6. Known noise patterns

- Republished press releases across 5+ outlets
- "Year in wine" listicles in December (mention every winery)   ← new
- Stock analyst boilerplate from Seeking Alpha                  ← new
```

Re-upload your context skill. Watch the next few runs — if the noise
recurs, the rule needs to be more specific.

## Periodic maintenance

### Monthly

- Read 3–5 random Slack posts from the past month. Are they all useful?
  If not, identify what's wrong (too noisy, wrong category, missing
  context) and update either `vanguard.yaml` or your context skill.
- Check `https://console.anthropic.com → Usage` for cost trends.
- Open the memory store. Are there competitors with zero findings? Likely
  the source isn't producing — investigate or drop the source.

### Quarterly

- Review your `understanding-{slug}` priorities. Have your strategic
  priorities shifted? Update.
- Check the high-keywords list. Add anything that emerged as
  industry-relevant in the last quarter.
- Review channel-overrides — does the routing still match how your team
  consumes the content?

### When you upgrade VanguardCMA

If you `git pull` a new version of this repo:

1. Read the changelog (top of `ReadMe.md`) for breaking changes.
2. Diff your `vanguard.yaml` against the new `vanguard.yaml.example` — look for
   new fields you might want to set.
3. **Don't merge changes into your `skills/custom/` directories.** Those
   are yours, not the upstream's.
4. `python scripts/deploy.py` to push the new core skills.

## Clean memory of an old competitor

If you removed a competitor and want to clear their findings:

```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from common import get_anthropic_client, load_env, load_state
load_env()
state = load_state()
c = get_anthropic_client()
ms_id = state['memory_store_id']
SLUG = 'old-competitor-slug'   # the competitor_slug, lowercase-hyphenated

memories = c.beta.memory_stores.memories.list(memory_store_id=ms_id, limit=1000)
deleted = 0
for m in memories.data:
    if m.path.startswith(f'findings/{SLUG}/'):
        c.beta.memory_stores.memories.delete(memory_id=m.id, memory_store_id=ms_id)
        deleted += 1
print(f'deleted {deleted} memories for {SLUG}')
"
```

Replace `old-competitor-slug` with the slug. The script lists every
memory under that prefix and deletes them. Audit log is preserved
(memory deletion creates a `memver_*` record); there's no full purge.

## What NOT to customize

- **Don't edit core skills.** They reference each other and the system
  prompt. Editing one means tracking down its references in other skills.
  Use `overriding-scoring` instead.
- **Don't edit `agent/system_prompt.md` directly** unless you know what
  you're doing. The script templates this file from `vanguard.yaml`. If you
  need behavior the system prompt doesn't enforce, prefer adding a
  paragraph to your context skill — it's loaded with the same authority
  in practice.
- **Don't add MCP servers** to the agent definition. The whole design
  premise of VanguardCMA is no MCP servers. Slack is reached via skill
  + curl, persistence via memory tools, sources via web_search/web_fetch.

## Next step

[`09-troubleshooting.md`](09-troubleshooting.md) — when something goes
wrong.
