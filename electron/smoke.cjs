const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');

module.exports = async function smoke(window, screenshotDir) {
  const run = source => window.webContents.executeJavaScript(source);
  async function waitFor(expression) {
    const deadline = Date.now() + 22000;
    while (Date.now() < deadline) {
      if (await run(expression)) return;
      await delay(100);
    }
    throw new Error(await run('document.body.innerText'));
  }
  async function capture(name) {
    if (!screenshotDir) return;
    fs.mkdirSync(screenshotDir, { recursive: true });
    fs.writeFileSync(path.join(screenshotDir, name), (await window.capturePage()).toPNG());
  }
  await waitFor('!document.getElementById("predict").disabled');
  assert.equal(await run('document.getElementById("model-state").textContent'), 'Frozen report model');
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
  await run('document.getElementById("predict").click()');
  await waitFor('!document.getElementById("predict").disabled');
  assert.equal(await run('document.getElementById("verdict").textContent'), 'Not flagged as spam');
  await capture('campus.png');
  await run('document.getElementById("evidence-view").click()');
  assert.deepEqual(await run('["tp", "fn", "fp", "tn"].map(id => document.getElementById(id).textContent)'), ['89', '11', '2', '98']);
  assert.ok(await run('document.documentElement.scrollWidth <= innerWidth'));
  await capture('validation.png');
  window.setContentSize(760, 680);
  await waitFor('innerWidth <= 760');
  assert.ok(await run('document.documentElement.scrollWidth <= innerWidth'));
  await run('document.getElementById("check-view").click()');
  assert.ok(await run('document.documentElement.scrollWidth <= innerWidth'));
  await capture('compact.png');
  console.log('Electron smoke passed: frozen model, both predictions, explanations, validation counts and compact layout.');
};
