# Footprints review guidance

- Footprints serves a local UI. Keep the server on loopback, retain the host and write-origin checks, and flag any new device access, data retention, or network request.
- The browser hashes a user-selected file. Forkit Core assigns and verifies passport IDs. Flag any path that uploads file contents, accepts a client-supplied ID, or treats a successful hash as proof of ownership.
- Discovery examples and tests use synthetic evidence. Flag credentials, device logs, personal data, and real local paths in a diff.
- For Windows packaging changes, check that the embedded Python archive is verified before extraction, that the ZIP contains only the runtime and public app files, and that the build smoke test runs the bundled interpreter.
- Check Node tests, Python integration tests, and the Windows packaging check when relevant. Identify missing evidence explicitly. Report actionable findings with file references and leave approval to a maintainer.
