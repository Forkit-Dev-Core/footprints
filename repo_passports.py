"""Forkit Core agent passports for the AI agent setup of a repository.

A passport here describes "the <tool> setup in <repository>", for example the
Claude Code setup of ~/Projects/app:

    name           <repo>/<tool>                     e.g. app/claude-code
    version        chosen by the user (1.0 or 1.0.0; no "v" prefix)
    creator        the person or team who vouches for the setup
    artifact_hash  fingerprint of the tool's config files (see repos.agent_setups);
                   their text is never stored
    model_id       a provider-reference model passport, e.g. "anthropic-claude":
                   the agent's model runs at the provider, there are no local weights
    tools          the MCP server names the setup configures
    parent_agent_id  the previous passport of the same repo and tool (lineage)

Forkit Core derives the passport ID from name, version, creator and fingerprint,
so the same setup always gets the same ID, and any edit to the agent files gives
a different one. Checking a passport later answers two questions:

    record   is the stored passport unchanged? (Forkit Core's own ID check)
    setup    do the agent files in the repository still match the fingerprint?

Passports are only created for repositories found by the latest repository scan,
and an existing passport is never overwritten.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from forkit.registry import LocalRegistry
from forkit.schemas import AgentPassport, ModelPassport

from repos import AGENT_SETUPS, agent_setups, describe_repository, load_history, resolve_display_path

SOURCE = "footprints-repo-agent"
_VERSION = re.compile(r"^\d{1,4}\.\d{1,4}(\.\d{1,4})?$")
_SLUG = re.compile(r"[^a-z0-9._-]+")

# Model passports that stand for a provider's hosted models. They carry no
# artifact hash: there is nothing local to fingerprint.
PROVIDERS = {
    "anthropic": ("anthropic-claude", "Anthropic", "Claude models, used through Anthropic's API and apps"),
    "github": ("github-copilot-models", "GitHub", "Models served through GitHub Copilot"),
    "google": ("google-gemini", "Google", "Gemini models, used through Google's API"),
    "cursor": ("cursor-models", "Anysphere", "Models served through Cursor"),
    "openai": ("openai-models", "OpenAI", "OpenAI models, used through OpenAI's API"),
    "perplexity": ("perplexity-models", "Perplexity", "Models served through Perplexity"),
    "xai": ("xai-grok", "xAI", "Grok models, used through xAI's API and apps"),
    "unspecified": ("user-configured-model", "Unspecified", "The model is chosen in the agent's own settings"),
}


class PassportRequestError(ValueError):
    def __init__(self, message: str, status: int = 422, **extra):
        super().__init__(message)
        self.status = status
        self.extra = extra


def _registry(registry_root: Path) -> LocalRegistry:
    registry = LocalRegistry(registry_root)
    registry.init()
    return registry


def provider_model(registry: LocalRegistry, provider: str) -> ModelPassport:
    name, creator, description = PROVIDERS.get(provider, PROVIDERS["unspecified"])
    model = ModelPassport(
        name=name, version="1.0", creator={"name": creator}, task_type="text-generation", architecture="other",
        description=description, status="active",
        metadata={"context": {"source": SOURCE, "kind": "provider-reference"}},
    )
    if registry.get_model(model.id) is None:
        registry.register_model(model)
    return model


def next_version(version: str) -> str:
    parts = [int(part) for part in version.split(".")]
    parts[1] += 1
    if len(parts) == 3:
        parts[2] = 0
    return ".".join(str(part) for part in parts)


def _repo_from_latest_scan(history_path: Path, home: Path, path: str) -> Path:
    scans = load_history(history_path)["scans"]
    if not scans:
        raise PassportRequestError("Scan repositories first.", 409)
    if path not in {repo.get("path") for repo in scans[-1].get("repos", [])}:
        raise PassportRequestError("This repository is not in the latest scan. Scan repositories again.", 404)
    return resolve_display_path(path, home)


def _passports_named(registry: LocalRegistry, name: str) -> list:
    return [row for row in registry.list(passport_type="agent") if row.get("name") == name]


def passport_display_name(request: dict):
    """A person's label for the passport, separate from its canonical identity."""
    value = request.get("display_name")
    if value is None:
        return None
    if not isinstance(value, str) or not 0 < len(value.strip()) <= 80 or any(ord(char) < 32 for char in value):
        raise PassportRequestError("Enter a passport name (up to 80 characters on one line).")
    return value.strip()


