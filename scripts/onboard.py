"""
onboard.py — interactive onboarding wizard for VanguardCMA.

Walks a fresh user through:
  1. Pre-flight — confirm prerequisites are in place
  2. Interview — collect company, Slack, and competitor info
  3. Write configs — vanguard.yaml, secrets.env, and a stubbed
     understanding-{slug} skill copied from the template
  4. Next steps — what the user does next (fill in context skill, deploy)

Does NOT run the deploy itself — that's a separate, more error-prone step
the user runs deliberately via ./deploy.sh.

Re-runs are refused if vanguard.yaml already exists, to avoid clobbering
work. Delete it first, or pass --overwrite.

Usage:
    python scripts/onboard.py
    python scripts/onboard.py --overwrite     # replace existing files
    python scripts/onboard.py --no-validate   # skip live API calls
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VANGUARD_YAML = ROOT / "vanguard.yaml"
SECRETS_ENV = ROOT / "secrets.env"
SKILLS_CUSTOM = ROOT / "skills" / "custom"
TEMPLATE_DIR = SKILLS_CUSTOM / "understanding-TEMPLATE"

# ---------- pretty-printing ------------------------------------------------

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_OK = "\033[32m"
C_WARN = "\033[33m"
C_ERR = "\033[31m"
C_CYAN = "\033[36m"


def heading(text: str) -> None:
    print()
    print(f"{C_BOLD}{C_CYAN}━━━ {text} ━━━{C_RESET}")


def ok(text: str) -> None:
    print(f"  {C_OK}✓{C_RESET} {text}")


def warn(text: str) -> None:
    print(f"  {C_WARN}!{C_RESET} {text}")


def err(text: str) -> None:
    print(f"  {C_ERR}✗{C_RESET} {text}")


def info(text: str) -> None:
    print(f"  {C_DIM}{text}{C_RESET}")


# ---------- input helpers --------------------------------------------------


def ask(prompt: str, default: str | None = None,
        validate=None, secret: bool = False) -> str:
    """
    Prompt with optional default + validator. Re-asks on validation fail.

    Semantics:
      default=None   → field is required; blank input is rejected.
      default=""     → blank input is allowed and returns "".
      default="abc"  → blank input returns "abc"; non-blank returns input.
    """
    has_default = default is not None
    suffix = f" [{default}]" if default else ""  # don't render "[]"
    while True:
        try:
            if secret:
                import getpass
                raw = getpass.getpass(f"  {prompt}{suffix}: ")
            else:
                raw = input(f"  {prompt}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)
        if raw:
            value = raw
        elif has_default:
            value = default
        else:
            err("required.")
            continue
        if validate:
            error = validate(value)
            if error:
                err(error)
                continue
        return value


def ask_yn(prompt: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        try:
            raw = input(f"  {prompt} [{suffix}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        err("answer y or n.")


# ---------- validators -----------------------------------------------------


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def v_slug(s: str) -> str | None:
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s):
        return "lowercase letters/digits, hyphens between words. Example: acme-wines"
    return None


def v_anthropic_key(s: str) -> str | None:
    if not s.startswith("sk-ant-"):
        return "must start with 'sk-ant-'."
    if len(s) < 20:
        return "looks too short — paste the full key."
    return None


def v_slack_bot_token(s: str) -> str | None:
    if not s.startswith("xoxb-"):
        return "must be the bot token starting with 'xoxb-' (NOT the 'xoxp-' user token)."
    if len(s) < 20:
        return "looks too short — paste the full token."
    return None


def v_channel_id(s: str) -> str | None:
    if not re.fullmatch(r"C[A-Z0-9]{8,}", s):
        return "Slack channel ID — starts with 'C', uppercase + digits. See docs/02-create-slack-bot.md step 6."
    return None


def v_model(s: str) -> str | None:
    if s not in ("claude-opus-4-7", "claude-sonnet-4-6"):
        return "use 'claude-opus-4-7' or 'claude-sonnet-4-6'."
    return None


# ---------- preflight ------------------------------------------------------


def preflight() -> bool:
    heading("Pre-flight: confirming you have what you need")

    # Auto: Python version
    py_ok = sys.version_info >= (3, 12)
    if py_ok:
        ok(f"Python {sys.version_info.major}.{sys.version_info.minor} (need 3.12+)")
    else:
        err(f"Python {sys.version_info.major}.{sys.version_info.minor} — need 3.12 or newer.")
        info("See docs/01-prerequisites.md.")

    # Auto: are we in the project root? Check for invariant project files
    # (don't include understanding-TEMPLATE here — the user may have renamed
    # or deleted it, which is fine and shouldn't fail preflight).
    in_root = (
        (ROOT / "scripts" / "deploy.py").exists()
        and (ROOT / "agent" / "system_prompt.md").exists()
        and (ROOT / "skills").is_dir()
    )
    if in_root:
        ok("Running from VanguardCMA project root.")
    else:
        err("This script must be run from the VanguardCMA project root.")
        info(f"  Got ROOT = {ROOT}")

    if not py_ok or not in_root:
        return False

    # Interactive: things we can't auto-detect
    print()
    info("The next few questions confirm prerequisites we can't auto-check.")
    info("If you answer 'no' to any, we'll point you at the right doc and stop.")
    print()

    checks = [
        (
            "anthropic_key",
            "Do you have an Anthropic API key (sk-ant-...)?",
            "Get one at https://console.anthropic.com/settings/keys. See docs/01-prerequisites.md §1.",
        ),
        (
            "memory_beta",
            "Have you enabled Memory (research preview) at https://console.anthropic.com → Settings → Beta features?",
            "Memory is required for VanguardCMA persistence. Request access on that page; wait for approval. See docs/01-prerequisites.md §1.",
        ),
        (
            "slack_admin",
            "Do you have admin or app-install rights in your Slack workspace?",
            "You need to install a bot and create a channel. Walk an admin through docs/02-create-slack-bot.md if not.",
        ),
        (
            "slack_bot",
            "Have you created the Slack app and copied the bot token (xoxb-...) and channel ID (C09...)?",
            "Walk through docs/02-create-slack-bot.md before continuing.",
        ),
        (
            "claude_code",
            "Do you have Claude Code installed with /schedule available? (Optional now — only needed for cron in step 7.)",
            "You can skip this for now and set up scheduling later. See docs/07-schedule-via-claude-code.md.",
        ),
    ]

    failures = []
    for key, q, hint in checks:
        # Claude Code is optional — different default
        default = True if key != "claude_code" else False
        answer = ask_yn(q, default=default)
        if answer:
            ok("ok")
        else:
            warn(hint)
            if key != "claude_code":  # claude_code can be deferred
                failures.append(key)

    if failures:
        print()
        err(f"Missing: {', '.join(failures)}.")
        info("Resolve those and re-run this script.")
        return False

    print()
    ok("All required prerequisites met.")
    return True


# ---------- interview ------------------------------------------------------


def interview() -> dict:
    heading("Interview: collecting your config")

    # Company
    print()
    info("First — your company.")
    company_name = ask("Company display name", validate=lambda s: None if len(s) >= 2 else "too short.")
    suggested_slug = slugify(company_name)
    company_slug = ask("Slug (lowercase, hyphens)", default=suggested_slug, validate=v_slug)
    context_skill_name = f"understanding-{company_slug}"

    # Agent / model
    print()
    info("Model choice. Opus is best quality; Sonnet is ~5x cheaper with slightly less nuance.")
    model = ask(
        "Model (claude-opus-4-7 / claude-sonnet-4-6)",
        default="claude-opus-4-7",
        validate=v_model,
    )

    # Anthropic API key
    print()
    info("Your Anthropic API key. Pasted invisibly (no echo).")
    anthropic_key = ask("Anthropic API key", validate=v_anthropic_key, secret=True)

    # Slack
    print()
    info("Slack credentials.")
    slack_token = ask("Slack bot token (xoxb-...)", validate=v_slack_bot_token, secret=True)
    slack_channel = ask("Slack channel ID (C09...)", validate=v_channel_id)

    # Competitors
    print()
    info("Add at least one competitor. The agent ONLY tracks competitors you list here.")
    info("More can be added later by editing vanguard.yaml.")
    competitors = []
    while True:
        idx = len(competitors) + 1
        print()
        if idx > 1:
            cont = ask_yn(f"Add another competitor? (you have {len(competitors)} so far)", default=True)
            if not cont:
                break
        comp_name = ask(
            f"Competitor #{idx} canonical name (e.g. 'Kendall-Jackson')",
            validate=lambda s: None if len(s) >= 2 else "too short.",
        )
        aliases_raw = ask(
            "  Aliases (comma-separated, blank for none)",
            default="",
            validate=lambda s: None,
        )
        aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()]
        sources_raw = ask(
            "  Sources (comma-separated; valid: news,blog,press_release,sec,github,youtube,reddit,job_boards)",
            default="news,blog,press_release",
            validate=lambda s: None if all(
                x.strip() in {"news","blog","press_release","sec","github","youtube","reddit","job_boards"}
                for x in s.split(",")
            ) else "unknown source name.",
        )
        sources = [s.strip() for s in sources_raw.split(",") if s.strip()]
        competitors.append({
            "name": comp_name,
            "aliases": aliases,
            "sources": sources,
        })
        if len(competitors) >= 10:
            warn("10 competitors is plenty. Stopping here.")
            break

    return {
        "company_name": company_name,
        "company_slug": company_slug,
        "context_skill_name": context_skill_name,
        "model": model,
        "anthropic_key": anthropic_key,
        "slack_token": slack_token,
        "slack_channel": slack_channel,
        "competitors": competitors,
    }


# ---------- live validation (optional) -------------------------------------


def validate_live(answers: dict) -> bool:
    """Optionally hit Slack auth.test to confirm the bot token is live."""
    heading("Live validation: confirming credentials work")
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        warn("slack-sdk not installed yet — skipping Slack validation.")
        info("That's fine; deploy.sh will install it and validate then.")
        return True

    try:
        resp = WebClient(token=answers["slack_token"]).auth_test()
        ok(f"Slack token good — bot user '{resp['user']}' in workspace '{resp['team']}'.")
        return True
    except SlackApiError as e:
        err(f"Slack token rejected: {e.response['error']}")
        info("Re-run docs/02-create-slack-bot.md and grab the right xoxb- token.")
        return False
    except Exception as e:
        warn(f"Couldn't reach Slack ({e}); skipping. deploy.sh will validate later.")
        return True


# ---------- writers --------------------------------------------------------


def write_secrets(answers: dict) -> None:
    SECRETS_ENV.write_text(
        textwrap.dedent(f"""\
        # Generated by scripts/onboard.py — DO NOT COMMIT
        ANTHROPIC_API_KEY={answers["anthropic_key"]}
        SLACK_BOT_TOKEN={answers["slack_token"]}
        """),
        encoding="utf-8",
    )
    ok(f"wrote {SECRETS_ENV.relative_to(ROOT)}")


def write_vanguard_yaml(answers: dict) -> None:
    """Render vanguard.yaml. We build the content without textwrap.dedent
    because the multi-line competitors block confuses dedent's common-prefix
    logic — easier and clearer to assemble at column 0."""
    name = answers["company_name"]
    slug = answers["company_slug"]
    ctx = answers["context_skill_name"]

    lines: list[str] = []
    A = lines.append

    A("# =========================================================================")
    A("# vanguard.yaml — orchestration config (you edit this).")
    A("# Generated by scripts/onboard.py. The agent.yaml file is auto-generated")
    A("# by deploy.py from this and is NOT edited by hand.")
    A("# =========================================================================")
    A("")
    A("company:")
    A(f'  name: "{name}"')
    A(f'  slug: "{slug}"')
    A(f'  context_skill_name: "{ctx}"')
    A("")
    A("agent:")
    A(f'  name: "Vanguard — {name}"')
    A(f'  model: "{answers["model"]}"')
    A(f'  description: "Competitive intelligence agent for {name}."')
    A("")
    A("slack:")
    A(f'  default_channel: "{answers["slack_channel"]}"')
    A("  channel_overrides: {}")
    A('  low_priority_strategy: "roundup"')
    A("")
    A("competitors:")
    for c in answers["competitors"]:
        aliases_yaml = "[" + ", ".join(f'"{a}"' for a in c["aliases"]) + "]"
        sources_yaml = "[" + ", ".join(f'"{s}"' for s in c["sources"]) + "]"
        A(f'  - name: "{c["name"]}"')
        A(f'    aliases: {aliases_yaml}')
        A(f'    sources: {sources_yaml}')
    A("")
    A("sources:")
    A("  news:          { enabled: true }")
    A("  blog:          { enabled: true,  feeds: [] }")
    A("  press_release: { enabled: true }")
    A("  sec:           { enabled: false, competitor_ciks: {} }")
    A("  github:        { enabled: false, competitor_orgs: {} }")
    A("  youtube:       { enabled: false, competitor_channels: {} }")
    A("  reddit:        { enabled: false, subreddits: [] }")
    A("  job_boards:    { enabled: false }")
    A("")
    A("scoring:")
    A("  high_keywords:")
    for kw in ["acquires", "acquisition", "layoffs", "raises", "series", "breach", "ceo"]:
        A(f'    - "{kw}"')
    A("  recency_cap_days: 7")
    A("  source_baseline:")
    for src, lvl in [("news", "medium"), ("blog", "medium"), ("press_release", "medium"),
                     ("sec", "high"), ("github", "low"), ("youtube", "low"),
                     ("reddit", "low"), ("job_boards", "low")]:
        A(f'    {src}: "{lvl}"')
    A("")
    A("memory:")
    A(f'  store_name: "vanguard-{slug}"')
    A(f'  description: "Vanguard competitive-intel state for {name}. One file per finding, keyed by competitor and content hash."')
    A("")
    A("environment:")
    A(f'  name: "vanguard-{slug}-prod"')
    A('  networking: "limited"')
    A("  allowed_hosts:")
    for host in ["news.google.com", "www.google.com", "feeds.feedburner.com",
                 "www.businesswire.com", "www.prnewswire.com", "data.sec.gov",
                 "api.github.com", "www.youtube.com", "www.reddit.com"]:
        A(f'    - "{host}"')
    A("")
    A("anthropic:")
    A("  beta_headers:")
    A('    - "managed-agents-2026-04-01"')
    A('    - "managed-agents-2026-04-01-research-preview"')
    A("")

    VANGUARD_YAML.write_text("\n".join(lines), encoding="utf-8")
    ok(f"wrote {VANGUARD_YAML.relative_to(ROOT)}")


MINIMAL_STUB = """---
name: {name}
description: "Company context for {company_name} — competitor priorities, voice, anti-priorities, and noise patterns. Loaded by scoring-findings and writing-why-it-matters before any scoring or contextualization. Edit this file to tune what the agent treats as important."
---

