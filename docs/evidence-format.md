# Evidence format

Discovery turns a list of **evidence items** into **findings**. An evidence item is one thing that was observed; a finding is an AI tool, app, agent, runtime or model that the evidence points to.

## Evidence item

| Field | Type | Required | Meaning |
|---|---|---|---|
| `kind` | string | yes | What was observed: `process`, `app`, `cli`, `package`, `editor-extension`, `browser-extension`, `native-host`, `runtime`, `model-file` |
| `value` | string | yes | The observed identifier: a process name, bundle ID, extension ID, native host name, runtime endpoint or file name |
| `app` | string | no | For a `process`: bundle ID of the app it lives in (macOS) |
| `parent` | string | no | For a `process`: bundle ID, or name, of the process that started it |
| `client` | string | no | For `mcp-server`: which agent uses it (`claude-desktop`, `claude-code`, `cursor`) |
| `signer` | string | no | For `process`, `app` and `cli`: who signed the program, checked with macOS `codesign`. Values: a Team ID such as `Q6L2SF6YDW` when the signature is valid; `apple` for Apple's own programs; `unsigned` when there is no publisher identity (unsigned or ad-hoc); `invalid` when a signature exists but doesn't verify; `script` for a script (starts with `#!`), which can't be signed, so nothing is verified. Missing means not checked |
| `count` | positive integer | no | How many identical items were observed, e.g. 5 sessions of the same process. Defaults to 1 |
| `permissions` | list of strings | no | Permission names that belong to this item; see below |
| other fields | string | no | Context for explanations, such as `version`, `editor`, `browser`, `profile`, `scope`, `mode`. Matching ignores them. |

Command-line tools have two kinds:

- `cli`: a command installed in a PATH or common install folder, e.g. `{ kind: 'cli', value: 'claude', signer: 'Q6L2SF6YDW', count: 1 }`. One item per name and signer; the same program linked from two folders counts once. The command's location is never included.
- `package`: a globally installed npm, pipx or uv tool package, e.g. `{ kind: 'package', value: '@anthropic-ai/claude-code', manager: 'npm', version: '2.1.287' }`.

- `interpreted-process`: a running `node`, `python`, `bun` or `deno` process that runs a requested tool, e.g. `{ kind: 'interpreted-process', value: '@google/gemini-cli', interpreter: 'node', parent: 'zsh', count: 2 }`.
  - The scan reads the command lines of interpreter processes **only**, in memory.
  - It follows command shims to their package folder (`node_modules/<package>`, `pipx/venvs/<package>`, `uv/tools/<package>`) or matches a requested command name.
  - Only the matched name is returned. Arguments, paths and anything secret in them never leave the scan, and unmatched processes produce nothing.

The scan only looks up the command and package names the catalog asks for. `scanRequest()` builds that list from the `cli` and `package` signals, so other tools on the device stay private.

Global packages and commands are searched in Homebrew, `/usr/local`, `~/.npm-global`, pipx and uv, and in every Node version installed with **nvm, fnm, asdf, mise** or nvm-windows, including their shim folders. Custom `FNM_DIR`, `ASDF_DATA_DIR` and `MISE_DATA_DIR` locations are honored.

Two kinds only add context to a tool that was found by other evidence:

- `mcp-server`: an MCP server **name** an agent is configured with, e.g. `{ kind: 'mcp-server', value: 'github', client: 'claude-code', scope: 'user', transport: 'http' }`
- `agent-rules`: Claude Code's permission mode and rule **counts**, e.g. `{ kind: 'agent-rules', value: 'claude-code', scope: 'user', mode: 'default', allow: '0', ask: '0', deny: '0' }`

### Permission names

| Prefix | Meaning | Example |
|---|---|---|
| `sandbox:` | `on` or `off`: whether a macOS app runs in the App Sandbox | `sandbox:off` |
| `entitlement:` | Declared in the app's code signature: what it **may ask** macOS for | `entitlement:device.camera` |
| `granted:` | Allowed by the user in macOS Privacy & Security | `granted:screen-recording` |
| `extension:` | A browser extension permission from its manifest | `extension:debugger` |
| `hosts:` / `content-scripts:` | Which websites an extension can access or run scripts on: `all-sites` or `some-sites` | `hosts:all-sites` |

A finding lists the permissions of every item that matched it. `describePermissions()` turns them into plain-language lines such as "⚠ Can read and change every website", broadest reach first.

Items with a missing or non-string `kind` or `value` are skipped.

### Normalization

