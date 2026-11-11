# Passports

Footprints creates Forkit Core agent passports for two things:
- **AI tools found by the device scan:** one passport per installation, e.g. "Claude Code, command-line tool, v2.1.287, published by Anthropic PBC".
- **Agent setups found by the repository scan:** e.g. "the Claude Code setup of `~/Projects/app`, v1.0.0, vouched for by Jane".

## Tool passports

### Create one

**Device** tab → **Scan this device**. On a tool's card, under **Passports**, choose **Create passport** next to an installation: an app, a command, or an editor or browser extension.

The page sends only the tool's identifier (bundle ID, command name or extension ID). The local service finds the program itself, so file paths never travel to the page.

### What a tool passport contains

| Field | Value |
|---|---|
| `name` | `<tool>/<installation>`, e.g. `claude-code/cli`, `claude-desktop/app`, `claude-code/vscode-extension`, `claude-in-chrome/chrome-extension` |
| `version` | The **detected** version (app or extension metadata). Command-line tools have no version metadata, so you enter it, prefilled from the npm package when known |
| `creator` | For a program with a valid code signature, the **publisher from the signing certificate**, e.g. "Anthropic PBC", never typed. Otherwise the person who vouches for it, and the passport records that (`creator_source: user`). A program whose signature doesn't verify gets no passport |
| `artifact_hash` | Fingerprint of the installed program, see below |
| `model_id` | The provider model: Anthropic Claude, GitHub, Google Gemini, Cursor, OpenAI, Perplexity, xAI Grok, or "user-configured" |
| `parent_agent_id` | The previous passport of the same installation (lineage across updates) |

### Fingerprints

| Installation | Fingerprinted | Strength |
|---|---|---|
| App | Main executable, plus the code signature's sealed list of every file in the app (`_CodeSignature/CodeResources`) | Strong: covers the whole app |
| Command | The program file | Strong for signed programs; for npm or pip scripts, only the script |
| Editor extension | `package.json` | Weak: no signature |
| Browser extension | `manifest.json`, plus Chrome's Web Store–signed file list (`_metadata/verified_contents.json`) when present | Medium |

### Checks

| Check | Result |
|---|---|
| **Install** | ✓ same program. New version installed: normal after an update; create a passport for the new version, linked to the old one. ⚠ program changed: different program, same version number, so it was rebuilt or replaced. Not installed |
| **Publisher** | ✓ still signed by the same team. ⚠ publisher changed. Vouched by you: no signature to check |

Creating a passport for a changed program under an existing version number is refused, because that's exactly what a replaced program looks like.

## Repository agent passports

### Create one

1. **Repositories** tab → **Scan repositories**.
2. On a repository card, under **Agent setups**, choose **Create passport** next to a tool.
3. Enter a version (`1.0` or `1.0.0`) and who vouches for the setup, then **Create agent passport**.

Passports can only be created for repositories found by the latest scan.

### What a repository passport contains

| Field | Value |
|---|---|
| `name` | `<repository>/<tool>`, e.g. `app/claude-code` |
| `version`, `creator` | What you entered. No `v` prefix: Forkit Core's own check would accept `v1.0.0` and create a second identity for the same release |
| `artifact_hash` | **Fingerprint** of the tool's config files: SHA-256 over their names and contents. Personal `*.local.*` files are left out, so the same commit gives the same fingerprint everywhere |
| `model_id` | A **provider model** passport for the agent's model family: Anthropic Claude, GitHub Copilot, Google Gemini, Cursor, or "user-configured". These have no artifact hash, because the models run at the provider |
| `tools` | MCP server names configured in the setup's files |
| `parent_agent_id` | The previous passport of the same repository and tool, so versions form a lineage |
| `metadata.context` | Repository path and origin, tool, and the names of the fingerprinted files |

**Never in a passport:** the text of the agent files, MCP commands or secrets, or the text of permission rules.

Files per tool:

| Tool | Files |
|---|---|
| Claude Code | `CLAUDE.md`, `.claude/settings.json`, `.claude/agents/*`, `.claude/commands/*`, `.mcp.json` |
| Cursor | `.cursorrules`, `.cursor/rules/*`, `.cursor/mcp.json` |
| GitHub Copilot | `.github/copilot-instructions.md`, `.github/instructions/*`, `.vscode/mcp.json` |
| Gemini CLI | `GEMINI.md`, `.gemini/settings.json` |
| AGENTS.md agents | `AGENTS.md` |
| Aider, Continue, Windsurf | `.aider.conf.yml`, `.continue/config.*`, `.windsurfrules` |

Forkit Core derives the passport ID from name, version, creator and fingerprint. The same setup always gets the same ID, and an edited setup gets a different one.

**No overwriting:**
- Creating the same passport again returns the existing one.
- Reusing a version for a changed setup is refused, and a new version is suggested (e.g. `1.1.0`).

## Checking passports

The **Passports** tab checks every passport in the local registry (`~/.forkit/footprints`):

| Check | Result |
|---|---|
| **Record** | ✓ intact: the stored passport still matches its ID (Forkit Core's check). ⚠ altered: someone edited the stored file |
| **Setup** (agent passports) | ✓ unchanged: the files still match the fingerprint. ⚠ changed: they were edited, so create a new version. ⚠ agent files removed. Repository not found |

A passport is a record of what a setup was and who vouched for it. It's not a claim that the setup is safe.
