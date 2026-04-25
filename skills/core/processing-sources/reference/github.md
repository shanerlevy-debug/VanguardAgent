# reference/github.md — GitHub source playbook

How to track a competitor's public GitHub activity. Loaded on demand by the
`processing-sources` skill when handling a `github` source.

## Table of contents

1. When this source applies
2. What to look at
3. Discovery
4. Item selection
5. URL canonicalization
6. Content hashing
7. Common pitfalls

## 1. When this source applies

Only for competitors with `github_orgs` populated in the system prompt. If the
list is empty or absent, skip this source. Many competitors (especially
enterprise SaaS) have no meaningful public GitHub presence.

Requires `GITHUB_TOKEN` in secrets for authenticated API access. Without it,
GitHub's unauthenticated rate limit (60 requests/hour) is too low for
production use. With a token, you get 5,000 requests/hour — more than enough.

## 2. What to look at

GitHub signals fall into three buckets:

| Signal | Where to find it | CI value |
|---|---|---|
| **New releases / tags** | `/{org}/{repo}/releases` or Atom feed | High — product launches, version bumps |
| **New public repos** | `GET /orgs/{org}/repos?sort=created` | Medium — new projects, SDK launches |
| **Notable commits** | Commit activity on key repos | Low to Medium — tech direction signals |

For competitive intelligence, **releases are the primary signal**. New repos
are occasional but high-value when they appear (competitor launching a new
product line). Commit-level monitoring is noisy and usually not worth the
token cost — skip unless the deployer specifically requests it.

## 3. Discovery

For each GitHub org in `competitors[].github_orgs`:

**Releases (primary):** Use the GitHub Atom feed, which is public and
doesn't count against API rate limits:

```
https://github.com/{org}/{repo}/releases.atom
```

Parse this with `feedparser` per `reference/blog-rss.md` §2. The feed
contains the 10 most recent releases with titles, dates, and release notes.

To discover which repos to watch, list the org's public repos sorted by
update time:

```
https://api.github.com/orgs/{org}/repos?sort=updated&per_page=10
```

Pick the top 3–5 repos by star count or recent activity. Don't monitor
every repo — most orgs have dozens of repos, most of which are
documentation, tooling, or archived experiments.

**New repos:** Same API call as above but `sort=created&direction=desc`.
A repo created within the run window (last 24h by default) is a finding candidate.

**Alternative (no API):** Use `web_search` with:

```
site:github.com/{org} release OR "released"
```

This is less structured but works without a `GITHUB_TOKEN`.

## 4. Item selection

For releases:

1. **Recency.** Published date within the run window (last 24h by default).
2. **Non-trivial.** Skip releases tagged as `pre-release` or with version
   strings like `v0.0.1-alpha` unless the repo itself is notable. Stable
   releases (`v1.0.0`, `v2.3.0`) are the signal.
3. **Meaningful release notes.** A release with just "bug fixes" is Low;
   a release with "Added support for {feature}" or "Breaking change: {X}"
   carries real competitive signal.

For new repos:

1. **Recency.** Created within the run window (last 24h by default).
2. **Not a fork.** Forked repos appear in the org's list but are usually
   not original work. The API response includes `fork: true` — skip those.
3. **Non-trivial.** A repo with only a README or a `.gitignore` is a
   placeholder. Look for repos with >1 file or a meaningful description.

## 5. URL canonicalization

GitHub URLs are already stable:

```
https://github.com/{org}/{repo}/releases/tag/{tag_name}   # release
https://github.com/{org}/{repo}                           # new repo
```

Apply standard rules: lowercase scheme + host, drop trailing slash, drop
fragments. GitHub URLs don't typically have tracking params.

## 6. Content hashing

For releases:

```
content = repo_full_name + "\n" + tag_name + "\n" + release_title + "\n" + release_body
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

For new repos:

```
content = repo_full_name + "\n" + description_or_empty
content_hash = sha256(content.encode("utf-8")).hexdigest()
```

## 7. Common pitfalls

- **Monorepo releases.** Some orgs use a single repo with per-package
  releases (e.g., `org/sdk` releasing `python-v1.2` and `node-v3.4`
  separately). Each release is a distinct finding.
- **Bot-generated releases.** CI/CD pipelines may create dozens of releases
  per day for nightly builds or snapshot versions. Filter by tag pattern:
  if the tag contains `nightly`, `snapshot`, `dev`, or `canary`, skip it
  unless it's the only activity.
- **Archived repos.** An archived repo still shows up in the org's repo
  list. The API response includes `archived: true` — skip these.
- **GitHub rate limits.** Authenticated: 5,000 req/hr. Budget 5–10 requests
  per competitor (repo list + a few release feeds). Atom feeds don't count
  against the limit — prefer them over the API for release monitoring.
- **Private repos.** Your token only sees public repos unless the deployer
  has org-level access. For competitive intelligence, public repos are the
  only relevant scope — you wouldn't have access to a competitor's private
  repos anyway.
