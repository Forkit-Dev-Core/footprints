const assert = require('node:assert/strict');
const test = require('node:test');
const { discover, sampleEvidence } = require('./discovery.js');

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
});

test('ignores near matches, the wrong evidence type, and malformed entries', () => {
  assert.deepEqual(discover([
    { kind: 'process', value: 'ollama-helper.exe' },
    { kind: 'runtime', value: 'ollama.exe' },
    { kind: 'process', value: 42 },
    null,
  ]), []);
});
