# reference/blog-rss.md — Blog/RSS source playbook

How to fetch and normalize a competitor's own blog feed. Loaded on demand by
the `processing-sources` skill when handling a `blog` source.

## Table of contents

1. Feed discovery
2. Parsing
3. Item selection
4. URL canonicalization
5. Content hashing
6. Common pitfalls

## 1. Feed discovery

For each competitor with `sources: [..., blog, ...]`, you need a feed URL.
For the POC's three competitors:

| Competitor | Likely feed URL |
|---|---|
| OpenAI | `https://openai.com/blog/rss.xml` (verify with `web_fetch`) |
| Mistral AI | `https://mistral.ai/news/rss` or `/feed.xml` (verify) |
| Perplexity | check `https://www.perplexity.ai/hub` for feed link |

These URLs may have changed since this file was written. If the first guess
404s, fall back to:

1. Fetch the competitor's blog index page (`domains[0]` + `/blog` or `/news`)
2. Look for `<link rel="alternate" type="application/rss+xml">` in the HTML head
3. Use the `href` from that link tag as the feed URL

If no RSS link is discoverable, mark that competitor's blog source as
"feed-unavailable" for this run and move on. Do NOT fall back to scraping
the blog index HTML — too fragile for the POC.

## 2. Parsing

RSS feeds are XML. The two common flavors are:

- **RSS 2.0** — items under `<channel><item>` with `<title>`, `<link>`, `<description>`, `<pubDate>`, `<guid>`
- **Atom** — entries under `<feed><entry>` with `<title>`, `<link href>`, `<summary>` or `<content>`, `<published>` or `<updated>`, `<id>`

Use a proper parser — the `feedparser` pip package handles both flavors
uniformly (it's in the environment's pre-installed pip list per
`packages.pip`). Regex-parsing XML will bite you; don't.

```python
import feedparser
feed = feedparser.parse(feed_url)
for entry in feed.entries:
    title   = entry.get("title", "")
    link    = entry.get("link", "")
    summary = entry.get("summary", "")
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    guid    = entry.get("id") or entry.get("guid") or link
```

## 3. Item selection

Unlike news search, a blog feed's items are all about the competitor by
definition. The selection criteria narrow to just recency:

- **Is `published` (or `updated` if no `published`) within the run window (last 24h by default)?** If yes, candidate. If no, discard — the feed is already sorted newest-first, so once you hit an old item you can stop iterating the rest.

Do NOT filter by topic at this stage. A blog post about "our team volunteer
day" is still a candidate finding; `scoring-findings` will mark it Low.
Filtering here would leak scoring logic into processing.

## 4. URL canonicalization

Blog feed items usually have stable URLs already — the publisher controls
them. But still apply the same rules as `reference/news.md` §3 for safety:

1. Lowercase scheme + host
2. Strip `utm_*`, `gclid`, `fbclid`, `ref`, `source`, `mc_*`, `_hs*`
3. Drop the fragment
4. Drop trailing slash (unless path is just `/`)

**Feed-specific:** some feeds use a `guid` element that's a URL, but the
`<link>` is the actual article. Use the `<link>`, not the `guid`, as the
`canonical_url`. The `guid` goes into `raw` for later reference.

## 5. Content hashing

Same as news:

```
content = title + "\n\n" + summary + "\n\n" + body_if_fetched
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

Blog summaries in feeds are usually longer than news snippets (full body or
excerpt, not a teaser). You often won't need to full-fetch the article to
get enough text to score — save the tokens.

## 6. Common pitfalls

- **Empty summary, full body only in article.** Some feeds have `<description>` with just the first 100 chars. In that case `web_fetch` the article URL to get enough body text. Budget: up to 3 full-fetches per competitor per run. If you're needing more, something else is wrong.
- **Published date is missing or future-dated.** Drafts occasionally slip into feeds with `pubDate` in the future, or with no date at all. If date is missing, use `datetime.utcnow()` and flag in `raw["date_missing"] = true`. If future-dated by more than a day, skip the item — likely not actually published.
- **Feed includes "Archived" or "Featured" sections.** Some blogs pin old posts. A pinned post from 2024 will appear at the top of a feed every day. Use the item's `published` timestamp, not its position, for the lookback check.
- **Encoding issues.** UTF-8 is standard; some older feeds use latin-1 or windows-1252. `feedparser` handles this. If you're bypassing feedparser for some reason, decode explicitly.
- **Same content in both RSS and news.** The the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) check on `canonical_url` handles this — if news processing saw `openai.com/blog/pricing` first and recorded it, blog RSS seeing the same URL will return `seen: true` and be silently discarded. This is the intended behavior; the two sources complement rather than duplicate.
