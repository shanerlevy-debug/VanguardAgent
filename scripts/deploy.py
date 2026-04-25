"""
deploy.py — one-shot Anthropic resource provisioning for VanguardCMA.

Reads vanguard.yaml + secrets.env, then idempotently:
  1. Validates config + verifies the company-context skill exists locally
  2. Validates the Slack bot token via auth.test
  3. Creates (or reuses) the Memory store
  4. Uploads the Slack bot token as a Files API file (token delivery path)
  5. Uploads (or refreshes) every skill in skills/
  6. Creates (or reuses) the Environment
  7. Creates (or updates) the Agent — pinned to current skill versions
  8. Writes resource IDs to .deploy-state.json

Usage:
    python scripts/deploy.py                    # full deploy
    python scripts/deploy.py --skill <name>     # re-upload one skill, re-pin agent
    python scripts/deploy.py --dry-run          # validate config + render prompt only
    python scripts/deploy.py --force-recreate {memory,environment,agent,skills,slack-token,all}

Re-runs are safe — anything already created is reused via .deploy-state.json.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    SKILLS_DIR,
    get_anthropic_client,
    list_skill_dirs,
    load_config,
    load_env,
    load_state,
    render_system_prompt,
    save_state,
    write_agent_manifest,
)


# ---------- step 1: validate ------------------------------------------------


def validate(config: dict) -> None:
    print("[1/8] Validating config...")
    company = config["company"]
    ctx_name = company["context_skill_name"]
    ctx_dir = SKILLS_DIR / "custom" / ctx_name
    if not ctx_dir.exists() or not (ctx_dir / "SKILL.md").exists():
        raise SystemExit(
            f"  ERROR: company.context_skill_name = '{ctx_name}'\n"
            f"  but skills/custom/{ctx_name}/SKILL.md does not exist.\n"
            f"  Copy skills/custom/understanding-TEMPLATE to skills/custom/{ctx_name},\n"
            f"  then edit the SKILL.md to describe your company."
        )
    parts = (ctx_dir / "SKILL.md").read_text(encoding="utf-8").split("---", 2)
    if len(parts) >= 2:
        meta = yaml.safe_load(parts[1])
        if meta.get("name") != ctx_name:
            raise SystemExit(
                f"  ERROR: skills/custom/{ctx_name}/SKILL.md frontmatter `name:` is "
                f"'{meta.get('name')}', should be '{ctx_name}'."
            )

    if not config["competitors"]:
        raise SystemExit("  ERROR: vanguard.yaml has no competitors.")
    chan = config["slack"]["default_channel"]
    if not chan.startswith("C"):
        raise SystemExit(
            f"  ERROR: slack.default_channel = '{chan}'. Must be a channel ID "
            "(starts with 'C'), not a name. See docs/02-create-slack-bot.md."
        )
    print("  ok")


# ---------- step 2: slack token ---------------------------------------------


def validate_slack(slack_token: str) -> None:
    print("[2/8] Validating Slack token via auth.test...")
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    try:
        resp = WebClient(token=slack_token).auth_test()
        print(f"  ok — bot user '{resp['user']}' in workspace '{resp['team']}'")
    except SlackApiError as e:
        raise SystemExit(f"  ERROR: Slack token rejected: {e.response['error']}")


# ---------- step 3: memory store --------------------------------------------


def setup_memory(client, config: dict, state: dict, force: bool) -> str:
    print("[3/8] Setting up memory store...")
    name = config["memory"]["store_name"]
    desc = config["memory"]["description"]

    if not force and state.get("memory_store_id"):
        try:
            ms = client.beta.memory_stores.retrieve(state["memory_store_id"])
            print(f"  reusing existing: {ms.id} ({ms.name})")
            return ms.id
        except Exception as e:
            print(f"  cached id stale ({e}); creating fresh")

    ms = client.beta.memory_stores.create(name=name, description=desc)
    print(f"  created: {ms.id} ({ms.name})")
    return ms.id


# ---------- step 4: slack-token file ----------------------------------------


def upload_slack_token(client, slack_token: str, state: dict, force: bool) -> str:
    """
    CMA sessions don't accept env vars, and environments don't accept secrets.
    The cleanest path to deliver SLACK_BOT_TOKEN to the agent is to upload it
    as a Files API file and mount it at /workspace/.slack-token at session
    creation. The posting-to-slack skill knows to read it from there.
    """
    print("[4/8] Uploading Slack token as a session-mountable file...")

    if not force and state.get("slack_token_file_id"):
        try:
            f = client.beta.files.retrieve_metadata(state["slack_token_file_id"])
            print(f"  reusing existing: {f.id}")
            return f.id
        except Exception as e:
            print(f"  cached id stale ({e}); uploading fresh")

    # Always delete the old one (if present) before uploading new
    if state.get("slack_token_file_id"):
        try:
            client.beta.files.delete(state["slack_token_file_id"])
        except Exception:
            pass

    buf = io.BytesIO(slack_token.encode("utf-8"))
    f = client.beta.files.upload(
        file=("slack-token.txt", buf, "text/plain"),
    )
    print(f"  uploaded: {f.id}")
    return f.id


# ---------- step 5: skills --------------------------------------------------


def _list_existing_skills_by_title(client) -> dict[str, str]:
    """Return {display_title: skill_id} for every skill in the workspace.

    Lets us adopt skills created by a prior partial deploy whose IDs aren't
    in our local state. The Anthropic API rejects skills.create() with a
    duplicate display_title, so we must look these up first.
    """
    by_title: dict[str, str] = {}
    page = client.beta.skills.list(limit=100)
    for sk in page:
        if sk.display_title:
            by_title[sk.display_title] = sk.id
    return by_title


def upload_skills(
    client, state: dict, only_skill: str | None, force: bool
) -> dict[str, str]:
    """
    For each skill dir, upload as a multi-file create (or as a new version
    if it already exists). Returns {skill_name: latest_version}.

    Discovery order for an existing skill:
      1. Local state file (`skills_state[name]["id"]`) — fastest path
      2. Workspace lookup by display_title — handles partial-deploy recovery
      3. Otherwise create fresh
    """
    print("[5/8] Uploading skills...")
    skills_state: dict[str, dict] = state.get("skills", {})
    pins: dict[str, str] = {}

    targets = list_skill_dirs()
    if only_skill:
        targets = [t for t in targets if t.name == only_skill]
        if not targets:
            raise SystemExit(f"  --skill {only_skill}: not found in skills/")

    # Workspace-wide title→id map, lazily fetched on first miss.
    workspace_skills: dict[str, str] | None = None

    for skill_dir in targets:
        skill_name = skill_dir.name

        # Anthropic requires SKILL.md to live inside a top-level folder, not
        # at the root of the multipart upload. Prepend the skill dir name so
        # `SKILL.md` becomes `<skill_name>/SKILL.md`, which the API accepts.
        files = []
        for p in sorted(skill_dir.rglob("*.md")):
            rel = p.relative_to(skill_dir).as_posix()
            arcname = f"{skill_name}/{rel}"
            files.append((arcname, p.read_bytes(), "text/markdown"))

        existing_id = (skills_state.get(skill_name) or {}).get("id")

        # If state has no ID, look in the workspace by display_title.
        if not existing_id:
            if workspace_skills is None:
                workspace_skills = _list_existing_skills_by_title(client)
            existing_id = workspace_skills.get(skill_name)
            if existing_id:
                print(f"  found existing {skill_name} in workspace: {existing_id} (adopting)")

        if existing_id and not force and not only_skill:
            # Reuse: just retrieve to pull latest_version.
            try:
                sk = client.beta.skills.retrieve(existing_id)
                skills_state[skill_name] = {"id": sk.id}
                pins[skill_name] = sk.latest_version
                print(f"  reusing {skill_name}: {sk.id} v{sk.latest_version}")
                continue
            except Exception as e:
                print(f"    retrieve failed for {skill_name} ({e}); will try a new version")

        if existing_id:
            # We have an ID and either force=True, only_skill set, or retrieve failed.
            # Push a new version onto the existing skill.
            try:
                sk = client.beta.skills.versions.create(existing_id, files=files)
                sver = sk.version if hasattr(sk, "version") else sk.latest_version
                skills_state[skill_name] = {"id": existing_id}
                pins[skill_name] = sver
                print(f"  refreshed {skill_name}: {existing_id} → v{sver}")
                continue
            except Exception as e:
                print(f"    versions.create failed for {skill_name} ({e}); falling back to create")

        # No existing skill — create fresh.
        sk = client.beta.skills.create(files=files, display_title=skill_name)
        skills_state[skill_name] = {"id": sk.id}
        pins[skill_name] = sk.latest_version
        print(f"  created {skill_name}: {sk.id} v{sk.latest_version}")

    state["skills"] = skills_state
    return pins


# ---------- step 6: environment ---------------------------------------------


def setup_environment(client, config: dict, state: dict, force: bool) -> str:
    print("[6/8] Setting up environment...")
    env_cfg = config["environment"]
    name = env_cfg["name"]

    if not force and state.get("environment_id"):
        try:
            env = client.beta.environments.retrieve(state["environment_id"])
            print(f"  reusing existing: {env.id} ({env.name})")
            return env.id
        except Exception as e:
            print(f"  cached id stale ({e}); creating fresh")

    networking = env_cfg.get("networking", "limited")
    if networking == "limited":
        hosts = list(env_cfg.get("allowed_hosts") or [])
        if "slack.com" not in hosts:
            hosts.append("slack.com")
        net = {
            "type": "limited",
            "allowed_hosts": hosts,
            "allow_package_managers": True,
        }
    else:
        net = {"type": "unrestricted"}

    env = client.beta.environments.create(
        name=name,
        config={"type": "cloud", "networking": net},
    )
    print(f"  created: {env.id} ({env.name})")
    return env.id


# ---------- step 7: agent ---------------------------------------------------


def setup_agent(
    client, config: dict, state: dict, skill_pins: dict[str, str], force: bool
) -> str:
    print("[7/8] Setting up agent...")
    a_cfg = config["agent"]
    system = render_system_prompt(config)

    skills_payload = []
    for sname, sver in skill_pins.items():
        sid = state["skills"][sname]["id"]
        skills_payload.append({"type": "custom", "skill_id": sid, "version": sver})

    # Try update first if we have a cached id; otherwise create.
    if not force and state.get("agent_id"):
        try:
            existing = client.beta.agents.retrieve(state["agent_id"])
            current_version = existing.version
            agent = client.beta.agents.update(
                state["agent_id"],
                version=current_version,
                model=a_cfg["model"],
                name=a_cfg["name"],
                system=system,
                description=a_cfg.get("description", ""),
                tools=[{"type": "agent_toolset_20260401"}],
                skills=skills_payload,
            )
            print(f"  updated existing: {agent.id} v{agent.version}")
            return agent.id
        except Exception as e:
            print(f"  update failed ({e}); creating fresh")

    agent = client.beta.agents.create(
        name=a_cfg["name"],
        model=a_cfg["model"],
        system=system,
        description=a_cfg.get("description", ""),
        tools=[{"type": "agent_toolset_20260401"}],
        skills=skills_payload,
    )
    print(f"  created: {agent.id} v{agent.version}")
    return agent.id


# ---------- main ------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate config + render the system prompt; no API calls")
    ap.add_argument("--skill", help="Re-upload one skill by name; re-pin agent")
    ap.add_argument(
        "--force-recreate",
        choices=["memory", "environment", "agent", "skills", "slack-token", "all"],
        action="append",
        default=[],
        help="Bypass cache and recreate the named resource (repeatable)",
    )
    args = ap.parse_args()

    load_env()
    config = load_config()
    state = load_state()

    if args.dry_run:
        print("--- dry run ---")
        validate(config)
        rendered = render_system_prompt(config)
        print(f"\nsystem prompt rendered: {len(rendered)} chars, "
              f"{len(rendered.splitlines())} lines")
        print(f"skills to upload: {len(list_skill_dirs())}")
        for s in list_skill_dirs():
            print(f"  - {s.name}")
        return 0

    slack_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not slack_token:
        raise SystemExit("SLACK_BOT_TOKEN missing in secrets.env")

    force = set(args.force_recreate)
    f_all = "all" in force
    f_mem = f_all or "memory" in force
    f_skills = f_all or "skills" in force
    f_env = f_all or "environment" in force
    f_agent = f_all or "agent" in force
    f_token = f_all or "slack-token" in force

    validate(config)
    validate_slack(slack_token)

    client = get_anthropic_client()

    state["memory_store_id"] = setup_memory(client, config, state, f_mem)
    save_state(state)

    state["slack_token_file_id"] = upload_slack_token(client, slack_token, state, f_token)
    save_state(state)

    skill_pins = upload_skills(client, state, args.skill, f_skills)
    save_state(state)

    state["environment_id"] = setup_environment(client, config, state, f_env)
    save_state(state)

    state["agent_id"] = setup_agent(client, config, state, skill_pins, f_agent)
    save_state(state)

    # Materialize the CMA-native agent manifest to agent.yaml so the user
    # can review what was POSTed (and paste it into the console as an
    # alternative path).
    skill_ids = {n: info["id"] for n, info in state["skills"].items()}
    write_agent_manifest(
        config,
        render_system_prompt(config),
        skill_pins,
        skill_ids,
    )
    print(f"  wrote agent.yaml (CMA-native manifest)")

    print("\n[8/8] Saved state to .deploy-state.json\n")
    print("Done. Resource IDs:")
    print(f"  Memory:           {state['memory_store_id']}")
    print(f"  Slack token file: {state['slack_token_file_id']}")
    print(f"  Environment:      {state['environment_id']}")
    print(f"  Agent:            {state['agent_id']}")
    print(f"  Skills:           {len(state['skills'])} uploaded")
    print()
    print("Next: ./run_once.sh    (macOS/Linux/Git-Bash)")
    print("      .\\run_once.ps1   (Windows PowerShell)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
