const el = id => document.getElementById(id);
const message = el('message');
const button = el('predict');
const loadModelButton = el('load-model');
const restoreModelButton = el('restore-model');
const retryModelButton = el('retry-model');
const modelNotice = el('default-model-notice');
let ready = false;
let busy = false;
let changingModel = false;
let revision = 0;
const examples = {
  promo: 'Congratulations! Claim your free prize today. Enter now at https://example.com/claim and reply WIN to receive your cash reward.',
  campus: 'Our project group meets at the library at 3 pm tomorrow. Please bring your notes for the presentation.'
};
const percent = value => (value * 100).toFixed(1) + '%';

function showError(error) {
  el('app-error').textContent = error.message.replace(/^Error invoking remote method '[^']+': Error: /, '');
  el('app-error').hidden = false;
}

function syncButtons() {
  const locked = busy || changingModel;
  button.disabled = !ready || locked;
  loadModelButton.disabled = locked;
  restoreModelButton.disabled = locked;
  retryModelButton.disabled = locked;
}

function clearResult() {
  revision++;
  el('verdict').textContent = 'Awaiting a message';
  el('verdict').parentElement.className = 'outcome';
  el('score').textContent = '—';
  el('meter').value = 0;
  el('language').hidden = true;
  el('language').textContent = '';
  el('positive').replaceChildren();
  el('negative').replaceChildren();
  el('feature-empty').hidden = false;
  el('feature-detail').hidden = true;
  if (ready) el('app-error').hidden = true;
}

function renderFeatures(id, values) {
  const rows = values.slice(0, 3).map(item => {
    const row = document.createElement('li');
    const feature = document.createElement('span');
    feature.textContent = item.feature.replace('word__', 'Word · ').replace('char__', 'Fragment · ');
    const value = document.createElement('strong');
    value.textContent = (item.contribution > 0 ? '+' : '') + item.contribution.toFixed(3);
    row.append(feature, value);
    return row;
  });
  if (!rows.length) {
    const empty = document.createElement('li');
    empty.textContent = 'No contributing features';
    rows.push(empty);
  }
  el(id).replaceChildren(...rows);
}

async function predict() {
  if (!ready || busy || changingModel) return;
  if (!message.value.trim()) {
    showError(new Error('Enter a message to check.'));
    message.focus();
    return;
  }
  const requestRevision = revision;
  busy = true;
  syncButtons();
  button.textContent = 'Checking…';
  el('app-error').hidden = true;
  try {
    const result = await window.spamcheck.predict(message.value);
    if (requestRevision !== revision) return;
    el('verdict').textContent = result.label === 'spam' ? 'Likely spam' : 'Not flagged as spam';
    el('verdict').parentElement.className = 'outcome ' + result.label;
    el('score').textContent = percent(result.probability);
    el('meter').value = result.probability;
    el('language').textContent = result.language_note;
    el('language').hidden = !result.language_note;
    for (const id of ['positive', 'negative']) renderFeatures(id, result.explanation[id]);
    el('feature-empty').hidden = true;
    el('feature-detail').hidden = false;
  } catch (error) {
    if (requestRevision === revision) showError(error);
  } finally {
    busy = false;
    syncButtons();
    button.textContent = 'Check message';
  }
}

for (const [id, example] of Object.entries(examples)) {
  el(id).addEventListener('click', () => {
    message.value = example;
    clearResult();
    message.focus();
  });
}
message.addEventListener('input', clearResult);
el('clear').addEventListener('click', () => { message.value = ''; clearResult(); message.focus(); });
button.addEventListener('click', predict);
document.addEventListener('keydown', event => {
  if (event.ctrlKey && event.key === 'Enter' && !el('check-panel').hidden && !modelNotice.open) {
    event.preventDefault();
    predict();
  }
});
for (const view of ['check', 'evidence']) {
  el(view + '-view').addEventListener('click', () => {
    for (const name of ['check', 'evidence']) {
      el(name + '-panel').hidden = view !== name;
      el(name + '-view').setAttribute('aria-pressed', String(view === name));
    }
  });
}

function showMetrics(metrics) {
  el('evaluation-details').hidden = !metrics;
  if (!metrics) {
    el('sample').textContent = 'The report’s validation results are available for the default model.';
    return;
  }
  el('sample').textContent = metrics.n + ' held-out messages · ' + metrics.spam_n + ' spam · ' + metrics.legitimate_n + ' normal';
  const cards = [
    ['Precision', percent(metrics.precision)], ['Recall', percent(metrics.recall)],
    ['False-positive rate', percent(metrics.false_positive_rate)], ['F1', metrics.f1.toFixed(3)]
  ].map(([label, value]) => {
    const item = document.createElement('div');
    item.className = 'metric';
    item.textContent = label;
    const number = document.createElement('strong');
    number.textContent = value;
    item.append(number);
    return item;
  });
  el('metrics').replaceChildren(...cards);
  for (const id of ['tp', 'fn', 'fp', 'tn']) el(id).textContent = metrics[id];
}

function showModel({ threshold, metrics, is_default: isDefault }) {
  clearResult();
  el('model-state').textContent = isDefault ? 'Frozen report model' : 'Custom model';
  el('app-error').hidden = true;
  restoreModelButton.hidden = isDefault;
  retryModelButton.hidden = true;
  el('threshold').textContent = 'Decision threshold ' + percent(threshold);
  el('threshold-marker').style.setProperty('--threshold', percent(threshold));
  showMetrics(metrics);
  ready = true;
}

function announceDefault(modelHash) {
  const key = 'spamcheck.default-model.' + modelHash;
  try {
    if (localStorage.getItem(key)) return;
  } catch {
    // The app can show the notice even if the browser profile disallows storage.
  }
  modelNotice.addEventListener('close', () => {
    try { localStorage.setItem(key, 'seen'); } catch {}
  }, { once: true });
  modelNotice.showModal();
}

async function loadModel(operation, announce = false) {
  if (busy || changingModel) return;
  changingModel = true;
  if (!ready) {
    el('model-state').textContent = 'Loading model';
    el('app-error').hidden = true;
    el('threshold').textContent = 'Preparing the model. The first launch may take longer.';
  }
  syncButtons();
  try {
    const info = await operation();
    if (!info) return;
    showModel(info);
    if (announce && info.is_default) announceDefault(info.model_sha256);
  } catch (error) {
    if (!ready) {
      el('model-state').textContent = 'Model unavailable';
      restoreModelButton.hidden = false;
      retryModelButton.hidden = false;
      el('threshold').textContent = 'The model is unavailable.';
    }
    showError(error);
  } finally {
    changingModel = false;
    syncButtons();
  }
}

loadModelButton.addEventListener('click', () => loadModel(window.spamcheck.installModel));
restoreModelButton.addEventListener('click', () => loadModel(window.spamcheck.restoreModel));
retryModelButton.addEventListener('click', () => loadModel(window.spamcheck.info, true));
clearResult();
loadModel(window.spamcheck.info, true);
