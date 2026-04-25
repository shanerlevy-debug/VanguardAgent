---
name: formatting-slack-posts
description: Constructs the finding dict that `posting-to-slack` consumes when sending a message to Slack. Use this skill after `scoring-findings` has produced category + importance + why_it_matters, just before calling `posting-to-slack`. This skill defines the field contract; the actual Block Kit JSON template lives in `posting-to-slack`.
---

# formatting-slack-posts

One narrow job: assemble a dict with the exact fields `posting-to-slack`
expects. The Block Kit JSON is built inside `posting-to-slack` from this
dict — keep them separate so the Block Kit template can be tweaked
without touching field semantics.

## The finding dict contract

Exactly these fields, in the right types. Missing or mistyped fields will
either fail Slack validation or render incorrectly.

| Field | Type | Required | Notes |
|---|---|---|---|
| `canonical_url` | str | yes | The canonicalized URL from `processing-sources`. |
| `content_hash` | str | yes | The sha256 hex digest from `processing-sources`. |
| `competitor` | str | yes | Canonical competitor name from the system prompt (not an alias). |
| `competitor_slug` | str | yes | Lowercase hyphenated slug (used for memory paths). |
| `category` | str | yes | One of the 12 category strings exactly as listed in `scoring-findings`. |
| `importance` | str | yes | `"High"`, `"Medium"`, or `"Low"` — strings, capital first letter. |
| `title` | str | yes | The finding headline. Under 150 chars — `posting-to-slack` truncates otherwise. |
| `summary` | str | yes | 2–3 sentences. Factual, present tense where possible. |
| `why_it_matters` | str or null | optional | Contextualization line. See `writing-why-it-matters` for the style. Can be null for Low items where context adds no value. |
| `source_name` | str or null | optional | Publisher display name ("OpenAI Blog", "Reuters"). If null, `posting-to-slack` falls back to "source". |
| `source_type` | str | yes | One of: news, blog, press_release, sec, github, youtube, reddit, job_boards. |
| `detected_at` | ISO 8601 str | yes | When the article was published at the source. UTC. |
| `first_seen_at` | ISO 8601 str | yes | When the agent first scored this URL (i.e., now). UTC. |
| `posted` | bool | yes | True if this finding will be sent to Slack. False for suppressed findings (still recorded). |
| `raw` | dict or null | optional | Original unstructured payload. Pass through from `processing-sources`. |

## Worked example

Scored finding (as the agent's working memory might have it):

```
OpenAI announced GPT-5 pricing changes today. Input tokens drop 50% to $0.01/1K.
Published on their blog 2026-04-10. High importance because pricing moves
are a tracked priority. Canonical URL:
https://openai.com/blog/gpt5-pricing-update — content hash already computed
in processing.
```

The dict to construct:

```python
finding = {
    "canonical_url": "https://openai.com/blog/gpt5-pricing-update",
    "content_hash": "3a7bd3e2360a3d29eea436fcfb7e44c735d117c42d1c1835420b6b9942dd4f1b",
    "competitor": "OpenAI",
    "competitor_slug": "openai",
    "category": "Pricing",
    "importance": "High",
    "title": "OpenAI cuts GPT-5 input token price 50% to $0.01 per 1K",
    "summary": "OpenAI announced updated GPT-5 pricing on their blog. Input tokens drop to $0.01 per 1K from $0.02; output token pricing unchanged. The change is effective immediately and applies to all API customers.",
    "why_it_matters": "Pricing moves are a tracked priority. A 50% cut on input is aggressive and likely triggers competitor responses within weeks.",
    "source_name": "OpenAI Blog",
    "source_type": "blog",
    "detected_at": "2026-04-10T14:30:00Z",
    "first_seen_at": "2026-04-24T09:00:12Z",
    "posted": True,
    "raw": {"source": "blog", "rss_guid": "openai-blog-42"},
}

# Then post via the posting-to-slack skill.
```

## Common mistakes to avoid

- **Wrong competitor form.** Use the canonical name from the system prompt
  ("Mistral AI"), not an alias ("Mistral"). Memory paths and Slack
  rendering both depend on it.
- **Wrong category string.** "product" (lowercase) or "Funding" (missing
  "/M&A") won't validate. Copy-paste from the table in `scoring-findings`.
- **Naive datetimes.** Always include the `Z` suffix or `+00:00` to
  indicate UTC. `"2026-04-10T14:30"` is naive and will display incorrectly.
- **URL in `source_name`.** `source_name` is human-readable ("TechCrunch"),
  not a URL. The URL lives in `canonical_url`.
- **Escaping markdown in `summary` or `why_it_matters`.** Don't pre-escape
  Slack markdown characters. `posting-to-slack` will pass them through to
  Slack's `mrkdwn` renderer; over-escaping looks ugly.

## Run summary dict

For the end-of-run summary, build a different dict — the `RunSummary`
schema from `formatting-run-log`. It's not a finding; it has its own
shape and its own block in `posting-to-slack`.

## Cross-references

- `scoring-findings` — produces `category`, `importance`, `why_it_matters`
- `writing-why-it-matters` — how to write the contextualization line
- `posting-to-slack` — consumes the dict built here; renders the Block Kit
- `formatting-run-log` — separate schema for end-of-run summary
