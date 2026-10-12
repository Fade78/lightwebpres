// Execute the private runtime from generated HTML. The geometry model below
// implements the CSS zoom distinction between lengths and auto/percent sizes;
// it is not a replacement for the separate real-browser geometry checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(process.argv[2], 'utf8');
assert.match(html, /<figure class="figure"><img/);
const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(match => match[1]).find(text => text.includes('var readingRuntime = (function'));
assert.ok(script);
const start = script.indexOf('  var readingRuntime = (function');
const end = script.indexOf('\n  function scheduleReadingLayout', start);
assert.ok(start >= 0 && end > start);

class Style {
  constructor(values = {}) { this.values = new Map(Object.entries(values)); this.priorities = new Map(); }
  getPropertyValue(name) { return this.values.get(name) || ''; }
  getPropertyPriority(name) { return this.priorities.get(name) || ''; }
  setProperty(name, value, priority = '') { this.values.set(name, value); this.priorities.set(name, priority); }
  removeProperty(name) { this.values.delete(name); this.priorities.delete(name); }
  get zoom() { return this.getPropertyValue('zoom'); }
  snapshot() { return [...this.values].sort().map(([key, value]) => [key, value, this.getPropertyPriority(key)]); }
}

function fixture({percent = false, pixels = false, caption = false} = {}) {
  const callbacks = {window: {}, document: {}};
  const frames = new Map();
  let nextFrame = 0;
  let width = percent ? 200 : 600;
  const figure = !percent && !pixels;
  const attributes = new Map();
  const document = {
    documentElement: {clientHeight: 700, style: new Style(), setAttribute() {}},
    addEventListener(name, callback) { callbacks.document[name] = callback; },
    querySelectorAll() { return []; },
  };
  function node(tag) {
    return {tagName: tag, style: new Style(), childNodes: [], hidden: false,
      ownerDocument: document, closest() { return null; },
      getClientRects() { return [this.getBoundingClientRect()]; },
      querySelectorAll() { return []; }, querySelector() { return null; }};
  }
  const slide = node('SECTION');
  const wrapper = figure ? node('FIGURE') : slide;
  const image = node('IMG');
  const ownZoom = node => Number(node.style.zoom) || 1;
  const ancestorZoom = () => figure ? ownZoom(wrapper) : 1;
  const dimension = (axis, localZoom) => {
    const available = axis === 'width' ? width / ancestorZoom() : 100 / ancestorZoom();
    const specified = image.style.getPropertyValue(axis);
    let value = specified.endsWith('%')
      ? available * parseFloat(specified) / 100 / localZoom
      : specified ? parseFloat(specified) : axis === 'width' ? 1000 : 2000;
    const max = image.style.getPropertyValue('max-' + axis) || (figure && axis === 'width' ? '100%' : 'none');
    if (max.endsWith('%')) value = Math.min(value, available * parseFloat(max) / 100 / localZoom);
    // The native auto height follows the image's constrained width.
    if (axis === 'height' && !specified) value = dimension('width', localZoom) * 2;
    return value;
  };
  const imageRect = () => {
    const zoom = ownZoom(image);
    const effective = zoom * ancestorZoom();
    return {width: dimension('width', zoom) * effective,
      height: dimension('height', zoom) * effective};
  };
  image.getBoundingClientRect = imageRect;
  wrapper.getBoundingClientRect = () => ({width,
    height: imageRect().height + (caption ? 400 * ancestorZoom() : 0)});
  slide.getBoundingClientRect = () => ({width, height: Math.max(700, imageRect().height), left: 0, right: width});
  Object.defineProperty(slide, 'scrollHeight', {get: () => slide.getBoundingClientRect().height});
  Object.defineProperty(slide, 'clientWidth', {get: () => width});
  if (figure) Object.defineProperty(wrapper, 'clientWidth', {get: () => width / ancestorZoom()});
  wrapper.parentElement = slide;
  image.parentElement = wrapper;
  if (figure) image.parentElement.closest = selector => selector.includes('figure') ? wrapper : null;
  slide.querySelectorAll = selector => {
    if (selector === 'table') return [];
    if (selector === '*') return figure ? [wrapper, image] : [image];
    if (selector === 'figure, .figure, img') return figure ? [wrapper, image] : [image];
    if (selector === 'img') return [image];
    return [];
  };
  if (figure) wrapper.querySelectorAll = selector => selector === 'img' ? [image] : [];
  slide.setAttribute = (name, value) => attributes.set(name, value);
  slide.removeAttribute = name => attributes.delete(name);
  if (percent) {
    image.style.setProperty('width', '40%');
    image.style.setProperty('height', '40%');
  } else if (pixels) {
    image.style.setProperty('width', '80px', 'important');
    image.style.setProperty('height', '40px');
    image.style.setProperty('zoom', '0.8');
    image.style.setProperty('max-width', 'none');
  }
  const computed = element => ({
    display: element === image ? 'inline' : 'block', visibility: 'visible',
    content: 'none', paddingLeft: '0px', paddingRight: '0px',
    fontSize: '20px', lineHeight: 'normal', zoom: String(ownZoom(element)),
    width: (element === image ? dimension('width', ownZoom(image)) : width) + 'px',
    height: (element === image ? dimension('height', ownZoom(image)) : 100) + 'px',
  });
  document.defaultView = {getComputedStyle: computed};
  const settings = {table_mode: 'clip', text_fit: 'fixed', table_shrink: false,
    object_shrink_horizontal: false, object_shrink_vertical: false,
    min_text_scale: .75, min_table_scale: .85, min_object_scale: .5};
  const context = vm.createContext({document, getComputedStyle: computed,
    window: {addEventListener(name, callback) { callbacks.window[name] = callback; }},
    requestAnimationFrame(callback) { frames.set(++nextFrame, callback); return nextFrame; },
    cancelAnimationFrame(id) { frames.delete(id); },
    allSlides: [slide], isIndex: false, isScrolling: false, presentationReanchorFrame: null,
    selectedTag: 'default', seriesViews: null, seriesActivating: false,
    seriesPendingRoute: null, readingSettings: settings, presentationZoom: 1,
    contentRoot: () => document, captureReadingPosition: () => null,
  });
  vm.runInContext(script.slice(start, end), context);
  const settle = () => {
    for (const [id, callback] of frames) { frames.delete(id); callback(); }
  };
  const layout = () => { vm.runInContext("readingRuntime.schedule('test')", context); settle(); };
  settle();
  return {image, wrapper, settings, context, callbacks, layout, settle,
    resize(value) { width = value; layout(); },
    zoom(value) { context.presentationZoom = value; layout(); }};
}

