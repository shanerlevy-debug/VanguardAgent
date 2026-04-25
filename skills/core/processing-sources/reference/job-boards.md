# reference/job-boards.md — Job boards source playbook

How to monitor a competitor's public job postings for competitive signals.
Loaded on demand by the `processing-sources` skill when handling a
`job_boards` source.

## Table of contents

1. When this source applies
2. What job postings tell you
3. Discovery
4. Item selection
5. URL canonicalization
6. Content hashing
7. Common pitfalls

## 1. When this source applies

When `sources.job_boards.enabled: true` in the system prompt. No API key is
needed — the boards covered here are all public. This source works for any
competitor that uses a standard ATS (applicant tracking system) with a public
careers page.

Job boards are a uniquely valuable competitive intelligence source because
companies reveal strategic direction through what they're hiring for before
they announce it publicly.

## 2. What job postings tell you

| Signal | What to look for | CI category |
|---|---|---|
| **New product lines** | Roles mentioning unreleased products, new platforms, or unfamiliar team names | Technology Direction, Roadmap Signals |
| **Geographic expansion** | New offices, remote roles in new countries | Partnerships, Customers/Wins |
| **Tech stack shifts** | "Experience with {new_technology}" replacing prior stack requirements | Technology Direction |
| **Hiring surges** | 20+ open roles in one department vs. baseline | Hiring, Funding/M&A |
| **Leadership gaps** | VP/C-level searches (especially unexpected ones) | Leadership Changes |
| **Layoff aftermath** | Sudden batch of re-posts for roles that were recently filled | Hiring |

## 3. Discovery

Most tech companies use one of these ATS platforms, all of which expose
public job listing pages:

**Greenhouse:**
```
https://boards.greenhouse.io/{company_slug}
```
Returns an HTML page. JSON API available at:
```
https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs
```
The JSON API is unauthenticated and returns structured data — prefer it.

**Lever:**
```
https://jobs.lever.co/{company_slug}
```
HTML page. No public JSON API, but the page is well-structured for parsing.

**Ashby:**
```
https://jobs.ashbyhq.com/{company_slug}
```

**Workday, BambooHR, others:**
No standard URL pattern. Use `web_search`:
```
site:myworkdayjobs.com "{competitor_name}"
```
or:
```
"{competitor_name}" careers jobs
```

**To discover which ATS a competitor uses:**
1. `web_fetch` the competitor's primary domain + `/careers` or `/jobs`
2. Look for redirects to `greenhouse.io`, `lever.co`, `ashbyhq.com`, etc.
3. Alternatively, `web_search` for `"{competitor_name}" greenhouse OR lever
   OR ashby careers`

Store the discovered board URL in `raw["board_url"]` for future runs.

## 4. Item selection

Job postings are numerous — a large company may have 500+ open roles. You
don't want 500 findings. Filter to high-signal postings:

1. **Recency.** Most ATS platforms include a `created_at` or `updated_at`
   timestamp. Only process postings created or updated within
   the run window (last 24h by default). If no date is available, process only the first
   page of results (typically 10–20 most recent).
2. **Seniority signal.** Prioritize Director+ and VP+ roles. A "Staff
   Engineer" posting is mildly interesting; a "VP of {New Thing}" posting is
   a strong roadmap signal.
3. **Novel teams or products.** Compare the posting's team/department name
   against previously seen teams (via `memory_search` filtered to
   `category: "Hiring"` for that competitor). A new team name is more
   interesting than a backfill in an existing team.
4. **Batch detection.** If you see 10+ new roles in the same department
   posted within a short window, that's a single "hiring surge" finding
   rather than 10 individual findings. Group them: one finding with a title
   like "{Competitor} hiring surge: 12 new {department} roles" and the
   individual postings listed in `raw["postings"]`.

## 5. URL canonicalization

ATS URLs are stable:

```
# Greenhouse
https://boards.greenhouse.io/{company}/jobs/{job_id}

# Lever
https://jobs.lever.co/{company}/{posting_id}

# Ashby
https://jobs.ashbyhq.com/{company}/{job_id}
```

Canonicalization:

1. Lowercase scheme + host.
2. Strip query parameters (`?gh_jid=...`, `?source=...`, `?lever-origin=...`).
3. Drop fragments and trailing slashes.
4. For Greenhouse JSON API results, construct the canonical URL from the
   `absolute_url` field — don't use the API endpoint URL.

## 6. Content hashing

```
content = competitor_name + "\n" + job_title + "\n" + department_or_team + "\n" + location
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

Do NOT include the full job description in the hash — descriptions get
minor edits (benefits updates, boilerplate changes) that would cause the
same role to appear as a new finding on every run. The title + department +
location tuple is stable enough to dedupe correctly.

## 7. Common pitfalls

- **Evergreen postings.** Some companies keep "General Application" or
  "Future Opportunities" postings open permanently. These re-appear as
  "new" on every run because their `updated_at` refreshes. Filter by title:
  skip postings containing "general application", "talent pool", or "future
  opportunities" (case-insensitive).
- **Internal transfers.** Some ATS platforms show internal-only postings on
  the public board. These are usually indistinguishable from external
  postings — process them normally.
- **ATS migration.** If a competitor switches from Greenhouse to Lever, all
  postings appear "new" at once. The batch detection logic (§4) should catch
  this as a single surge finding rather than hundreds of individual ones.
- **Confidential postings.** Some VP/C-level roles are posted without naming
  the company ("Leading AI company seeks VP Engineering"). These won't
  appear on the competitor's own board. `web_search` may surface them on
  third-party aggregators — but attributing them to a specific competitor
  is speculative. Skip unless the posting clearly identifies the company.
- **Seasonal patterns.** Hiring tends to spike in Q1 and Q3. A burst of
  postings in January isn't necessarily a strategic signal — it may be
  annual budget unlocking. Note the time of year in `raw["context"]` and
  let `scoring-findings` calibrate.
- **Rate limiting.** Greenhouse's public JSON API has no documented rate
  limit but will return 429s under heavy load. One request per competitor
  per run is sufficient — the API returns all open jobs in one call.
