---
name: writing-why-it-matters
description: Composes the one- or two-sentence `why_it_matters` line that accompanies every scored finding. Use this skill whenever `scoring-findings` produces a finding that will be posted (i.e., not suppressed). The line is what makes a finding actionable to the human reader; without it, the Slack post is just a headline with no context.
---

# writing-why-it-matters

The `why_it_matters` field is what separates a useful competitive-intel post
from a news aggregator. Without it, the reader has to recompute "so what?"
from scratch every time. With it, they get a ready answer they can
accept, reject, or argue with.

Load `understanding-{company}` before writing — the contextualization
has to match the deployer company's voice and priorities.

> **Note:** Replace `{company}` throughout this file with your actual
> company context skill name (the value of `company.context_skill_name`
> in `vanguard.yaml`). For example, if your skill is `understanding-acme-corp`,
> this line becomes `Load understanding-acme-corp before writing`.

## What the line needs to do

In 1–2 sentences, answer:

1. **Why should our team care?** Tie the finding to something the deployer company actually does or watches.
2. **What's the near-term implication, if any?** An action, a watching prompt, a "this confirms / contradicts X."

Either of those on its own is usually enough. Both is fine when the
connection isn't obvious.

## Length and format

- 1 sentence minimum, 2 sentences maximum. Hard cap: ~280 characters.
- Plain prose. No bullet points, no bold, no headers.
- Present tense or near-future where natural.
- Can be `None` for Low findings where honest context is "nothing to do here." Don't invent significance.

## Examples (OpenAI, Pricing category, High)

**Good:**
> Pricing moves are a tracked priority. A 50% cut on input tokens is aggressive and likely triggers competitor responses within weeks — worth briefing sales before next week's quarterly pricing review.

**Also good (shorter):**
> Pricing moves are a tracked priority. This is the steepest cut of the year and almost certainly forces Mistral and Anthropic to respond.

**Bad (too vague):**
> This is an important pricing change.

**Bad (marketing tone):**
> OpenAI's exciting new pricing is a game-changer for the industry!

**Bad (hedged into meaninglessness):**
> It seems this pricing change could potentially be significant depending on how the market responds.

## Examples (Mistral, Product, Medium)

**Good:**
> Mistral shipping agentic tooling primitives directly is exactly the competitive axis we track. Worth inspecting the API surface this week to see how it overlaps with ours.

**Bad:**
> Mistral released a new tool.

## When the right answer is `None`

For findings scored Low — especially ones going into a roundup post — it's
often better to leave `why_it_matters` as `None` than to fabricate
significance. Roundup readers skim; extra text dilutes the signal.

Leave `None` when:
- The finding is factual but routine (one new customer logo from a long list)
- The category is `Hiring` and scored Low per the anti-priority rule
- The only honest "why" is "completeness of tracking"

## Tone anchors

Before writing, internalize `understanding-{company}`'s voice section.
Specifically:

- **Terse, not brusque.** Short sentences are fine; rudeness or sarcasm is not.
- **First-person plural ("our team", "we should watch") is allowed and preferred** when the finding implies an action or priority.
- **No throat-clearing.** Don't start with "This is interesting because…" or "It's worth noting that…". Just start with the point.
- **No adjectives of drama.** "Significant" is acceptable once per week across all findings; "game-changing," "massive," "huge," "stunning" are always wrong.

## Cross-references

- `understanding-{company}` — the company voice and priorities this line must match
- `scoring-findings` — produces the finding; this skill shapes its contextualization
- `formatting-slack-posts` — the field this line ends up in (the finding dict's `why_it_matters` field)
