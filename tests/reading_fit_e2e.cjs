// Instrument only the served test response; the shipped reading API stays private.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  let browser;
  try {
    browser = await chromium.launch(process.env.PW_CHROMIUM_PATH
      ? { executablePath: process.env.PW_CHROMIUM_PATH } : {});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  try {
    const page = await browser.newPage({ viewport: { width: 1100, height: 700 } });
    const errors = [];
    const checks = [];
    page.on('pageerror', error => errors.push(error.message));
    const instrumentReading = async route => {
      const response = await route.fetch();
      const html = await response.text();
      const marker = '  var allSlides =';
      assert.ok(html.includes(marker), 'real navigation IIFE is present');
      await route.fulfill({ response, body: html.replace(marker, `
  window.readingProbe = {
    set: setReadingOption, schedule: scheduleReadingLayout,
    theme: applyTheme, clearTheme: clearExplicitTheme,
    preset: applyPresentation, tag: selectTag, zoom: setPresentationZoom,
    settings: function () { return readingSettings; }
  };
${marker}`) });
    };
    await page.route('**/reading.html', instrumentReading);
    await page.goto(process.argv[2]);
    const settle = () => page.evaluate(() => new Promise(resolve =>
      requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const set = async (name, value) => {
      assert.equal(await page.evaluate(([n, v]) => readingProbe.set(n, v), [name, value]), true);
      await settle();
    };
    const selectSlides = async ids => {
      await page.evaluate(ids => {
        document.querySelectorAll('section.slide').forEach(slide => {
          slide.hidden = !ids.includes(slide.id);
        });
        readingProbe.schedule('test-visibility');
      }, ids);
      await settle();
    };
    const scales = () => page.evaluate(() => Array.from(
      document.querySelectorAll('section.slide:not([hidden])'), s => ({
        id: s.id, scale: Number(s.dataset.lwpTextScale || 1),
        overflow: s.dataset.lwpFitOverflow === 'true',
        height: s.getBoundingClientRect().height,
      })));
    await settle();
    assert.deepEqual(errors, []);
    assert.equal(await page.$eval('#short .probe-text', el => getComputedStyle(el).fontSize), '30px');
    checks.push('fixed preserves authored typography');

    await selectSlides(['short', 'dense']);
    await set('text_fit', 'uniform');
    let common = await scales();
    assert.equal(common.length, 2);
    assert.equal(common[0].scale, common[1].scale);
    assert.ok(common[0].scale >= .75 && common[0].scale < 1, JSON.stringify(common));
    assert.ok(common.every(s => !s.overflow), JSON.stringify(common));
    const hierarchy = await page.$eval('#short .probe-text', el =>
      parseFloat(getComputedStyle(el.querySelector('strong')).fontSize)
        / parseFloat(getComputedStyle(el).fontSize));
    assert.ok(Math.abs(hierarchy - 1.2) < .001);
    checks.push('uniform common factor and relative hierarchy');

    await set('text_fit', 'per-slide');
    const individual = await scales();
    assert.equal(individual[0].scale, 1);
    assert.ok(individual[1].scale < 1, JSON.stringify(individual));
    checks.push('per-slide factors vary');

    await page.setViewportSize({ width: 1100, height: 1200 });
    await settle();
    assert.ok((await scales()).every(s => s.scale === 1));
    await page.setViewportSize({ width: 1100, height: 700 });
    await settle();
    assert.ok((await scales())[1].scale < 1);
    checks.push('resize reverses and reapplies shrink');

    await selectSlides(['inherited']);
    for (const tag of ['strong', 'a']) {
      await set('text_fit', 'fixed');
      await page.$eval('#inherited-container', (el, tag) => {
        const child = document.createElement(tag);
        child.innerHTML = el.firstElementChild.innerHTML;
        if (tag === 'a') child.href = '#short';
        el.replaceChildren(child);
      }, tag);
      const original = await page.$eval('#inherited-container', el => ({
        height: el.getBoundingClientRect().height,
        slideHeight: el.closest('.slide').getBoundingClientRect().height,
      }));
      assert.ok(original.slideHeight > 700, JSON.stringify(original));
      await set('text_fit', 'per-slide');
      const fitted = await page.$eval('#inherited-container', el => ({
        height: el.getBoundingClientRect().height,
        slideHeight: el.closest('.slide').getBoundingClientRect().height,
        scale: Number(el.closest('.slide').dataset.lwpTextScale),
        parentSize: parseFloat(getComputedStyle(el).fontSize),
        parentLine: parseFloat(getComputedStyle(el).lineHeight),
        childSize: parseFloat(getComputedStyle(el.firstElementChild).fontSize),
        childLine: parseFloat(getComputedStyle(el.firstElementChild).lineHeight),
      }));
      assert.ok(fitted.slideHeight <= 701, tag + ': ' + JSON.stringify(fitted));
      assert.ok(fitted.height < original.height);
      assert.ok(Math.abs(fitted.height / original.height - fitted.scale) < .002);
      assert.ok(Math.abs(fitted.parentSize - 40 * fitted.scale) < .01);
      assert.ok(Math.abs(fitted.parentLine - 60 * fitted.scale) < .01);
      assert.equal(fitted.childSize, fitted.parentSize);
      assert.equal(fitted.childLine, fitted.parentLine);
      assert.equal(await page.$eval('#hidden-type', el => el.style.fontSize), '');
      assert.equal(await page.$eval('#svg-type', el => el.style.fontSize), '14px');
      await set('text_fit', 'fixed');
      assert.ok(Math.abs(await page.$eval('#inherited-container', el =>
        el.getBoundingClientRect().height) - original.height) < .01);
    }
    checks.push('emphasis-only and link-only containers scale their line boxes without double inheritance');

    await selectSlides(['paired']);
    const pairGeometry = () => page.$eval('#paired-images', el => ({
      slideHeight: el.closest('.slide').getBoundingClientRect().height,
      scale: Number(el.closest('.slide').dataset.lwpTextScale || 1),
      images: Array.from(el.querySelectorAll('img'), image => ({
        width: image.getBoundingClientRect().width,
        height: image.getBoundingClientRect().height,
        zoom: Number(image.style.zoom),
        authoredWidth: image.style.width, authoredHeight: image.style.height,
      })),
    }));
    const originalPair = await pairGeometry();
    assert.ok(originalPair.slideHeight > 700, JSON.stringify(originalPair));
    assert.ok(originalPair.images.every(image => image.height === 300));
    await set('object_shrink', true);
    const fittedPair = await pairGeometry();
    assert.ok(fittedPair.slideHeight <= 701, JSON.stringify(fittedPair));
    assert.equal(fittedPair.scale, 1);
    assert.equal(fittedPair.images[0].zoom, fittedPair.images[1].zoom);
    assert.ok(Math.abs(fittedPair.images[0].height * 2
      - (701 - (originalPair.slideHeight - 600))) < 1, JSON.stringify(fittedPair));
    assert.ok(fittedPair.images.every(image => image.zoom > .9 && image.zoom < 1
      && image.height >= 255 && image.height < 300
      && Math.abs(image.height / 300 - image.zoom) < .001
      && Math.abs(image.width / 100 - image.zoom) < .001), JSON.stringify(fittedPair));
    await set('text_fit', 'uniform');
    assert.equal((await pairGeometry()).scale, 1);
    await set('object_shrink', false);
    await set('text_fit', 'fixed');
    assert.deepEqual(await pairGeometry(), originalPair);
    checks.push('combined image height is fitted before text and restores when disabled');

    await page.$eval('#paired-images', el => {
      const label = document.createElement('p');
      label.id = 'paired-label';
      label.textContent = 'One authored line';
      label.style.cssText = 'font-size:40px;line-height:80px;margin:0';
      el.prepend(label);
    });
    await set('object_shrink', true);
    const floorPair = await pairGeometry();
    assert.ok(floorPair.slideHeight > 700, JSON.stringify(floorPair));
    assert.ok(floorPair.images.every(image => image.zoom === .85));
    await selectSlides(['paired', 'impossible']);
    await set('text_fit', 'uniform');
    const recoveredPair = await pairGeometry();
    assert.equal(recoveredPair.scale, .75);
    assert.ok(recoveredPair.slideHeight <= 701, JSON.stringify(recoveredPair));
    assert.ok(recoveredPair.images.every(image => image.zoom > .85 && image.zoom < 1
      && image.height > 255 && image.height < 300), JSON.stringify(recoveredPair));
    assert.ok(await page.$eval('#paired-label', el => el.getBoundingClientRect().height) <= 60.1);
    await set('text_fit', 'fixed');
    await set('object_shrink', false);
    await page.$eval('#paired-label', el => el.remove());
    assert.deepEqual(await pairGeometry(), originalPair);
    checks.push('objects recover available space after a shared text floor');

    await page.evaluate(() => readingProbe.tag('long', false));
    await settle();
    await set('text_fit', 'uniform');
    const impossible = await scales();
    assert.ok(impossible.some(s => s.id === 'impossible' && s.scale === .75
      && s.overflow && s.height > 700), JSON.stringify(impossible));
    assert.ok(await page.$eval('#impossible', s => getComputedStyle(s).overflowY !== 'hidden'));
    checks.push('tag refresh includes longform and marks impossible floor');

    await page.$eval('#impossible', s => window.scrollTo({
      top: s.offsetTop + s.offsetHeight * .4, behavior: 'instant',
    }));
    await settle();
    const anchorRatio = () => page.$eval('#impossible', s =>
      -s.getBoundingClientRect().top / s.getBoundingClientRect().height);
    const beforeAnchor = await anchorRatio();
    await set('text_fit', 'fixed');
    assert.ok(Math.abs(await anchorRatio() - beforeAnchor) < .01);
    await set('text_fit', 'uniform');
    assert.ok(Math.abs(await anchorRatio() - beforeAnchor) < .01);
    await page.evaluate(() => readingProbe.theme('dracula', false));
    await settle();
    assert.ok(Math.abs(await anchorRatio() - beforeAnchor) < .01);
    await page.evaluate(() => readingProbe.preset('commons/roomy', false));
    await settle();
    assert.ok(Math.abs(await anchorRatio() - beforeAnchor) < .01);
    await page.evaluate(() => {
      readingProbe.preset('builtin/standard', false);
      readingProbe.clearTheme(false);
    });
    await settle();
    checks.push('reading option changes preserve intra-article position');

    await selectSlides(['short']);
    await page.evaluate(() => {
      const text = document.querySelector('#short .probe-text');
      text.style.fontSize = '13px';
      // A theme change, rather than editing a runtime-owned inline override.
      const style = document.createElement('style');
      style.textContent = '#short .probe-text { font-size:13px } #short { min-height:900px }';
      style.id = 'floor-fixture';
      document.head.appendChild(style);
    });
    await set('text_fit', 'fixed');
    await set('text_fit', 'uniform');
    assert.equal(await page.$eval('#short .probe-text', el => getComputedStyle(el).fontSize), '12px');
    await page.evaluate(() => document.getElementById('floor-fixture').remove());
    checks.push('12px readable floor');

    await selectSlides(['tables']);
    await set('text_fit', 'fixed');
    const table = await page.$('#raw-table');
    await page.evaluate(() => {
      window.originalTable = document.getElementById('raw-table');
      window.tableClicks = 0;
      document.getElementById('table-link').addEventListener('click', e => {
        e.preventDefault(); window.tableClicks++;
      });
    });
    for (const mode of ['scroll', 'overflow', 'clip', 'scroll']) {
      await set('table_mode', mode);
      const state = await table.evaluate(el => ({
        same: el === originalTable,
        wrappers: el.closest('.slide').querySelectorAll('#raw-table').length,
        display: getComputedStyle(el).display,
        overflow: getComputedStyle(el.parentElement).overflowX,
        focus: el.parentElement.getAttribute('tabindex'),
        label: el.parentElement.getAttribute('aria-label'),
        deckWidth: document.documentElement.scrollWidth,
      }));
      assert.equal(state.same, true);
      assert.equal(state.wrappers, 1);
      assert.equal(state.display, 'table');
      assert.equal(state.overflow, { scroll: 'auto', overflow: 'visible', clip: 'clip' }[mode]);
      assert.equal(state.focus, mode === 'scroll' ? '0' : null);
      if (mode === 'scroll') assert.equal(state.label, 'Wide measurements');
      if (mode !== 'overflow') assert.ok(state.deckWidth <= 1101, JSON.stringify(state));
    }
    await page.$eval('#table-link', el => el.click());
    assert.equal(await page.evaluate(() => tableClicks), 1);
    assert.equal(await page.$eval('.comparison-table', el => getComputedStyle(el).display), 'table');
    checks.push('local table modes preserve DOM, semantics, focus and handlers');

    await set('table_shrink', true);
    assert.ok(Math.abs(await table.evaluate(el => parseFloat(getComputedStyle(el).zoom)) - .85) < .001);
    await set('table_shrink', false);
    assert.equal(await table.evaluate(el => el.style.zoom), '');
    checks.push('independent table shrink floor and restoration');

    await selectSlides(['objects']);
    const originals = await page.$eval('#author-image', el => ({
      width: el.getAttribute('width'), height: el.getAttribute('height'), style: el.getAttribute('style'),
    }));
    await set('object_shrink', true);
    const objectZoom = await page.$eval('#author-figure', el => parseFloat(getComputedStyle(el).zoom));
    assert.ok(objectZoom >= .85 && objectZoom < 1);
    assert.deepEqual(await page.$eval('#author-image', el => ({
      width: el.getAttribute('width'), height: el.getAttribute('height'), style: el.getAttribute('style'),
    })), originals);
    assert.equal(await page.$eval('#author-player', el => el.style.zoom), '1.1');
    await page.$eval('#author-image', el => {
      el.style.width = '100px'; el.style.height = '50px';
      el.dispatchEvent(new Event('load'));
    });
    await settle();
    assert.equal(await page.$eval('#author-figure', el => el.style.zoom), '');
    await page.$eval('#author-image', (el, original) => {
      el.setAttribute('style', original.style);
      el.dispatchEvent(new Event('load'));
    }, originals);
    await settle();
    assert.ok(await page.$eval('#author-figure', el => Number(el.style.zoom) < 1));
    await set('object_shrink', false);
    assert.equal(await page.$eval('#author-figure', el => el.style.zoom), '');
    await page.$eval('#author-image', el => {
      const image = el.cloneNode();
      image.id = 'standalone-image';
      el.closest('.slide').appendChild(image);
    });
    await set('object_shrink', true);
    const standalone = await page.$eval('#standalone-image', el => ({
      zoom: Number(el.style.zoom), width: el.style.width, height: el.style.height,
      widthAttribute: el.getAttribute('width'), heightAttribute: el.getAttribute('height'),
    }));
    assert.ok(Math.abs(standalone.zoom - 1.2 * .85) < .001, JSON.stringify(standalone));
    assert.equal(standalone.width, '1000px');
    assert.equal(standalone.height, '700px');
    assert.equal(standalone.widthAttribute, '1000');
    assert.equal(standalone.heightAttribute, '700');
    await set('object_shrink', false);
    assert.equal(await page.$eval('#standalone-image', el => el.style.zoom), '1.2');
    await page.$eval('#standalone-image', el => el.remove());
    checks.push('image dimensions and author zoom survive; players untouched');

    await selectSlides(['short']);
    await set('text_fit', 'uniform');
    await page.evaluate(() => {
      const style = document.createElement('style');
      style.id = 'font-fixture';
      style.textContent = '#short .probe-text { font-size:42px }';
      document.head.appendChild(style);
      document.fonts.dispatchEvent(new Event('loadingdone'));
    });
    await settle();
    assert.equal(await page.$eval('#short .probe-text', el => getComputedStyle(el).fontSize), '42px');
    await page.evaluate(() => document.getElementById('font-fixture').remove());
    checks.push('font loading refreshes CSS baselines');

    await page.$eval('#short .probe-text', el => { el.textContent = 'Unbreakable'.repeat(80); });
    await page.evaluate(() => readingProbe.schedule('long-token'));
    await settle();
    assert.equal((await scales())[0].overflow, true);
    assert.equal((await scales())[0].scale, .75);
    await page.$eval('#short .probe-text', el => { el.textContent = 'Short text restored.'; });
    checks.push('horizontal text overflow is marked without counting intentional table spill');

    await page.evaluate(() => readingProbe.tag('default', false));
    await selectSlides(['short', 'dense']);
    await set('text_fit', 'uniform');
    const beforeZoom = await scales();
    await page.evaluate(() => { readingProbe.zoom(1.5); readingProbe.schedule('zoom-probe'); });
    await settle();
    assert.deepEqual((await scales()).map(s => s.scale), beforeZoom.map(s => s.scale));
    assert.equal(await page.evaluate(() => document.documentElement.style.zoom), '1.5');
    checks.push('presentation zoom magnifies instead of cancelling fit');

    for (const theme of ['dracula', 'print-ink']) {
      assert.equal(await page.evaluate(theme => readingProbe.theme(theme, false), theme), true);
      await settle();
      assert.ok((await scales()).every(s => s.scale >= .75 && s.scale <= 1));
      await set('text_fit', 'fixed');
      const baseline = await page.$eval('#dense h2', el => parseFloat(getComputedStyle(el).fontSize));
      await set('text_fit', 'uniform');
      const fitted = await page.$eval('#dense h2', el => parseFloat(getComputedStyle(el).fontSize));
      assert.ok(Math.abs(fitted - baseline * (await scales())[0].scale) < .1);
    }
    assert.equal(await page.evaluate(() => readingProbe.clearTheme(false)), true);
    await settle();
    assert.equal(await page.evaluate(() => readingProbe.preset('commons/roomy', false)), true);
    await settle();
    assert.ok(await page.$eval('#raw-table', el => el.parentElement.classList.contains('lwp-table-viewport')));
    checks.push('theme, default theme and preset DOM refresh');

    await set('table_shrink', true);
    await set('object_shrink', true);
    await page.$eval('#raw-table', el => { el.parentElement.scrollLeft = 160; });
    const beforePrint = await page.evaluate(() => ({
      settings: { ...readingProbe.settings() },
      styles: Array.from(document.querySelectorAll('.slide [style]'), el => el.getAttribute('style')),
    }));
    await page.evaluate(() => {
      for (const el of document.querySelectorAll('.help-overlay, .about-overlay, .presenter-panel, .share-popover, .share-qr-modal')) el.classList.add('open');
      window.dispatchEvent(new Event('beforeprint'));
    });
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).zoom), '1');
    assert.equal(await page.$eval('#raw-table', el => getComputedStyle(el.parentElement).overflowX), 'visible');
    assert.ok(await page.evaluate(() => Array.from(document.querySelectorAll(
      '.help-overlay, .about-overlay, .presenter-panel, .share-popover, .share-qr-modal'))
      .every(el => getComputedStyle(el).display === 'none')));
    assert.equal(await page.$eval('#author-figure', el => el.style.zoom), '');
    assert.equal(await page.$eval('#dense h2', el => el.style.fontSize), '');
    await page.emulateMedia({ media: 'screen' });
    await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    await settle();
    assert.deepEqual(await page.evaluate(() => ({
      settings: { ...readingProbe.settings() },
      styles: Array.from(document.querySelectorAll('.slide [style]'), el => el.getAttribute('style')),
    })), beforePrint);
    assert.equal(await page.evaluate(() => document.documentElement.style.zoom), '1.5');
    assert.ok(await page.$eval('#raw-table', el => el.parentElement.scrollLeft >= 159));
    checks.push('print removes scaling and foreground chrome, then restores without drift');
    assert.deepEqual(errors, []);

    const noJS = await browser.newPage({ javaScriptEnabled: false });
    for (const [url, mode] of [[process.argv[2], 'clip'], [process.argv[3], 'scroll'],
      [process.argv[4], 'overflow']]) {
      await noJS.goto(url);
      const staticTable = await noJS.$eval('.comparison-table', el => {
        const viewport = el.parentElement;
        viewport.scrollLeft = 50;
        return { mode: document.body.dataset.lwpTableMode,
          overflow: getComputedStyle(viewport).overflowX,
          tableWidth: el.getBoundingClientRect().width,
          viewportWidth: viewport.getBoundingClientRect().width,
          scrollLeft: viewport.scrollLeft };
      });
      assert.equal(staticTable.mode, mode);
      assert.equal(staticTable.overflow, { clip: 'clip', scroll: 'auto', overflow: 'visible' }[mode]);
      assert.ok(staticTable.tableWidth > staticTable.viewportWidth, JSON.stringify(staticTable));
      assert.equal(staticTable.scrollLeft, mode === 'scroll' ? 50 : 0);
    }
    checks.push('default clip and configured scroll/overflow work without JavaScript');
    await noJS.close();

    const configured = await browser.newPage({ viewport: { width: 1100, height: 700 } });
    await configured.route('**/reading.html', instrumentReading);
    await configured.goto(process.argv[3]);
    await configured.waitForFunction(() => document.documentElement.dataset.lwpTableMode === 'scroll'
      && document.querySelector('#dense').hasAttribute('data-lwp-text-scale'));
    const configuredState = await configured.evaluate(() => ({
      scale: Number(document.querySelector('#dense').dataset.lwpTextScale),
      table: Number(document.querySelector('#raw-table').style.zoom),
      figure: Number(document.querySelector('#author-figure').style.zoom),
      payload: JSON.parse(document.getElementById('lwp-reading-data').textContent),
    }));
    assert.equal(configuredState.scale, .9);
    assert.equal(configuredState.table, .93);
    assert.equal(configuredState.figure, .94);
    assert.equal(configuredState.payload.text_fit, 'uniform');
    await configured.evaluate(() => readingProbe.set('table_mode', 'clip'));
    await configured.waitForFunction(() => document.documentElement.dataset.lwpTableMode === 'clip');
    assert.equal(await configured.$eval('.comparison-table', el =>
      getComputedStyle(el.parentElement).overflowX), 'clip');
    checks.push('resolved Python payload drives configured scalar floors');
    await configured.close();
    process.stdout.write(JSON.stringify({ checks }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
