# 03 — Configure vanguard.yaml

`vanguard.yaml` is the single source of truth for your deployment. The deploy
script reads it, templates the system prompt with these values, and
provisions every Anthropic resource.

## Two paths to a working file

**Fastest path:** the interactive onboarding wizard asks you the
required questions and writes `vanguard.yaml` for you. Run it once,
then come back to this doc to tune anything beyond the basics:

```bash
./onboard.sh        # macOS/Linux/Git-Bash
.\onboard.ps1       # Windows PowerShell
```

The wizard handles fields under `company`, `agent`, `slack`, and writes
at least one `competitors` entry. Sources, scoring tuning, and
environment hostnames default to sensible values you tune later by
editing the file.

**Manual path:** copy the example file and fill it in.

## 1. Create your config file (manual path only)

```bash
cp vanguard.yaml.example vanguard.yaml
```

Then open `vanguard.yaml` in your editor.

> 💡 `vanguard.yaml` is in `.gitignore` — it's local to your machine. The
> example file is committed; your filled-in copy is not. (If you maintain
> a private fork in your own repo, **never** commit `vanguard.yaml` —
> channel IDs and Slack workspace data are sensitive.)

## 2. Fields, in the order they appear

### `company:`

```yaml
company:
  name: "Acme Wines"
  slug: "acme-wines"
  context_skill_name: "understanding-acme-wines"
```

| Field | Notes |
|---|---|
| `name` | Your company's display name. Appears in the system prompt and run-summary messages. |
| `slug` | Lowercase, hyphens, no spaces. Used as a prefix on Anthropic resource names so multiple deployments in one Anthropic account don't collide. |
| `context_skill_name` | Must equal the directory name under `skills/custom/`. Convention: `understanding-{slug}`. You'll create this skill in `04-fill-company-context.md`. |

### `agent:`

```yaml
agent:
  name: "Vanguard — Acme Wines"
  model: "claude-opus-4-7"
  description: "Competitive intelligence agent for Acme Wines."
```

| Field | Notes |
|---|---|
| `name` | Display name in the Anthropic console. |
| `model` | `claude-opus-4-7` (best quality) or `claude-sonnet-4-6` (~5× cheaper, slightly less nuanced scoring). Must be Claude 4.5 or newer — earlier models don't run on CMA. |
| `description` | Free-form, shows in the Anthropic console. |

### `slack:`

```yaml
slack:
  default_channel: "C0123456789"
  channel_overrides: {}
  low_priority_strategy: "roundup"
```

| Field | Notes |
|---|---|
| `default_channel` | The channel ID (`C09…`) you got in `02-create-slack-bot.md`. **Not** the channel name. |
| `channel_overrides` | Optional. Map of category name → channel ID. Findings in those categories post to the override channel instead of the default. Example below. |
| `low_priority_strategy` | `roundup` (one batch message at end of run), `individual` (post each Low separately, noisy), or `drop` (record but never post). Almost everyone wants `roundup`. |

Example with overrides:

```yaml
channel_overrides:
  "Funding/M&A": "C09FUNDING01"
  "Security/Incidents": "C09SECURITY1"
```

The category names must match the canonical 12 categories exactly:
`Product`, `Pricing`, `Customers/Wins`, `Partnerships`, `Hiring`,
`Leadership Changes`, `Funding/M&A`, `Marketing Positioning`,
`Security/Incidents`, `Technology Direction`, `Roadmap Signals`,
`Analyst/Press Sentiment`. Capitalize and punctuate exactly as listed.

### `competitors:`

The list of companies the agent tracks. The agent **only** tracks
competitors listed here — it won't go off-script.

```yaml
competitors:
  - name: "Kendall-Jackson"
    aliases: ["KJ", "Kendall Jackson"]
    sources: ["news", "blog", "press_release"]
  - name: "Robert Mondavi"
    aliases: ["Mondavi"]
    sources: ["news", "press_release"]
```

Per competitor:

| Field | Notes |
|---|---|
| `name` | Canonical name — the form that appears in Slack posts. Pick the most professional/correct rendering ("Mistral AI" not "mistral"). |
| `aliases` | Other ways the competitor is referenced in the wild. `Mistral AI` should include `Mistral`; `Kendall-Jackson` should include `KJ` and the un-hyphenated form. The agent uses these to tighten search queries and reject false matches. |
| `sources` | Which source types to scan for this competitor. **Only sources that are also globally enabled (under `sources:` below) actually run.** |
| `priority_multiplier` | Optional, default 1.0. Set above 1.0 to upweight this competitor (rarely needed). |

3–10 competitors is the sweet spot. More competitors → more API tokens
per run → higher cost. If you genuinely need 20+, run multiple deployments
with different scopes rather than one mega-deploy.

### `sources:`

Global source toggles. A competitor only uses a source if **(a)** the
source is enabled here AND **(b)** it's listed in that competitor's
`sources:` array.

