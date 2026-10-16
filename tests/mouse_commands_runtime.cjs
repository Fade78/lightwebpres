// Execute the generated controller and event adapter with controlled browser
// acknowledgements. This tests state/races, not native capture or screen geometry.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
const source = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(script => script.includes('function createMouseSequence()'));
assert.ok(source, 'the built page carries its mouse controller');
function between(start, end) {
  const at = source.indexOf(start);
  assert.ok(at >= 0, start);
  const until = source.indexOf(end, at + start.length);
  assert.ok(until > at, end);
  return source.slice(at, until);
}
function fn(name) {
  const at = source.indexOf('  function ' + name + '(');
  assert.ok(at >= 0, name);
  return source.slice(at, source.indexOf('\n  }', at) + 4);
}
function element() {
  const names = new Set();
  return {style: {}, dataset: {}, attrs: {}, hidden: true,
    closest: () => null,
    classList: {contains: name => names.has(name), add: name => names.add(name),
      remove: name => names.delete(name), toggle(name, yes = !names.has(name)) {
        if (yes) names.add(name); else names.delete(name); return yes;
      }}, setAttribute(name, value) { this.attrs[name] = value; }};
}
function surface() {
  const listeners = new Map();
  return {addEventListener(type, callback) {
    if (!listeners.has(type)) listeners.set(type, []);
    listeners.get(type).push(callback);
  }, fire(type, event = {}) {
    for (const callback of listeners.get(type) || []) {
      callback(event); if (event.stopped) break;
    }
  }};
}
function harness(primaryFine = true) {
  let now = 10000, nextTimer = 0;
  const timers = new Map(), calls = [];
  const root = element(), body = element(), window = surface(), document = surface();
  const status = element(), menu = element(), pause = element();
  Object.assign(document, {documentElement: root, body, pointerLockElement: null,
    getElementById: id => ({pointerLockStatus: status, menuPointerLock: menu})[id] || null});
  window.getSelection = () => ({removeAllRanges() { calls.push('clear-selection'); }});
  window.pageYOffset = 80;
  let top = 0;
  const slides = [0, 1, 2].map(() => ({getBoundingClientRect: () => ({top})}));
  const context = {window, document, Date: {now: () => now},
    setTimeout(callback, delay) { const id = ++nextTimer; timers.set(id, {callback, at: now + delay}); return id; },
    clearTimeout: id => timers.delete(id),
    lwpString: key => key, hasFinePointer: primaryFine, isFullscreen: () => false,
    navButtons: element(), navDots: element(), slideCounter: element(), pauseOverlay: pause,
    multiTouchActive: false, multiTouchClicksUntil: 0, cardLongPressClick: null,
    helpIsOpen: () => false, tableScrollViewport: () => null,
    foregroundSurface: null,
    modalWheelSurface: () => context.foregroundSurface,
    modalWheelCanScroll: () => true,
    clearCardLongPress: () => {}, clearCardLongPressClick: () => {},
    currentFullscreenElement: () => null,
    requestWakeLock: () => {}, releaseWakeLock: () => {}, scheduleReadingLayout: () => {},
    clickNavigationDirection: direction => direction, isScrolling: false,
    isIndex: false, slides, current: 1, currentVisible: () => 0, jumpBuffer: '',
    syncCurrentToViewport: () => context.current,
    overflowsViewport: () => false, scrollWithinSlide: () => {},
    goTo: (index, instant) => { calls.push(['slide', index, instant]); context.current = index; },
    stepIndexCards: direction => { calls.push(['card', direction]); return true; },
    goHome: () => calls.push('home'), goToFirstSlide: () => calls.push('beginning'),
    jumpScrollTo: y => calls.push(['jump', y]),
  };
  root.requestFullscreen = () => calls.push('fullscreen');
  document.exitFullscreen = () => calls.push('exit-fullscreen');
  root.requestPointerLock = () => calls.push('lock-request');
  document.exitPointerLock = () => {
    calls.push('unlock'); document.pointerLockElement = null; document.fire('pointerlockchange');
  };
  vm.createContext(context);
  vm.runInContext([
    between('  // Mouse command grammar.', '  // The cursor is hidden'),
    between('  var fsMoveStart = 0;', '  // Wake lock:'),
    between('  function setNavIdle(', '  function rememberTouchPosition('),
    between('  var idleTimer = null;', '  function activateSeriesView('),
    between('  // F, the presenter menu,', '  // Mouse command grammar.'),
    fn('handleFullscreenChange'), fn('closePause'), fn('isPauseNavigationKey'), fn('togglePause'),
    fn('changeSlide'), fn('mouseClickStep'), fn('atSlideTop'), fn('goToBeginningOrHome'),
    between("  // A modal's own overlay may scroll", '  function slideTitle('),
    between('  var consumedMouseButtons = {};', '  // --- Touch swipe and double tap'),
  ].join('\n'), context);
  function fire(type, fields = {}) {
    const event = {button: 0, detail: 1, target: root, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; },
      stopPropagation() { this.stopped = true; },
      stopImmediatePropagation() { this.stopped = true; }, ...fields};
    window.fire(type, event); if (!event.stopped) document.fire(type, event);
    return event;
  }
  return {context, calls, root, document, status, menu, pause, fire,
    press: button => fire('mousedown', {button}),
    moveTop: value => top = value,
    tick(milliseconds) {
      now += milliseconds;
      for (const [id, timer] of [...timers]) if (timer.at <= now) {
        timers.delete(id); timer.callback();
      }
    },
    acknowledge() { document.pointerLockElement = root; document.fire('pointerlockchange'); },
  };
}

