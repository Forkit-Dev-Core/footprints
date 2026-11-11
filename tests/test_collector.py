"""Collector tests on a fake home folder and process list: no real device data."""

import json
import os
import plistlib
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

from collector import (collect, editor_extension_evidence, extension_permissions, interpreted_evidence,
                       match_interpreted, node_installs, package_evidence, package_roots,
                       parse_windows_command_lines, read_signer, version_manager_command_dirs)

# Built with os.path.join so the paths are exactly what the OS reports.
SYSTEM_PROGRAM = os.path.join(os.sep, "usr", "sbin", "distnoted")
LAUNCHD = os.path.join(os.sep, "sbin", "launchd")


def make_app(directory: Path, name: str, bundle_id: str, version: str = "1.0") -> Path:
    contents = directory / f"{name}.app" / "Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_bytes(
        plistlib.dumps({"CFBundleIdentifier": bundle_id, "CFBundleShortVersionString": version}))
    return directory / f"{name}.app"


class CollectorTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home" / "example-user"
        self.apps = self.root / "Applications"
        self.home.mkdir(parents=True)
        self.apps.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def scan(self, processes=(), platform="darwin", **readers):
        readers.setdefault("entitlements_reader", lambda _app: None)
        readers.setdefault("signer_reader", lambda _target: None)
        readers.setdefault("command_dirs_override", [])
        readers.setdefault("command_line_reader", lambda _pids, _platform: {})
        readers.setdefault("package_roots_override", {})
        readers.setdefault("tcc_paths", [])
        readers.setdefault("managed_settings", self.root / "no-managed-settings.json")
        return collect(home=self.home, platform=platform, processes=list(processes),
                       applications_dirs=[self.apps], **readers)

    def evidence(self, result, kind):
        return [item for item in result["evidence"] if item["kind"] == kind]

    def test_attributes_processes_to_their_app_and_parent(self):
        desktop = make_app(self.apps, "Claude", "com.anthropic.claudefordesktop")
        bundled = make_app(self.home / "Library" / "Claude" / "claude-code", "claude", "com.anthropic.claude-code")
        vscode = make_app(self.apps, "Visual Studio Code", "com.microsoft.VSCode")
        processes = [
            ("1", "0", "/sbin/launchd"),
            ("10", "1", f"{desktop}/Contents/MacOS/Claude"),
            ("11", "10", f"{bundled}/Contents/MacOS/claude"),
            ("12", "10", f"{bundled}/Contents/MacOS/claude"),
            ("20", "1", f"{vscode}/Contents/MacOS/Electron"),
            ("21", "20", f"{vscode}/Contents/Frameworks/Code Helper (Plugin).app/Contents/MacOS/Code Helper (Plugin)"),
            ("22", "21", f"{self.home}/.vscode/extensions/anthropic.claude-code-2.1.319-darwin-arm64/resources/native-binary/claude"),
        ]
        items = self.evidence(self.scan(processes), "process")
        self.assertIn({"kind": "process", "value": "Claude", "app": "com.anthropic.claudefordesktop",
                       "parent": "launchd", "count": 1}, items)
        self.assertIn({"kind": "process", "value": "claude", "app": "com.anthropic.claude-code",
                       "parent": "com.anthropic.claudefordesktop", "count": 2}, items)
        # Nested helper .app bundles count as the outer app.
        self.assertIn({"kind": "process", "value": "claude", "parent": "com.microsoft.VSCode", "count": 1}, items)

    def test_reads_app_bundle_ids_and_versions(self):
        make_app(self.apps, "Cursor", "com.todesktop.230313mzl4w4u92", "2.0.34")
        (self.apps / "Not an app").mkdir()
        self.assertEqual(self.evidence(self.scan(), "app"), [
            {"kind": "app", "value": "com.todesktop.230313mzl4w4u92", "version": "2.0.34"}])

    def test_editor_extensions_keep_only_the_newest_version_per_editor(self):
        for editor_dir, folder in [
            (".vscode", "anthropic.claude-code-2.1.300-darwin-arm64"),
            (".vscode", "anthropic.claude-code-2.1.319-darwin-arm64"),
            (".vscode", "github.copilot-chat-0.22.0"),
            (".vscode", ".obsolete"),
            (".cursor", "GitHub.copilot-1.250.0"),
        ]:
            (self.home / editor_dir / "extensions" / folder).mkdir(parents=True, exist_ok=True)
        (self.home / ".vscode" / "extensions" / "extensions.json").write_text("[]")
        self.assertEqual(editor_extension_evidence(self.home), [
            {"kind": "editor-extension", "value": "anthropic.claude-code", "editor": "vscode", "version": "2.1.319"},
            {"kind": "editor-extension", "value": "github.copilot-chat", "editor": "vscode", "version": "0.22.0"},
            {"kind": "editor-extension", "value": "github.copilot", "editor": "cursor", "version": "1.250.0"},
        ])

    def test_browser_extensions_per_profile_and_native_hosts(self):
        chrome = self.home / "Library" / "Application Support" / "Google" / "Chrome"
        ext = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
        for profile in ("Default", "Profile 9"):
            for version in ("1.0.105_0", "1.0.106_0"):
                (chrome / profile / "Extensions" / ext / version).mkdir(parents=True)
        (chrome / "Default" / "Extensions" / "Temp").mkdir()
        (chrome / "System Profile" / "Extensions" / ext / "1.0.0_0").mkdir(parents=True)
        (chrome / "NativeMessagingHosts").mkdir()
        (chrome / "NativeMessagingHosts" / "com.anthropic.claude_browser_extension.json").write_text("{}")
        result = self.scan()
        self.assertEqual(self.evidence(result, "browser-extension"), [
            {"kind": "browser-extension", "value": ext, "browser": "chrome", "profile": "Default", "version": "1.0.106"},
            {"kind": "browser-extension", "value": ext, "browser": "chrome", "profile": "Profile 9", "version": "1.0.106"},
        ])
        self.assertEqual(self.evidence(result, "native-host"), [
            {"kind": "native-host", "value": "com.anthropic.claude_browser_extension", "browser": "chrome"}])

    def test_output_contains_no_paths_or_username(self):
        desktop = make_app(self.apps, "Claude", "com.anthropic.claudefordesktop")
        (self.home / ".vscode" / "extensions" / "continue.continue-1.0.0").mkdir(parents=True)
        processes = [("1", "0", "/sbin/launchd"),
                     ("2", "1", f"{desktop}/Contents/MacOS/Claude"),
                     ("3", "1", f"{self.home}/bin/secret-tool")]
        text = json.dumps(self.scan(processes))
        self.assertNotIn("example-user", text)
        self.assertNotIn(str(self.root), text)
        self.assertNotIn("/Contents/", text)

    def test_reports_what_was_not_checked(self):
        linux = self.scan(platform="linux")
        self.assertIn("app", linux["not_collected"])
        self.assertIn("browser-extension", linux["collected"])
        windows = self.scan(platform="win32")
        self.assertIn("native-host", windows["not_collected"])
        self.assertNotIn("native-host", windows["collected"])

    def test_app_permissions_come_from_the_signature(self):
        make_app(self.apps, "Claude", "com.anthropic.claudefordesktop")
        make_app(self.apps, "Store App", "com.example.sandboxed")
        make_app(self.apps, "Unsigned", "com.example.unsigned")
        signatures = {
            "Claude.app": {"com.apple.security.app-sandbox": False, "com.apple.security.device.camera": True,
                           "com.apple.security.cs.allow-jit": True, "com.apple.security.device.usb": False},
            "Store App.app": {"com.apple.security.app-sandbox": True,
                              "com.apple.security.application-groups": ["group.example"]},
        }
        result = self.scan(entitlements_reader=lambda app: signatures.get(app.name))
        apps = {item["value"]: item.get("permissions") for item in self.evidence(result, "app")}
        self.assertEqual(apps["com.anthropic.claudefordesktop"],
                         ["entitlement:cs.allow-jit", "entitlement:device.camera", "sandbox:off"])
        self.assertEqual(apps["com.example.sandboxed"], ["sandbox:on"])
        self.assertIsNone(apps["com.example.unsigned"])  # unknown is not reported as "not sandboxed"

    def test_granted_privacy_permissions_when_macos_allows_reading_them(self):
        make_app(self.apps, "Claude", "com.anthropic.claudefordesktop")
        tcc = self.root / "TCC.db"
        with closing(sqlite3.connect(tcc)) as db:
            db.execute("CREATE TABLE access (service TEXT, client TEXT, client_type INTEGER, auth_value INTEGER)")
            db.executemany("INSERT INTO access VALUES (?, ?, ?, ?)", [
                ("kTCCServiceScreenCapture", "com.anthropic.claudefordesktop", 0, 2),
                ("kTCCServiceMicrophone", "com.anthropic.claudefordesktop", 0, 2),
                ("kTCCServiceCamera", "com.anthropic.claudefordesktop", 0, 0),  # denied
                ("kTCCServiceAccessibility", "/usr/local/bin/some-tool", 1, 2),  # a path, not an app
            ])
            db.commit()
        result = self.scan(tcc_paths=[tcc])
        self.assertIn("granted-permissions", result["collected"])
        self.assertEqual(self.evidence(result, "app")[0]["permissions"], ["granted:microphone", "granted:screen-recording"])
        self.assertNotIn("some-tool", json.dumps(result))

        unreadable = self.root / "locked.db"
        unreadable.write_bytes(b"not a database")
        locked = self.scan(tcc_paths=[unreadable])
        self.assertIn("granted-permissions", locked["not_collected"])
        self.assertNotIn("permissions", self.evidence(locked, "app")[0])

    def test_browser_extension_permissions_from_the_newest_manifest(self):
        ext = self.home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Extensions" / ("a" * 32)
        (ext / "1.0_0").mkdir(parents=True)
        (ext / "1.0_0" / "manifest.json").write_text(json.dumps({"permissions": ["history"]}))
        (ext / "2.0_0").mkdir()
        (ext / "2.0_0" / "manifest.json").write_text(json.dumps({
            "permissions": ["debugger", "tabs", {"not": "a string"}],
            "host_permissions": ["<all_urls>"],
            "content_scripts": [{"matches": ["https://example.com/*"], "js": ["inject.js"]}],
        }))
        item = self.evidence(self.scan(), "browser-extension")[0]
        self.assertEqual(item["version"], "2.0")
        self.assertEqual(item["permissions"],
                         ["content-scripts:some-sites", "extension:debugger", "extension:tabs", "hosts:all-sites"])

    def test_extension_site_patterns_are_reduced_to_all_or_some(self):
        self.assertEqual(extension_permissions({"permissions": ["https://*/*", "storage"]}),
                         ["extension:storage", "hosts:all-sites"])
        self.assertEqual(extension_permissions({"host_permissions": ["https://mail.example.com/*"]}),
                         ["hosts:some-sites"])
        self.assertEqual(extension_permissions({"permissions": ["not a permission name!"]}), [])

    def test_mcp_servers_names_only_never_commands_secrets_or_paths(self):
        desktop = self.home / "Library" / "Application Support" / "Claude"
        desktop.mkdir(parents=True)
        (desktop / "claude_desktop_config.json").write_text(json.dumps({"mcpServers": {
            "docs": {"command": "/Users/example-user/bin/docs-server", "args": ["--token", "SECRET-ARG"],
                     "env": {"API_KEY": "SECRET-ENV"}}}}))
        (self.home / ".claude.json").write_text(json.dumps({
            "mcpServers": {"github": {"type": "http", "url": "https://mcp.example.com/?key=SECRET-URL"}},
            "projects": {"/Users/example-user/private-project": {"mcpServers": {"db": {"command": "npx"}}}},
            "oauthAccount": {"emailAddress": "person@example.com"},
        }))
        result = self.scan()
        self.assertEqual(self.evidence(result, "mcp-server"), [
            {"kind": "mcp-server", "value": "docs", "client": "claude-desktop", "scope": "user", "transport": "stdio"},
            {"kind": "mcp-server", "value": "github", "client": "claude-code", "scope": "user", "transport": "http"},
            {"kind": "mcp-server", "value": "db", "client": "claude-code", "scope": "project", "transport": "stdio"},
        ])
        text = json.dumps(result)
        for secret in ("SECRET-ARG", "SECRET-ENV", "SECRET-URL", "private-project", "person@example.com", "docs-server"):
            self.assertNotIn(secret, text)

    def test_claude_code_rules_are_counted_never_copied(self):
        (self.home / ".claude").mkdir()
        (self.home / ".claude" / "settings.json").write_text(json.dumps({"permissions": {
            "defaultMode": "acceptEdits", "allow": ["Bash(npm test)", "Read(~/secret-notes/**)"],
            "deny": ["Bash(rm -rf:*)"]}}))
        managed = self.root / "managed-settings.json"
        managed.write_text(json.dumps({"permissions": {"defaultMode": "bad mode; rm -rf /", "ask": ["WebFetch"]}}))
        result = self.scan(managed_settings=managed)
        self.assertEqual(self.evidence(result, "agent-rules"), [
            {"kind": "agent-rules", "value": "claude-code", "scope": "user", "mode": "acceptEdits",
             "allow": "2", "ask": "0", "deny": "1"},
            {"kind": "agent-rules", "value": "claude-code", "scope": "managed", "mode": "default",
             "allow": "0", "ask": "1", "deny": "0"},
        ])
        self.assertNotIn("secret-notes", json.dumps(result))

    def test_signer_is_checked_once_per_app_and_program_but_not_for_system_programs(self):
        desktop = make_app(self.apps, "Claude", "com.anthropic.claudefordesktop")
        fake = self.home / "bin" / "claude"
        processes = [
            ("1", "0", LAUNCHD),
            ("2", "1", SYSTEM_PROGRAM),
            ("10", "1", f"{desktop}/Contents/MacOS/Claude"),
            ("11", "10", f"{desktop}/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper"),
            ("20", "1", str(fake)),
        ]
        checked = []

        def signer_reader(target):
            checked.append(target)
            return {str(desktop): "Q6L2SF6YDW", str(fake): "unsigned"}.get(target)

        result = self.scan(processes, signer_reader=signer_reader)
        self.assertEqual(sorted(checked), sorted([str(desktop), str(fake)]))  # once each, no system programs
        signers = {(i["kind"], i["value"]): i.get("signer") for i in result["evidence"]}
        self.assertEqual(signers[("process", "Claude")], "Q6L2SF6YDW")
        self.assertEqual(signers[("process", "Claude Helper")], "Q6L2SF6YDW")
        self.assertEqual(signers[("app", "com.anthropic.claudefordesktop")], "Q6L2SF6YDW")
        self.assertEqual(signers[("process", "claude")], "unsigned")
        self.assertIsNone(signers[("process", "distnoted")])
        self.assertIn("signer", result["collected"])
        self.assertIn("signer", self.scan(platform="linux")["not_collected"])

    def test_read_signer_interprets_codesign_output(self):
        def fake_run(display, verify_rc=0):
            def run(args, **_kwargs):
                if "--verify" in args:
                    return subprocess.CompletedProcess(args, verify_rc, b"", b"")
                return subprocess.CompletedProcess(args, display[0], "", display[1])
            return run

        cases = [
            ((0, "Authority=Developer ID Application: Example (ABCDE12345)\nTeamIdentifier=ABCDE12345\n"), 0, "ABCDE12345"),
            ((0, "Authority=macOS Software Signing\nTeamIdentifier=not set\n"), 0, "apple"),
            ((0, "Signature=adhoc\nTeamIdentifier=not set\n"), 0, "unsigned"),
            ((1, "code object is not signed at all\n"), 0, "unsigned"),
            ((0, "TeamIdentifier=ABCDE12345\n"), 1, "invalid"),
            ((1, "No such file or directory\n"), 0, None),
        ]
        for display, verify_rc, expected in cases:
            with mock.patch("collector.subprocess.run", side_effect=fake_run(display, verify_rc)):
                self.assertEqual(read_signer("target"), expected, display[1])

    def test_skips_extensions_the_editor_marked_as_removed(self):
        extensions = self.home / ".vscode" / "extensions"
        for folder in ("github.copilot-1.372.0", "github.copilot-chat-0.33.3", "continue.continue-2.0.0"):
            (extensions / folder).mkdir(parents=True)
        (extensions / ".obsolete").write_text(json.dumps({
            "github.copilot-1.372.0": True, "github.copilot-chat-0.33.3": True, "something-else-1.0.0": False}))
        self.assertEqual([item["value"] for item in editor_extension_evidence(self.home)], ["continue.continue"])

    def test_finds_requested_commands_once_per_program_with_their_signer(self):
        first, second = self.root / "bin-a", self.root / "bin-b"
        first.mkdir()
        second.mkdir()
        claude = first / "claude"
        claude.write_text("#!/bin/sh\n")
        claude.chmod(0o755)
        (second / "claude").symlink_to(claude)  # same program linked from a second folder
        (first / "codex").write_text("not executable")
        (first / "copilot").write_text("#!/bin/sh\n")
        (first / "copilot").chmod(0o755)
        real = os.path.realpath(claude)
        result = self.scan(cli_names=["claude", "codex", "Gemini"], command_dirs_override=[str(first), str(second)],
                           signer_reader=lambda target: "Q6L2SF6YDW" if target == real else None)
        self.assertEqual(self.evidence(result, "cli"),
                         [{"kind": "cli", "value": "claude", "signer": "Q6L2SF6YDW", "count": 1}])
        self.assertNotIn(str(self.root), json.dumps(result))

        windows = self.root / "win-bin"
        windows.mkdir()
        (windows / "Claude.CMD").write_text("@echo off\n")
        found = self.scan(cli_names=["claude"], platform="win32", command_dirs_override=[str(windows)])
        self.assertEqual(self.evidence(found, "cli"), [{"kind": "cli", "value": "claude", "count": 1}])

    def test_finds_requested_global_packages_without_listing_others(self):
        npm, pipx = self.root / "node_modules", self.root / "pipx-venvs"
        (npm / "@anthropic-ai" / "claude-code").mkdir(parents=True)
        (npm / "@anthropic-ai" / "claude-code" / "package.json").write_text(json.dumps({"version": "2.1.287"}))
        (npm / "private-company-tool").mkdir()
        (pipx / "aider-chat").mkdir(parents=True)
        result = self.scan(package_names=["@anthropic-ai/claude-code", "aider-chat", "@openai/codex", "../../etc"],
                           package_roots_override={"npm": [npm], "pipx": [pipx], "uv": []})
        self.assertEqual(self.evidence(result, "package"), [
            {"kind": "package", "value": "@anthropic-ai/claude-code", "manager": "npm", "version": "2.1.287"},
            {"kind": "package", "value": "aider-chat", "manager": "pipx"},
        ])
        self.assertNotIn("private-company-tool", json.dumps(result))

    def test_commands_and_packages_are_only_looked_up_when_requested(self):
        result = self.scan()
        self.assertIn("cli", result["not_collected"])
        self.assertIn("package", result["not_collected"])

    def test_scripts_are_reported_as_scripts_not_as_unsigned(self):
        shim = self.root / "gemini"
        shim.write_text("#!" + os.path.join(os.sep, "usr", "bin", "env") + " node\nrequire('./cli');\n")
        with mock.patch("collector.subprocess.run", side_effect=AssertionError("codesign must not run")):
            self.assertEqual(read_signer(str(shim)), "script")

    def test_finds_packages_and_commands_of_node_version_managers(self):
        def install(base, version_dir, package):
            folder = base / version_dir / "lib" / "node_modules" / package
            folder.mkdir(parents=True)
            (folder / "package.json").write_text(json.dumps({"version": "1.0.0"}))
            (base / version_dir / "bin").mkdir(exist_ok=True)

        install(self.home / ".nvm" / "versions" / "node", "v20.1.0", "nvm-agent")
        install(self.home / "Library" / "Application Support" / "fnm" / "node-versions", "v22.0.0/installation", "fnm-agent")
        install(self.home / ".asdf" / "installs" / "nodejs", "20.11.0", "@example/asdf-agent")
        custom_mise = self.root / "custom-mise"
        install(custom_mise / "installs" / "node", "22.3.0", "mise-agent")
        environ = {"MISE_DATA_DIR": str(custom_mise)}

        self.assertEqual(len(node_installs(self.home, "darwin", environ)), 4)
        roots = package_roots(self.home, "darwin", environ)
        found = package_evidence(self.home, "darwin", ["nvm-agent", "fnm-agent", "@example/asdf-agent", "mise-agent"],
                                 roots_by_manager=roots)
        self.assertEqual(sorted(item["value"] for item in found),
                         ["@example/asdf-agent", "fnm-agent", "mise-agent", "nvm-agent"])

        dirs = version_manager_command_dirs(self.home, "darwin", environ)
        self.assertIn(str(self.home / ".asdf" / "shims"), dirs)
        self.assertIn(str(custom_mise / "shims"), dirs)
        self.assertIn(str(self.home / ".nvm" / "versions" / "node" / "v20.1.0" / "bin"), dirs)

    def test_attributes_node_and_python_processes_to_requested_tools_only(self):
        package = self.root / "lib" / "node_modules" / "@google" / "gemini-cli" / "dist"
        package.mkdir(parents=True)
        (package / "index.js").write_text("// cli")
        shim = self.root / "bin" / "gemini"
        shim.parent.mkdir()
        shim.symlink_to(package / "index.js")
        venv_python = self.root / "pipx" / "venvs" / "aider-chat" / "bin" / "python"
        rows = [
            ("1", "0", "zsh"),
            ("10", "1", "node"),                         # gemini via its command shim
            ("11", "1", "Python"),                       # aider via its pipx environment
            ("12", "1", "node"),                         # an unrelated script with a secret
            ("13", "1", "node"),                         # a CLI that was not requested
            ("14", "1", "bash"),                         # not an interpreter: never read
        ]
        lines = {
            "10": f"node {shim} --api-key SECRET-1",
            "11": f"{venv_python} {self.root}/bin/aider --openai-api-key SECRET-2",
            "12": f"node {self.root}/server.js --token=SECRET-3",
            "13": f"node {self.root}/lib/node_modules/@openai/codex/bin/codex.js",
        }
        asked = []

        def reader(pids, _platform):
            asked.extend(pids)
            return lines

        evidence = interpreted_evidence(rows, "linux", ["gemini", "aider"], ["@google/gemini-cli", "aider-chat"], reader)
        self.assertEqual(sorted(asked), ["10", "11", "12", "13"])  # only interpreter processes
        self.assertEqual(sorted(evidence, key=lambda item: item["value"]), [
            {"kind": "interpreted-process", "value": "@google/gemini-cli", "interpreter": "node", "parent": "zsh", "count": 1},
            {"kind": "interpreted-process", "value": "aider-chat", "interpreter": "python", "parent": "zsh", "count": 1},
        ])
        text = json.dumps(evidence)
        for leaked in ("SECRET-1", "SECRET-2", "SECRET-3", str(self.root), "codex"):
            self.assertNotIn(leaked, text)
        self.assertEqual(interpreted_evidence(rows, "linux", [], [], reader), [])

    def test_windows_command_lines(self):
        self.assertEqual(parse_windows_command_lines('{"ProcessId": 7, "CommandLine": "node a.js"}'), {"7": "node a.js"})
        self.assertEqual(parse_windows_command_lines('[{"ProcessId": 7, "CommandLine": null}]'), {})
        self.assertEqual(parse_windows_command_lines("not json"), {})
        quoted = ('"C:\\Program Files\\nodejs\\node.exe" "C:\\Users\\A B\\AppData\\Roaming\\npm\\node_modules'
                  '\\@google\\gemini-cli\\dist\\index.js" --api-key X')
        self.assertEqual(match_interpreted(quoted, {"@google/gemini-cli"}, set()), "@google/gemini-cli")
        self.assertEqual(match_interpreted("node C:\\tools\\codex.cmd", set(), {"codex"}), "codex")

    def test_windows_process_names_have_no_parent(self):
        items = self.evidence(self.scan([("100", None, "claude.exe")], platform="win32"), "process")
        self.assertEqual(items, [{"kind": "process", "value": "claude.exe", "count": 1}])


if __name__ == "__main__":
    unittest.main()