def create_repo_agent_passport(registry_root: Path, history_path: Path, request: dict, home=None) -> dict:
    home = Path(home) if home is not None else Path.home()
    path, tool = request.get("repo"), request.get("tool")
    version = str(request.get("version") or "").strip()
    creator = str(request.get("creator") or "").strip()
    organization = str(request.get("organization") or "").strip() or None
    display_name = passport_display_name(request)
    if not isinstance(path, str) or tool not in AGENT_SETUPS:
        raise PassportRequestError("Choose a repository and one of its agent setups.")
    if not _VERSION.match(version):
        raise PassportRequestError("Use a version like 1.0 or 1.0.0 (numbers only, no \"v\").")
    if not 0 < len(creator) <= 100 or "\n" in creator or (organization and len(organization) > 100):
        raise PassportRequestError("Enter who vouches for this setup (up to 100 characters).")

    repo = _repo_from_latest_scan(history_path, home, path)
    if not repo.is_dir():
        raise PassportRequestError("The repository is no longer there. Scan repositories again.", 404)
    info = describe_repository(repo, home)
    setup = next((item for item in info["agents"] if item["tool"] == tool), None)
    if setup is None:
        raise PassportRequestError(f"No {AGENT_SETUPS[tool]['label']} files in this repository.", 404)

    registry = _registry(registry_root)
    model = provider_model(registry, setup["provider"])
    repo_slug = _SLUG.sub("-", Path(info["path"]).name.lower()).strip("-") or "repository"
    name = f"{repo_slug}/{tool}"
    previous = _passports_named(registry, name)  # newest first
    servers = [entry["server"] for entry in info["ai"].get("mcp_servers", []) if entry["config"] in setup["files"]]
    passport = AgentPassport(
        name=name, version=version, creator={"name": creator, "organization": organization},
        model_id=model.id, task_type="code-assistant", architecture="Tool-Use", role="assistant",
        artifact_hash=setup["fingerprint"], tools=[{"name": server} for server in servers],
        parent_agent_id=previous[0]["id"] if previous else None,
        deployment_env="local", status="active",
        description=f"{setup['label']} setup in {info['path']}",
        metadata={"context": {"source": SOURCE, "repo_path": info["path"], "repo_origin": info.get("origin"),
                              "tool": tool, "tool_label": setup["label"], "files": setup["files"],
                              "display_name": display_name}},
    )

    existing = registry.get_agent(passport.id)
    if existing is not None:
        return {"status": "already-registered", "passport": existing.to_dict(),
                "check": registry.verify_passport(passport.id)}
    taken = [row for row in previous if row.get("version") == version]
    if taken:
        raise PassportRequestError(
            f"Version {version} already has a passport for a different setup. "
            f"Use a new version, e.g. {next_version(version)}.", 409, suggested_version=next_version(version))
    registry.register_agent(passport)
    return {"status": "registered", "passport": passport.to_dict(), "check": registry.verify_passport(passport.id)}


def _setup_state(context: dict, artifact_hash, home: Path) -> str:
    repo = resolve_display_path(str(context.get("repo_path") or ""), home)
    if not context.get("repo_path") or not repo.is_dir() or not (repo / ".git").exists():
        return "repo-missing"
    current = next((setup for setup in agent_setups(repo) if setup["tool"] == context.get("tool")), None)
    if current is None:
        return "files-removed"
    return "unchanged" if current["fingerprint"] == artifact_hash else "changed"


def list_passports(registry_root: Path, home=None, platform=None, tool_state_options=None) -> dict:
    """Every passport in the registry, with its record check, and the setup or install check."""
    from tool_passports import SOURCE as TOOL_SOURCE, installation_summary, tool_state  # avoids a circular import

    home = Path(home) if home is not None else Path.home()
    platform = platform or sys.platform
    registry = _registry(registry_root)
    passports = []
    for row in registry.list():
        stored = registry.get(row["id"])
        if stored is None:
            continue
        data = stored.to_dict()
        check = registry.verify_passport(row["id"])
        context = (data.get("metadata") or {}).get("context") or {}
        item = {
            "id": data["id"], "type": data.get("passport_type"), "name": data["name"], "version": data["version"],
            "creator": (data.get("creator") or {}).get("name"),
            "organization": (data.get("creator") or {}).get("organization"),
            "created_at": data.get("created_at"), "description": data.get("description"),
            "record": "intact" if check.get("valid") else check.get("reason", "invalid"),
            "kind": "model", "display_name": context.get("display_name"),
        }
        if context.get("source") == SOURCE and data.get("passport_type") == "agent":
            item.update(kind="repo-agent", repo=context.get("repo_path"), tool=context.get("tool"),
                        tool_label=context.get("tool_label"), files=context.get("files", []),
                        tools=[tool.get("name") for tool in data.get("tools") or []],
                        parent=data.get("parent_agent_id"),
                        setup=_setup_state(context, data.get("artifact_hash"), home),
                        suggested_version=next_version(data["version"]) if _VERSION.match(data["version"]) else None)
        elif context.get("source") == TOOL_SOURCE and data.get("passport_type") == "agent":
            item.update(kind="device-tool", finding=context.get("finding"), label=context.get("label"),
                        installation=installation_summary(context), surface=data["name"].split("/", 1)[-1],
                        installation_kind=context.get("kind"),
                        creator_source=context.get("creator_source"), parent=data.get("parent_agent_id"),
                        fingerprinted=context.get("fingerprinted", []),
                        request={key: context.get(key) for key in ("finding", "label", "tool_kind", "kind",
                                                                  "value", "editor", "browser", "profile")
                                 if context.get(key) is not None},
                        **tool_state(data, context, home, platform, **(tool_state_options or {})))
        elif context.get("kind") == "provider-reference":
            item["kind"] = "provider-model"
        elif data.get("passport_type") == "model":
            item.update(artifact_hash=data.get("artifact_hash"), artifact_files=data.get("artifact_files") or [])
        passports.append(item)
    order = {"device-tool": 0, "repo-agent": 1, "model": 2, "provider-model": 3}
    passports.sort(key=lambda p: (order.get(p["kind"], 3), p["name"], p.get("created_at") or ""))
    return {"passports": passports}
