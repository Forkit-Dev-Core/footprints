# Security policy

Footprints is preview software. Report against the latest published preview or a specific commit. Passport checks establish consistency of recorded identity fields and measured files; they do not certify software safety, ownership, or publisher identity.

## Report privately

Do not post vulnerabilities, credentials, private repository details, raw device scans, or registry files in public issues or discussions. Email **info@forkit.dev**, the project's existing reporting contact. GitHub private vulnerability reporting may also be used if the repository offers it; this policy does not claim that it is enabled.

Include the affected version or commit, impact, and minimal reproduction using synthetic data. Do not send active secrets, customer data, personal logs, or proprietary code. Maintainers investigate privately and coordinate any public advisory. No response-time guarantee is made.

## Review boundaries

Keep the local service on loopback and retain host and write-origin checks. Review any new device access, retention, network requests, dependency, workflow permission, or packaging change explicitly. Public examples and CI evidence must use synthetic data. Keep private investigation notes outside this repository.

If sensitive material has already been published, report its location privately without copying it into another public surface. Revoke exposed credentials first where applicable; then assess commits, releases, artifacts, caches, and forks. Editing the latest file does not erase history. Coordinate any history rewrite with maintainers and contributors before changing shared refs.
