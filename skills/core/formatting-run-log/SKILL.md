---
name: formatting-run-log
description: Defines the end-of-run summary schema that the agent emits after every competitive-intel cycle. Use this skill at the end of every run to construct the `RunSummary` dict that `posting-to-slack` § "run summary" consumes. The summary is posted even when no new findings are recorded, so the Slack channel never goes silent.
---

# formatting-run-log

At the end of every run — regardless of how many findings were recorded —
the agent must post a run summary. This skill defines the dict shape and
the rules for populating it.

## The `RunSummary` dict

```python
{
    "new_findings_count": 3,            # int, >= 0. Posted findings (posted=true).
    "duplicates_skipped": 12,           # int, >= 0. Memory-dedupe hits.
    "competitors": ["OpenAI", "Mistral AI"],  # list[str]. Competitors scanned.
    "run_time_utc": "2026-04-24T09:00:00Z",   # ISO 8601 UTC.
    "notes": "SEC source unavailable — EDGAR returned 503.",  # str | None
}
```

### Field rules

| Field | Type | Required | Description |
|---|---|---|---|
| `new_findings_count` | int | Yes | Count of findings where `posted == true` from `scoring-findings`. Does NOT include suppressed findings. |
| `duplicates_skipped` | int | Yes | Count of candidate items where the `processing-sources` memory check returned a hit. Indicates dedup is working. |
| `competitors` | list[str] | Yes | Canonical names of all competitors processed this run, whether or not they had findings. Must match the system prompt's competitor list exactly. |
| `run_time_utc` | ISO 8601 str | Yes | Timestamp of the run's start (when the kickoff message arrived). Used in the summary header. |
| `notes` | str or None | No | Free-form text for unusual conditions. Keep under 280 characters. Use for: source failures, unexpectedly high/low finding counts, partial runs, errors encountered. |

### When to set `notes`

Set `notes` when something unusual happened:

- A source returned errors ("SEC EDGAR returned 503 for 2 of 3 competitors")
- The run was cut short by timeout
- Zero findings across all competitors (likely a source issue, not a quiet news day)
- An unusually high count that may indicate a duplicate-detection miss
- A Slack post failed for a specific finding ("Slack `not_in_channel` for #vanguard-funding override; finding recorded but not posted")

Leave `notes` as `None` for normal runs where everything worked as expected.

## Posting rules

1. **Always post.** Even when `new_findings_count == 0` and
   `duplicates_skipped == 0`. A silent channel makes the deployer wonder
   if the agent is broken. A "0 new findings, 0 duplicates" summary
   confirms it ran and found nothing.

2. **Post to the default channel.** Not to category-specific override
   channels. The run summary is operational metadata, not a finding.

3. **Post last.** The run summary is the final message of the run, after
   all individual findings and the low-priority roundup (if any) have
   been posted.

4. **Use the run-summary Block Kit template** in `posting-to-slack`
   § "run summary" — different shape from a finding.

## Cross-references

- `posting-to-slack` — § "run summary" renders this dict
- `scoring-findings` — provides the finding counts (count of `posted == true`)
- `processing-sources` — provides the duplicate count
- system prompt — competitor list
