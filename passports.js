// Passports view: Forkit Core passports for AI tools found by the device scan
// (one per installation) and for agent setups found by the repository scan, plus
// every passport in the local registry with its checks:
//   record     the stored passport still matches its ID (Forkit Core's check)
//   install    tool passports: the installed program still matches the fingerprint
//   publisher  tool passports: the program is still signed by the same publisher
//   setup      repo passports: the agent files still match the fingerprint
// See tool_passports.py and repo_passports.py for what goes into a passport.

const RECORD_BADGES = {
  intact: { text: '✓ Record intact', tone: 'ok', title: 'The stored passport still matches its ID' },
};
const SETUP_BADGES = {
  unchanged: { text: '✓ Setup unchanged', tone: 'ok', title: 'The agent files still match the passport' },
  changed: { text: '⚠ Setup changed', tone: 'warn', title: 'The agent files were edited since this passport' },
  'files-removed': { text: '⚠ Agent files removed', tone: 'warn', title: 'The repository no longer has these agent files' },
  'repo-missing': { text: 'Repository not found', tone: 'muted', title: 'The repository moved or was deleted' },
};
const INSTALL_BADGES = {
  unchanged: () => ({ text: '✓ Same program', tone: 'ok', title: 'The installed program still matches the passport' }),
  updated: passport => ({ text: `New version installed: v${passport.current_version}`, tone: 'info',
    title: 'The tool was updated since this passport' }),
  changed: () => ({ text: '⚠ Program changed', tone: 'warn',
    title: 'The program changed but reports the same version: rebuilt or replaced' }),
  missing: () => ({ text: 'Not installed', tone: 'muted', title: 'This installation is no longer on the device' }),
};
const PUBLISHER_BADGES = {
  verified: { text: '✓ Publisher verified', tone: 'ok', title: 'Still signed by the same publisher' },
  changed: { text: '⚠ Publisher changed', tone: 'warn', title: 'Now signed by someone else, or no longer signed' },
  user: { text: 'Vouched by you', tone: 'muted', title: 'No publisher signature; a person vouched for this tool' },
};
const NEEDS_ATTENTION = {
  setup: ['changed', 'files-removed'], install: ['changed'], publisher: ['changed'],
};

function passportBadges(passport) {
  const badges = [{ text: `v${passport.version}`, tone: 'info' }];
  badges.push(RECORD_BADGES[passport.record]
    ?? { text: '⚠ Record altered', tone: 'warn', title: `Forkit Core check: ${passport.record}` });
  if (passport.kind === 'repo-agent' && SETUP_BADGES[passport.setup]) badges.push(SETUP_BADGES[passport.setup]);
  if (passport.kind === 'device-tool') {
    if (INSTALL_BADGES[passport.install]) badges.push(INSTALL_BADGES[passport.install](passport));
    if (PUBLISHER_BADGES[passport.publisher]) badges.push(PUBLISHER_BADGES[passport.publisher]);
  }
  if (passport.kind === 'provider-model') badges.push({ text: 'Provider model', tone: 'muted' });
  return badges;
}

function needsAttention(passport) {
  return passport.record !== 'intact'
    || Object.entries(NEEDS_ATTENTION).some(([check, states]) => states.includes(passport[check]));
}

function summarizePassports(passports) {
  return {
    tools: passports.filter(passport => passport.kind === 'device-tool').length,
    agents: passports.filter(passport => passport.kind === 'repo-agent').length,
    models: passports.filter(passport => passport.kind === 'model').length,
    attention: passports.filter(needsAttention).length,
  };
}

// ── passports view (browser only) ─────────────────────────────────────────────

let passportDraft = null;

function hasPublisherSignature(signer) {
  return typeof signer === 'string' && !['unsigned', 'invalid', 'script'].includes(signer);
}

// From a repository card: a passport for one agent setup of the repository.
function startAgentPassport(draft) {
  openPassportForm({ type: 'repo', ...draft });
}

// From a device card: a passport for one installation of a scanned tool.
function startToolPassport(draft) {
  openPassportForm({ type: 'tool', ...draft });
}

function openPassportForm(draft) {
  passportDraft = draft;
  renderPassportForm();
  showView('passports');
  document.getElementById('agent-passport').scrollIntoView({ block: 'start' });
}

function readStored(key) {
  try { return localStorage.getItem(key) ?? ''; } catch { return ''; }
}

