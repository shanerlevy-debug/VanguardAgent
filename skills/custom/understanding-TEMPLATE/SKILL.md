---
name: understanding-TEMPLATE
description: "[TEMPLATE — DO NOT UPLOAD AS-IS] Company context skill template. Copy this directory to understanding-{your-company}, fill in every section, then update company.context_skill_name in vanguard.yaml to match. This is the single highest-leverage artifact in the system — a well-filled template produces output that sounds like a competent analyst on your team wrote it."
---

# understanding-{your-company}

> **This is a template.** Do not upload this skill as-is. Copy the entire
> `understanding-TEMPLATE/` directory to `understanding-{your-company}/`
> (e.g., `understanding-acme-corp/`), then edit this file.
>
> When done, update `company.context_skill_name` in `vanguard.yaml` to match
> the directory name, and run `python scripts/deploy.py --skill understanding-{your-company}`.

## FAQ — read before filling this out

**How long should this be?**
300–600 lines is typical. Shorter is fine if your context is simple. Don't
pad — the agent reads every line at token cost.

**Who should write it?**
Someone who understands your competitive positioning: a product marketer,
strategy lead, or senior PM. The person filling this out doesn't need to be
technical — they need to know what your company cares about.

**When should I update it?**
Whenever your strategic priorities shift, a new competitor enters the picture,
or the agent's output consistently misses something you care about. Run
`python scripts/deploy.py --skill understanding-{your-company}` after edits.

**What happens if I leave sections empty?**
The agent falls back to generic behavior for that section. Output quality
degrades proportionally — an empty "Priorities" section means every finding
gets equal weight. An empty "Voice" section means output tone is generic AI.

---

## 1. Who we are

_Describe your company in 3–5 sentences. What do you do? What's your core
product? Who are your customers? What market segment are you in?_

_The agent uses this to frame findings from a specific perspective. A B2B
SaaS company cares about different signals than a consumer hardware company._

**Example (for a hypothetical AI tooling company):**

> We build a developer-facing platform for agentic AI applications. Our
> customers are engineering teams at mid-to-large enterprises who are building
> AI-powered workflows. We compete primarily on developer experience,
> reliability, and pricing. Revenue is API-based (per-token).

**What good looks like:** Concrete, specific, names your actual market
position. Mentions customer type and revenue model.

**What bad looks like:** "We are an innovative technology company disrupting
the industry." Too vague for the agent to do anything with.

YOUR CONTENT HERE:

> [Replace this block with your company description]

---

## 2. What we track competitors for

_Why are you running competitive intelligence? What decisions does this
feed into? Be specific — "stay informed" is not a reason._

**Example:**

> We run competitive intel to support three functions:
> 1. Product roadmap — knowing when competitors ship features that overlap
>    or compete with our planned work.
> 2. Sales enablement — giving the sales team ammunition when prospects
>    compare us to alternatives.
> 3. Pricing strategy — tracking competitor pricing moves so we can respond
>    proactively rather than reactively.

YOUR CONTENT HERE:

> [Replace this block]

---

## 3. Priorities (what ranks higher attention)

_List 2–5 specific topics that should be scored Medium or High even when the
default rubric would say Low. These are the things your team drops everything
to read about._

_Each priority should name a specific competitive axis, not a vague category._

**Example:**

> 1. **Agentic AI tooling moves.** New primitives, frameworks, or tools that
>    expand what's possible to build on top of their models. This is our most
>    direct competitive axis.
> 2. **Pricing moves.** Any meaningful change in API pricing, especially
>    model-tier or per-token pricing. Pricing wars compress our margins.
> 3. **Enterprise deals.** Named customer wins in our target segments
>    (financial services, healthcare, government). Tells us where competitors
>    are gaining traction.

**What good looks like:** Specific enough that the agent can look at a finding
and decide "yes, this matches priority #2." Each priority names a concrete
signal pattern.

**What bad looks like:** "Important strategic developments." Every finding
is an "important strategic development" — this gives the agent no
discrimination power.

YOUR CONTENT HERE:

> [Replace this block with 2–5 numbered priorities]

---

## 4. Anti-priorities (what we explicitly don't care about)

_List topics that should always be scored Low or suppressed, even when the
headline sounds dramatic. These are your noise filters._

**Example:**

> - **Hiring announcements.** Job postings, "we're hiring!" social media,
>   headcount milestones. Unless it's a named C-level move (which falls
>   under Leadership Changes), treat as Low and probably suppress.
> - **Conference talk announcements.** "{Competitor} CEO to keynote at
>   {Conference}" is not competitive intelligence. The talk content
>   afterward might be.
> - **Vanity metrics.** "We reached 10 million users" press releases with
>   no detail on revenue, retention, or segment.

YOUR CONTENT HERE:

> [Replace this block with anti-priorities, or write "None — score everything normally"]

---

## 5. Voice and style

_How should the agent write `summary` and `why_it_matters` fields? This
controls the tone of every Slack post._

**Example:**

> - **Terse.** 2–3 sentences for summary, 1–2 for why-it-matters. No
>   throat-clearing.
> - **No hedging.** "Competitor cut prices" — not "Competitor appears to
>   have cut prices." If the source is credible, state it.
> - **No marketing-speak.** Don't say "exciting," "game-changing,"
>   "revolutionary." Neutral factual tone.
> - **First-person plural when framing matters.** "We should watch…" is
>   fine in why-it-matters. "One should consider…" is not.
> - **Dollar amounts as-is.** "$50M", not "fifty million dollars."

YOUR CONTENT HERE:

> [Replace this block, or keep the defaults above if they work for you]

---

## 6. Known noise patterns

_Specific recurring items that look like findings but aren't. The agent
learns to filter these faster when you name them explicitly._

**Example:**

> - Republished press releases across 5+ outlets with no added analysis
> - CEO interview soundbites where the content is vague vision-talk
> - Year-in-review listicle content that mentions the competitor among 30 others
> - Sponsored content or advertorials disguised as news articles

YOUR CONTENT HERE:

> [Replace this block, or write "None known yet — will add as patterns emerge"]

---

## 7. Competitor-specific notes (optional)

_Per-competitor context that doesn't fit into the general sections above.
Useful when different competitors warrant different handling._

**Example:**

> **Competitor A:** Our most direct competitor. Anything they ship in the
> agentic tooling space is automatically High importance. Their blog is the
> most reliable source — press coverage usually lags 24h behind.
>
> **Competitor B:** Indirect competitor. Only care about them when they enter
> our core market (enterprise API tooling). Consumer product announcements
> are noise for us.

YOUR CONTENT HERE:

> [Replace this block, or omit this section entirely if not needed]

---

## Cross-references

- `scoring-findings` references this skill for importance calibration
- `writing-why-it-matters` references this skill for tone and framing
- `vanguard.yaml` defines the competitor list and scoring keywords
