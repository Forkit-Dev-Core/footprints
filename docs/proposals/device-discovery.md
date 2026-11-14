# Proposal: scan this device for AI tools

**Status:** draft for discussion (see CONTRIBUTING: new permissions are explained before they are merged)

## Problem

Discovery only matches a fixed, fictional sample. Footprints cannot show what AI tools are on the user's own device, and a browser page alone cannot see processes or installed apps.

## Proposal

Add a **Scan this device** button. It calls a new local endpoint, `POST /discovery/scan`, on the existing Footprints service (`python serve.py`). The service reads a fixed list of identifiers and returns them as evidence items (see [evidence-format.md](../evidence-format.md)). The page then runs the same `discover()` matcher it uses for the sample.

## What is read

This is the complete list. Anything not listed is not read.

| Evidence | Source | What is taken | Platforms |
|---|---|---|---|
| `process` | OS process list (`ps` / `tasklist`) | process ID, parent ID, executable name. On macOS the executable path is used only to find the enclosing app's bundle ID and is not returned | macOS, Linux, Windows (no parent on Windows) |
| `app` | `Info.plist` of apps in `/Applications` and `~/Applications` | `CFBundleIdentifier`, `CFBundleShortVersionString` | macOS |
| `editor-extension` | folder **names** in the VS Code, VS Code Insiders, Cursor, VSCodium and Windsurf extension folders | extension ID, newest version | all |
| `browser-extension` | folder **names** under `<Chromium browser>/<profile>/Extensions` (Chrome, Edge, Brave, Arc, Chromium) | extension ID, browser, profile folder name, newest version | all |
| `native-host` | file **names** in each browser's `NativeMessagingHosts` folder | host name | macOS, Linux |
| `signer` on `process` and `app` | code signature of each app and each non-system program, via `codesign -dv` and `codesign --verify --ignore-resources` (8 in parallel, once per program; Apple's system folders are skipped) | Team ID of a valid signature, `apple`, `unsigned` or `invalid` | macOS |
| `cli` | file **names** in PATH folders and common install folders (Homebrew, `~/.local/bin`, npm, Bun, Cargo, Volta); Apple's system folders are skipped | only command names **the catalog requested**, plus their signer | all (signer: macOS) |
| `interpreted-process` | command lines of running `node`, `python`, `bun` and `deno` processes only, held in memory | only the requested package or command name the process runs, interpreter, parent | all |
| `package` | the requested package's own folder in global npm, pipx and uv tool folders; for npm, `version` from its `package.json` | only package names **the catalog requested**, manager, version | all |
| removed editor extensions | the editor's `.obsolete` file in each extension folder | names of folders marked as uninstalled, which are then skipped | all |
| app permissions | each app's code signature, via `codesign -d --entitlements` | whether the app is sandboxed, and the **names** of entitlements set to true (what it may ask macOS for) | macOS |
| granted permissions | macOS privacy databases (TCC), read-only | service name and bundle ID of allowed grants, e.g. `screen-recording` for an app. macOS only allows this with **Full Disk Access**; without it the scan says "not checked" | macOS |
| extension permissions | `manifest.json` of the newest version of each browser extension | `permissions` names; `host_permissions` and content-script sites reduced to "all sites" or "some sites" | all |
| `mcp-server` | Claude desktop config, `~/.claude.json`, `~/.cursor/mcp.json` | server **name**, which agent, user or project scope, transport | all (Claude desktop: macOS, Windows) |
| `agent-rules` | `~/.claude/settings.json` and Claude Code managed settings | permission mode and the **number** of allow, ask and deny rules | all |

## What is never read or returned

- Command-line arguments, environment variables, open files or network connections of any process
- File contents, other than the fields listed above
- MCP server commands, arguments, environment variables, URLs and project paths, which often contain keys or tokens
- The text of Claude Code permission rules (only their number), and anything else in `~/.claude.json` such as account details
- Specific websites an extension may access (only "all sites" or "some sites")
- Conversations, prompts, tokens, browser history, browser profile display names (only folder names like `Profile 9`) or extension settings
- Paths, user names or device names. The response contains identifiers, versions and counts only.

## Permissions and data flow

- **When it runs:** only when the user presses the button. Nothing runs in the background and nothing is stored.
- **What it needs:** normal user permissions. No admin rights, no new dependencies, no network access.
- **Who can call it:** the endpoint uses the same protections as `/models`. It accepts POST only, with a JSON body, from the local page's origin, on the `127.0.0.1` host.
  - Other paths return 404, other origins 403, other hosts 400, and a non-JSON request (like a form another website could submit) 415.
- **What the request contains:** `{ "cli": [...], "packages": [...] }`, the names the catalog knows.
  - The service accepts at most 200 names.
  - Each must look like a plain command or package name: lower-case letters, digits, `.`, `_`, `-`, and an optional `@scope/`. Anything else, such as a path or `..`, is dropped.
  - Command and package folders are only checked for those names, never listed in full.
- **Where results go:** to the local page only. Nothing leaves the device.

## Tests

- `tests/test_collector.py` runs on a fake home folder and process list. It checks attribution (app and parent), deduplication of versions and profiles, the not-collected report per platform, and that the output contains **no paths and no user name**.
- `tests/test_integration.py` checks that the endpoint accepts only same-origin POST requests on the local host. It uses a fake collector, so it never reads the test machine.
- `discovery.test.js` has a match and a near match for every new signal.

## Known limits

- A process name with no telling context, such as a Windows `claude.exe` started by Explorer, is not attributed. Discovery reports nothing rather than guessing.
- An extension folder can remain after uninstalling, and disabled browser extensions are still listed. The result means "installed", not "enabled".
- Linux `ps` names are cut to 15 characters. Linux and Windows apps, Firefox and Safari extensions, and Windows native hosts (registry) are not read yet.
- The catalog only contains identifiers that were verified on a real device. More tools need contributors to verify their identifiers.
- Permissions come in three levels, and only two are always visible:
  - **declared:** entitlements and extension manifests;
  - **configured:** MCP servers and Claude Code rules;
  - **granted:** macOS privacy grants, which need Full Disk Access.

  What an agent actually *did* with a permission is not observed.
- Entitlements show what an app may ask for, not what it was allowed. An app that isn't sandboxed can read the user's files without any entitlement, apart from folders macOS protects with a prompt.
- Project-level Claude Code settings (`.claude/settings.json` inside each project) are not read, because that would mean searching the disk for projects.
- Checking code signatures makes a scan take about 3 seconds on a Mac with about 80 non-system programs running and 25 apps.
- Signature checks verify the program code and the publisher's signature, but skip hashing every bundled resource file (`--ignore-resources`). Verifying everything took 3 seconds for a single large app.
- Linux and Windows programs aren't signature-checked yet, so their results say "Publisher not checked". Tools installed through Homebrew or as Linux packages usually have no Team ID: they show as unsigned, which is accurate, not proof of a fake.
- Expected publishers are only in the catalog where they were verified on a real device. Ollama's is still missing.
- CLI tools that run on Node or Python are attributed by reading the command lines of interpreter processes only (`node`, `python`, `bun`, `deno`; via `ps`, or `Get-CimInstance` on Windows). They are compared in memory with the requested names, and only a matched name is returned. A tool started in an unusual way, e.g. through a wrapper that hides its path, is reported as installed only.
- Node versions from nvm, fnm, asdf, mise and nvm-windows are searched. Per-project installs (`npx`, local `node_modules`) are not.
- The Windows paths for command lines and version managers follow those tools' documented defaults, but haven't been tested on a Windows machine yet.
