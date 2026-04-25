# 02 — Create the Slack bot

This walks you through making a Slack app, installing it to your
workspace, and getting the **bot user OAuth token** the agent needs to
post messages.

You'll spend ~15 minutes here. The token you get at the end goes into
`secrets.env` later.

## 1. Create the app

1. Go to **https://api.slack.com/apps** and sign in.
2. Click **Create New App** → **From scratch**.
3. **App Name:** `Vanguard` (or whatever your org calls this — the name
   appears as the bot's display name in Slack).
4. **Pick a workspace:** choose your company's Slack workspace.
5. Click **Create App**.

You're now on the app's settings page.

## 2. Add scopes (permissions)

In the left sidebar, click **OAuth & Permissions**.

Scroll to **Bot Token Scopes**. Click **Add an OAuth Scope** and add each
of these (one at a time):

| Scope | Why |
|---|---|
| `chat:write` | Post messages to channels the bot is in |
| `chat:write.public` | Post to public channels without being invited |

Don't add more than these. Least-privilege keeps the blast radius small if
the token ever leaks.

## 3. Install the app

Still on the **OAuth & Permissions** page, scroll up to the top.

Click **Install to <Your Workspace>**.

Slack will show a permission summary. Click **Allow**.

If your workspace requires admin approval, you'll see "Approval requested"
instead — get an admin to approve it from the Slack app management UI.

Once installed, the **OAuth & Permissions** page now shows two tokens:

- **Bot User OAuth Token:** starts with `xoxb-…`. **This is the one
  you need.** Copy it now and store it somewhere temporary (you'll paste
  it into `secrets.env` in step 6).
- **User OAuth Token:** starts with `xoxp-…`. **You do not need this.**
  Don't copy it; don't use it.

> ⚠️ **The `xoxb-` token is a secret.** Treat it like a password.
> Anyone with this token can post to your Slack workspace as the bot.
> Don't paste it into chat, email, or anywhere it might be logged.

## 4. Pick the channel for findings

Decide where Vanguard's posts will land. Recommend a dedicated channel:

- **Public channel** named e.g. `#vanguard-intel` — easy, the bot doesn't
  even need to be invited (because of `chat:write.public`). Recommended.
- **Private channel** e.g. `#vanguard-private` — works, but you must
  explicitly **invite the bot to the channel** (see step 5).

Create the channel in Slack now if it doesn't exist.

## 5. Invite the bot to the channel (private channels only)

In Slack, open the channel.

```
/invite @Vanguard
```

(Use whatever name you gave the app in step 1.)

For public channels with `chat:write.public`, this step is optional but
harmless — invite anyway to make the bot discoverable.

## 6. Get the channel ID

Vanguard posts to channels by ID, not by name. Names can change; IDs
can't.

In Slack:
1. Right-click the channel name in the sidebar → **View channel details**
   (or click the channel name at the top of the conversation).
2. Scroll to the bottom of the **About** tab.
3. The line that reads **Channel ID: `C09XXXXXX`** — copy that ID.
   It always starts with `C`.

## 7. Test the bot can post (optional but recommended)

Quick smoke test from your laptop, before you run the full deploy.

```bash
# Replace the two values with your real ones:
TOKEN="xoxb-XXX..."
CHANNEL="C09XXXXXX"

curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "{\"channel\":\"$CHANNEL\",\"text\":\"Vanguard bot test — please ignore.\"}"
```

(PowerShell users: replace `\` with backtick `` ` `` line continuations,
or just paste it as one line.)

Expected response: `{"ok":true,"channel":"C09…","ts":"..."}`. You should
also see the message appear in Slack.

If you see `{"ok":false,"error":"…"}`:

| `error` | What it means |
|---|---|
| `not_in_channel` | Bot wasn't invited to a private channel — invite it. |
| `channel_not_found` | Channel ID typo, or channel doesn't exist. |
| `invalid_auth` / `not_authed` | Token is wrong or revoked — double-check from the OAuth page. |
| `missing_scope` | You forgot `chat:write` — go back to step 2. |

Fix and re-test until you get `ok: true`.

## 8. Save what you'll need

Make sure you have these two values noted somewhere safe:

- **Bot User OAuth Token:** `xoxb-…`
- **Channel ID:** `C09…`

You'll paste them into `secrets.env` and `vanguard.yaml` respectively in the
next step.

## Token rotation later

If you ever need to rotate the token:

1. On the Slack app page, **OAuth & Permissions** → click **Revoke
   Tokens** at the top, then **Reinstall to Workspace**.
2. Copy the new `xoxb-…` token.
3. Replace the value in `secrets.env`.
4. Re-run `python scripts/deploy.py --force-recreate slack-token`.

The deploy script will upload the new token to Anthropic's Files API and
re-pin the agent. Old token becomes useless on Slack's side as soon as
it's revoked.

## Next step

[`03-configure-vanguard-yaml.md`](03-configure-vanguard-yaml.md) — write your
manifest.
