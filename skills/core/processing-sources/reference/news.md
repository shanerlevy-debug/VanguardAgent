# reference/news.md — News source playbook

How to find and normalize news mentions of a competitor for the POC. Loaded
on demand by the `processing-sources` skill when handling a `news` source.

## Table of contents

1. Search query construction
2. Result selection
3. URL canonicalization
4. Content hashing
5. Recency window
6. Common pitfalls

## 1. Search query construction

For each competitor, build a Google News query using the competitor's
canonical name AND its aliases (joined with OR):

```
"{name}" OR "{alias1}" OR "{alias2}"
```

Example for OpenAI (`aliases: ["OpenAI", "Open AI"]`):

```
"OpenAI" OR "Open AI"
```

Use `web_search` with the query plus `site:news.google.com` if you want to
constrain to Google News specifically. Otherwise the agent's web_search will
return general results — fine for the POC, just be more selective when
scoring.

Pass the run window (last 24h) to bound recency. Most queries
return results spanning weeks; you only care about items from the last
run window.

## 2. Result selection

The web_search results are a list of `{title, url, snippet, date}` items.
For each one, ask:

1. **Does the title or snippet actually mention the competitor by name (or alias)?** Discard items where the competitor is only adjacent context (e.g., an article about "AI startups" that lists OpenAI in passing).
2. **Is the date within the lookback window?** the run window (last 24h by default) is the cutoff. Items older than that go to the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) for dedupe but are scored as Low if they pass.
3. **Is the source plausibly authoritative?** Major outlets, the competitor's own newsroom, recognized industry publications — keep. Aggregator spam (random "AI News Roundup" SEO sites) — discard before processing.

## 3. URL canonicalization

The `canonical_url` you produce is the dedupe key alongside `content_hash`.
Two URLs that point at the same article must canonicalize to the same string,
or the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) will treat them as different findings.

Rules, applied in order:

1. **Lowercase the scheme and host.** `HTTPS://OpenAI.com/...` → `https://openai.com/...`.
2. **Strip query parameters that are tracking/session noise:** `utm_*`, `gclid`, `fbclid`, `ref`, `source`, `mc_cid`, `mc_eid`, `_hsenc`, `_hsmi`. Keep query parameters that affect content (`?article=12345`, `?p=789`).
3. **Drop the URL fragment** (everything after `#`). Fragments don't change content.
4. **Drop a trailing slash** unless the path is just `/`. `example.com/news/` → `example.com/news`.
5. **For Google News redirector URLs** (`news.google.com/articles/...`): follow the redirect once with `web_fetch` to get the underlying publisher URL, then canonicalize that. This step is the most expensive — do it only after you've confirmed (1)–(2) didn't already match an existing finding.

If a URL is from `web.archive.org`, treat the wayback path as the canonical
form — don't try to extract the original URL from it. Archive snapshots are
genuinely different findings from the live page.

## 4. Content hashing

```
content = title + "\n\n" + summary_or_snippet + "\n\n" + body_if_fetched
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

Notes:
- Use the snippet from web_search if you didn't full-fetch the body.
- If you DID full-fetch, use the extracted main body text (not the raw HTML).
- Strip leading/trailing whitespace from each component before joining.
- Lowercase nothing — case matters for content distinction.

The content hash exists so a stable URL whose page got materially edited
gets a new finding. Most edits (typo fixes, layout changes) won't produce a
different sha256 because they don't affect the title+body materially. That's
the intent — sha256 is fine here, no need for fuzzy matching.

## 5. Recency window

the system prompt provides two timeframes:

- the run window (last 24h by default) — how far back to look for new candidate items (default 12)
- the system prompt's `recency_cap_days` — items older than this never get above Low importance regardless of category (default 7)

Use the first to filter what enters processing. The second is a scoring
input, not a filter — pass items through anyway, they'll just score Low.

## 6. Common pitfalls

- **Press release republication.** Same press release shows up on 8 outlets within an hour. The article texts are nearly identical but URLs and titles vary. Result: 8 separate findings that look like 8 separate stories. Mitigation: when processing a competitor's news, check the first 2–3 results' bodies for high textual overlap; if so, score them all together and pick the one from the most authoritative source.
- **Competitor's own blog leaking into news.** Google News indexes openai.com/blog. Don't double-process it — the `blog` source handles RSS for the same content. Cheapest dedupe is the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) after canonicalization, but you can save tokens by skipping news results whose URL host matches the competitor's known domain (from system prompt).
- **Date confusion.** "2 hours ago" in a result is relative to the search time. Use the actual published timestamp in your `detected_at`, not the relative wording. If the timestamp is missing, fall back to the date from the URL (many news URLs include `/2026/04/13/`).
- **Aliases that are common words.** "Mistral" as a search term hits the wind, the Mistral car, the band. The aliases list in the system prompt is intentionally tight; if it's too tight (missing real mentions), that's a system prompt issue, not a processing issue.