function writeStored(key, value) {
  try { localStorage.setItem(key, value); } catch { /* storage unavailable: just don't remember */ }
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(payload?.detail ?? `Footprints returned HTTP ${response.status}.`);
    error.payload = payload;
    throw error;
  }
  return payload;
}

function renderPassportForm() {
  const container = document.getElementById('agent-passport');
  const draft = passportDraft;
  if (!draft) {
    container.replaceChildren(el('p', { class: 'muted' },
      'Choose "Create passport" on a tool in the Device tab, or on an agent setup in the Repositories tab.'));
    return;
  }
  const tool = draft.type === 'tool';
  // Only an installation whose own program carries a valid signature gets its publisher from it;
  // e.g. a Chrome extension has no signature even when the tool's other parts do.
  const signed = tool && hasPublisherSignature(draft.installation.signer) && draft.verification?.status === 'confirmed';
  const detectedVersion = tool ? draft.installation.version : null;
  const status = el('p', { class: 'status', role: 'status' });
  const version = el('input', { name: 'version', value: detectedVersion ?? draft.suggestedVersion ?? draft.version ?? '1.0.0',
    required: true, pattern: '[0-9]+\\.[0-9]+(\\.[0-9]+)?', title: 'A version such as 1.0 or 1.0.0',
    readonly: Boolean(detectedVersion) });
  const creator = el('input', { name: 'creator', value: readStored('footprints.creator'), required: !signed, maxlength: '100' });
  const organization = el('input', { name: 'organization', value: readStored('footprints.organization'), maxlength: '100' });
  const submit = el('button', { type: 'submit', class: 'primary' }, tool ? 'Create tool passport' : 'Create agent passport');
  const form = el('form', { class: 'card agent-form' },
    el('h3', {}, tool ? `${draft.label}: ${installationLabel(draft.installation)}` : `${draft.label} setup`),
    el('p', { class: 'muted small mono' }, tool ? draft.installation.value : draft.repo),
    tool
      ? el('p', { class: 'muted small' }, 'Footprints finds this program on the device and records a fingerprint of it. '
        + 'The passport later shows whether the same program is still installed.')
      : [draft.files ? el('p', { class: 'small' }, 'Fingerprinted files: ', draft.files.join(', ')) : null,
        el('p', { class: 'muted small' },
          'The passport records a fingerprint of these files, never their text. If they change later, the passport shows it.')],
    el('fieldset', {},
      el('label', {}, detectedVersion ? 'Version (detected)' : 'Version', version),
      signed
        ? el('p', { class: 'small' }, el('strong', {}, 'Publisher: '),
          `${draft.verification.text.replace(/^Signed by /, '')}, taken from the verified code signature.`)
        : [el('label', {}, tool ? 'Vouched for by (no verified publisher)' : 'Vouched for by', creator),
          el('label', {}, 'Organization (optional)', organization)],
      submit),
    status);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    submit.disabled = true;
    status.textContent = 'Creating the passport with Forkit Core…';
    if (!signed) {
      writeStored('footprints.creator', creator.value.trim());
      writeStored('footprints.organization', organization.value.trim());
    }
    const common = { version: version.value.trim(), creator: creator.value.trim(), organization: organization.value.trim() };
    try {
      const result = tool
        ? await postJson('/passports/tool', {
          finding: draft.finding, label: draft.label, tool_kind: draft.toolKind, ...draft.installation, ...common,
        })
        : await postJson('/passports/repo-agent', { repo: draft.repo, tool: draft.tool, ...common });
      const { name, version: created, id, creator: by } = result.passport;
      status.textContent = result.status === 'already-registered'
        ? `This exact ${tool ? 'program' : 'setup'} already has a passport: ${name} v${created} (${id.slice(0, 12)}…).`
        : `Created ${name} v${created} for ${by.name} (${id.slice(0, 12)}…). Record check: `
          + (result.check?.valid ? 'intact.' : 'failed.');
      await loadPassports();
    } catch (error) {
      if (error.payload?.suggested_version) version.value = error.payload.suggested_version;
      status.textContent = `Passport not created. ${error.message}`;
    } finally {
      submit.disabled = false;
    }
  });
  container.replaceChildren(form);
}