(async () => {
  for (const [buttons, action] of [[[1, 0], 'fullscreen'], [[1, 2], 'lock-request'],
    [[1, 1, 0], 'home']]) {
    const h = harness(); buttons.forEach(h.press);
    assert.ok(h.calls.includes(action), JSON.stringify(buttons));
    assert.equal(h.context.mouseSequence.active(), false);
  }
  {
    const h = harness(); h.press(1); h.tick(800); h.press(1); h.tick(800); h.press(2);
    assert.equal(h.pause.classList.contains('open'), true, '2M renews its deadline');
    [1, 1, 2].forEach(h.press);
    assert.equal(h.pause.classList.contains('open'), false, 'theme pause toggles');
  }
  for (const count of [1, 2]) {
    const h = harness(); for (let i = 0; i < count; i++) h.press(1);
    h.tick(900); assert.equal(h.press(0).defaultPrevented, false);
    assert.equal(h.calls.length, 0, 'an expired prefix has no action');
  }
  {
    const h = harness(); [1, 1, 1].forEach(h.press);
    assert.equal(h.context.mouseSequence.active(), false);
    assert.equal(h.press(0).defaultPrevented, false);
    assert.equal(h.calls.length, 0, '3M cancels without becoming a fresh M');
  }
  for (const type of ['keydown', 'wheel', 'touchstart', 'pointercancel', 'blur']) {
    for (const count of [1, 2]) {
      const h = harness(); for (let i = 0; i < count; i++) h.press(1);
      const event = h.fire(type, {key: 'Shift', target: {closest: () => true}});
      assert.equal(event.defaultPrevented, false, 'cancelling input retains its action');
      assert.equal(h.context.mouseSequence.active(), false, type);
      assert.equal(h.press(0).defaultPrevented, false);
    }
  }
  {
    const h = harness(); h.press(1); h.fire('pointerdown', {pointerType: 'pen'});
    assert.equal(h.context.mouseSequence.active(), false);
    h.press(1); h.press(3); assert.equal(h.context.mouseSequence.active(), false);
    h.press(1); h.fire('mousemove'); h.tick(100); h.fire('mousemove'); h.press(0);
    assert.ok(h.calls.includes('fullscreen'), 'movement does not cancel a command');
    assert.equal(h.fire('click', {detail: 0}).defaultPrevented, false,
      'keyboard activation is not a consumed physical suffix');
    assert.equal(h.fire('contextmenu', {button: 0, detail: 0}).defaultPrevented, false,
      'a keyboard context menu is not a consumed physical suffix');
  }
  for (const beforeRelease of [true, false]) {
    const h = harness(); h.press(1); h.press(2);
    if (beforeRelease) assert.equal(h.fire('contextmenu', {button: 2}).defaultPrevented, true);
    assert.equal(h.fire('mouseup', {button: 2}).defaultPrevented, true);
    h.acknowledge();
    if (!beforeRelease) assert.equal(h.fire('contextmenu', {button: 2}).defaultPrevented, true);
    assert.equal(h.fire('auxclick', {button: 2}).defaultPrevented, true);
    assert.equal(h.menu.attrs['aria-pressed'], 'true');
    assert.equal(h.root.classList.contains('nav-idle'), true);
    assert.equal(h.context.idleTimer, null, 'capture needs no movement/idle timer');
    h.context.setNavIdle(false); h.context.revealChrome();
    assert.equal(h.root.classList.contains('nav-idle'), true, 'capture dominates reveal');
    h.press(2);
    assert.equal(h.calls.filter(value => Array.isArray(value) && value[0] === 'slide').length, 1);
    h.fire('contextmenu', {button: 2}); h.fire('auxclick', {button: 2});
    assert.equal(h.calls.filter(value => Array.isArray(value) && value[0] === 'slide').length, 1,
      'one right press cannot also navigate through its contextmenu');
    [1, 2].forEach(h.press);
    assert.equal(h.document.pointerLockElement, null);
    assert.equal(h.menu.attrs['aria-pressed'], 'false');
    assert.equal(h.context.document.body.style.cursor, '', 'unlock reveals immediately');
  }
  {
    const h = harness(); h.press(1); h.press(2);
    assert.equal(h.menu.attrs['aria-pressed'], 'false', 'pending is not locked');
    h.context.preparePointerSurface(); h.acknowledge();
    assert.equal(h.document.pointerLockElement, null, 'late capture after menu open is released');
    h.context.togglePause('t'); h.context.preparePointerSurface();
    assert.equal(h.pause.classList.contains('open'), true, 'foreground surfaces preserve pause');
  }
  {
    const h = harness(); [1, 2].forEach(h.press);
    h.document.pointerLockElement = h.root;
    h.press(1); // Native state is available before its queued notification.
    h.document.fire('pointerlockchange'); h.press(0);
    assert.ok(h.calls.includes('fullscreen'), 'a requested acquisition must preserve a newer M prefix');
  }
  {
    const h = harness(); [1, 2].forEach(h.press); h.acknowledge();
    h.document.exitPointerLock = () => { h.calls.push('unlock'); h.document.pointerLockElement = null; };
    [1, 2].forEach(h.press);
    h.press(1); h.document.fire('pointerlockchange'); h.press(0);
    assert.ok(h.calls.includes('fullscreen'), 'a requested release must preserve a newer M prefix');
  }
  {
    const h = harness(); [1, 2].forEach(h.press); h.acknowledge();
    h.document.exitPointerLock = () => { h.calls.push('unlock'); h.document.pointerLockElement = null; };
    [1, 2].forEach(h.press); // Release, with its notification still pending.
    [1, 2].forEach(h.press); // Start a new acquisition before that old notice.
    h.document.fire('pointerlockchange');
    h.document.pointerLockElement = h.root;
    h.press(1); h.document.fire('pointerlockchange'); h.press(0);
    assert.ok(h.calls.includes('fullscreen'), 'an old release notice cannot clear a newer acquisition');
  }
  {
    const h = harness(); [1, 2].forEach(h.press); h.acknowledge();
    h.press(1); h.document.fire('pointerlockchange'); h.press(0);
    assert.ok(h.calls.includes('fullscreen'), 'an unchanged duplicate notice must not cancel a new command');
  }
  {
    const h = harness(); [1, 2].forEach(h.press); h.acknowledge();
    h.press(1); h.document.pointerLockElement = null;
    h.document.fire('pointerlockchange'); h.press(0);
    assert.ok(!h.calls.includes('fullscreen'), 'an external release still cancels a pending prefix');
  }
  {
    const h = harness(); h.press(1); h.acknowledge(); h.press(0);
    assert.ok(!h.calls.includes('fullscreen'), 'an unrequested capture still cancels a pending prefix');
  }
  {
    const h = harness(); [1, 2].forEach(h.press);
    h.document.pointerLockElement = h.root;
    h.document.exitPointerLock = () => { h.calls.push('unlock'); h.document.pointerLockElement = null; };
    h.context.releasePointerLock();
    h.document.fire('pointerlockchange');
    [1, 2].forEach(h.press);
    assert.equal(h.calls.filter(call => call === 'lock-request').length, 2,
      'a capture released before either notice cannot leave acquisition stuck pending');
  }
  for (const failure of ['legacy', 'throw', 'promise', 'unavailable']) {
    const h = harness();
    if (failure === 'unavailable') delete h.root.requestPointerLock;
    else if (failure === 'throw') h.root.requestPointerLock = () => { throw Error('denied'); };
    else if (failure === 'promise') h.root.requestPointerLock = () => Promise.reject(Error('denied'));
    h.context.togglePointerLock();
    if (failure === 'legacy') h.document.fire('pointerlockerror');
    await Promise.resolve();
    assert.equal(h.document.pointerLockElement, null);
    assert.equal(h.menu.attrs['aria-pressed'], 'false');
    assert.equal(h.status.hidden, false, failure + ' failure is visible');
  }
  {
    const h = harness(); [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => h.root;
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(h.calls.includes('lock-request'), 'a requested fullscreen acknowledgement preserves a newer prefix');
  }
  {
    const h = harness(); h.context.currentFullscreenElement = () => h.root;
    h.context.handleFullscreenChange(); [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => null;
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(h.calls.includes('lock-request'), 'a requested fullscreen exit preserves a newer prefix');
  }
  {
    const h = harness(); [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => h.root; h.context.handleFullscreenChange();
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(h.calls.includes('lock-request'), 'duplicate fullscreen notifications do not erase a prefix');
  }
  for (const entering of [true, false]) {
    const h = harness();
    h.context.currentFullscreenElement = () => entering ? null : h.root;
    h.context.handleFullscreenChange(); h.press(1);
    h.context.currentFullscreenElement = () => entering ? h.root : null;
    h.context.handleFullscreenChange(); h.press(2);
    assert.ok(!h.calls.includes('lock-request'), 'an unrequested fullscreen transition still cancels');
  }
  {
    const h = harness(); [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => h.root; [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => null; [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => h.root; h.context.handleFullscreenChange();
    h.press(1); h.context.currentFullscreenElement = () => null;
    h.context.handleFullscreenChange(); h.press(2);
    assert.ok(!h.calls.includes('lock-request'), 'a newer entry retires older exit intent before an external loss');
  }
  {
    const h = harness(); h.root.requestFullscreen = () => Promise.reject(Error('refused'));
    [1, 0].forEach(h.press); await Promise.resolve();
    h.context.currentFullscreenElement = () => h.root;
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(!h.calls.includes('lock-request'), 'a refused fullscreen request cannot authorize a later external entry');
  }
  {
    const h = harness(); let reject;
    h.root.requestFullscreen = () => new Promise((resolve, fail) => { reject = fail; });
    [1, 0].forEach(h.press);
    h.root.requestFullscreen = () => h.calls.push('fullscreen');
    [1, 0].forEach(h.press); reject(Error('old request')); await Promise.resolve();
    h.context.currentFullscreenElement = () => h.root;
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(h.calls.includes('lock-request'), 'an old rejection cannot discard a newer fullscreen request');
  }
  for (const unavailable of [false, true]) {
    const h = harness();
    if (unavailable) delete h.root.requestFullscreen;
    else h.root.requestFullscreen = () => { throw Error('refused'); };
    assert.doesNotThrow(() => [1, 0].forEach(h.press));
    h.context.currentFullscreenElement = () => h.root;
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(!h.calls.includes('lock-request'), 'unavailable/throwing APIs cannot leave an entry intent');
  }
  {
    const h = harness(); delete h.root.requestFullscreen; delete h.document.exitFullscreen;
    h.root.webkitRequestFullscreen = () => h.calls.push('webkit-fullscreen');
    h.document.webkitExitFullscreen = () => h.calls.push('webkit-exit-fullscreen');
    [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => h.root;
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(h.calls.includes('lock-request'), 'event-only WebKit entry preserves the newer prefix');
    h.acknowledge();
    [1, 0].forEach(h.press);
    h.context.currentFullscreenElement = () => null;
    h.press(1); h.context.handleFullscreenChange(); h.press(2);
    assert.ok(h.calls.includes('webkit-fullscreen') && h.calls.includes('webkit-exit-fullscreen'));
    assert.equal(h.calls.filter(call => call === 'lock-request').length, 2,
      'event-only WebKit exit preserves the newer prefix');
  }
  {
    const h = harness(); h.moveTop(-120); [1, 1, 0].forEach(h.press);
    assert.ok(h.calls.includes('beginning'), 'a scrolled first slide returns to its own top');
    h.calls.length = 0; h.moveTop(0); h.context.isScrolling = true; [1, 1, 0].forEach(h.press);
    assert.ok(h.calls.includes('beginning'), 'an in-flight arrival is not already at the beginning');
    h.calls.length = 0; h.context.isIndex = true; [1, 1, 0].forEach(h.press);
    assert.ok(h.calls.includes('beginning'), 'the index only returns to its top');
  }
  {
    const h = harness();
    for (const key of ['m', 'M', 'f', 'p', 'h', 'Shift', 'q']) {
      assert.equal(!!h.context.isPauseNavigationKey({key}), false, key);
    }
    for (const key of ['ArrowDown', 'PageUp', 'Home', 'End', ' ', 'Backspace']) {
      assert.equal(!!h.context.isPauseNavigationKey({key}), true, key);
    }
    h.context.jumpBuffer = '2';
    assert.equal(!!h.context.isPauseNavigationKey({key: 'Enter'}), true);
    h.context.togglePause('t');
    h.context.foregroundSurface = {contains: () => true};
    h.fire('wheel', {deltaY: 30});
    assert.equal(h.pause.classList.contains('open'), true, 'menu scrolling preserves pause');
    h.context.foregroundSurface = null;
    h.fire('wheel', {deltaY: 30, ctrlKey: true});
    assert.equal(h.pause.classList.contains('open'), true, 'native zoom preserves pause');
    h.fire('wheel', {deltaY: 30});
    assert.equal(h.pause.classList.contains('open'), false, 'reading wheel navigation dismisses pause');
  }
  {
    // Primary touch stays coarse even with a connected/late-arriving mouse.
    const h = harness(false);
    h.context.currentFullscreenElement = () => h.root;
    [1, 2].forEach(h.press); h.acknowledge();
    assert.equal(h.document.pointerLockElement, h.root, 'mouse commands work on a primary-touch device');
    assert.equal(h.context.hasFinePointer, false, 'device detection does not rewrite touch capability');
    assert.equal(h.root.classList.contains('mouse-input'), true);
    assert.equal(h.document.body.style.cursor, 'none');
    assert.equal(h.document.body.classList.contains('fs-noselect'), true);
    h.fire('pointerdown', {pointerType: 'touch'});
    assert.equal(h.document.pointerLockElement, null, 'touch restores its native ownership');
    assert.equal(h.root.classList.contains('mouse-input'), false);
    assert.equal(h.document.body.classList.contains('fs-noselect'), false,
      'fullscreen mouse selection policy does not steal touch text selection');
    h.context.setNavIdle(true);
    for (let i = 0; i < 8; i++) {
      h.fire('mousemove', {sourceCapabilities: {firesTouchEvents: true}}); h.tick(50);
    }
    assert.equal(h.root.classList.contains('nav-idle'), true,
      'touch compatibility movement does not wake mouse chrome');
    assert.equal(h.fire('contextmenu', {button: 2, pointerType: 'touch'}).defaultPrevented, false,
      'a touch long press is not a stale consumed right mouse command');
    h.press(1);
    h.fire('touchstart');
    assert.equal(h.context.mouseSequence.active(), false);
    assert.equal(h.fire('mousedown', {sourceCapabilities: {firesTouchEvents: true}}).defaultPrevented, false);
    h.fire('pointerdown', {pointerType: 'mouse'});
    h.context.setNavIdle(true);
    for (let i = 0; i < 8; i++) { h.fire('mousemove'); h.tick(50); }
    assert.equal(h.root.classList.contains('nav-idle'), false,
      'a mouse wakes chrome on a primary-touch device');
    h.context.currentFullscreenElement = () => null;
    [1, 0].forEach(h.press);
    assert.ok(h.calls.includes('fullscreen'));
  }
  console.log('Mouse command runtime checks passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