# understanding-{slug}

> Onboarding wrote this stub because skills/custom/understanding-TEMPLATE
> wasn't present. Fill in each section below. See
> docs/04-fill-company-context.md for what each one needs.

## 1. Who we are

> [Describe your company in 3–5 sentences: what you do, your customers,
> your market, your revenue model.]

## 2. What we track competitors for

> [Why are you running competitive intel? What decisions does this output
> feed?]

## 3. Priorities (what ranks higher attention)

> [List 2–5 specific topics that should always score Medium or High.]

## 4. Anti-priorities (what to suppress or always-Low)

> [List specific noise topics — hiring news, conference announcements, etc.]

## 5. Voice and style

> [How should summaries and why-it-matters lines read? Terse? Hedged?
> First-person plural?]

## 6. Known noise patterns

> [Recurring items that look like findings but aren't.]

## 7. Competitor-specific notes (optional)

> [Per-competitor context that doesn't fit elsewhere.]
"""


def find_template_dir() -> Path | None:
    """
    Locate understanding-TEMPLATE for cloning. Prefers the canonical name;
    falls back to any directory under skills/custom/ whose SKILL.md
    frontmatter declares `name: understanding-TEMPLATE` (handles the case
    where the user renamed it for their own deployment).
    """
    if TEMPLATE_DIR.exists() and (TEMPLATE_DIR / "SKILL.md").exists():
        return TEMPLATE_DIR
    if not SKILLS_CUSTOM.exists():
        return None
    for sub in SKILLS_CUSTOM.iterdir():
        if not sub.is_dir():
            continue
        skill_md = sub / "SKILL.md"
        if not skill_md.exists():
            continue
        head = skill_md.read_text(encoding="utf-8")[:400]
        if re.search(r"^name:\s*understanding-TEMPLATE\s*$", head, re.MULTILINE):
            return sub
    return None


def stub_context_skill(answers: dict) -> None:
    """
    Create skills/custom/understanding-{slug}/.

    Preferred path: copy from understanding-TEMPLATE (or any dir with that
    frontmatter name). Fallback: write a minimal stub if no template is
    found on disk.
    """
    target = SKILLS_CUSTOM / answers["context_skill_name"]
    if target.exists():
        warn(f"{target.relative_to(ROOT)} already exists — leaving it alone.")
        return

    template = find_template_dir()
    if template is None:
        # Fallback: write a minimal stub
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text(
            MINIMAL_STUB.format(
                name=answers["context_skill_name"],
                slug=answers["company_slug"],
                company_name=answers["company_name"],
            ),
            encoding="utf-8",
        )
        warn("understanding-TEMPLATE not found on disk — wrote a minimal stub.")
        info(f"Edit {target.relative_to(ROOT)}/SKILL.md to fill in the seven sections.")
        info("See docs/04-fill-company-context.md for what each section needs.")
        return

    shutil.copytree(template, target)
    skill_md = target / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")

    parts = content.split("---", 2)
    if len(parts) < 3:
        warn("template SKILL.md frontmatter didn't parse; you'll need to edit by hand.")
        return
    new_frontmatter = (
        f'\nname: {answers["context_skill_name"]}\n'
        f'description: "Company context for {answers["company_name"]} — competitor priorities, voice, anti-priorities, and noise patterns. Loaded by scoring-findings and writing-why-it-matters before any scoring or contextualization. Edit this file to tune what the agent treats as important."\n'
    )
    new_content = "---" + new_frontmatter + "---" + parts[2]
    skill_md.write_text(new_content, encoding="utf-8")
    src_name = template.name
    ok(f"created {target.relative_to(ROOT)} (copy of {src_name})")


# ---------- main -----------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true",
                    help="Replace existing vanguard.yaml + secrets.env")
    ap.add_argument("--no-validate", action="store_true",
                    help="Skip the live Slack token check")
    args = ap.parse_args()

    if VANGUARD_YAML.exists() and not args.overwrite:
        err(f"{VANGUARD_YAML.relative_to(ROOT)} already exists.")
        info("Delete it (or pass --overwrite) and re-run, or edit it directly.")
        return 1
    if SECRETS_ENV.exists() and not args.overwrite:
        err(f"{SECRETS_ENV.relative_to(ROOT)} already exists.")
        info("Delete it (or pass --overwrite) and re-run.")
        return 1

    print()
    print(f"{C_BOLD}VanguardCMA Onboarding{C_RESET}")
    print(f"{C_DIM}Walks you through the minimum config to deploy. Takes ~5 min.{C_RESET}")

    if not preflight():
        return 1

    answers = interview()

    if not args.no_validate:
        if not validate_live(answers):
            print()
            err("Live validation failed. Fix and re-run.")
            return 1

    heading("Writing files")
    write_secrets(answers)
    write_vanguard_yaml(answers)
    stub_context_skill(answers)

    heading("Next steps")
    print()
    print(f"  {C_BOLD}1. Author your company-context skill (highest leverage step).{C_RESET}")
    print(f"     Open: skills/custom/{answers['context_skill_name']}/SKILL.md")
    print(f"     Fill in the seven sections — see docs/04-fill-company-context.md.")
    print(f"     Plan ~60 minutes. Don't skim.")
    print()
    print(f"  {C_BOLD}2. (Optional) Tune vanguard.yaml.{C_RESET}")
    print(f"     - Add more competitors under `competitors:`")
    print(f"     - Enable additional sources under `sources:` (sec, github, youtube, reddit)")
    print(f"     - Add per-competitor IDs (sec_cik, github_org, youtube_channel)")
    print(f"     - Tune `scoring.high_keywords` for your industry")
    print(f"     - Add channel routing under `slack.channel_overrides`")
    print(f"     See docs/03-configure-vanguard-yaml.md for every field.")
    print()
    print(f"  {C_BOLD}3. Deploy.{C_RESET}")
    print(f"     ./deploy.sh                  (macOS/Linux/Git-Bash)")
    print(f"     .\\deploy.ps1                 (Windows PowerShell)")
    print(f"     The wrapper sets up the venv + installs deps automatically.")
    print()
    print(f"  {C_BOLD}4. First run.{C_RESET}")
    print(f"     ./run_once.sh                  (macOS/Linux/Git-Bash)")
    print(f"     .\\run_once.ps1                 (Windows PowerShell)")
    print(f"     Verify findings appear in your Slack channel.")
    print(f"     See docs/06-first-run.md.")
    print()
    print(f"  {C_BOLD}5. Schedule the daily cron.{C_RESET}")
    print(f"     See docs/07-schedule-via-claude-code.md.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
