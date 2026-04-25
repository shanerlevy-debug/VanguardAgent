---
name: posting-to-slack
description: Posts findings, low-priority roundups, and run summaries to Slack by calling Slack's Web API directly via bash and curl. Use this skill whenever the agent needs to send a message to Slack — there is no Slack MCP server in this deployment. Reads the bot token from the SLACK_BOT_TOKEN environment variable. Includes the exact Block Kit JSON templates for each of the three message types.
---

# posting-to-slack

This skill is what `slack-mcp` used to do, but as instructions instead of
a server. To post anything to Slack, you call `chat.postMessage` directly
with `bash` and `curl`. The bot token is mounted into the session as a
file at `/workspace/.slack-token` — read it once at the start of the
posting phase and reuse the value:

```bash
SLACK_BOT_TOKEN=$(cat /workspace/.slack-token | tr -d '\n\r')
```

There are three message types: **finding** (one per High/Medium item),
**low-priority roundup** (one batch at end of run), and **run summary**
(always last, always posted). Each has its own Block Kit template below.

## Authentication and the call shape

Every call has the same outer shape:

```bash
curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @/tmp/payload.json
```

Write the JSON body to a temp file first (it's faster and easier than
escaping nested JSON on the command line). Slack's response is JSON; check
that `ok` is `true` before continuing:

```bash
RESPONSE=$(curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @/tmp/payload.json)
echo "$RESPONSE" | grep -q '"ok":true' || { echo "Slack post failed: $RESPONSE"; exit 1; }
```

Capture `ts` from the response if you want to thread replies; the POC
doesn't use threading.

If `ok` is `false`, common error codes:

| Slack `error` | What it means | What to do |
|---|---|---|
| `not_in_channel` | Bot wasn't invited to that channel | Note in run summary; don't retry |
| `channel_not_found` | Channel ID is wrong, or bot can't see it | Note in run summary; don't retry |
| `invalid_auth` / `not_authed` | Bot token is wrong or revoked | Abort the run with a clear log line |
| `ratelimited` | Too many calls in a window | Read `Retry-After` header, sleep, retry once |
| `msg_too_long` | Single message > 40k chars | Split, or truncate `summary` |

## Channel selection

For a finding, look up the override first:
1. If the finding's `category` appears in the system-prompt's
   "channel overrides" block, use that channel ID.
2. Otherwise use the system-prompt's default channel ID.

For roundups and run summaries: always the default channel.

Channel IDs (the `C09…` ones), not channel names. Slack's API accepts
both, but IDs survive renames.

## Message type 1: individual finding

Use this for every High and Medium importance finding. One message per
finding.

The `text` field is the fallback notification text (what shows in the
sidebar / push notification). Keep it under 100 characters.

`blocks` is the rich rendering. Three blocks: header, fields, context.

```json
{
  "channel": "C0123456789",
  "text": "[High] OpenAI: GPT-5 pricing cut 50%",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "OpenAI cuts GPT-5 input token price 50% to $0.01 per 1K"
      }
    },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*Competitor:*\nOpenAI" },
        { "type": "mrkdwn", "text": "*Category:*\nPricing" },
        { "type": "mrkdwn", "text": "*Importance:*\n:rotating_light: High" },
        { "type": "mrkdwn", "text": "*Source:*\n<https://openai.com/blog/...|OpenAI Blog>" }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "OpenAI announced updated GPT-5 pricing on their blog. Input tokens drop to $0.01 per 1K from $0.02; output token pricing unchanged. The change is effective immediately and applies to all API customers.\n\n_Pricing moves are a tracked priority. A 50% cut on input is aggressive and likely triggers competitor responses within weeks._"
      }
    },
    {
      "type": "context",
      "elements": [
        { "type": "mrkdwn", "text": "Detected 2026-04-10 14:30 UTC · <https://openai.com/blog/gpt5-pricing-update|Read original>" }
      ]
    }
  ]
}
```

### Importance emojis

- High → `:rotating_light:`
- Medium → `:eyes:`
- Low → `:bookmark_tabs:` (only used in roundups, not individual posts)

### Building the blocks

For a finding dict from `formatting-slack-posts`:

- `header.text.text` → `finding["title"]`, truncated to 150 chars if needed
- `fields[0]` → `*Competitor:*\n{finding["competitor"]}`
- `fields[1]` → `*Category:*\n{finding["category"]}`
- `fields[2]` → `*Importance:*\n{emoji} {finding["importance"]}`
- `fields[3]` → if `source_name` present:
  `*Source:*\n<{canonical_url}|{source_name}>`
  else: `*Source:*\n<{canonical_url}|source>`
- The body section: `summary` paragraph, then a blank line, then
  `_{why_it_matters}_` if `why_it_matters` is non-null. Italicized.
- `context.elements[0].text` → `Detected {detected_at_human} · <{canonical_url}|Read original>`

`detected_at_human` format: `"%Y-%m-%d %H:%M UTC"` from the ISO datetime.

If `why_it_matters` is null (allowed for some Lows in roundups, never for
individual High/Medium), omit the italicized line entirely.

## Message type 2: low-priority roundup

Posted once at the end of the run if `low_priority_strategy` is `roundup`
and there's at least one Low finding. Cap rendered list at 8 items; if
there are more, append "_…and N more omitted_" as the last list item.

