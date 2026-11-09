const sampleEvidence = [
  { kind: 'process', value: 'ollama.exe' },
  { kind: 'process', value: 'OLLAMA.EXE' },
  { kind: 'process', value: 'ollama-helper.exe' },
  { kind: 'runtime', value: 'ollama:api/tags' },
  { kind: 'model-file', value: 'demo-model.gguf' },
];

const knownSignals = new Map([
  ['process:ollama.exe', { id: 'ollama-tool', label: 'Ollama', kind: 'AI tool' }],
  ['runtime:ollama:api/tags', { id: 'ollama-runtime', label: 'Ollama API', kind: 'Runtime' }],
  ['model-file:demo-model.gguf', { id: 'demo-model', label: 'Demo model', kind: 'Model file' }],
]);

function discover(evidence) {
  const findings = new Map();

  for (const item of evidence) {
    if (typeof item?.kind !== 'string' || typeof item?.value !== 'string') continue;

    const signal = `${item.kind}:${item.value.trim().toLowerCase()}`;
    const match = knownSignals.get(signal);
    if (match && !findings.has(match.id)) {
      findings.set(match.id, { ...match, evidence: item.value });
    }
  }

  return [...findings.values()];
}

if (typeof document !== 'undefined') {
  const findings = discover(sampleEvidence);
  document.getElementById('summary').textContent = `Discovery results (${findings.length})`;
  const list = document.getElementById('findings');

  for (const finding of findings) {
    const row = document.createElement('li');
    const label = document.createElement('strong');
    label.textContent = `${finding.label} · ${finding.kind}`;
    row.append(label, `Example signal: ${finding.evidence}`);
    list.append(row);
  }
}

if (typeof module !== 'undefined') {
  module.exports = { discover, sampleEvidence };
}
