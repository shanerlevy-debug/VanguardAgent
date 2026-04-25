---
name: scoring-findings
description: Assigns a category and importance level (High, Medium, or Low) to a new competitive-intelligence finding, decides whether it should be posted or suppressed, and writes the result to the persistent memory store. Use this skill after `processing-sources` has produced a candidate finding that is NOT already in memory. The output drives both `formatting-slack-posts` (which needs category+importance+why_it_matters) and `posting-to-slack` (which actually sends the message).
---

# scoring-findings

Takes a normalized candidate finding and decides three things:

1. **Category** — which of the 12 tracked categories this finding belongs to
2. **Importance** — High, Medium, or Low
3. **Whether to post at all** — some findings get suppressed before reaching Slack

After deciding, **always write the finding to memory** (whether posted or
suppressed) so future runs dedupe correctly.

## Input (from `processing-sources`)

A candidate with at least:
- `canonical_url`, `content_hash`, `competitor_slug`, `raw` — opaque plumbing
- `title`, `summary` — what the agent actually reads to score
- `competitor` — canonical name (from the system prompt)
- `source_type`, `source_name` — publisher info
- `detected_at` — when this item was published (from the source), not when the agent saw it

## Output (toward `formatting-slack-posts`)

Add these fields to the candidate:
- `category` — one of the 12 strings listed below (verbatim)
- `importance` — `"High"`, `"Medium"`, or `"Low"`
- `why_it_matters` — short contextualization line (see `writing-why-it-matters`)
- `posted` — bool, set true if this finding will be posted to Slack
- `first_seen_at` — ISO 8601 UTC datetime of "now" (when this run scored it)

## The 12 categories

Use these exact strings. Not "product" — "Product". Not "Funding" — "Funding/M&A".

| Category | What belongs here |
|---|---|
| Product | Feature launches, new model releases, API changes, product sunsets |
| Pricing | Price changes up or down, new tiers, discount programs, enterprise deal signals |
| Customers/Wins | Named customer announcements, case studies, logos added to marketing |
| Partnerships | Integrations, reseller deals, joint announcements, co-marketing |
| Hiring | Role openings, team expansions. Distinct from Leadership Changes. |
| Leadership Changes | Named executive hires, departures, CEO/CTO/CRO moves |
| Funding/M&A | Rounds raised, valuations disclosed, acquisitions made or rumored |
| Marketing Positioning | New messaging, rebrands, new taglines, high-profile ad campaigns |
| Security/Incidents | Breaches, outages, CVEs disclosed, post-mortems, regulatory actions |
| Technology Direction | Research papers, open-source releases, architectural announcements |
| Roadmap Signals | Leaked or hinted future direction, beta invites, trademark filings |
| Analyst/Press Sentiment | Gartner/Forrester pieces, major positive or negative coverage |

When in doubt between two categories, pick the one that better answers
"what would our tracking company want to know about this?" — that's usually
the more specific one. Don't invent a 13th category; if nothing fits,
pick the closest and explain the fit in `why_it_matters`.

## Importance rubric

The system prompt lists `high_keywords`, `recency_cap_days`, and per-source
baselines under "Scoring tuning." Use those values, not hard-coded defaults.

### High

Assign High when the finding contains any keyword from the system prompt's
`high_keywords` list. Match anywhere in `title` or `summary`,
case-insensitive, word-boundary only (so "series" matches "Series B" but
not "miniseries"). Also assign High when:

- Category is `Funding/M&A` and a dollar amount ≥ $50M is mentioned
- Category is `Security/Incidents` and affects customer data
- Category is `Leadership Changes` and the role is CEO, CTO, or CFO
- Category is `Pricing` and the change is ≥ 20% in either direction

### Medium

The default for a finding that's clearly on-topic but not a pulse-quickener.
Examples:
- New product feature that's an incremental improvement
- A customer logo added that isn't a marquee name
- A partnership announcement with a mid-tier vendor
- Pricing change under 20%
- Any category tag except Hiring / Analyst Sentiment, in the absence of High signals

### Low

Assign Low when:

- The finding is **older than `recency_cap_days`** (from the system
  prompt). Recency cap is a hard ceiling: older findings can't score above
  Low regardless of content.
- Category is `Hiring` AND it's a generic role posting (a job req, not a
  team-expansion announcement)
- Category is `Analyst/Press Sentiment` AND coverage is neutral
- The article mentions the competitor only in passing (single-sentence
  mention in a list of companies)

Low-importance findings are batched into a roundup, not posted
individually — see the system prompt's `low_priority_strategy`.

### Source baselines

Use the per-source baseline from the system prompt as a tiebreaker. If
the rubric above produces Medium but the source baseline is Low, score
Low. If the rubric produces High, source baseline doesn't downgrade.
SEC filings baseline High because they're official disclosures; Reddit
baselines Low because most mentions are noise.

## Suppress-entirely rules (don't post at all)

Not every processed finding deserves a Slack post. Suppress (set
`posted: false`, but still write to memory) when:

- The finding is about a different entity that shares a name with the
  competitor (e.g., an article about wind mistrals when tracking "Mistral
  AI"). Aliases from the system prompt help — if the title contains an
  alias *and* a competitor-relevant noun, it's likely a real match.
- The content is a regurgitated press release the agent has already seen
  at another URL this run (dedupe against in-session findings, not just
  memory)
- The item is satire, a stock-ticker update, or automated market commentary
- The title is a duplicate of a previously-posted finding for the same
  competitor within the last 24 hours (use `memory_search`, see below)

When suppressing, write to memory anyway, with `posted: false` and
`why_it_matters: "Suppressed at scoring: <reason>."` This way the agent
doesn't rediscover and re-suppress the same thing on the next run.

## Fuzzy dedupe against recent findings

Before finalizing a score, check memory for similar recent findings.
The memory store has all prior findings as files; use `memory_search`
with the competitor as a filter:

```
memory_search(
    query="<first 10 words of title>",
    path_prefix=f"findings/{competitor_slug}/"
)
```

For each result returned (limit ~20), read the YAML frontmatter and check:

- Same `canonical_url` → already handled by the exact `memory_read` check
  in `processing-sources`. Should not appear here.
- Different URL but `title` highly similar (first 10 words match, or edit
  distance < 5) AND `first_seen_at` within last 24h:
  - If the new finding has genuinely new detail → score normally, prefix
    title with "Update:"
  - If no new detail → suppress per above

Cache the search results per competitor per run; don't re-search for
every candidate.

## Writing to memory

Every scored finding — posted or suppressed — gets written to:

```
findings/{competitor_slug}/{content_hash}.md
```

Use the format defined in `processing-sources` § "memory format". Use the
`memory_write` tool with the rendered markdown as content.

This write happens **after** scoring but **before** posting to Slack. If
a Slack post fails, you've still recorded the finding in memory; the
human reviewer can replay it later if needed.

## Cross-references

- `processing-sources` — produces the candidates scored here, defines the
  memory format
- `{{context_skill_name}}` — deployer's priorities and anti-priorities
  that calibrate importance (the system prompt names this skill)
- `overriding-scoring` — optional per-deployer rule overrides (check
  before finalizing a score)
- `writing-why-it-matters` — how to phrase the contextualization line
- `formatting-slack-posts` — consumes category + importance + why_it_matters
- `posting-to-slack` — actually sends the messages
- `formatting-run-log` — `new_findings_count` reflects only `posted: true`
  records from this skill
- system prompt — `high_keywords`, `recency_cap_days`, `source_baseline`,
  competitor list with aliases
