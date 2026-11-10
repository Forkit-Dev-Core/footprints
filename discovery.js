// Footprints discovery: match fictional evidence against a small catalog of
// known signals and explain why each result was found.
//
// Privacy rule: results only ever contain catalog values. Raw input values,
// including near matches and unknown entries, are never copied into results.

const sampleEvidence = [
  { kind: 'process', value: 'ollama.exe', observedAt: '2026-11-10T09:12:00Z' },
  { kind: 'process', value: 'OLLAMA.EXE', observedAt: '2026-11-10T09:14:00Z' },
  { kind: 'process', value: 'ollama-helper.exe', observedAt: '2026-11-10T09:14:00Z' },
  { kind: 'runtime', value: 'ollama:api/tags', observedAt: '2026-11-10T09:15:00Z' },
  { kind: 'model-file', value: 'demo-model.gguf', observedAt: '2026-11-10T09:16:00Z' },
];

// Each signal says what it points to, how it is reached, and why it counts.
// weight is the confidence one matching signal contributes (0 to 1).
const signalCatalog = [
  {
    signal: 'process.ollama',
    kind: 'process',
    value: 'ollama.exe',
    result: { id: 'ollama-tool', label: 'Ollama', kind: 'AI tool' },
    accessMethod: 'terminal',
    executionEnv: 'local',
    weight: 0.6,
    explanation: 'A process with the exact Ollama executable name is running.',
  },
  {
    signal: 'runtime.ollama-tags',
    kind: 'runtime',
    value: 'ollama:api/tags',
    result: { id: 'ollama-runtime', label: 'Ollama API', kind: 'Runtime' },
    accessMethod: 'api',
    executionEnv: 'local',
    weight: 0.9,
    explanation: 'The local Ollama API answered its model list endpoint.',
  },
  {
    signal: 'model-file.demo',
    kind: 'model-file',
    value: 'demo-model.gguf',
    result: { id: 'demo-model', label: 'Demo model', kind: 'Model file' },
    accessMethod: 'file',
    executionEnv: 'local',
    weight: 0.5,
    explanation: 'A model file with the known demo filename is present.',
  },
];

function normalise(text) {
  return text.trim().toLowerCase();
}

const knownSignals = new Map(
  signalCatalog.map(entry => [`${entry.kind}:${normalise(entry.value)}`, entry]),
);

function validTimestamp(value) {
  return typeof value === 'string' && !Number.isNaN(Date.parse(value));
}

// Combine independent signals: 1 minus the product of (1 - weight).
function combinedConfidence(weights) {
  const miss = weights.reduce((product, weight) => product * (1 - weight), 1);
  return Math.round((1 - miss) * 100) / 100;
}

function discover(evidence) {
  const findings = new Map();
  if (!Array.isArray(evidence)) return [];

  for (const item of evidence) {
    if (typeof item?.kind !== 'string' || typeof item?.value !== 'string') continue;

    const entry = knownSignals.get(`${normalise(item.kind)}:${normalise(item.value)}`);
    if (!entry) continue;

    let finding = findings.get(entry.result.id);
    if (!finding) {
      finding = {
        ...entry.result,
        evidence: entry.value,
        accessMethods: [],
        executionEnv: entry.executionEnv,
        signals: [],
      };
      findings.set(entry.result.id, finding);
    }

    let signal = finding.signals.find(existing => existing.signal === entry.signal);
    if (!signal) {
      signal = {
        signal: entry.signal,
        kind: entry.kind,
        value: entry.value,
        explanation: entry.explanation,
        occurrences: 0,
        firstObservedAt: null,
        lastObservedAt: null,
        weight: entry.weight,
      };
      finding.signals.push(signal);
      if (!finding.accessMethods.includes(entry.accessMethod)) {
        finding.accessMethods.push(entry.accessMethod);
      }
    }

    signal.occurrences += 1;
    if (validTimestamp(item.observedAt)) {
      const at = new Date(item.observedAt).toISOString();
      if (!signal.firstObservedAt || at < signal.firstObservedAt) signal.firstObservedAt = at;
      if (!signal.lastObservedAt || at > signal.lastObservedAt) signal.lastObservedAt = at;
    }
  }

  return [...findings.values()].map(finding => {
    const confidence = combinedConfidence(finding.signals.map(signal => signal.weight));
    const signals = finding.signals.map(({ weight, ...rest }) => rest);
    return { ...finding, confidence, signals };
  });
}

const executionEnvText = { local: 'on this device', cloud: 'in the cloud' };
const accessMethodText = {
  terminal: 'a running process',
  api: 'a local API',
  file: 'a file on disk',
};

function describeFinding(finding) {
  const where = executionEnvText[finding.executionEnv] || finding.executionEnv;
  const how = finding.accessMethods.map(method => accessMethodText[method] || method);
  return `Confidence ${Math.round(finding.confidence * 100)}%. ` +
    `Runs ${where}, seen through ${how.join(' and ')}.`;
}

function describeSignal(signal) {
  const times = signal.occurrences === 1 ? 'once' : `${signal.occurrences} times`;
  return `${signal.explanation} Matched ${signal.kind} "${signal.value}" ${times}.`;
}

if (typeof document !== 'undefined') {
  const findings = discover(sampleEvidence);
  document.getElementById('summary').textContent = `Discovery results (${findings.length})`;
  const list = document.getElementById('findings');

  for (const finding of findings) {
    const row = document.createElement('li');
    const label = document.createElement('strong');
    label.textContent = `${finding.label} · ${finding.kind}`;
    const meta = document.createElement('span');
    meta.textContent = describeFinding(finding);
    const reasons = document.createElement('ul');
    reasons.className = 'reasons';
    for (const signal of finding.signals) {
      const reason = document.createElement('li');
      reason.textContent = describeSignal(signal);
      reasons.append(reason);
    }
    row.append(label, meta, reasons);
    list.append(row);
  }
}

if (typeof module !== 'undefined') {
  module.exports = { discover, sampleEvidence, signalCatalog, describeFinding, describeSignal };
}
