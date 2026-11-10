# Evidence format

Footprints discovery turns a list of evidence items into explained results. The sample in [`discovery.js`](../discovery.js) is fictional: Footprints does not scan your device.

## Evidence items

Each evidence item is a plain object:

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | The type of evidence: `process`, `runtime`, or `model-file`. |
| `value` | yes | The observed value, such as a process name or file name. |
| `observedAt` | no | When it was seen, as an ISO 8601 date and time with a zone, such as `2026-11-10T09:12:00Z` or `2026-11-10T10:12:00+01:00`. Results store it in UTC. |

```js
[
  { kind: 'process', value: 'ollama.exe', observedAt: '2026-11-10T09:12:00Z' },
  { kind: 'runtime', value: 'ollama:api/tags' },
  { kind: 'model-file', value: 'demo-model.gguf' },
]
```

Matching rules:

- `kind` and `value` are trimmed and compared without case, so `' OLLAMA.EXE '` matches `ollama.exe`.
- Only exact catalog matches count. `ollama-helper.exe` is a near match and is ignored.
- A value under the wrong `kind` is ignored, for example `{ kind: 'runtime', value: 'ollama.exe' }`.
- `kind` and `value` are compared as a pair, so `{ kind: 'runtime:ollama', value: 'api/tags' }` does not match `runtime` `ollama:api/tags`.
- `value` is the bare name as listed in the catalog. Full paths, other spellings such as `ollama` without `.exe`, and look-alike characters are not matched.
- Items without a string `kind` and `value` are skipped. An `observedAt` that is not an ISO 8601 date and time with a zone, such as `2026-11-10T09:12:00` or `Tue Nov 10 2026`, is ignored. The item still counts.

## Signal catalog

`signalCatalog` in `discovery.js` lists every known signal:

| Field | Meaning |
|---|---|
| `signal` | Stable signal ID, such as `process.ollama`. |
| `kind`, `value` | What evidence matches it. |
| `result` | The result it points to: `id`, `label`, and `kind`. |
| `accessMethod` | How the tool is reached: `terminal`, `api`, or `file`. |
| `executionEnv` | Where it runs: `local` for every current signal. |
| `weight` | Confidence from 0 to 1 that one matching signal adds. |
| `explanation` | Plain-language reason the signal counts. |

To add a signal, add a catalog entry and a test with one representative match and one near match that must be ignored.

## Results

`discover(evidence)` returns one result per catalog `result.id`, in first-seen order:

| Field | Meaning |
|---|---|
| `id`, `label`, `kind` | From the catalog result. |
| `evidence` | The catalog value of the first matching signal. Kept for compatibility. |
| `signals` | Every distinct signal behind the result, with `signal`, `kind`, `value`, `explanation`, `occurrences`, `firstObservedAt`, and `lastObservedAt`. |
| `accessMethods` | Distinct access methods across those signals. |
| `executionEnv` | Where the result runs. |
| `confidence` | Combined confidence from 0 to 1: one minus the product of `(1 - weight)` over distinct signals. Repeats of the same signal raise `occurrences`, not confidence. |

## Privacy

Results only contain catalog values and timestamps. Raw input text, including near matches, unknown entries, untrimmed values, and extra fields, is never copied into results. Use fictional evidence in examples, tests, and issues.
