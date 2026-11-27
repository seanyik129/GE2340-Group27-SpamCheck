const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');

const STARTUP_TIMEOUT_MS = 180_000;
const PREDICTION_TIMEOUT_MS = 20_000;

function createModelWorker(python, bridge, cwd) {
  let worker;
  let pending;

  function finish(error, result) {
    if (!pending) return;
    const { resolve, reject, timer } = pending;
    pending = undefined;
    clearTimeout(timer);
    if (error) reject(error);
    else resolve(result);
  }

  function stop(current, message) {
    if (!current || worker !== current) return;
    worker = undefined;
    current.lines.close();
    current.child.stdin.destroy();
    current.child.stdout.destroy();
    current.child.kill();
    finish(new Error(message));
  }

  function start() {
    const child = spawn(python, ['-I', '-X', 'utf8', bridge, '--serve'], {
      cwd, windowsHide: true, stdio: ['pipe', 'pipe', 'ignore']
    });
    const lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
    const current = { child, lines, ready: false };
    worker = current;
    const stoppedMessage = 'The model process stopped. Try the last action again.';
    child.on('error', () => stop(current,
      'Python could not start. Create the project environment using the setup steps in README.md.'));
    child.once('close', () => stop(current, stoppedMessage));
    child.stdin.on('error', () => stop(current, stoppedMessage));
    lines.on('line', line => {
      if (worker !== current || !pending) return;
      try {
        const response = JSON.parse(line);
        if (typeof response.error === 'string') {
          if (current.ready) finish(new Error(response.error));
          else stop(current, response.error);
          return;
        }
        if (!Object.hasOwn(response, 'result')) throw new Error('Missing result');
        current.ready = true;
        finish(null, response.result);
      } catch {
        stop(current, 'The local model returned an invalid response.');
      }
    });
    return current;
  }

  function request(action, fields = {}) {
    if (pending) return Promise.reject(new Error('A model request is already running.'));
    const current = worker || start();
    const timeout = current.ready && action === 'predict' ? PREDICTION_TIMEOUT_MS : STARTUP_TIMEOUT_MS;
    const timeoutMessage = action === 'info'
      ? 'The model took too long to start. Select Retry loading to try again.'
      : 'The model took too long to respond. Try the last action again.';
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => stop(current, timeoutMessage), timeout);
      pending = { resolve, reject, timer };
      current.child.stdin.write(JSON.stringify({ action, ...fields }) + '\n');
    });
  }

  return { request, close: () => stop(worker, 'The app is closing.') };
}

module.exports = { createModelWorker, STARTUP_TIMEOUT_MS };
