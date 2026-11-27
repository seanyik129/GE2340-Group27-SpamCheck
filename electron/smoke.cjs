const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');
const { STARTUP_TIMEOUT_MS } = require('./model-worker.cjs');

module.exports = async function smoke(window, screenshotDir) {
  const run = source => window.webContents.executeJavaScript(source);
  async function waitFor(expression, timeout = 22_000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      if (await run(expression)) return;
      if (await run('!document.getElementById("app-error").hidden')) {
        throw new Error(await run('document.getElementById("app-error").textContent'));
      }
      await delay(100);
    }
    throw new Error(await run('document.body.innerText'));
  }
  async function capture(name) {
    if (!screenshotDir) return;
    fs.mkdirSync(screenshotDir, { recursive: true });
    fs.writeFileSync(path.join(screenshotDir, name), (await window.capturePage()).toPNG());
  }
  await waitFor('document.getElementById("default-model-notice").open', STARTUP_TIMEOUT_MS + 2_000);
  assert.equal(await run('document.getElementById("default-model-title").textContent'), 'Default model imported');
  assert.match(await run('document.getElementById("default-model-instructions").textContent'), /Change model.*\.skops.*Use default model/);
  await capture('default-model-notice.png');
  await run('document.getElementById("acknowledge-model").click()');
  await waitFor('!document.getElementById("default-model-notice").open');
  await waitFor('!document.getElementById("predict").disabled');
  assert.equal(await run('document.getElementById("model-state").textContent'), 'Frozen report model');
  assert.ok(await run('!document.getElementById("load-model").disabled'));
  assert.ok(await run('document.getElementById("feature-detail").hidden'));
  await run('document.getElementById("promo").click(); document.getElementById("predict").click()');
  await waitFor('!document.getElementById("predict").disabled');
  assert.equal(await run('document.getElementById("verdict").textContent'), 'Likely spam');
  assert.ok(await run('!document.getElementById("feature-detail").hidden'));
  assert.ok(await run('document.querySelector("#positive strong") !== null'));
  await capture('spam.png');
  await run('document.getElementById("campus").click()');
  assert.equal(await run('document.getElementById("score").textContent'), '—');
  assert.ok(await run('document.getElementById("feature-detail").hidden'));
  assert.equal(await run('document.querySelectorAll("#positive li, #negative li").length'), 0);
  await run('document.getElementById("message").value += " — bring your notes 📚"; document.getElementById("predict").click()');
  await waitFor('!document.getElementById("predict").disabled');
  assert.equal(await run('document.getElementById("verdict").textContent'), 'Not flagged as spam');
  await capture('campus.png');
  await run('document.getElementById("evidence-view").click()');
  const { metrics } = require('../results/new200/metrics.json');
  const cells = await run('["tp", "fn", "fp", "tn"].map(id => document.getElementById(id).textContent)');
  assert.deepEqual(cells, [metrics.tp, metrics.fn, metrics.fp, metrics.tn].map(String));
  assert.ok(await run('document.documentElement.scrollWidth <= innerWidth'));
  await capture('validation.png');
  window.setContentSize(760, 680);
  await waitFor('innerWidth <= 760');
  assert.ok(await run('document.documentElement.scrollWidth <= innerWidth'));
  await run('document.getElementById("check-view").click()');
  assert.ok(await run('document.documentElement.scrollWidth <= innerWidth'));
  await capture('compact.png');
  console.log('Electron smoke passed: automatic model load, startup notice, both predictions, validation counts and compact layout.');
};
