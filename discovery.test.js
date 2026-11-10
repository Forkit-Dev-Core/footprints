const assert = require('node:assert/strict');
const test = require('node:test');
const {
  discover, sampleEvidence, signalCatalog, describeFinding, describeSignal,
} = require('./discovery.js');

test('finds distinct tool, runtime, and model results in the sample', () => {
  assert.deepEqual(discover(sampleEvidence).map(result => result.id), [
    'ollama-tool', 'ollama-runtime', 'demo-model',
  ]);
});

test('deduplicates equivalent process names', () => {
  const result = discover([
    { kind: 'process', value: 'ollama.exe' },
    { kind: 'process', value: '  OLLAMA.EXE  ' },
  ]);
  assert.equal(result.length, 1);
  assert.equal(result[0].evidence, 'ollama.exe');
  assert.equal(result[0].signals.length, 1);
  assert.equal(result[0].signals[0].occurrences, 2);
});

test('ignores near matches, the wrong evidence type, and malformed entries', () => {
  assert.deepEqual(discover([
    { kind: 'process', value: 'ollama-helper.exe' },
    { kind: 'runtime', value: 'ollama.exe' },
    { kind: 'process', value: 42 },
    null,
  ]), []);
});

test('deduplicates equivalent runtime signals', () => {
  const result = discover([
    { kind: 'runtime', value: 'ollama:api/tags' },
    { kind: 'Runtime', value: ' OLLAMA:API/TAGS ' },
  ]);
  assert.deepEqual(result.map(finding => finding.id), ['ollama-runtime']);
  assert.equal(result[0].signals[0].occurrences, 2);
});

test('ignores runtime near matches', () => {
  assert.deepEqual(discover([
    { kind: 'runtime', value: 'ollama:api/tags/extra' },
    { kind: 'runtime', value: 'ollama:api' },
    { kind: 'process', value: 'ollama:api/tags' },
  ]), []);
});

test('deduplicates equivalent model-file signals', () => {
  const result = discover([
    { kind: 'model-file', value: 'demo-model.gguf' },
    { kind: 'model-file', value: 'DEMO-MODEL.GGUF' },
  ]);
  assert.deepEqual(result.map(finding => finding.id), ['demo-model']);
  assert.equal(result[0].signals[0].occurrences, 2);
});

test('ignores model-file near matches', () => {
  assert.deepEqual(discover([
    { kind: 'model-file', value: 'demo-model.gguf.part' },
    { kind: 'model-file', value: 'other-demo-model.gguf' },
    { kind: 'model-file', value: 'demo-model' },
  ]), []);
});

test('explains each result with its signal, catalog value, and reason', () => {
  const [finding] = discover([{ kind: 'runtime', value: 'ollama:api/tags' }]);
  assert.deepEqual(finding.signals, [{
    signal: 'runtime.ollama-tags',
    kind: 'runtime',
    value: 'ollama:api/tags',
    explanation: 'The local Ollama API answered its model list endpoint.',
    occurrences: 1,
    firstObservedAt: null,
    lastObservedAt: null,
  }]);
  assert.equal(finding.executionEnv, 'local');
  assert.deepEqual(finding.accessMethods, ['api']);
  assert.equal(finding.confidence, 0.9);
  assert.match(describeSignal(finding.signals[0]), /model list endpoint\. Matched runtime "ollama:api\/tags" once\./);
  assert.equal(describeFinding(finding), 'Confidence 90%. Runs on this device, seen through a local API.');
});

test('tracks first and last observation time and ignores invalid timestamps', () => {
  const [finding] = discover([
    { kind: 'process', value: 'ollama.exe', observedAt: '2026-11-10T09:14:00Z' },
    { kind: 'process', value: 'ollama.exe', observedAt: '2026-11-10T09:12:00Z' },
    { kind: 'process', value: 'ollama.exe', observedAt: 'yesterday-ish' },
  ]);
  const [signal] = finding.signals;
  assert.equal(signal.occurrences, 3);
  assert.equal(signal.firstObservedAt, '2026-11-10T09:12:00.000Z');
  assert.equal(signal.lastObservedAt, '2026-11-10T09:14:00.000Z');
});

test('results contain only catalog values, never raw input text', () => {
  const canary = 'fictional-canary-7f3a';
  const results = discover([
    { kind: 'process', value: '  OLLAMA.EXE  ', note: canary },
    { kind: 'model-file', value: canary },
    { kind: 'process', value: `ollama.exe ${canary}` },
  ]);
  const text = JSON.stringify(results);
  assert.ok(!text.includes('canary-7f3a'), 'raw input leaked into results');
  assert.ok(!text.includes('  OLLAMA.EXE  '), 'untrimmed raw value leaked into results');
  assert.equal(results[0].evidence, 'ollama.exe');
});

test('handles non-array input', () => {
  assert.deepEqual(discover(undefined), []);
  assert.deepEqual(discover({ kind: 'process', value: 'ollama.exe' }), []);
});

test('catalog entries are complete and unique', () => {
  const keys = new Set();
  for (const entry of signalCatalog) {
    for (const field of ['signal', 'kind', 'value', 'accessMethod', 'executionEnv', 'explanation']) {
      assert.equal(typeof entry[field], 'string', `${entry.signal} is missing ${field}`);
    }
    assert.ok(entry.weight > 0 && entry.weight < 1, `${entry.signal} weight out of range`);
    const key = `${entry.kind}:${entry.value.toLowerCase()}`;
    assert.ok(!keys.has(key), `duplicate catalog key ${key}`);
    keys.add(key);
  }
});
