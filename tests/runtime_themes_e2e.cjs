// Browser probe for the runtime theme payload, the C picker and the
// global M menu. Invoked by tests/test_runtime_themes.py.

const { chromium } = require('playwright');

function fail(message) {
  console.error('E2E failure: ' + message);
  process.exitCode = 1;
}

async function main() {
  const [base, staticBase] = process.argv.slice(2);
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const context = await browser.newContext({
    locale: 'fr-FR',
    viewport: { width: 1280, height: 800 },
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(String(error)));
  await page.goto(base + '/index.html', { waitUntil: 'load' });

  const french = await page.evaluate(() => {
    const node = document.getElementById('lwp-language-data');
    const data = node ? JSON.parse(node.textContent) : null;
    return {
      htmlLang: document.documentElement.getAttribute('lang'),
      auto: data && data.auto,
      packs: data ? Object.keys(data.packs).sort() : [],
      helpTitle: document.getElementById('helpTitle').textContent,
      shareLabel: document.querySelector('[data-lwp-i18n="menu_share"]').textContent,
      menuHelp: document.querySelector('[data-lwp-i18n="menu_help"]').textContent,
    };
  });
  if (french.htmlLang !== 'fr' || french.auto !== true
      || french.packs.join('|') !== 'en|fr'
      || french.helpTitle !== 'Raccourcis clavier'
      || french.shareLabel !== 'Partager'
      || french.menuHelp !== 'Aide') {
    fail('French browser locale did not select the French interface: '
      + JSON.stringify(french));
  }

  const englishContext = await browser.newContext({
    locale: 'en-US',
    viewport: { width: 1280, height: 800 },
  });
  const englishPage = await englishContext.newPage();
  const englishErrors = [];
  englishPage.on('pageerror', (error) => englishErrors.push(String(error)));
  await englishPage.goto(base + '/index.html', { waitUntil: 'load' });
  const english = await englishPage.evaluate(() => ({
    htmlLang: document.documentElement.getAttribute('lang'),
    helpTitle: document.getElementById('helpTitle').textContent,
    shareLabel: document.querySelector('[data-lwp-i18n="menu_share"]').textContent,
    readLabel: document.querySelector('[data-lwp-i18n="series_read"]').textContent,
    menuHelp: document.querySelector('[data-lwp-i18n="menu_help"]').textContent,
  }));
  if (english.htmlLang !== 'en'
      || english.helpTitle !== 'Keyboard shortcuts'
      || english.shareLabel !== 'Share'
      || english.readLabel !== 'Read the article'
      || english.menuHelp !== 'Help') {
    fail('English browser locale did not select the English interface: '
      + JSON.stringify(english));
  }
  await englishContext.close();
  if (englishErrors.length) fail('English page errors: ' + englishErrors.join(' | '));

  const touchContext = await browser.newContext({
    locale: 'fr-FR',
    hasTouch: true,
    isMobile: true,
    viewport: { width: 390, height: 844 },
  });
  const touchPage = await touchContext.newPage();
  const touchErrors = [];
  touchPage.on('pageerror', (error) => touchErrors.push(String(error)));
  await touchPage.goto(base + '/index.html', { waitUntil: 'load' });
  await touchPage.touchscreen.tap(120, 360);
  await touchPage.waitForTimeout(100);
  await touchPage.touchscreen.tap(120, 360);
  const permanentMode = await touchPage.evaluate(() => ({
    permanent: document.documentElement.classList.contains('nav-permanent'),
    toast: document.getElementById('navModeToast').textContent,
    toastVisible: document.getElementById('navModeToast').classList.contains('show'),
  }));
  if (!permanentMode.permanent || !permanentMode.toastVisible
      || permanentMode.toast !== 'La navigation reste visible') {
    fail('mobile double tap did not announce permanent navigation: '
      + JSON.stringify(permanentMode));
  }
  await touchPage.keyboard.press('h');
  const mobileHelp = await touchPage.evaluate(() => {
    const keys = document.querySelector('.help-keys');
    const desc = document.querySelector('.help-desc');
    return {
      open: document.getElementById('helpOverlay').classList.contains('open'),
      keysWidth: keys ? keys.getBoundingClientRect().width : 0,
      descWidth: desc ? desc.getBoundingClientRect().width : 0,
    };
  });
  if (!mobileHelp.open || mobileHelp.descWidth <= mobileHelp.keysWidth) {
    fail('mobile help columns are not balanced: ' + JSON.stringify(mobileHelp));
  }
  await touchContext.close();
  if (touchErrors.length) fail('Mobile page errors: ' + touchErrors.join(' | '));

  const initial = await page.evaluate(() => ({
    payload: !!document.getElementById('lwp-theme-data'),
    primary: JSON.parse(document.getElementById('lwp-theme-data').textContent).primary,
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
  }));
  if (!initial.payload || initial.primary !== 'print-oldpress') {
    fail('the index did not load the effective primary theme: ' + JSON.stringify(initial));
  }

  await page.keyboard.press('c');
  const picker = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    focused: document.activeElement && document.activeElement.id,
    options: document.querySelectorAll('.theme-option').length,
    previews: Array.prototype.map.call(document.querySelectorAll('.theme-option'), (button) => {
      const style = getComputedStyle(button);
      return {
        background: style.backgroundColor,
        gradient: style.backgroundImage,
        foreground: style.color,
      };
    }),
  }));
  if (!picker.open || picker.focused !== 'themeFilter' || picker.options !== 2) {
    fail('C did not open the theme picker correctly: ' + JSON.stringify(picker));
  }
  if (picker.previews.some((preview) =>
      !preview.background || preview.background === 'rgba(0, 0, 0, 0)'
      || !preview.gradient || preview.gradient === 'none'
      || !preview.foreground || preview.foreground === 'rgba(0, 0, 0, 0)')) {
    fail('theme picker options do not carry resolved visual previews: '
      + JSON.stringify(picker.previews));
  }

  await page.keyboard.press('ArrowDown');
  const themeDownFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('ArrowUp');
  const themeUpFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('End');
  const themeEndFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('Home');
  const themeHomeFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('ArrowRight');
  const themeRightFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('ArrowLeft');
  const themeLeftFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  if (themeDownFocus !== 'print-oldpress'
      || themeUpFocus !== 'print-ink'
      || themeEndFocus !== 'print-ink'
      || themeHomeFocus !== 'print-oldpress'
      || themeRightFocus !== 'print-ink'
      || themeLeftFocus !== 'print-oldpress') {
    fail('theme picker arrow/home/end navigation is wrong: '
      + JSON.stringify({ themeDownFocus, themeUpFocus, themeEndFocus,
        themeHomeFocus, themeRightFocus, themeLeftFocus }));
  }
  await page.keyboard.press('Escape');
  await page.keyboard.press('c');
  const reopenedPicker = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    focused: document.activeElement && document.activeElement.id,
  }));
  if (!reopenedPicker.open || reopenedPicker.focused !== 'themeFilter') {
    fail('C did not reopen the theme picker after arrow navigation: '
      + JSON.stringify(reopenedPicker));
  }

  // The filter is focused first; two Tab presses reach the alternate theme.
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  const switched = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    font: document.documentElement.style.getPropertyValue('--font-text'),
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
    stored: sessionStorage.length,
  }));
  if (switched.open || switched.stored !== 1
      || switched.ink.toLowerCase().indexOf('#123456') !== 0) {
    fail('the alternate theme did not apply while keeping the pinned ink: '
      + JSON.stringify(switched));
  }
  if (switched.font.indexOf('Charter') === -1) {
    fail('the alternate theme did not change the runtime font: ' + JSON.stringify(switched));
  }

  const articleHref = await page.locator('a.article-card').first().getAttribute('href');
  await page.goto(new URL(articleHref, base + '/index.html').href, { waitUntil: 'load' });
  const carried = await page.evaluate(() => ({
    font: document.documentElement.style.getPropertyValue('--font-text'),
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
  }));
  if (carried.font.indexOf('Charter') === -1
      || carried.ink.toLowerCase().indexOf('#123456') !== 0) {
    fail('the theme choice did not persist to the article page: ' + JSON.stringify(carried));
  }

  await page.keyboard.press('c');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  const restored = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    inline: document.documentElement.style.getPropertyValue('--font-text'),
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
    stored: sessionStorage.length,
  }));
  if (restored.open || restored.inline || restored.stored !== 0
      || restored.ink.toLowerCase().indexOf('#123456') !== 0) {
    fail('the primary theme did not restore cleanly: ' + JSON.stringify(restored));
  }

  await page.keyboard.press('h');
  const help = await page.evaluate(() => ({
    open: document.getElementById('helpOverlay').classList.contains('open'),
    role: document.getElementById('helpOverlay').getAttribute('role'),
    labelledby: document.getElementById('helpOverlay').getAttribute('aria-labelledby'),
    titleId: !!document.getElementById('helpTitle'),
    cardTabindex: document.querySelector('.help-card').getAttribute('tabindex'),
    themeLine: Array.prototype.some.call(
      document.querySelectorAll('#helpList li'),
      (li) => li.textContent.indexOf('Changer de thème pendant la présentation') !== -1
    ),
    helpOpenLine: Array.prototype.some.call(
      document.querySelectorAll('#helpList li'),
      (li) => li.textContent.indexOf('Ouvre la fenêtre d\'aide') !== -1
    ),
    stamp: document.querySelector('.help-stamp')
      ? document.querySelector('.help-stamp').textContent.trim() : '',
    stampNameIsBold: !!document.querySelector('.help-stamp strong'),
    noHelpFoot: !document.querySelector('.help-foot'),
  }));
  if (!help.open || help.role !== 'dialog' || !help.titleId
      || help.labelledby !== 'helpTitle' || help.cardTabindex !== '0'
      || !help.themeLine || !help.helpOpenLine || !help.noHelpFoot
      || !/^Compilé avec LightWebPres v\d+\.\d+\.\d+$/.test(help.stamp)
      || !help.stampNameIsBold) {
    fail('H did not expose a proper modal with theme action and version stamp: ' + JSON.stringify(help));
  }
  const helpBeforeNav = await page.evaluate(() => ({ pageY: window.scrollY }));
  // A wheel during help must not scroll the page behind the modal.
  await page.mouse.wheel(0, 600);
  await page.waitForTimeout(300);
  const helpAfterWheel = await page.evaluate(() => ({
    pageY: window.scrollY,
    open: document.getElementById('helpOverlay').classList.contains('open'),
  }));
  if (helpAfterWheel.pageY !== helpBeforeNav.pageY || !helpAfterWheel.open) {
    fail('help allowed wheel navigation behind the modal: '
      + JSON.stringify({ helpBeforeNav, helpAfterWheel }));
  }
  // Any key closes the help (not just H or Escape).
  await page.keyboard.press('x');
  const closedByKey = await page.evaluate(() => ({
    open: document.getElementById('helpOverlay').classList.contains('open'),
    lock: document.documentElement.classList.contains('help-open'),
    overflow: getComputedStyle(document.documentElement).overflow,
  }));
  if (closedByKey.open || closedByKey.lock || closedByKey.overflow === 'hidden') {
    fail('any-key close did not restore scrolling: ' + JSON.stringify(closedByKey));
  }
  // A click also closes the help.
  await page.keyboard.press('h');
  await page.mouse.click(640, 400);
  await page.waitForTimeout(200);
  const closedByClick = await page.evaluate(() => ({
    open: document.getElementById('helpOverlay').classList.contains('open'),
  }));
  if (closedByClick.open) {
    fail('a click did not close the help overlay: ' + JSON.stringify(closedByClick));
  }

  const navMenuButton = page.locator('#navMenu');
  const navLayout = await page.evaluate(() => {
    const rect = (id) => {
      const box = document.getElementById(id).getBoundingClientRect();
      return { left: box.left, top: box.top, right: box.right, bottom: box.bottom };
    };
    return {
      fullscreen: rect('navFullscreen'), prev: rect('navPrev'),
      next: rect('navNext'), menu: rect('navMenu'),
      prevDisabled: document.getElementById('navPrev').classList.contains('disabled'),
      nextDisabled: document.getElementById('navNext').classList.contains('disabled'),
      visible: Array.prototype.map.call(
        document.querySelectorAll('.nav-buttons .nav-btn:not([hidden])'),
        (button) => button.id),
    };
  });
  const centers = [navLayout.fullscreen, navLayout.prev, navLayout.next, navLayout.menu]
    .map((box) => (box.left + box.right) / 2);
  if (navLayout.visible.join('|') !== 'navFullscreen|navPrev|navNext|navMenu'
      || navLayout.fullscreen.top >= navLayout.prev.top
      || navLayout.prev.top >= navLayout.next.top
      || navLayout.next.top >= navLayout.menu.top
      || centers.some((center) => Math.abs(center - centers[0]) > 0.5)
      || !navLayout.prevDisabled || navLayout.nextDisabled) {
    fail('the navigation controls were not one column, bottom-up menu/down/up/fullscreen: '
      + JSON.stringify(navLayout));
  }
  await navMenuButton.click();
  const openedFromNav = await page.evaluate(() => ({
    menuOpen: document.getElementById('presenterMenu').classList.contains('open'),
    focus: document.activeElement && document.activeElement.getAttribute('data-menu-action'),
    expanded: document.getElementById('navMenu').getAttribute('aria-expanded'),
  }));
  if (!openedFromNav.menuOpen || openedFromNav.focus !== 'prev'
      || openedFromNav.expanded !== 'true') {
    fail('the presenter menu nav button did not open and focus the menu: '
      + JSON.stringify(openedFromNav));
  }
  await page.keyboard.press('Escape');
  const closedFromNav = await page.evaluate(() => ({
    menuOpen: document.getElementById('presenterMenu').classList.contains('open'),
    focus: document.activeElement && document.activeElement.id,
    expanded: document.getElementById('navMenu').getAttribute('aria-expanded'),
  }));
  if (closedFromNav.menuOpen || closedFromNav.focus !== 'navMenu'
      || closedFromNav.expanded !== 'false') {
    fail('closing the presenter menu did not restore nav focus: '
      + JSON.stringify(closedFromNav));
  }
  await page.keyboard.press('Enter');
  const openedByNavKey = await page.evaluate(() => ({
    menuOpen: document.getElementById('presenterMenu').classList.contains('open'),
    focus: document.activeElement && document.activeElement.getAttribute('data-menu-action'),
  }));
  if (!openedByNavKey.menuOpen || openedByNavKey.focus !== 'prev') {
    fail('Enter on the nav menu button did not open the presenter menu: '
      + JSON.stringify(openedByNavKey));
  }
  await page.keyboard.press('Escape');

  await page.keyboard.press('m');
  const menu = await page.evaluate(() => ({
    open: document.getElementById('presenterMenu').classList.contains('open'),
    expanded: document.getElementById('navMenu').getAttribute('aria-expanded'),
    visibleActions: Array.prototype.filter.call(
      document.querySelectorAll('.presenter-menu-action'),
      (button) => getComputedStyle(button).display !== 'none'
    ).length,
  }));
  if (!menu.open || menu.expanded !== 'true' || menu.visibleActions !== 11) {
    fail('M did not expose the complete presenter menu: ' + JSON.stringify(menu));
  }
  const firstMenuFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-menu-action'));
  if (firstMenuFocus !== 'prev') {
    fail('M did not focus the first presenter action: ' + firstMenuFocus);
  }
  const menuFocusState = async () => page.evaluate(() => {
    const action = document.activeElement;
    const box = action.getBoundingClientRect();
    return {
      id: action.getAttribute('data-menu-action'),
      top: box.top,
      left: box.left,
      center: (box.left + box.right) / 2,
    };
  });
  const firstMenuState = await menuFocusState();
  await page.keyboard.press('ArrowRight');
  const rightMenuState = await menuFocusState();
  await page.keyboard.press('ArrowLeft');
  const leftMenuState = await menuFocusState();
  await page.keyboard.press('ArrowDown');
  const downMenuState = await menuFocusState();
  await page.keyboard.press('ArrowUp');
  const upMenuState = await menuFocusState();
  await page.keyboard.press('End');
  const endMenuFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-menu-action'));
  await page.keyboard.press('Home');
  const homeMenuFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-menu-action'));
  if (Math.abs(rightMenuState.top - firstMenuState.top) > 1
      || rightMenuState.left <= firstMenuState.left
      || leftMenuState.id !== 'prev'
      || downMenuState.top <= firstMenuState.top
      || Math.abs(downMenuState.center - firstMenuState.center) > 1
      || upMenuState.id !== 'prev'
      || endMenuFocus !== 'pause-theme' || homeMenuFocus !== 'prev') {
    fail('presenter menu grid arrows/home/end navigation is wrong: '
      + JSON.stringify({ firstMenuState, rightMenuState, leftMenuState,
        downMenuState, upMenuState, endMenuFocus, homeMenuFocus }));
  }
  await page.keyboard.press('Tab');
  const tabMenuFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-menu-action'));
  await page.keyboard.press('Shift+Tab');
  const shiftTabMenuFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-menu-action'));
  if (tabMenuFocus !== 'home' || shiftTabMenuFocus !== 'prev') {
    fail('presenter menu Tab navigation is wrong: '
      + JSON.stringify({ tabMenuFocus, shiftTabMenuFocus }));
  }
  const helpAction = page.locator('[data-menu-action="help"]');
  const beforeHover = await helpAction.boundingBox();
  await helpAction.hover();
  const afterHover = await helpAction.boundingBox();
  if (!beforeHover || !afterHover
      || Math.abs(beforeHover.width - afterHover.width) > 0.5
      || Math.abs(beforeHover.height - afterHover.height) > 0.5) {
    fail('presenter menu action changed size on hover: '
      + JSON.stringify({ beforeHover, afterHover }));
  }
  await helpAction.click();
  const helpFromMenu = await page.evaluate(() => ({
    helpOpen: document.getElementById('helpOverlay').classList.contains('open'),
    menuOpen: document.getElementById('presenterMenu').classList.contains('open'),
  }));
  if (!helpFromMenu.helpOpen || helpFromMenu.menuOpen) {
    fail('the presenter menu Help action did not leave the help modal open: '
      + JSON.stringify(helpFromMenu));
  }
  await page.keyboard.press('x');

  if (staticBase) {
    await page.goto(staticBase + '/index.html', { waitUntil: 'load' });
    const staticPayload = await page.evaluate(() => ({
      payload: !!document.getElementById('lwp-theme-data'),
    }));
    if (staticPayload.payload) {
      fail('--no-essential-theme unexpectedly left a runtime payload: '
        + JSON.stringify(staticPayload));
    }
    await page.keyboard.press('h');
    const staticHelp = await page.evaluate(() => ({
      open: document.getElementById('helpOverlay').classList.contains('open'),
      themeLine: Array.prototype.some.call(
        document.querySelectorAll('#helpList li'),
        (li) => li.textContent.indexOf('Changer de thème pendant la présentation') !== -1
      ),
    }));
    if (!staticHelp.open || staticHelp.themeLine) {
      fail('static pages advertised a theme picker without alternatives: '
        + JSON.stringify(staticHelp));
    }
    await page.keyboard.press('x');
    await page.keyboard.press('c');
    const staticPicker = await page.evaluate(() => ({
      open: document.getElementById('themeMenu').classList.contains('open'),
    }));
    if (staticPicker.open) {
      fail('C opened a picker on a static page: ' + JSON.stringify(staticPicker));
    }
  }

  await browser.close();
  if (errors.length) fail('page errors: ' + errors.join(' | '));
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