const near = (actual, expected, message) => assert.ok(Math.abs(actual - expected) < .1,
  `${message}: ${actual} instead of ${expected}`);
const responsive = fixture();
const styles = responsive.image.style.snapshot();
near(responsive.image.getBoundingClientRect().height, 1200, 'native constrained image');
responsive.settings.object_shrink_vertical = true;
responsive.layout();
near(responsive.image.getBoundingClientRect().height, 700, 'height fitting reaches the viewport');
near(responsive.image.getBoundingClientRect().width, 350, 'height fitting preserves aspect ratio');
responsive.layout();
near(responsive.image.getBoundingClientRect().height, 700, 'repeated layout has no drift');
responsive.zoom(2);
near(responsive.image.getBoundingClientRect().height, 700, 'manual zoom cannot push a fitted image past the viewport');
near(responsive.image.getBoundingClientRect().width, 350, 'height cap preserves aspect ratio during zoom');
responsive.callbacks.window.beforeprint();
assert.deepEqual(responsive.image.style.snapshot(), styles, 'print restores authored sizing');
near(responsive.image.getBoundingClientRect().height, 1200, 'print uses responsive original geometry');
responsive.callbacks.window.afterprint();
responsive.settle();
near(responsive.image.getBoundingClientRect().height, 700, 'screen height cap resumes after print');
responsive.zoom(1);
responsive.settings.object_shrink_vertical = false;
responsive.layout();
assert.deepEqual(responsive.image.style.snapshot(), styles, 'disabled fitting restores styles');
for (const factor of [.5, 2, 1]) {
  responsive.zoom(factor);
  near(responsive.image.getBoundingClientRect().width, 600 * factor, 'responsive manual width');
  near(responsive.image.getBoundingClientRect().height, 1200 * factor, 'responsive manual height');
}
assert.deepEqual(responsive.image.style.snapshot(), styles, '100% restores responsive styles');
responsive.resize(300);
responsive.zoom(2);
near(responsive.image.getBoundingClientRect().width, 600, 'resize takes a fresh baseline');
responsive.zoom(1);
assert.deepEqual(responsive.image.style.snapshot(), styles);

const bounded = fixture();
bounded.settings.min_object_scale = .85;
bounded.settings.object_shrink_vertical = true;
bounded.layout();
near(bounded.image.getBoundingClientRect().height, 700, 'height fitting ignores the horizontal image floor');
bounded.settings.object_shrink_vertical = false;
bounded.layout();
bounded.image.style.setProperty('max-width', 'none', 'important');
bounded.settings.object_shrink_horizontal = true;
bounded.layout();
near(bounded.image.getBoundingClientRect().width, 1000 * .85, 'width-only fitting obeys author floor');
bounded.settings.min_object_scale = .5;
bounded.layout();
near(bounded.image.getBoundingClientRect().width, 600, 'width fitting measures the image beyond its wrapper');
bounded.settings.object_shrink_horizontal = false;
bounded.layout();
assert.equal(bounded.image.style.getPropertyValue('max-width'), 'none');
assert.equal(bounded.image.style.getPropertyPriority('max-width'), 'important');

for (const options of [{percent: true}, {pixels: true}]) {
  const sample = fixture(options);
  const original = sample.image.style.snapshot();
  const baseline = sample.image.getBoundingClientRect();
  for (const factor of [.5, 2, 1]) {
    sample.zoom(factor);
    near(sample.image.getBoundingClientRect().width, baseline.width * factor, 'authored units scale once');
    near(sample.image.getBoundingClientRect().height, baseline.height * factor, 'authored height scales once');
  }
  assert.deepEqual(sample.image.style.snapshot(), original, 'original units and priorities survive');
}
console.log('Image reading runtime checks passed');
