# reference/youtube.md — YouTube source playbook

How to monitor a competitor's YouTube channel for new video uploads. Loaded
on demand by the `processing-sources` skill when handling a `youtube` source.

## Table of contents

1. When this source applies
2. Channel feed discovery
3. Parsing
4. Item selection
5. URL canonicalization
6. Content hashing
7. Common pitfalls

## 1. When this source applies

Only for competitors with `youtube_channels` populated in the system prompt.
Each entry is either a channel ID (starts with `UC`) or a channel handle
(starts with `@`). If the list is empty, skip this source.

There are two access methods:

- **YouTube Data API** (requires `YOUTUBE_API_KEY` in secrets). Structured,
  quota-managed, returns metadata including view counts and descriptions.
  Quota cost: 1 unit per search call, 1 per video list call. Daily quota
  default is 10,000 units — more than enough.
- **Channel RSS feed** (no API key needed). Free, no quota, but limited to
  the 15 most recent uploads with less metadata. Sufficient for competitive
  monitoring.

Prefer the RSS feed unless the deployer specifically wants richer metadata.

## 2. Channel feed discovery

YouTube exposes an Atom feed per channel:

```
https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}
```

If the system prompt has a handle (`@openai`) instead of a channel ID:

1. `web_fetch` `https://www.youtube.com/@openai`
2. Look for `channel_id` in the page's meta tags or canonical URL
3. Use the extracted channel ID for the feed URL

Alternatively, use `web_search` to resolve:

```
site:youtube.com "@{handle}"
```

**YouTube Data API (if available):**

```
GET https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={id}&order=date&maxResults=10&type=video&key={api_key}
```

## 3. Parsing

The RSS feed is Atom XML. Parse with `feedparser`:

```python
import feedparser
feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
for entry in feed.entries:
    title     = entry.get("title", "")
    link      = entry.get("link", "")         # youtube.com/watch?v=...
    published = entry.get("published_parsed")
    summary   = entry.get("summary", "")      # video description (first ~300 chars)
    video_id  = entry.get("yt_videoid", "")
```

The `yt_videoid` field is YouTube-specific metadata that `feedparser`
extracts from the `<yt:videoId>` element.

## 4. Item selection

1. **Recency.** Published date within the run window (last 24h by default).
2. **Non-trivial.** Skip videos shorter than 30 seconds (usually test
   uploads or bumpers) — though the RSS feed doesn't include duration. If
   using the API, filter by `contentDetails.duration`.
3. **Relevance.** Company channels often mix product demos, conference talks,
   hiring videos, and office tours. All are valid candidates — let
   `scoring-findings` sort them by importance. Don't filter here.

## 5. URL canonicalization

YouTube watch URLs are already canonical:

```
https://www.youtube.com/watch?v={video_id}
```

Canonicalization rules:

1. Always use the `www.youtube.com/watch?v=` form, not short URLs
   (`youtu.be/{id}`) or embed URLs (`youtube.com/embed/{id}`).
2. Strip all query parameters except `v=`. Remove `t=`, `list=`,
   `index=`, `si=`, `feature=`, etc.
3. Lowercase the scheme and host.
4. No trailing slash.

## 6. Content hashing

```
content = video_id + "\n" + title + "\n" + description_or_summary
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

Including the `video_id` means even if a creator re-uploads the same content
under a different video ID, it produces a new finding. This is correct —
a re-upload is a distinct event.

## 7. Common pitfalls

- **Premieres and scheduled videos.** YouTube shows upcoming premieres in
  the feed with a future `published` date. Skip items with `published`
  more than 1 hour in the future.
- **Unlisted videos appearing briefly.** Occasionally a video appears in
  the feed, then is set to unlisted or private. If your `web_fetch` on the
  watch URL returns a "Video unavailable" page, record it from the feed
  metadata and flag `raw["possibly_unlisted"] = true`.
- **Shorts vs. long-form.** YouTube Shorts (vertical, <60s) appear in the
  same feed as long-form videos. They're often lower-signal (promotional
  clips, memes) but are still valid candidates. Don't filter them out.
- **Multiple channels.** Some competitors have several channels (main,
  developer, regional). the system prompt supports a list in
  `youtube_channels` — process each one.
- **Description truncation in RSS.** The feed's `summary` is truncated to
  ~300 characters. For scoring purposes this is usually sufficient. If the
  title and truncated description don't provide enough context to score,
  `web_fetch` the video page for the full description — but budget this to
  1–2 full fetches per competitor.
