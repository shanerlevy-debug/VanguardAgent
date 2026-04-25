# 04 — Fill the company context skill

This is the single highest-leverage task in the entire setup. A
well-filled context skill produces output that sounds like a competent
analyst on your team wrote it. An empty one produces generic AI output
that you'll get tired of within a week.

Plan to spend 60 minutes here. Don't skim.

## 1. Copy the template to your slug

If your `company.slug` in `vanguard.yaml` is `acme-wines`, then:

```bash
# Bash / Git Bash
cp -r skills/custom/understanding-TEMPLATE skills/custom/understanding-acme-wines
```

```powershell
# PowerShell
Copy-Item -Recurse skills/custom/understanding-TEMPLATE skills/custom/understanding-acme-wines
```

> ⚠️ **Don't edit `understanding-TEMPLATE`.** Leave it untouched as a
> reference. Edits go in your **copy** (`understanding-acme-wines/SKILL.md`).
> The deploy script intentionally skips `understanding-TEMPLATE` when
> uploading.

## 2. Update the frontmatter

Open `skills/custom/understanding-{your-slug}/SKILL.md`.

The first ~5 lines look like this (template values shown):

```yaml
---
name: understanding-TEMPLATE
description: "[TEMPLATE — DO NOT UPLOAD AS-IS] Company context skill template..."
---
```

Replace with your skill's actual name and a real description:

```yaml
---
name: understanding-acme-wines
description: "Company context for Acme Wines — competitor priorities, voice, anti-priorities, and noise patterns. Loaded by scoring-findings and writing-why-it-matters before any scoring or contextualization. Edit this file to tune what the agent treats as important."
---
```

The `name:` field **must equal** the directory name (and must equal
`company.context_skill_name` in `vanguard.yaml`).

## 3. Fill in each of the seven sections

The template has seven numbered sections. Read each section's "Example"
and "What good looks like" callouts before writing your own content.

### Section 1: Who we are

3–5 sentences. What does your company do? Who are your customers? What
market segment? What's your revenue model?

This frames every finding. A B2B-SaaS company cares about different signals
than a consumer brand — the agent uses this paragraph to know which lens
to apply.

### Section 2: What we track competitors for

Why are you running this? What decisions does the output feed?

"To stay informed" is not an answer. "To inform our quarterly pricing
review and give the sales team competitive talking points" is.

### Section 3: Priorities

2–5 specific topics that should always score Medium or High. Each priority
should name a concrete competitive axis the agent can recognize:

> Bad: "Important strategic developments"
> Good: "Pricing changes on enterprise tiers — pricing wars compress our
> margins and trigger sales enablement work"

### Section 4: Anti-priorities

Topics to suppress or always-Low. Hiring announcements? Conference talk
news? Vanity metrics?

If you only fill in one section, fill in this one. The biggest cause of
"the agent is too noisy" complaints is missing anti-priorities.

### Section 5: Voice and style

How should `summary` and `why_it_matters` read? Terse? Hedged?
First-person plural? No marketing-speak?

The template has good defaults. Adjust if your company has a strong
internal voice.

### Section 6: Known noise patterns

Specific recurring items that look like findings but aren't. The agent
filters these faster when you name them. Examples:

- Republished press releases across 5+ outlets
- Year-in-review listicles that mention you among 30 others
- Sponsored content disguised as news

### Section 7: Competitor-specific notes (optional)

Per-competitor context that doesn't fit elsewhere. Example:

> **Kendall-Jackson:** Our most direct competitor in the $20–40 segment.
> Anything they ship in the rosé category is automatically Medium even if
> the default rubric says Low.

Skip this section if you don't need it.

## 4. Re-run the dry-run

```bash
python scripts/deploy.py --dry-run
```

Now you should see:

```
[1/8] Validating config...
  ok

skills to upload: 8
  - ...
  - understanding-acme-wines
  - ...
```

If you get `ERROR: skills/custom/understanding-acme-wines/SKILL.md
frontmatter 'name:' is 'understanding-TEMPLATE'`, you forgot step 2 —
update the frontmatter `name` to match your slug.

## 5. (Optional but recommended) Have a colleague review

Before deploying, have someone on your strategy/marketing team read your
`understanding-{slug}/SKILL.md`. They'll catch missing priorities you
forgot to name. The cost is 15 minutes; the payoff is months of better
output.

## What good looks like, end to end

Here's an excerpt from a good context skill (anonymized):

```markdown
## 3. Priorities

1. **Pricing changes on enterprise tiers.** Anything indicating a competitor
   has raised, lowered, or restructured pricing for $50K+ ARR customers.
   This is our most direct competitive axis — pricing wars compress our
   margins.

2. **Enterprise customer wins in financial services.** When a competitor
   announces a Goldman Sachs / JPMorgan / BlackRock-tier customer, our
   sales team needs to know within hours so they can adjust active deals.

3. **Acquisition activity.** Either side of M&A. We track multiple
   competitors who are likely tuck-in acquisition targets; an acquisition
   changes our positioning toward that company overnight.

## 4. Anti-priorities

- **Hiring announcements.** Including senior hires, unless they're at the
  CEO/CFO/CRO level. We don't compete for talent in any consequential way.
- **Conference keynote announcements.** "Our CEO will speak at" is not
  intel. The talk content is.
- **AI/cloud platform partnerships.** Every B2B SaaS company has these now.
  Score Low and roundup unless the partnership names a marquee anchor
  customer.
```

Versus what bad looks like:

```markdown
## 3. Priorities

1. Important news about competitors.
2. Big announcements.
3. Anything strategic.
```

The first is actionable; the second has zero discrimination power and
will produce noise.

## How updates work later

Whenever your strategic priorities shift, edit
`skills/custom/understanding-{slug}/SKILL.md` and re-upload just that
skill:

```bash
python scripts/deploy.py --skill understanding-{slug}
```

This re-uploads the skill, creates a new version, and re-pins the agent
to the latest version. Takes ~30 seconds. Existing memory is untouched.

## Next step

[`05-deploy.md`](05-deploy.md) — actually deploy.
