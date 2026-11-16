# Community direction and maintenance

## Purpose

Forkit Core is the open-source AI Passport engine. Footprints is the local interface for supported discovery, evidence insights, and passport workflows. Anyone may contribute documentation, tests, accessibility improvements, translations, examples, or code. Participation does not require a commercial account.

Public work focuses on reproducible community use. Keep customer information, business plans, private integrations, credentials, and personal device evidence outside public repositories. Use synthetic fixtures and screenshots. Preserve existing license and attribution notices: Footprints is MIT; Core is separately Apache-2.0.

## Maintainers and decisions

The maintainer contacts are [arpitasarker01](https://github.com/arpitasarker01) and [syedofc](https://github.com/syedofc). Use public Issues for scoped changes and Discussions for questions. Use [private reporting](SECURITY.md) for sensitive matters.

For each change, name a contributor and a reviewing maintainer in the issue or PR. For each release, record a release owner and verifier before building; a request for ownership is not acceptance. Maintainers resolve disagreements by documenting the technical tradeoffs and decision. Changes to identity, storage, permissions, licensing, or public scope require an explicit maintainer decision.

Work through focused pull requests. Review the diff and relevant passing checks before merging. AI-assisted work follows the same review rules; its author remains responsible for the result. Preserve contributor authorship and credit; explain when a PR is superseded and link its replacement. Do not bypass protection rules to finish routine work.

## Current priorities

1. Collect reproducible feedback on [Windows preview.2](https://github.com/Forkit-Dev-Core/footprints/releases/tag/v0.1.0-preview.2), especially launch, scan, registration, and recheck behavior. Report Windows version, release tag, expected and observed behavior using synthetic evidence.
2. Adapt remaining evidence explanations and timestamp validation from [PR #5](https://github.com/Forkit-Dev-Core/footprints/pull/5) to current discovery contracts, retaining the original contributor's credit. Keep numerical confidence separate from verified identity or safety claims.
3. Update the pinned Core dependency in a separate reviewed PR, including its archive hash, compatibility checks, and packaging tests. The published preview.2 intentionally bundles Core `8347f11`; it does not include Core PR #27.
4. Improve keyboard navigation, accessible labels, newcomer setup, and synthetic regression examples. Agree a small scope in an issue before starting.

These are priorities, not promised delivery dates. Follow the [Windows release procedure](docs/windows-release.md): build from merged main, verify the exact ZIP checksum and provenance, test the extracted launcher without elevation, and publish under a new preview tag. Do not replace already-published ZIPs silently.

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [community highlights](docs/community.md).
