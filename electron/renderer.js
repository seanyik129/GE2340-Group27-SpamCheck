const el = id => document.getElementById(id);
const message = el('message');
const button = el('predict');
let ready = false;
let busy = false;
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
  el('app-error').hidden = true;
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
  if (!ready || busy) return;
  if (!message.value.trim()) {
    showError(new Error('Enter a message to check.'));
    message.focus();
    return;
  }
  const requestRevision = revision;
  busy = true;
  button.disabled = true;
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
    button.disabled = !ready;
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
  if (event.ctrlKey && event.key === 'Enter' && !el('check-panel').hidden) {
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

clearResult();
window.spamcheck.info().then(({ threshold, metrics }) => {
  el('model-state').textContent = 'Frozen report model';
  el('threshold').textContent = 'Decision threshold ' + percent(threshold);
  el('threshold-marker').style.setProperty('--threshold', percent(threshold));
  el('sample').textContent = metrics.n + ' held-out messages · ' + metrics.spam_n + ' spam · ' + metrics.legitimate_n + ' normal';
  for (const [label, value] of [
    ['Precision', percent(metrics.precision)], ['Recall', percent(metrics.recall)],
    ['False-positive rate', percent(metrics.false_positive_rate)], ['F1', metrics.f1.toFixed(3)]
  ]) {
    const item = document.createElement('div');
    item.className = 'metric';
    item.textContent = label;
    const number = document.createElement('strong');
    number.textContent = value;
    item.append(number);
    el('metrics').append(item);
  }
  for (const id of ['tp', 'fn', 'fp', 'tn']) el(id).textContent = metrics[id];
  ready = true;
  button.disabled = false;
}).catch(error => { el('model-state').textContent = 'Model unavailable'; showError(error); });