```yaml
sources:
  news:        { enabled: true }
  blog:        { enabled: true,  feeds: [] }
  press_release: { enabled: true }
  sec:         { enabled: false, competitor_ciks: {} }
  github:      { enabled: false, competitor_orgs: {} }
  youtube:     { enabled: false, competitor_channels: {} }
  reddit:      { enabled: false, subreddits: [] }
  job_boards:  { enabled: false }
```

Source-specific config:

| Source | Extra config |
|---|---|
| `blog` | `feeds:` — optional list of RSS URLs to always poll. Usually unnecessary; the agent discovers feeds automatically. |
| `sec` | `competitor_ciks:` — map of `"<competitor name>": "<CIK>"`. Find a public company's CIK at sec.gov by searching their name. Skip for private competitors. |
| `github` | `competitor_orgs:` — map of `"<competitor name>": "<github org slug>"`. Set for competitors with public OSS activity worth watching. |
| `youtube` | `competitor_channels:` — map of `"<competitor name>": "<channel ID>"`. Channel IDs (the `UCxxxx…` form, not the handle) — get from the channel's About → Share. |
| `reddit` | `subreddits:` — optional list of subreddits to scope to. Empty = search all of Reddit (noisy). |
| `job_boards` | High noise. Recommend leaving disabled unless you specifically care about competitor hiring patterns. |

Recommendation for first deploy: enable `news` + `blog` + `press_release`
only. Confirm everything works, then add other sources one at a time.

### `scoring:`

```yaml
scoring:
  high_keywords:
    - "acquires"
    - "acquisition"
    - "layoffs"
    - "raises"
    - "series"
    - "breach"
    - "ceo"
  recency_cap_days: 7
  source_baseline:
    news: "medium"
    blog: "medium"
    press_release: "medium"
    sec: "high"
    github: "low"
    youtube: "low"
    reddit: "low"
    job_boards: "low"
```

| Field | Notes |
|---|---|
| `high_keywords` | Headline keywords that auto-score a finding High (case-insensitive, word-boundary match against title + summary). Tune to your industry — wine companies might add `harvest`, `vintage`, `appellation`. |
| `recency_cap_days` | Findings older than this score Low max, regardless of content. 7 is a good default. |
| `source_baseline` | Per-source default importance (the scoring rubric uses this as a tiebreaker). SEC filings are official disclosures so default High; Reddit is mostly noise so default Low. |

### `memory:`

```yaml
memory:
  store_name: "vanguard-acme-wines"
  description: "Vanguard competitive-intel state for Acme Wines..."
```

The Anthropic memory store that holds all prior findings (the dedupe
table). Don't change `store_name` after the first deploy — the deploy
script keys off it. The `description` is shown to the agent so it knows
what's in there.

### `environment:`

```yaml
environment:
  name: "vanguard-acme-wines-prod"
  networking: "limited"
  allowed_hosts:
    - "news.google.com"
    - "www.google.com"
    - "feeds.feedburner.com"
    - "www.businesswire.com"
    - "www.prnewswire.com"
    - "data.sec.gov"
    - "api.github.com"
    - "www.youtube.com"
    - "www.reddit.com"
```

| Field | Notes |
|---|---|
| `networking` | `limited` (recommended; agent can only reach hosts in `allowed_hosts` plus `slack.com` plus package mirrors) or `unrestricted` (agent can reach anywhere). |
| `allowed_hosts` | List of hostnames (no scheme, no path). The deploy script auto-adds `slack.com`. Add per-competitor newsroom hosts here if you want the agent to fetch from them: `www.kj.com`, `www.robertmondavi.com`, etc. |

### `anthropic:`

```yaml
anthropic:
  beta_headers:
    - "managed-agents-2026-04-01"
    - "managed-agents-2026-04-01-research-preview"
```

Don't change unless Anthropic publishes new beta versions. The
research-preview header is required for memory.

## 3. Validate your config

Before doing anything else, run:

```bash
python scripts/deploy.py --dry-run
```

Expected output:

```
--- dry run ---
[1/8] Validating config...
  ok

system prompt rendered: 6500 chars, 150 lines
skills to upload: 8
  - formatting-run-log
  - formatting-slack-posts
  - posting-to-slack
  - processing-sources
  - scoring-findings
  - overriding-scoring
  - understanding-{your-slug}
  - writing-why-it-matters
```

If you see "skills to upload: 7" — your `understanding-{slug}` skill
doesn't exist yet. That's fine; you'll create it in the next doc, then
re-run the dry-run.

If you see an error like:

```
ERROR: company.context_skill_name = 'understanding-acme-wines'
  but skills/custom/understanding-acme-wines/SKILL.md does not exist.
```

That's the expected error before step 4 — proceed.

If you see anything else (YAML parse error, channel format error, etc.),
fix it before moving on.

## Next step

[`04-fill-company-context.md`](04-fill-company-context.md) — author the
company context skill. This is the highest-leverage thing you'll do.