function passportCard(passport) {
  const repoAgent = passport.kind === 'repo-agent';
  const deviceTool = passport.kind === 'device-tool';
  const title = repoAgent ? `${passport.tool_label} · ${passport.repo.split(/[\\/]/).pop()}`
    : deviceTool ? passport.label : passport.name;
  const subtitle = repoAgent ? passport.repo
    : deviceTool ? `${passport.surface.replace(/-/g, ' ')} · ${passport.installation}` : passport.description ?? passport.type;
  const newSetupVersion = repoAgent && passport.setup === 'changed' && passport.suggested_version;
  const newToolVersion = deviceTool && passport.install === 'updated' && passport.request;
  return el('li', { class: `card${needsAttention(passport) ? ' card-warn' : ''}` },
    el('div', { class: 'card-head' },
      el('div', {}, el('h3', {}, title), el('p', { class: 'muted small mono' }, subtitle)),
      el('div', { class: 'badges' }, passportBadges(passport).map(item => badge(item.text, item.tone, item.title)))),
    el('dl', { class: 'meta-grid' },
      el('dt', {}, deviceTool && passport.creator_source === 'code-signature' ? 'Publisher' : 'Vouched for by'),
      el('dd', {}, [passport.creator, passport.organization].filter(Boolean).join(', ') || 'unknown',
        deviceTool && passport.creator_source === 'code-signature' ? el('span', { class: 'muted' }, ' (from code signature)') : null),
      el('dt', {}, 'Created'), el('dd', {}, formatDate(passport.created_at, true)),
      el('dt', {}, 'Passport ID'), el('dd', { class: 'mono', title: passport.id }, `${passport.id.slice(0, 16)}…`),
      (repoAgent || deviceTool) && passport.parent ? [el('dt', {}, 'Lineage'),
        el('dd', { class: 'mono', title: passport.parent }, `follows ${passport.parent.slice(0, 12)}…`)] : null,
      repoAgent && passport.tools.length ? [el('dt', {}, 'MCP servers'), el('dd', {}, passport.tools.join(', '))] : null,
      deviceTool ? [el('dt', {}, 'Fingerprint of'), el('dd', {}, passport.fingerprinted.join(', '))] : null),
    repoAgent ? el('div', { class: 'tags' }, passport.files.map(file => el('span', { class: 'tag' }, file))) : null,
    newSetupVersion ? el('button', {
      type: 'button', class: 'secondary',
      onclick: () => startAgentPassport({
        repo: passport.repo, tool: passport.tool, label: passport.tool_label, files: null, version: passport.suggested_version,
      }),
    }, `Create v${passport.suggested_version} for the changed setup`) : null,
    newToolVersion ? el('button', {
      type: 'button', class: 'secondary',
      onclick: () => {
        const { finding, label, tool_kind: toolKind, ...installation } = passport.request;
        startToolPassport({
          finding, label, toolKind,
          installation: { ...installation, version: passport.current_version,
            signer: passport.publisher === 'verified' ? 'verified' : undefined },
          verification: passport.publisher === 'verified' ? { status: 'confirmed', text: `Signed by ${passport.creator}` } : null,
        });
      },
    }, `Create passport for v${passport.current_version}`) : null);
}

async function loadPassports() {
  const status = document.getElementById('passports-status');
  status.textContent = 'Checking passports…';
  try {
    const { passports } = await postJson('/passports/list', {});
    const totals = summarizePassports(passports);
    renderTiles(document.getElementById('passport-tiles'), [
      { label: 'Tool passports', value: totals.tools },
      { label: 'Repository setup passports', value: totals.agents },
      { label: 'Model passports', value: totals.models },
      { label: 'Need attention', value: totals.attention, tone: totals.attention ? 'warn' : 'ok',
        hint: 'Record altered, program or publisher changed, or agent files changed' },
    ]);
    document.getElementById('passport-list').replaceChildren(...(passports.length ? passports.map(passportCard)
      : [el('li', { class: 'empty' }, 'No passports yet.')]));
    status.textContent = `Checked ${passports.length} passport${passports.length === 1 ? '' : 's'} `
      + `at ${formatDate(new Date().toISOString(), true)}.`;
  } catch (error) {
    status.textContent = `Could not load passports. ${error.message}`;
  }
}

if (typeof document !== 'undefined' && isLocalService()) {
  document.getElementById('passports-local').hidden = false;
  document.getElementById('refresh-passports').addEventListener('click', loadPassports);
  renderPassportForm();
  loadPassports();
}

if (typeof module !== 'undefined') {
  module.exports = { passportBadges, summarizePassports, needsAttention, hasPublisherSignature };
}
