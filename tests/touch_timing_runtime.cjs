// Execute emitted handlers unchanged, with independent input and dispatch clocks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(text => text.includes('var DOUBLE_TAP_MS = 350;'));
assert.ok(script);
const start = script.indexOf('  // --- Touch swipe and double tap (mobile / tablet) ---');
const end = script.indexOf('  // --- Toggle nav chrome', start);
assert.ok(start >= 0 && end > start);

function fixture() {
  let now = 10000;
  const listeners = {}, calls = [];
  const context = vm.createContext({
    Date: {now: () => now}, window: {visualViewport: {scale: 1}},
    document: {addEventListener(type, callback) { listeners[type] = callback; }},
    tableGesture: null, tableScrollViewport: () => null,
    isInteractive: () => false, helpIsOpen: () => false,
    cancelMouseSequence() { calls.push('cancel'); },
    runStepped: callback => callback(), stepForward() { calls.push('next'); },
    stepBackward() { calls.push('previous'); },
    rememberTouchPosition() { calls.push('remember'); },
    restoreTouchPosition() { calls.push('restore'); },
    toggleNavVisibility() { calls.push('toggle'); }, swallowClicksUntil: 0,
  });
  vm.runInContext(script.slice(start, end), context);
  return {context, calls,
    send(type, timestamp, wall, x = 195, count = type === 'touchend' ? 0 : 1) {
      now = wall;
      const point = {clientX: x, clientY: 400};
      listeners[type]({type, timeStamp: timestamp,
        touches: Array.from({length: count}, () => point), changedTouches: [point]});
    }};
}

{
  const h = fixture();
  h.send('touchstart', 0, 10000); h.send('touchend', 20, 10010);
  h.send('touchstart', 60, 10480); h.send('touchend', 80, 10490);
  assert.deepEqual(h.calls, ['remember','restore','toggle'], 'queued short input is still a double tap');
  assert.equal(h.context.swallowClicksUntil, 10490 + 450,
    'compatibility-click quarantine starts at delivery, not at the old input timestamp');
}
{
  const h = fixture();
  h.send('touchstart', 0, 10000); h.send('touchend', 600, 10010);
  h.send('touchstart', 700, 10100); h.send('touchend', 720, 10110);
  assert.deepEqual(h.calls, ['remember'], 'a queued long press cannot become the first tap of a pair');
}
{
  const h = fixture();
  h.send('touchstart', 0, 10000); h.send('touchend', 20, 10010);
  h.send('touchstart', 400, 10020); h.send('touchend', 420, 10030);
  assert.deepEqual(h.calls, ['remember','remember'], 'late independent taps do not pair when delivered together');
}
for (const [x, action] of [[100, 'next'], [280, 'previous']]) {
  const h = fixture();
  h.send('touchstart', 10, 10000); h.send('touchend', 100, 10900, x);
  assert.deepEqual(h.calls, [action], 'short native swipe duration survives delivery delay');
}
{
  const h = fixture();
  h.send('touchstart', 0, 10000); h.send('touchend', 0, 10001);
  h.send('touchstart', 30, 10030); h.send('touchend', 40, 10040);
  assert.deepEqual(h.calls, ['remember','restore','toggle'], 'zero is a valid input timestamp');
}
{
  const h = fixture();
  h.send('touchstart', 0, 10000); h.send('touchend', 20, 10020);
  h.context.isInteractive = () => true;
  h.send('touchstart', 30, 10030); h.send('touchend', 40, 10040);
  h.context.isInteractive = () => false;
  h.send('touchstart', 60, 10060); h.send('touchend', 80, 10080);
  assert.deepEqual(h.calls, ['remember','remember'], 'controls retain ownership and invalidate the old tap');
}
console.log('Touch event clock checks passed');
