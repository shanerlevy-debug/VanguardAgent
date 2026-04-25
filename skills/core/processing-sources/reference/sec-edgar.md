# reference/sec-edgar.md — SEC EDGAR source playbook

How to find and normalize SEC filings for a tracked competitor. Loaded on
demand by the `processing-sources` skill when handling a `sec` source.

## Table of contents

1. When this source applies
2. EDGAR full-text search
3. Filing types that matter
4. Item selection
5. URL canonicalization
6. Content hashing
7. Common pitfalls

## 1. When this source applies

Only for competitors that are US-listed public companies (or have US-listed
subsidiaries). The competitor's `sec_cik` field in the system prompt is the
Central Index Key — a 10-digit number that uniquely identifies the filer.
If `sec_cik` is null or absent, skip this source for that competitor.

SEC data is free, public, and structured. No API key needed.

## 2. EDGAR full-text search

EDGAR's full-text search API (EFTS) is the fastest way to find recent
filings:

```
https://efts.sec.gov/LATEST/search-index?q="{competitor_name}"&dateRange=custom&startdt={start}&enddt={end}&forms=8-K,10-Q,10-K
```

Alternatively, use the company-specific filings page:

```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={sec_cik}&type=8-K&dateb=&owner=include&count=10
```

Or use `web_search` with:

```
site:sec.gov "{competitor_name}" 8-K OR 10-Q
```

**Important:** EDGAR requires a `User-Agent` header with a company name and
email on programmatic requests. The CMA agent's `web_fetch` sends a standard
browser UA, which EDGAR accepts for occasional requests. Do not loop
aggressively — 1–3 requests per competitor per run is fine.

## 3. Filing types that matter

Not all SEC filings are competitive intelligence. Focus on:

| Filing | What it is | Signal value |
|---|---|---|
| **8-K** | Current report — material events (M&A, leadership changes, material agreements, bankruptcy, delistings) | High. These are breaking news from the horse's mouth. |
| **10-Q** | Quarterly report — financials, risk factors, MD&A | Medium. Revenue trends, customer concentration, competitive language in risk factors. |
| **10-K** | Annual report — same as 10-Q but yearly, plus strategy discussion | Medium. Strategy shifts, segment changes, new risk factors. |
| **DEF 14A** | Proxy statement — executive compensation, board changes | Low unless leadership changes are a priority. |
| **S-1 / S-1/A** | IPO registration | High if the competitor is going public. |

Skip: 4, SC 13D/G (ownership reports), EFFECT (effectiveness notices), and
routine exhibits unless specifically configured.

## 4. Item selection

For each filing found:

1. **Recency.** Filing date within the run window (last 24h by default). Note: SEC filings
   are dated by filing date, not event date. An 8-K filed today may report
   an event from last week. Use the filing date for `detected_at`.
2. **CIK match.** Confirm the filing's CIK matches `competitors[].sec_cik`.
   EDGAR search results can include filings that merely mention the
   competitor in their body text — you want filings BY the competitor, not
   filings that mention them.
3. **Material content.** For 8-Ks, the item numbers tell you what the filing
   is about. Items 1.01 (material agreements), 2.01 (acquisitions), 5.02
   (director/officer changes), and 8.01 (other events) are usually worth
   scoring. Item 7.01 (Regulation FD) often contains earnings pre-releases.
   Item 9.01 (financial exhibits) alone is rarely worth a finding unless
   accompanied by a substantive item.

## 5. URL canonicalization

EDGAR filing URLs follow a stable pattern:

```
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number}/{filename}
```

The accession number (e.g., `0001193125-26-123456`) is globally unique.
Canonicalize to the filing index page:

```
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_with_dashes}/
```

Do NOT use the EDGAR search result URL — it includes session-specific
parameters. Always resolve to the archive path.

Lowercase the scheme and host per standard rules; the path is
case-insensitive on EDGAR but preserve case for safety.

## 6. Content hashing

For SEC filings, use the filing's accession number as a stable identifier
rather than hashing the full document (10-Qs can be 100+ pages):

```
content = filing_type + "\n" + accession_number + "\n" + title_or_description
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

This is a pragmatic deviation from the news/blog pattern. SEC filing
content doesn't change after filing (amendments get new accession numbers),
so the accession number alone provides uniqueness. Including the type and
title gives the hash enough entropy to avoid collisions with other filing
types from the same company on the same day.

## 7. Common pitfalls

- **Amended filings.** An `8-K/A` is an amendment to a prior 8-K. It gets
  a new accession number and should be treated as a new finding — but the
  title and summary should note it's an amendment, not a fresh event.
- **Exhibit-only filings.** Some 8-Ks are filed solely to attach an exhibit
  (press release, presentation) with no substantive cover page. Check
  whether the filing has a meaningful body or just a list of exhibits. If
  exhibit-only, the press release is likely already captured by the
  `press_release` source — the memory dedupe check (`memory_read findings/{competitor_slug}/{content_hash}.md`) handles the overlap.
- **XBRL / iXBRL data.** 10-Q and 10-K filings include inline XBRL
  financial data. Ignore the structured data for competitive intel purposes
  — the narrative sections (MD&A, risk factors, business description) are
  where the signal lives. Look for the `.htm` filing, not the `.xml`.
- **Rate limiting.** EDGAR doesn't have a strict rate limit for browser-like
  access, but aggressive scraping will get your IP blocked. Stick to 1–3
  requests per competitor per run. The CMA environment's IP is
  Anthropic-managed — don't burn it.
- **Foreign private issuers.** Non-US companies listed in the US file on
  Form 20-F (annual) and 6-K (current report) instead of 10-K and 8-K.
  If a competitor is a foreign private issuer, adjust the filing type
  filter accordingly.