```json
{
  "channel": "C0123456789",
  "text": "Low-priority roundup: 5 items",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "Low-priority roundup — 5 items"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "• *OpenAI* (Hiring) — <https://...|Hiring 30 engineers in EU>\n• *Mistral* (Technology Direction) — <https://...|New paper on inference optimization>\n• *Anthropic* (Marketing Positioning) — <https://...|Refreshed homepage>\n• …"
      }
    },
    {
      "type": "context",
      "elements": [
        { "type": "mrkdwn", "text": "These didn't meet the threshold for individual posts. Acknowledge or thumbs-down to tune." }
      ]
    }
  ]
}
```

### Building the bullets

For each Low finding (up to 8):

```
• *{competitor}* ({category}) — <{canonical_url}|{title}>
```

Title truncate to ~80 chars per line so the message stays scannable.

If you have >8 Low findings, the 8th line should be:

```
• _…and {N - 7} more omitted (recorded but not posted)_
```

(Show 7 actual items + the "more" line so the total bullet count is 8.)

## Message type 3: run summary

The last message of every run. Posted even when `new_findings_count == 0`.
Use the `RunSummary` schema from `formatting-run-log`.

```json
{
  "channel": "C0123456789",
  "text": "Vanguard run complete: 3 new, 12 deduped",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "Vanguard run complete"
      }
    },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*New findings:*\n3" },
        { "type": "mrkdwn", "text": "*Duplicates skipped:*\n12" },
        { "type": "mrkdwn", "text": "*Competitors scanned:*\nOpenAI, Mistral AI, Anthropic" },
        { "type": "mrkdwn", "text": "*Run time:*\n2026-04-24 09:00 UTC" }
      ]
    },
    {
      "type": "context",
      "elements": [
        { "type": "mrkdwn", "text": "_Notes: SEC EDGAR returned 503 for 1 of 3 competitors._" }
      ]
    }
  ]
}
```

The `notes` context block is **only included if `notes` is non-null**.
Drop the entire `context` block when there's nothing to note.

The `text` fallback varies with the count:
- `new_findings_count == 0` → `"Vanguard run complete: nothing new"`
- `new_findings_count >= 1` → `"Vanguard run complete: {N} new, {dups} deduped"`

## End-to-end worked example (bash)

For agents who prefer to see the whole flow:

```bash
# 0. (once per run) Read the bot token from the mounted secret file.
SLACK_BOT_TOKEN=$(cat /workspace/.slack-token | tr -d '\n\r')

# 1. Build the JSON in /tmp (heredoc avoids shell quoting hell):
cat > /tmp/finding.json <<'EOF'
{
  "channel": "C0123456789",
  "text": "[High] OpenAI: GPT-5 pricing cut 50%",
  "blocks": [
    {"type":"header","text":{"type":"plain_text","text":"OpenAI cuts GPT-5 input token price 50% to $0.01 per 1K"}},
    {"type":"section","fields":[
      {"type":"mrkdwn","text":"*Competitor:*\nOpenAI"},
      {"type":"mrkdwn","text":"*Category:*\nPricing"},
      {"type":"mrkdwn","text":"*Importance:*\n:rotating_light: High"},
      {"type":"mrkdwn","text":"*Source:*\n<https://openai.com/blog/gpt5-pricing-update|OpenAI Blog>"}
    ]},
    {"type":"section","text":{"type":"mrkdwn","text":"OpenAI announced updated GPT-5 pricing...\n\n_Pricing moves are a tracked priority._"}},
    {"type":"context","elements":[{"type":"mrkdwn","text":"Detected 2026-04-10 14:30 UTC · <https://openai.com/blog/gpt5-pricing-update|Read original>"}]}
  ]
}
EOF

# 2. Post:
RESPONSE=$(curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @/tmp/finding.json)

# 3. Verify:
echo "$RESPONSE" | python3 -c "import sys,json;r=json.load(sys.stdin);assert r['ok'],r" \
  || { echo "FAILED: $RESPONSE"; exit 1; }

# 4. Clean up:
rm /tmp/finding.json
```

Use `python3 -c` for parsing — it's pre-installed in CMA containers and
gives clearer errors than `jq`-style parsing.

## Common mistakes

- **Don't pre-escape Slack mrkdwn.** Slack handles `*bold*` and `_italic_`
  natively. Don't double-escape backslashes or asterisks.
- **Don't post the channel name with a `#`.** Use the channel ID
  (`C0123456789`). Names work but break on rename.
- **Don't omit `text`.** It's required as a fallback. Slack will reject
  messages with only `blocks`.
- **Don't loop without delay.** Slack rate-limits at ~1 msg/sec per
  channel. Sleep 1s between posts in the per-finding loop.
- **Don't put secrets in `text` or `blocks`.** Anything you write here
  goes to Slack permanently and is searchable by every member of the
  workspace.

## Cross-references

- `formatting-slack-posts` — produces the finding dict this skill posts
- `formatting-run-log` — produces the `RunSummary` dict for the
  end-of-run message
- `scoring-findings` — `importance` field drives emoji + post type
- system prompt — has `default_channel`, `channel_overrides`,
  `low_priority_strategy`