Before matching, `kind`, `value`, `app` and `parent` are trimmed and lower-cased. For `process` values (and `parent`), a path is reduced to its last part and a trailing `.exe` is removed. So `ollama`, `OLLAMA.EXE`, `/usr/local/bin/ollama` and `C:\Program Files\Ollama\ollama.exe` are the same process.

## Catalog entry

Each finding in `catalog` (in `discovery.js`) lists the **signals** that identify it:

```js
{
  id: 'claude-code', label: 'Claude Code', kind: 'Coding agent',
  signals: [
    { kind: 'editor-extension', value: 'anthropic.claude-code', explain: 'Extension {version} in {editor}' },
    { kind: 'process', value: 'claude', app: 'com.anthropic.claude-code',
      explain: '{count} session{s} inside Claude desktop' },
    { kind: 'process', value: 'claude', parent: ['com.microsoft.vscode', 'zsh', 'bash'],
      explain: '{count} session{s} started by {parent}' },
  ],
}
```

- A finding matches if **any** of its signals matches an evidence item.
- A signal matches if **every** field it names matches; a list means "any of these".
- `explain` tells people why the signal counts. Placeholders:
  - `{count}` is the total for that signal.
  - `{s}` and `{es}` are plural endings.
  - Any evidence field (`{value}`, `{version}`, `{editor}`, `{browser}`, `{parent}`, …) is replaced by its value(s). Known IDs become readable names, such as `com.microsoft.VSCode` → VS Code, and a missing field shows as `unknown`.
  - A signal without `explain` shows its value, plus `(×N)` when there are several.
- `attachOnly: true` signals (used for `mcp-server` and `agent-rules`) add a line to a finding that other signals found, but never create a finding or count as a match. A configuration file can outlive the tool.
- `groupBy: 'scope'` keeps one line per value of that field, e.g. user and managed rules, instead of merging them.

## Result

Each finding is reported once:

| Field | Meaning |
|---|---|
| `id`, `label`, `kind` | From the catalog |
| `evidence` | The first matching evidence value, as observed |
| `matches` | Total of the `count` of every matching item |
| `reasons` | One explanation per matching signal, in the order first seen |
| `permissions` | Sorted permission names from all matching items |
| `verification` | `{ status, text }`: whether the matching programs come from the expected publisher; see below |

### Publisher verification

Names, bundle IDs and process names can be copied by anyone. A valid code signature from a publisher's Apple Team ID cannot. So a catalog entry can name its expected publisher:

```js
{ id: 'claude-desktop', publisher: { name: 'Anthropic PBC', teams: ['Q6L2SF6YDW'] }, signals: [...] }
```

Each matching `process` or `app` item is compared with it:

| `status` | When | Example `text` |
|---|---|---|
| `unverified` | Any matching item is unsigned, has an invalid signature, or is signed by another team. This wins over everything else, so a fake next to the real tool is still flagged | Unverified: 1 item is not signed by Anthropic PBC |
| `confirmed` | Signed items all come from the expected team | Signed by Anthropic PBC (Q6L2SF6YDW) |
| `signed` | Signed, but the catalog doesn't know the expected publisher yet | Signed by team ABCDE12345; publisher not in the catalog yet |
| `not-checked` | No signature to check: extensions, config, or a scan on Linux or Windows | Publisher not checked |

The explanation line of a failing item gets a warning, e.g. `Running (1 process) · ⚠ unsigned program, publisher unknown`. Programs without a catalog publisher (like Ollama today) can't be `confirmed`, but an unsigned one is still flagged.

For example, a device running Claude Code inside the desktop app and in VS Code gives:

```js
{ id: 'claude-code', matches: 7, reasons: [
  '5 sessions inside Claude desktop', '1 session started by VS Code', 'Extension 2.1.319 in VS Code',
] }
```

## A match and a near match

The process name `claude` alone is ambiguous: the Claude desktop app's main process has the same name as Claude Code. Context decides.

| Evidence | Result | Why |
|---|---|---|
| `{ kind: 'process', value: 'claude', parent: 'com.microsoft.VSCode' }` | Claude Code | VS Code started it |
| `{ kind: 'process', value: 'Claude', app: 'com.anthropic.claudefordesktop' }` | Claude desktop app | It lives in the desktop app's bundle |
| `{ kind: 'process', value: 'claude.exe', parent: 'explorer.exe' }` | nothing | Same name, but nothing says which Claude it is, so discovery does not guess |

All examples use fictional or public identifiers. When adding a signal, add a test for a representative match and one for a near match that must be ignored.
