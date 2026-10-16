// Run the emitted lifecycle unchanged; only the browser API acknowledgement is controlled.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(text => text.includes('function requestWakeLock()'));
assert.ok(script);
const start = script.indexOf('  var wakeLock = null;');
const end = script.indexOf('  function handleFullscreenChange()', start);
assert.ok(start >= 0 && end > start);

function fixture({available = true, throws = false} = {}) {
  const requests = [], callbacks = {};
  const document = {visibilityState: 'visible', fullscreenElement: {},
    addEventListener(type, callback) { callbacks[type] = callback; }};
  const navigator = {};
  if (available) navigator.wakeLock = {request(type) {
    assert.equal(type, 'screen');
    if (throws) throw Error('unavailable');
    let resolve, reject;
    const promise = new Promise((done, fail) => { resolve = done; reject = fail; });
    requests.push({resolve, reject});
    return promise;
  }};
  const context = vm.createContext({document, navigator,
    currentFullscreenElement: () => document.fullscreenElement});
  vm.runInContext(script.slice(start, end), context);
  return {document, requests, context,
    request: () => context.requestWakeLock(),
    release: () => context.releaseWakeLock(),
    visibility(value) { document.visibilityState = value; callbacks.visibilitychange(); }};
}
function sentinel() {
  const listeners = [];
  return {released: false, releases: 0,
    addEventListener(type, callback) { assert.equal(type, 'release'); listeners.push(callback); },
    expire() { this.released = true; listeners.forEach(callback => callback()); },
    release() { this.releases++; this.expire(); return Promise.resolve(); }};
}
async function settle() { await Promise.resolve(); await Promise.resolve(); }

(async () => {
  const late = fixture();
  late.request();
  late.document.fullscreenElement = null;
  late.release();
  const orphan = sentinel();
  late.requests[0].resolve(orphan);
  await settle();
  assert.equal(orphan.releases, 1, 'a late acknowledgement after exit must not retain a screen lock');

  const overlapping = fixture();
  overlapping.request(); overlapping.request();
  assert.equal(overlapping.requests.length, 1, 'duplicate notifications share one pending request');
  overlapping.release();
  overlapping.request();
  const newer = sentinel(), older = sentinel();
  overlapping.requests[1].resolve(newer); await settle();
  overlapping.requests[0].resolve(older); await settle();
  assert.equal(older.releases, 1, 'an earlier fullscreen session cannot take ownership');
  assert.equal(newer.releases, 0, 'a late old reply does not release the current session');
  overlapping.release();
  assert.equal(newer.releases, 1);

  const visible = fixture();
  visible.request();
  const first = sentinel(); visible.requests[0].resolve(first); await settle();
  visible.visibility('hidden');
  assert.equal(first.releases, 1, 'hidden documents release their active screen lock');
  visible.visibility('visible');
  assert.equal(visible.requests.length, 2, 'a visible fullscreen document reacquires the browser-released lock');
  const second = sentinel(); visible.requests[1].resolve(second); await settle();
  second.expire();
  visible.request();
  assert.equal(visible.requests.length, 3, 'a released sentinel is never mistaken for an active lock');

  const pending = fixture();
  pending.request(); pending.visibility('hidden'); pending.visibility('visible');
  const hiddenReply = sentinel(), shownReply = sentinel();
  pending.requests[0].resolve(hiddenReply); await settle();
  pending.request();
  assert.equal(pending.requests.length, 2, 'a stale acknowledgement cannot clear the newer pending flag');
  pending.requests[1].resolve(shownReply); await settle();
  assert.equal(hiddenReply.releases, 1); assert.equal(shownReply.releases, 0);

  const rejected = fixture();
  rejected.request(); rejected.requests[0].reject(Error('refused')); await settle();
  rejected.request(); assert.equal(rejected.requests.length, 2, 'a refusal permits a later intentional request');
  rejected.release(); rejected.request();
  rejected.requests[1].reject(Error('old request')); await settle();
  rejected.request(); assert.equal(rejected.requests.length, 3, 'an old rejection cannot clear a newer pending request');

  const ordinary = fixture(); ordinary.document.fullscreenElement = null;
  ordinary.request(); ordinary.visibility('visible');
  assert.equal(ordinary.requests.length, 0, 'ordinary reading never acquires a screen wake lock');
  const hidden = fixture(); hidden.document.visibilityState = 'hidden'; hidden.request();
  assert.equal(hidden.requests.length, 0, 'hidden reading never starts an acquisition');
  fixture({available: false}).request();
  fixture({throws: true}).request();
  console.log('Screen wake lock lifecycle checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
