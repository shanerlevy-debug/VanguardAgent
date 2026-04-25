---
name: overriding-scoring
description: Optional per-deployer scoring adjustments. Load this skill alongside `scoring-findings` when it exists and contains rules. It overrides or supplements the default scoring rubric with deployer-specific rules like "always score security incidents High" or "downweight pricing changes to Low." If this skill is empty or contains only this documentation, ignore it.
---

# overriding-scoring

This is an optional skill for deployer-specific scoring overrides. If you
don't need custom scoring rules, leave this file as-is — the agent will
see the description, check the body, find no rules, and move on.

## When to use this

Add rules here when the default `scoring-findings` rubric doesn't match
your needs and you don't want to fork the core skill. Common scenarios:

- A category that's always High for your company (e.g., "Security/Incidents
  are always High because we're in a regulated industry")
- A category that's always Low (e.g., "Hiring is always Low unless it's
  C-level")
- A competitor that should be scored more aggressively (e.g., "Any finding
  about Competitor X is at least Medium")
- A temporary boost (e.g., "For the next 30 days, anything about
  Competitor Y's pricing is High — we're in active price negotiations")

## Format

Write rules as clear, imperative statements. The agent reads them literally.

**Example rules:**

```
1. Security/Incidents findings are always High, regardless of source or recency.
2. Hiring findings are always Low unless the title mentions VP, C-suite, or "head of".
3. Any finding about Competitor X is at least Medium, even if the category would default to Low.
4. Pricing findings from SEC filings are High (not the default Medium for SEC source baseline).
```

## Your rules

_Add your scoring overrides below. Delete the placeholder text._

No custom scoring rules configured. The default rubric in `scoring-findings`
applies to all findings.

## Cross-references

- `scoring-findings` — the default rubric this skill overrides
- `vanguard.yaml` → `scoring.high_keywords` and `scoring.source_baseline` — the
  config-level scoring controls; this skill is for rules that can't be
  expressed as keywords or source baselines
