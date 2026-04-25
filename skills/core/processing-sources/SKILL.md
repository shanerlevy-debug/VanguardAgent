---
name: processing-sources
description: Finds and normalizes competitor content from configured sources, then dedupes against the persistent memory store. Use this skill at the start of every competitive-intel cycle, once per competitor per source type (news, blog, press_release, sec, github, youtube, reddit, job_boards). It does NOT score findings — it produces candidate items with canonical URLs and content hashes that `scoring-findings` then consumes.
---

# processing-sources

Fetches and normalizes competitor content from up to eight source types:
**news** (Google News search), **blog** (RSS), **press_release** (wire
services and company newsrooms), **sec** (SEC EDGAR filings), **github**
(releases and new repos), **youtube** (channel uploads), **reddit**
(subreddit mentions), and **job_boards** (public ATS listings). The
agent's system prompt lists which sources each competitor uses.

## When to use this skill

At the start of every run, for every (competitor, source) pair listed in
the system prompt. The competitor list, aliases, and per-competitor
sources are all in the prompt — there is no `config.yaml` reader.

## The dispatcher pattern

This skill is a **dispatcher**. The detailed playbooks for each source type
live in reference files:

- News content → read `reference/news.md`
- Blog/RSS content → read `reference/blog-rss.md`
- Press releases → read `reference/press-release.md`
- SEC filings → read `reference/sec-edgar.md`
- GitHub activity → read `reference/github.md`
- YouTube uploads → read `reference/youtube.md`
- Reddit mentions → read `reference/reddit.md`
- Job board postings → read `reference/job-boards.md`

Do NOT try to handle a source type from this file alone. Open the relevant
reference file when you start processing that source type. The references
have concrete query shapes, canonicalization rules, and content-extraction
patterns that don't belong in the dispatcher.

## Output contract

Regardless of source type, every processed item must produce these fields
so the memory dedupe check works:

| Field | Type | Description |
|---|---|---|
| `canonical_url` | string | Stable URL with tracking params stripped, host lowercased, no trailing slash. See `reference/news.md` §URL canonicalization for the exact rules. |
| `content_hash` | string | sha256 hex digest of the article body text (title + summary + body). Used to detect meaningful content changes at a stable URL. Compute via `bash`: `printf '%s' "$TEXT" \| sha256sum \| cut -c1-64`. |
| `competitor_slug` | string | Lowercase, hyphens-only form of the competitor's canonical name. "OpenAI" → "openai", "Mistral AI" → "mistral-ai", "Robert Mondavi" → "robert-mondavi". |
| `title` | string | Headline. |
| `summary` | string | 2–3 sentence body (snippet from source, or first paragraph if no snippet). |
| `competitor` | string | Canonical competitor name (matches the system prompt). |
| `detected_at` | ISO 8601 string | When the source published the item, in UTC. NOT when the agent saw it. |
| `source_type` | string | One of: news, blog, press_release, sec, github, youtube, reddit, job_boards. |
| `source_name` | string | Human-readable publisher ("OpenAI Blog", "Reuters", "TechCrunch"). |
| `raw` | dict | Original payload from the source (RSS item, news entry, API response). |

## Memory dedupe

After producing each candidate, check the memory store before scoring:

```python
# pseudocode — actual call is via the memory_read tool
memory_path = f"findings/{competitor_slug}/{content_hash}.md"
existing = memory_read(memory_path)
if existing:
    # discard silently; do NOT score, do NOT post
    continue
else:
    pass_to_scoring(candidate)
```

If `memory_read` returns "not found," it's a new finding — pass to
`scoring-findings`. If `memory_read` succeeds, the finding has been
processed before — discard silently and increment the
`duplicates_skipped` counter for the run summary.

## Memory format

When `scoring-findings` finalizes a finding (post or suppress), it writes
to memory at `findings/{competitor_slug}/{content_hash}.md` with this
exact body shape:

```markdown
---
canonical_url: https://openai.com/blog/gpt5-pricing-update
content_hash: 3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b
competitor: OpenAI
competitor_slug: openai
category: Pricing
importance: High
title: OpenAI cuts GPT-5 input token price 50% to $0.01 per 1K
source_type: blog
source_name: OpenAI Blog
detected_at: 2026-04-10T14:30:00Z
first_seen_at: 2026-04-24T09:00:12Z
posted: true
slack_ts: "1745491212.123456"
---

OpenAI announced updated GPT-5 pricing on their blog. Input tokens drop to
$0.01 per 1K from $0.02; output token pricing unchanged. The change is
effective immediately and applies to all API customers.

Why it matters: Pricing moves are a tracked priority. A 50% cut on input
is aggressive and likely triggers competitor responses within weeks.
```

For suppressed findings, set `posted: false` and replace "Why it matters"
with a single sentence noting the suppression reason.

This format keeps records small (well under the 100KB per-memory limit)
and makes `memory_search` useful for the fuzzy dedupe in
`scoring-findings`.

## What NOT to do here

- **Don't score.** Assigning importance and category is the next skill's
  job (`scoring-findings`). Keep these steps separate.
- **Don't write to Slack.** That's `formatting-slack-posts` +
  `posting-to-slack`, much later in the cycle.
- **Don't write to memory yet.** Memory writes happen after scoring.
  Pre-score, you only `memory_read` to dedupe.
- **Don't invent sources.** If a competitor's source list is `[news,
  blog, github]`, process those three and stop. Do not explore Twitter,
  LinkedIn, podcasts.
- **Don't deep-fetch every result.** Use the source's summary (news
  snippet, RSS description) when possible. Only fall back to full
  `web_fetch` when the summary is too thin to score reliably. Token
  budget matters.

## Cross-references

- `scoring-findings` — what happens after processing produces candidate items
- `posting-to-slack` — how findings reach Slack
- `formatting-run-log` — `duplicates_skipped` count comes from this skill's
  dedupe checks
- system prompt — competitor list, source list, scoring tuning
