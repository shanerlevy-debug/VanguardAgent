# reference/reddit.md — Reddit source playbook

How to find competitor mentions on Reddit. Loaded on demand by the
`processing-sources` skill when handling a `reddit` source.

## Table of contents

1. When this source applies
2. Search strategy
3. Item selection
4. URL canonicalization
5. Content hashing
6. Signal vs. noise
7. Common pitfalls

## 1. When this source applies

Only when `sources.reddit.enabled: true` in the system prompt. Requires
`REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in secrets for authenticated
API access. Without auth, Reddit aggressively rate-limits and may block.

The `sources.reddit.subreddits` list in the system prompt scopes which
subreddits to search. If the list is empty, search all of Reddit (noisier
but catches discussions in unexpected communities).

Reddit is a Phase 2 source — noisier than news or press releases, but
valuable for early product feedback, community sentiment shifts, and
information that doesn't make it to mainstream press.

## 2. Search strategy

**Option A — Reddit API (preferred):**

Authenticate via OAuth2 client credentials:

```
POST https://www.reddit.com/api/v1/access_token
  grant_type=client_credentials
  Authorization: Basic base64(client_id:client_secret)
```

Then search:

```
GET https://oauth.reddit.com/search?q="{competitor_name}"&sort=new&t=day&limit=25
```

Or scoped to specific subreddits:

```
GET https://oauth.reddit.com/r/{subreddit}/search?q="{competitor_name}"&restrict_sr=on&sort=new&t=day&limit=25
```

**Option B — web_search fallback:**

If API credentials aren't configured, use `web_search`:

```
site:reddit.com "{competitor_name}" OR "{alias}"
```

Less structured but works. Results include both posts and comments — you'll
get the thread URL, not the specific comment.

**Option C — RSS feeds:**

Reddit exposes RSS for search results (no auth needed):

```
https://www.reddit.com/search.rss?q="{competitor_name}"&sort=new&t=day
```

Parse with `feedparser`. Limited to 25 results, no pagination.

## 3. Item selection

Reddit is noisy. Apply these filters in order:

1. **Recency.** Created within the run window (last 24h by default).
2. **Minimum engagement.** For posts: score (upvotes minus downvotes) ≥ 5,
   OR comment count ≥ 3. This filters out posts that the community ignored.
   For API results, these are in the `score` and `num_comments` fields.
   For web_search results, you won't have this data — accept all and let
   scoring handle it.
3. **Subreddit relevance.** If `subreddits` is configured, only process
   posts from those subreddits. If not, accept all but note the subreddit
   in `raw["subreddit"]` for scoring context.
4. **Post type.** Prioritize text posts (`self.{subreddit}`) and link posts
   that reference the competitor. Skip image-only posts, meme posts
   (identifiable by flair or subreddit culture), and bot-generated posts.
5. **Competitor is the subject.** The competitor's name must appear in the
   post title OR the first 500 characters of the body. Mentions buried deep
   in a comment thread are too tangential.

## 4. URL canonicalization

Reddit post URLs follow this pattern:

```
https://www.reddit.com/r/{subreddit}/comments/{post_id}/{slug}/
```

Canonicalization:

1. Always use `www.reddit.com`, not `old.reddit.com`, `new.reddit.com`, or
   `redd.it` short links.
2. Strip the slug — it's cosmetic and changes if the title is edited.
   Canonical form: `https://www.reddit.com/r/{subreddit}/comments/{post_id}/`
3. Drop query parameters (`?utm_source=...`, `?context=3`, etc.).
4. Lowercase scheme + host.
5. Keep the trailing slash for Reddit URLs (Reddit redirects without one).

For comment-level URLs (`/comments/{post_id}/slug/{comment_id}/`),
canonicalize to the post level — we track posts, not individual comments.

## 5. Content hashing

```
content = subreddit + "\n" + post_title + "\n" + selftext_or_empty
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

Include the subreddit to differentiate cross-posts (same title, different
community). Do NOT include the score or comment count — those change over
time and would cause the same post to generate a new finding on every run.

## 6. Signal vs. noise

Reddit is the noisiest source in the system. The scoring skill handles
importance, but you can reduce token waste by recognizing low-signal
patterns during processing:

**Higher signal:**
- Posts in r/programming, r/MachineLearning, r/artificial, r/technology,
  r/sysadmin, or industry-specific subreddits
- Posts with 50+ upvotes (community-validated interest)
- Posts discussing pricing changes, outages, product launches, pivots
- "I switched from {competitor} to {alternative}" posts (customer churn signal)

**Lower signal (still valid findings, just score Low):**
- "What do you think of {competitor}?" opinion polls
- Support questions ("How do I do X in {competitor}'s product?")
- Hiring-related posts
- Memes or jokes about the competitor

Do NOT filter low-signal posts out during processing — pass them all to
scoring. This list is guidance for what `scoring-findings` will likely do,
not a processing filter.

## 7. Common pitfalls

- **Cross-posts.** The same content posted to 3 subreddits. Each is a
  different URL and a different community discussion, but the content hash
  will match. the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) catches exact matches. If the title
  differs slightly across cross-posts, you'll get multiple findings — this
  is acceptable; they represent genuinely different community reactions.
- **Deleted posts.** Reddit's API returns deleted posts with `[deleted]` as
  the title and `[removed]` as the body. Skip these — no content to score.
- **Bot posts.** AutoModerator and news aggregator bots post links with
  auto-generated titles. The author field will be `AutoModerator` or a known
  bot account. Skip posts where `author` contains `bot` (case-insensitive)
  or equals `AutoModerator`.
- **Rate limiting.** Reddit's API allows 60 requests per minute for
  OAuth-authenticated apps. Budget 3–5 requests per competitor (search +
  a few post detail fetches). The RSS fallback has no documented rate limit
  but is throttled in practice; space requests by at least 2 seconds.
- **NSFW content.** Some subreddits or posts are marked NSFW. The API
  includes an `over_18` field — skip these posts entirely.
