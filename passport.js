const form = document.getElementById('passport-form');
const statusText = document.getElementById('passport-status');
const result = document.getElementById('passport-result');
const passportId = document.getElementById('passport-id');
const artifactHash = document.getElementById('artifact-hash');
const verifyAgain = document.getElementById('verify-again');
const fieldset = form.querySelector('fieldset');

async function coreRequest(path, body) {
  const options = { method: 'POST', signal: AbortSignal.timeout(15_000) };
  if (body) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.error?.message || `Core returned HTTP ${response.status}.`);
  }
  return payload;
}

async function verify(id) {
  statusText.textContent = 'Checking the stored passport with Forkit Core…';
  try {
    const check = await coreRequest(`/verify/${encodeURIComponent(id)}`);
    if (check.valid !== true || check.stored_id !== id) {
      throw new Error('Core did not confirm this passport ID.');
    }
    statusText.textContent = 'Passport identity verified by Forkit Core.';
  } catch (error) {
    statusText.textContent = `Passport verification failed. ${error.message}`;
  }
}

function setBusy(busy) {
  fieldset.disabled = busy;
  verifyAgain.disabled = busy;
}

async function register(event) {
  event.preventDefault();
  const fields = new FormData(form);
  const file = fields.get('artifact');
  const name = fields.get('name').trim();
  const creator = fields.get('creator').trim();

  result.hidden = true;
  if (!file.size || file.size > 64 * 1024 * 1024) {
    statusText.textContent = 'Choose a nonempty model file up to 64 MiB.';
    return;
  }
  if (!name || !creator) {
    statusText.textContent = 'Enter a model name and creator.';
    return;
  }

  setBusy(true);
  statusText.textContent = 'Hashing the selected file…';
  try {
    const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
    statusText.textContent = 'Registering the passport with Forkit Core…';
    const passport = await coreRequest('/models', {
      name,
      version: fields.get('version'),
      creator: { name: creator },
      task_type: fields.get('task_type'),
      architecture: fields.get('architecture'),
      artifact_hash: hash,
      artifact_files: [file.name],
    });
    if (!/^[a-f0-9]{64}$/.test(passport.id) || passport.artifact_hash !== hash) {
      throw new Error('Core returned an unexpected passport record.');
    }
    passportId.textContent = passport.id;
    artifactHash.textContent = hash;
    result.hidden = false;
    await verify(passport.id);
  } catch (error) {
    statusText.textContent = `Passport creation failed. ${error.message}`;
  } finally {
    setBusy(false);
  }
}

if (location.hostname === '127.0.0.1' && location.pathname === '/footprints/') {
  document.getElementById('local-service-note').hidden = true;
  form.hidden = false;
  form.addEventListener('submit', register);
  verifyAgain.addEventListener('click', async () => {
    setBusy(true);
    try {
      await verify(passportId.textContent);
    } finally {
      setBusy(false);
    }
  });
}
