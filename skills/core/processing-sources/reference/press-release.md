# reference/press-release.md — Press release source playbook

How to find and normalize a competitor's press releases. Loaded on demand by
the `processing-sources` skill when handling a `press_release` source.

## Table of contents

1. Where to look
2. Search strategy
3. Item selection
4. URL canonicalization
5. Content hashing
6. Common pitfalls

## 1. Where to look

Press releases show up in three places, in order of authority:

1. **The competitor's own newsroom.** Most companies have a `/press`,
   `/newsroom`, `/news`, or `/about/press` page on their primary domain.
   Check `competitors[].domains[0]` + each of those path suffixes. This is
   the most authoritative source — use it when available.
2. **Wire services.** PRNewswire (`prnewswire.com`), BusinessWire
   (`businesswire.com`), and GlobeNewswire (`globenewswire.com`) syndicate
   press releases with a search-by-company feature.
3. **News search.** Google News indexes wire service releases. If the first
   two methods are blocked or empty, a targeted news search for
   `"{competitor}" press release` or `"{competitor}" announces` may surface
   them. Overlap with `news.md` is handled by the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`).

For any competitor with `sources: [..., press_release, ...]`, try the
newsroom first. Fall back to wire services if the newsroom has no feed or
the page is behind JavaScript rendering.

## 2. Search strategy

**Newsroom page:** `web_fetch` the newsroom URL. Look for either:
- An RSS feed link (`<link rel="alternate" type="application/rss+xml">`) — if
  present, parse it per `reference/blog-rss.md` §2. Many company newsrooms
  are just a blog with different branding.
- A list of press release entries in the HTML. Extract title, URL, and date
  from each. Most newsrooms display 10–20 items per page; the first page is
  sufficient for a single run.

**Wire services:** Use `web_search` with a query like:

```
site:prnewswire.com "{competitor_name}"
```

or:

```
site:businesswire.com "{competitor_name}"
```

Filter results by the run window (last 24h by default). Wire services typically show the
publication date in the URL or snippet.

**Budget:** Press release scanning is cheap — 1–2 search calls + 0–2
`web_fetch` calls per competitor. The content is structured and the signal
density is high (press releases are almost always scorable).

## 3. Item selection

Press releases are inherently about the issuing company, so unlike news
search, you don't need to verify the competitor is actually the subject.
Filter to:

1. **Recency.** Within the run window (last 24h by default).
2. **Duplicate avoidance.** The same press release often appears on 3–5 wire
   services and the company's own newsroom simultaneously. Process the
   newsroom version first (most authoritative URL). Wire service copies will
   be caught by the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) if the content hash matches.
3. **Relevance.** Some newsroom pages mix press releases with blog posts,
   event announcements, and media mentions. A release about "Q3 Earnings
   Call Scheduled for October 15" is a valid finding; a "Media Kit" link is
   not. Look for items tagged "Press Release" or items with the structured
   dateline format ("CITY, State — DATE — Company...").

## 4. URL canonicalization

Same rules as `reference/news.md` §3:

1. Lowercase scheme + host
2. Strip tracking params (`utm_*`, `gclid`, etc.)
3. Drop fragment
4. Drop trailing slash (unless path is just `/`)

**Wire-specific:** PRNewswire URLs contain a numeric release ID
(`prnewswire.com/news-releases/...-123456789.html`). This ID is stable; the
slug before it may vary between syndications. Canonicalize by keeping the
full path — the ID provides uniqueness even if the slug drifts.

BusinessWire URLs use a date-based path
(`businesswire.com/news/home/20260413005678/en/`). Canonicalize as-is.

## 5. Content hashing

Same as `reference/news.md` §4:

```
content = title + "\n\n" + body_or_summary
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

Press release bodies are long and structured (dateline, body paragraphs,
boilerplate "About {Company}" footer, media contacts). Include the full body
if fetched; exclude the boilerplate footer if you can reliably identify it
(it doesn't change between releases and would reduce hash uniqueness).

## 6. Common pitfalls

- **Republished wire content creates duplicates.** The same release on
  PRNewswire, BusinessWire, and the company's newsroom will have near-identical
  body text but different URLs. the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) catches exact
  (url, hash) matches, but if the body text drifts slightly (formatting
  differences), you get duplicates. Mitigation: process the newsroom version
  first; when you encounter wire versions within the same run, compare
  titles — if title similarity is >90%, check `memory_search` for
  a finding from the same competitor with the same title and skip.
- **"About {Company}" boilerplate.** Every press release ends with a
  paragraph describing the company. Don't flag this as a finding about the
  competitor's strategy — it's standard disclosure text unchanged for years.
- **Earnings call announcements vs. earnings releases.** "Q3 Earnings Call
  Scheduled" is a scheduling notice with no material content. "Q3 Revenue Up
  15%" is a material release. Both are valid findings but score very
  differently — let `scoring-findings` handle this distinction.
- **Embargoed releases.** Occasionally a release appears briefly then
  vanishes. If your `web_fetch` returns a 404 or a "content not found" page
  for a URL you saw in search results, record it with what you have from the
  search snippet and flag `raw["possibly_embargoed"] = true`.
- **Non-English releases.** Multinational competitors may issue releases in
  multiple languages. Process English releases only for now; non-English
  content will confuse the scoring and formatting skills.
