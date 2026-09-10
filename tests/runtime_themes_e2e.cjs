// Browser probe for the runtime theme payload, the C picker and the
// global M menu. Invoked by tests/test_runtime_themes.py.

const { chromium } = require('playwright');

function fail(message) {
  console.error('E2E failure: ' + message);
  process.exitCode = 1;
}

async function main() {
  const [base, staticBase, zeroDurationBase, presentationBase] = process.argv.slice(2);
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
      scrollLabel: document.querySelector('[data-lwp-i18n="menu_scroll"]').textContent,
      scrollValue: document.getElementById('menuScrollValue').textContent,
      menuHelp: document.querySelector('[data-lwp-i18n="menu_help"]').textContent,
    };
  });
  if (french.htmlLang !== 'fr' || french.auto !== true
      || french.packs.join('|') !== 'en|fr'
      || french.helpTitle !== 'Raccourcis clavier'
      || french.shareLabel !== 'Partager'
      || french.scrollLabel !== 'Défilement'
      || french.scrollValue !== '350 ms'
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
    scrollLabel: document.querySelector('[data-lwp-i18n="menu_scroll"]').textContent,
    scrollValue: document.getElementById('menuScrollValue').textContent,
    readLabel: document.querySelector('[data-lwp-i18n="series_read"]').textContent,
    menuHelp: document.querySelector('[data-lwp-i18n="menu_help"]').textContent,
  }));
  if (english.htmlLang !== 'en'
      || english.helpTitle !== 'Keyboard shortcuts'
      || english.shareLabel !== 'Share'
      || english.scrollLabel !== 'Scroll'
      || english.scrollValue !== '350 ms'
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
  const hiddenNavigation = await touchPage.evaluate(() => ({
    idle: document.documentElement.classList.contains('nav-idle'),
    opacity: getComputedStyle(document.querySelector('.nav-buttons')).opacity,
    pointerEvents: getComputedStyle(document.querySelector('.nav-buttons')).pointerEvents,
  }));
  if (!hiddenNavigation.idle || hiddenNavigation.pointerEvents !== 'none') {
    fail('mobile double tap did not hide navigation immediately: '
      + JSON.stringify(hiddenNavigation));
  }
  await touchPage.keyboard.press('h');
  const mobileHelp = await touchPage.evaluate(() => {
    const keys = document.querySelector('.help-keys');
    const desc = document.querySelector('.help-desc');
    const keyboard = document.querySelector('.help-keyboard');
    const touch = document.querySelector('.help-touch');
    return {
      open: document.getElementById('helpOverlay').classList.contains('open'),
      keysWidth: keys ? keys.getBoundingClientRect().width : 0,
      descWidth: desc ? desc.getBoundingClientRect().width : 0,
      mode: document.getElementById('helpModeToggle').getAttribute('aria-checked'),
      modeValue: document.getElementById('helpModeValue').textContent,
      keyboardCount: document.querySelectorAll('.help-keyboard').length,
      keyboardHidden: keyboard ? keyboard.hidden : true,
      touchVisible: !!touch && !touch.hidden,
    };
  });
  if (!mobileHelp.open || mobileHelp.descWidth <= mobileHelp.keysWidth) {
    fail('mobile help columns are not balanced: ' + JSON.stringify(mobileHelp));
  }
  if (mobileHelp.mode !== 'true' || mobileHelp.modeValue !== 'Tactile'
      || mobileHelp.keyboardCount === 0 || !mobileHelp.keyboardHidden
      || !mobileHelp.touchVisible) {
    fail('mobile help did not default to touch variants while retaining keyboard help: '
      + JSON.stringify(mobileHelp));
  }
  await touchPage.click('#helpModeToggle');
  const mobileKeyboardHelp = await touchPage.evaluate(() => ({
    mode: document.getElementById('helpModeToggle').getAttribute('aria-checked'),
    modeValue: document.getElementById('helpModeValue').textContent,
    keyboardHidden: document.querySelector('.help-keyboard').hidden,
    touchHidden: document.querySelector('.help-touch').hidden,
  }));
  if (mobileKeyboardHelp.mode !== 'false' || mobileKeyboardHelp.modeValue !== 'Clavier'
      || mobileKeyboardHelp.keyboardHidden || !mobileKeyboardHelp.touchHidden) {
    fail('mobile help switch could not expose keyboard variants: '
      + JSON.stringify(mobileKeyboardHelp));
  }
  await touchContext.close();
  if (touchErrors.length) fail('Mobile page errors: ' + touchErrors.join(' | '));

  const initial = await page.evaluate(() => ({
    payload: !!document.getElementById('lwp-theme-data'),
    primary: JSON.parse(document.getElementById('lwp-theme-data').textContent).primary,
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
  }));
  if (!initial.payload || initial.primary !== 'custom(print-oldpress)') {
    fail('the index did not load the effective primary theme: ' + JSON.stringify(initial));
  }

  await page.setViewportSize({ width: 600, height: 800 });
  await page.keyboard.press('c');
  const picker = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    focused: document.activeElement && document.activeElement.id,
    options: document.querySelectorAll('#themeOptions .theme-option').length,
    previews: Array.prototype.map.call(
      document.querySelectorAll('#themeOptions .theme-option[data-theme]'), (button) => {
        const style = getComputedStyle(button);
        return {
          background: style.backgroundColor,
          gradient: style.backgroundImage,
          foreground: style.color,
        };
      }),
  }));
  if (!picker.open || picker.focused !== 'themeFilter' || picker.options < 4) {
    fail('C did not open the theme picker correctly: ' + JSON.stringify(picker));
  }
  if (picker.previews.some((preview) =>
      !preview.background || preview.background === 'rgba(0, 0, 0, 0)'
      || !preview.gradient || preview.gradient === 'none'
      || !preview.foreground || preview.foreground === 'rgba(0, 0, 0, 0)')) {
    fail('theme picker options do not carry resolved visual previews: '
      + JSON.stringify(picker.previews));
  }

  const themeGrid = await page.evaluate(() => Array.prototype.map.call(
    document.querySelectorAll('#themeOptions .theme-option'), (button) => {
      const rect = button.getBoundingClientRect();
      return { theme: button.getAttribute('data-theme'), left: rect.left, top: rect.top };
    }
  ));
  if (themeGrid.length < 4
      || Math.abs(themeGrid[0].top - themeGrid[1].top) > 1
      || themeGrid[2].top <= themeGrid[0].top
      || Math.abs(themeGrid[0].left - themeGrid[2].left) > 1) {
    fail('theme picker did not render the expected two-column grid: '
      + JSON.stringify(themeGrid));
  }

  await page.keyboard.press('ArrowDown');
  const themeDownFromFilterFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.evaluate(() => document.getElementById('themeFilter').focus());
  await page.keyboard.press('ArrowUp');
  const themeUpFromFilterFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowDown');
  const themeDownFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('ArrowUp');
  const themeUpFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('ArrowRight');
  const themeRightFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('ArrowLeft');
  const themeLeftFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('End');
  const themeEndFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('ArrowUp');
  const themeUpFromLastRowFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  await page.keyboard.press('Home');
  const themeHomeFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-theme'));
  if (themeDownFromFilterFocus !== null
      || themeUpFromFilterFocus !== themeGrid[themeGrid.length - 1].theme
      || themeDownFocus !== 'print-oldpress'
      || themeUpFocus !== null
      || themeRightFocus !== 'custom(print-oldpress)'
      || themeLeftFocus !== null
      || themeEndFocus !== themeGrid[themeGrid.length - 1].theme
      || themeUpFromLastRowFocus !== themeGrid[themeGrid.length - 3].theme
      || themeHomeFocus !== null
      ) {
    fail('theme picker arrow/home/end navigation is wrong: '
      + JSON.stringify({ themeDownFromFilterFocus, themeUpFromFilterFocus,
        themeDownFocus, themeUpFocus, themeEndFocus, themeUpFromLastRowFocus,
        themeHomeFocus, themeRightFocus, themeLeftFocus }));
  }
  await page.keyboard.press('Escape');
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.keyboard.press('c');
  const reopenedPicker = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    focused: document.activeElement && document.activeElement.id,
  }));
  if (!reopenedPicker.open || reopenedPicker.focused !== 'themeFilter') {
    fail('C did not reopen the theme picker after arrow navigation: '
      + JSON.stringify(reopenedPicker));
  }

  // The filter is focused first; four theme choices follow it in the dialog's
  // tab order. Presentation choices are before the filter and do not count.
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
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
      || switched.ink.toLowerCase().indexOf('#000000') !== 0) {
    fail('the raw alternate theme did not replace the settings-only ink: '
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
      || carried.ink.toLowerCase().indexOf('#000000') !== 0) {
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
    appearanceLine: Array.prototype.some.call(
      document.querySelectorAll('#helpList li'),
      (li) => li.textContent.indexOf('Changer d’apparence pendant la présentation') !== -1
    ),
    helpOpenLine: Array.prototype.some.call(
      document.querySelectorAll('#helpList li'),
      (li) => li.textContent.indexOf('Ouvre la fenêtre d\'aide') !== -1
    ),
    scrollLine: Array.prototype.some.call(
      document.querySelectorAll('#helpList li'),
      (li) => li.querySelector('.help-keys')
        && li.querySelector('.help-keyboard')
        && li.querySelector('.help-keyboard').textContent === 'I'
        && li.textContent.indexOf('défilement') !== -1
    ),
    mode: document.getElementById('helpModeToggle').getAttribute('aria-checked'),
    modeValue: document.getElementById('helpModeValue').textContent,
    keyboardCount: document.querySelectorAll('.help-keyboard').length,
    keyboardHidden: document.querySelector('.help-keyboard').hidden,
    touchHidden: document.querySelector('.help-touch').hidden,
    stamp: document.querySelector('.help-stamp')
      ? document.querySelector('.help-stamp').textContent.trim() : '',
    stampNameIsBold: !!document.querySelector('.help-stamp strong'),
    noHelpFoot: !document.querySelector('.help-foot'),
  }));
  if (!help.open || help.role !== 'dialog' || !help.titleId
      || help.labelledby !== 'helpTitle' || help.cardTabindex !== '0'
      || !help.appearanceLine || !help.helpOpenLine || !help.scrollLine || !help.noHelpFoot
      || help.mode !== 'false' || help.modeValue !== 'Clavier'
      || help.keyboardCount === 0 || help.keyboardHidden || !help.touchHidden
      || !/^Compilé avec LightWebPres v\d+\.\d+\.\d+$/.test(help.stamp)
      || !help.stampNameIsBold) {
    fail('H did not expose a proper modal with theme action and version stamp: ' + JSON.stringify(help));
  }
  const helpScrollBefore = await page.evaluate(() => {
    const overlay = document.getElementById('helpOverlay');
    const card = document.querySelector('.help-card');
    // Force overflow so this test remains about keyboard ownership rather
    // than the fixture's current amount of translated help text.
    card.style.minHeight = Math.max(window.innerHeight * 2, 1200) + 'px';
    overlay.scrollTop = 0;
    card.focus();
    return {
      top: overlay.scrollTop,
      max: overlay.scrollHeight - overlay.clientHeight,
    };
  });
  if (helpScrollBefore.max <= 0) {
    fail('the help probe did not create a scrollable foreground surface: '
      + JSON.stringify(helpScrollBefore));
  }
  await page.keyboard.press('ArrowDown');
  const helpScrollAfter = await page.evaluate(() => ({
    top: document.getElementById('helpOverlay').scrollTop,
    open: document.getElementById('helpOverlay').classList.contains('open'),
  }));
  if (!helpScrollAfter.open || helpScrollAfter.top <= helpScrollBefore.top) {
    fail('ArrowDown did not scroll the open help overlay: '
      + JSON.stringify({ helpScrollBefore, helpScrollAfter }));
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

  await page.keyboard.press('h');
  await page.click('#helpModeToggle');
  const touchHelp = await page.evaluate(() => ({
    mode: document.getElementById('helpModeToggle').getAttribute('aria-checked'),
    modeValue: document.getElementById('helpModeValue').textContent,
    keyboardHidden: document.querySelector('.help-keyboard').hidden,
    touchHidden: document.querySelector('.help-touch').hidden,
  }));
  if (touchHelp.mode !== 'true' || touchHelp.modeValue !== 'Tactile'
      || !touchHelp.keyboardHidden || touchHelp.touchHidden) {
    fail('help switch did not expose the touch variants: ' + JSON.stringify(touchHelp));
  }
  await page.click('#helpAbout');
  const about = await page.evaluate(() => ({
    helpOpen: document.getElementById('helpOverlay').classList.contains('open'),
    open: document.getElementById('aboutOverlay').classList.contains('open'),
    hidden: document.getElementById('aboutOverlay').getAttribute('aria-hidden'),
    role: document.getElementById('aboutOverlay').getAttribute('role'),
    focus: document.activeElement && document.activeElement.id,
    title: document.getElementById('aboutTitle').textContent,
    description: document.getElementById('aboutDescription').textContent,
    github: document.querySelector('.about-link').getAttribute('href'),
    license: document.querySelector('.about-card p[data-lwp-i18n="about_license"]').textContent,
  }));
  if (!about.helpOpen || !about.open || about.hidden !== 'false'
      || about.role !== 'dialog' || about.focus !== 'aboutClose'
      || about.title !== 'À propos de LightWebPres'
      || about.description.indexOf('articles Markdown') === -1
      || about.github !== 'https://github.com/Fade78/lightwebpres'
      || about.license.indexOf('GNU GPL') === -1
      || about.license.indexOf('Output Exception') === -1) {
    fail('LightWebPres about dialog is incomplete: ' + JSON.stringify(about));
  }
  await page.keyboard.press('Escape');
  const aboutClosed = await page.evaluate(() => ({
    helpOpen: document.getElementById('helpOverlay').classList.contains('open'),
    aboutOpen: document.getElementById('aboutOverlay').classList.contains('open'),
    focus: document.activeElement && document.activeElement.id,
  }));
  if (!aboutClosed.helpOpen || aboutClosed.aboutOpen || aboutClosed.focus !== 'helpAbout') {
    fail('closing the about dialog did not return to help: ' + JSON.stringify(aboutClosed));
  }
  await page.keyboard.press('Escape');
  await page.reload({ waitUntil: 'load' });
  await page.keyboard.press('h');
  const rememberedHelp = await page.evaluate(() => ({
    mode: document.getElementById('helpModeToggle').getAttribute('aria-checked'),
    modeValue: document.getElementById('helpModeValue').textContent,
    keyboardHidden: document.querySelector('.help-keyboard').hidden,
    touchHidden: document.querySelector('.help-touch').hidden,
  }));
  if (rememberedHelp.mode !== 'true' || rememberedHelp.modeValue !== 'Tactile'
      || !rememberedHelp.keyboardHidden || rememberedHelp.touchHidden) {
    fail('help mode choice was not remembered: ' + JSON.stringify(rememberedHelp));
  }
  await page.keyboard.press('x');

  if (zeroDurationBase) {
    const zeroPage = await context.newPage();
    const zeroErrors = [];
    zeroPage.on('pageerror', (error) => zeroErrors.push(String(error)));
    await zeroPage.goto(zeroDurationBase + '/index.html', { waitUntil: 'load' });
    await zeroPage.keyboard.press('m');
    const zeroScroll = await zeroPage.evaluate(() => {
      const action = document.getElementById('menuScroll');
      return {
        hidden: action ? action.hidden : false,
        disabled: action ? action.disabled : false,
        display: action ? getComputedStyle(action).display : '',
      };
    });
    if (!zeroScroll.hidden || !zeroScroll.disabled || zeroScroll.display !== 'none') {
      fail('zero-duration series exposed an inert Scroll action: '
        + JSON.stringify(zeroScroll));
    }
    await zeroPage.close();
    if (zeroErrors.length) fail('Zero-duration page errors: ' + zeroErrors.join(' | '));
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
  if (!openedFromNav.menuOpen || openedFromNav.focus !== 'reading'
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
  if (!openedByNavKey.menuOpen || openedByNavKey.focus !== 'reading') {
    fail('Enter on the nav menu button did not open the presenter menu: '
      + JSON.stringify(openedByNavKey));
  }
  await page.keyboard.press('Escape');

  await page.keyboard.press('m');
  const menu = await page.evaluate(() => ({
    open: document.getElementById('presenterMenu').classList.contains('open'),
    expanded: document.getElementById('navMenu').getAttribute('aria-expanded'),
    visibleActions: Array.prototype.filter.call(
      document.querySelectorAll('#presenterMenu .presenter-menu-action'),
      (button) => getComputedStyle(button).display !== 'none'
    ).length,
  }));
  if (!menu.open || menu.expanded !== 'true' || menu.visibleActions !== 13) {
    fail('M did not expose the complete presenter menu: ' + JSON.stringify(menu));
  }
  const menuTypography = await page.evaluate(() => {
    const size = (id) => getComputedStyle(document.getElementById(id)).fontSize;
    return { prev: size('menuPrev'), home: size('menuHome'), next: size('menuNext') };
  });
  if (menuTypography.prev !== menuTypography.home
      || menuTypography.home !== menuTypography.next) {
    fail('a custom nav-btn.size changed the presenter Home action text size: '
      + JSON.stringify(menuTypography));
  }
  const firstMenuFocus = await page.evaluate(() =>
    document.activeElement && document.activeElement.getAttribute('data-menu-action'));
  if (firstMenuFocus !== 'reading') {
    fail('M did not focus the first presenter action: ' + firstMenuFocus);
  }
  const scrollAction = page.locator('[data-menu-action="scroll"]');
  await scrollAction.click();
  const scrollOff = await page.evaluate(() => ({
    value: document.getElementById('menuScrollValue').textContent,
    pressed: document.getElementById('menuScroll').getAttribute('aria-pressed'),
  }));
  await page.keyboard.press('m');
  await page.locator('[data-menu-action="scroll"]').click();
  const scrollOn = await page.evaluate(() => ({
    value: document.getElementById('menuScrollValue').textContent,
    pressed: document.getElementById('menuScroll').getAttribute('aria-pressed'),
  }));
  if (scrollOff.value !== '0 ms' || scrollOff.pressed !== 'false'
      || scrollOn.value !== '350 ms' || scrollOn.pressed !== 'true') {
    fail('Scroll menu action did not toggle the configured duration: '
      + JSON.stringify({ scrollOff, scrollOn }));
  }

  await page.keyboard.press('m');
  await page.keyboard.press('i');
  const shortcutOff = await page.evaluate(() => ({
    menuOpen: document.getElementById('presenterMenu').classList.contains('open'),
    value: document.getElementById('menuScrollValue').textContent,
    pressed: document.getElementById('menuScroll').getAttribute('aria-pressed'),
  }));
  await page.keyboard.press('i');
  const shortcutOn = await page.evaluate(() => ({
    value: document.getElementById('menuScrollValue').textContent,
    pressed: document.getElementById('menuScroll').getAttribute('aria-pressed'),
  }));
  if (shortcutOff.menuOpen || shortcutOff.value !== '0 ms'
      || shortcutOff.pressed !== 'false' || shortcutOn.value !== '350 ms'
      || shortcutOn.pressed !== 'true') {
    fail('I did not toggle the configured scroll duration: '
      + JSON.stringify({ shortcutOff, shortcutOn }));
  }

  // The menu state is page-local, so use an article page to test the actual
  // slide jump. `html` carries scroll-behavior: smooth; the instant path must
  // override it rather than merely skipping requestAnimationFrame().
  const instantPage = await context.newPage();
  const instantErrors = [];
  instantPage.on('pageerror', (error) => instantErrors.push(String(error)));
  await instantPage.goto(base + '/first.html', { waitUntil: 'load' });
  await instantPage.waitForSelector('.nav-dots a');
  await instantPage.keyboard.press('m');
  await instantPage.locator('[data-menu-action="scroll"]').click();
  const instantJump = await instantPage.evaluate(() => {
    const slide = document.querySelectorAll('section.slide')[1];
    const targetY = slide.getBoundingClientRect().top + window.scrollY;
    document.getElementById('navNext').click();
    return { targetY, scrollY: window.scrollY };
  });
  if (Math.abs(instantJump.scrollY - instantJump.targetY) > 1) {
    fail('the Scroll menu action did not make the next slide instant: '
      + JSON.stringify(instantJump));
  }
  await instantPage.close();
  if (instantErrors.length) fail('Instant-scroll page errors: ' + instantErrors.join(' | '));

  await page.keyboard.press('m');
  // The reading submenu launcher is the first cell of the main action grid.
  await page.locator('[data-menu-action="reading"]').focus();
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
      || leftMenuState.id !== 'reading'
      || downMenuState.top <= firstMenuState.top
      || Math.abs(downMenuState.center - firstMenuState.center) > 1
      || upMenuState.id !== 'reading'
      || endMenuFocus !== 'pause-theme' || homeMenuFocus !== 'reading') {
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
  if (tabMenuFocus !== 'prev' || shiftTabMenuFocus !== 'reading') {
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

  if (presentationBase) {
    const presentationContext = await browser.newContext({
      locale: 'fr-FR',
      viewport: { width: 1280, height: 800 },
    });
    const presentationPage = await presentationContext.newPage();
    const presentationErrors = [];
    presentationPage.on('pageerror', (error) => presentationErrors.push(String(error)));
    await presentationPage.goto(presentationBase + '/index.html', { waitUntil: 'load' });

    const presentationInitial = await presentationPage.evaluate(() => {
      const data = JSON.parse(document.getElementById('lwp-presentation-data').textContent);
      return {
        primary: data.primary,
        selectors: data.presets.map((preset) => preset.selector),
        indexShell: !!document.querySelector('#lwp-presentation-index .lwp-doc-index-frame'),
        appearance: document.querySelector('[data-menu-action="theme"] .presenter-menu-label').textContent,
        buttonPreviews: Array.from(
          document.querySelectorAll('#presentationOptions .presentation-option'),
        ).map((button) => ({
          background: button.style.backgroundColor,
          gradient: button.style.backgroundImage,
          foreground: button.style.color,
        })),
      };
    });
    if (presentationInitial.primary !== 'lightwebpres-docs@0.1.0/docs'
        || presentationInitial.selectors.join('|')
          !== 'lightwebpres-docs@0.1.0/docs|lightwebpres-docs@0.1.0/compact|builtin/standard'
        || !presentationInitial.indexShell
        || presentationInitial.appearance !== 'Changer d’apparence'
        || presentationInitial.buttonPreviews.length !== 2
        || presentationInitial.buttonPreviews.some((preview) => !preview.background
          || preview.background === 'rgba(0, 0, 0, 0)'
          || !preview.gradient || preview.gradient === 'none'
          || !preview.foreground || preview.foreground === 'rgba(0, 0, 0, 0)')) {
      fail('runtime presentation catalogue or appearance label is wrong: '
        + JSON.stringify(presentationInitial));
    }

    await presentationPage.keyboard.press('c');
    const presentationPicker = await presentationPage.evaluate(() => ({
      open: document.getElementById('themeMenu').classList.contains('open'),
      title: document.getElementById('themeMenuTitle').textContent,
      presentationTitle: document.getElementById('presentationAxisTitle').textContent,
      identityTitle: document.getElementById('identityAxisTitle').textContent,
      identities: Array.from(document.querySelectorAll('#identityOptions .identity-option'))
        .map((button) => button.textContent),
      themeTitle: document.getElementById('themeAxisTitle').textContent,
      options: document.querySelectorAll('#presentationOptions .presentation-option').length,
      active: document.querySelector('#presentationOptions .presentation-option.active')
        .getAttribute('data-presentation'),
      standard: JSON.parse(document.getElementById('lwp-presentation-data').textContent)
        .presets.find((preset) => preset.selector === 'builtin/standard'),
    }));
    if (!presentationPicker.open
        || presentationPicker.title !== 'Choisir une apparence'
        || presentationPicker.presentationTitle !== 'Preset'
        || presentationPicker.identityTitle !== 'Identité'
        || presentationPicker.identities.join('|') !== 'LightWebPres documentation|LightWebPres'
        || presentationPicker.themeTitle !== 'Thème'
        || presentationPicker.options !== 2
        || presentationPicker.standard.label !== 'Standard'
        || presentationPicker.standard.identity !== 'builtin'
        || presentationPicker.active !== 'lightwebpres-docs@0.1.0/docs') {
      fail('C did not expose the identity, preset and theme axes: '
        + JSON.stringify(presentationPicker));
    }

    await presentationPage.locator('#identityOptions .identity-option').first().focus();
    await presentationPage.keyboard.press('ArrowRight');
    const identityRight = await presentationPage.evaluate(() =>
      document.activeElement.getAttribute('data-identity'));
    await presentationPage.keyboard.press('Home');
    const identityHome = await presentationPage.evaluate(() =>
      document.activeElement.getAttribute('data-identity'));
    await presentationPage.keyboard.press('End');
    const identityEnd = await presentationPage.evaluate(() =>
      document.activeElement.getAttribute('data-identity'));
    await presentationPage.keyboard.press('Home');
    await presentationPage.keyboard.press('Shift+Tab');
    const trappedLast = await presentationPage.evaluate(() =>
      !!document.activeElement.closest('#themeMenu')
      && document.activeElement.matches('#themeOptions .theme-option'));
    await presentationPage.keyboard.press('Tab');
    const trappedFirst = await presentationPage.evaluate(() =>
      document.activeElement.matches('#identityOptions .identity-option'));
    if (identityRight !== 'builtin' || identityEnd !== 'builtin'
        || identityHome !== 'lightwebpres-docs@0.1.0' || !trappedLast || !trappedFirst) {
      fail('identity grid or three-axis focus trap is wrong: '
        + JSON.stringify({ identityRight, identityHome, identityEnd, trappedLast, trappedFirst }));
    }
    await presentationPage.selectOption('#themeSource', 'identity');
    const kitThemes = await presentationPage.evaluate(() => Array.from(
      document.querySelectorAll('#themeOptions [data-theme]'),
      (button) => button.getAttribute('data-theme')));
    if (kitThemes.join('|') !== 'kit:lightwebpres-docs@0.1.0/docs|kit:lightwebpres-docs@0.1.0/compact') {
      fail('current identity omitted a secondary kit theme: ' + JSON.stringify(kitThemes));
    }
    await presentationPage.selectOption('#themeSource', 'all');
    const allThemes = await presentationPage.locator('#themeOptions [data-theme]').count();
    await presentationPage.selectOption('#themeSource', 'applicable');
    const applicableThemes = await presentationPage.locator('#themeOptions [data-theme]').count();
    if (allThemes !== applicableThemes || allThemes <= kitThemes.length) {
      fail('Applicable must include all published typed themes, without a brand restriction');
    }
    if (kitThemes.length) {
      await presentationPage.locator(
        '#themeOptions [data-theme="kit:lightwebpres-docs@0.1.0/compact"]',
      ).click();
      const appliedKitTheme = await presentationPage.evaluate(() => {
        const data = JSON.parse(document.getElementById('lwp-theme-data').textContent);
        const theme = data.themes.find((item) => item.slug === 'kit:lightwebpres-docs@0.1.0/compact');
        const inkIndex = data.vars.indexOf('--color-ink');
        return {
          expected: theme.values.find(([index]) => index === inkIndex)[1],
          actual: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
          preset: document.querySelector('#presentationOptions .active').getAttribute('data-presentation'),
        };
      });
      if (appliedKitTheme.actual !== appliedKitTheme.expected
          || appliedKitTheme.preset !== 'lightwebpres-docs@0.1.0/docs') {
        fail('secondary kit theme was not applied independently of its preset: '
          + JSON.stringify(appliedKitTheme));
      }
      await presentationPage.keyboard.press('c');
      await presentationPage.locator('#themeOptions [data-theme-mode="preset-default"]').click();
      await presentationPage.keyboard.press('c');
    }

    await presentationPage.keyboard.press('Escape');
    await presentationPage.locator('a.article-card').first().focus();
    const focusedArticleHref = await presentationPage.locator('a.article-card').first().getAttribute('href');
    await presentationPage.keyboard.press('c');

    await presentationPage.locator('#presentationOptions .presentation-option').nth(1).click();
    const restoredArticleHref = await presentationPage.evaluate(() => document.activeElement.getAttribute('href'));
    if (restoredArticleHref !== focusedArticleHref) {
      fail('index replacement lost the picker return focus');
    }
    const articleHref = await presentationPage.locator('a.article-card').first().getAttribute('href');
    await presentationPage.goto(new URL(articleHref, presentationBase + '/index.html').href,
      { waitUntil: 'load' });
    const compactArticle = await presentationPage.evaluate(() => ({
      hero: !!document.querySelector('.lwp-doc-cover-hero'),
      footer: document.querySelector('section.slide').textContent
        .includes('LIGHTWEBPRES / OFFICIAL DOCUMENTATION'),
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
      slideCount: document.querySelectorAll('section.slide').length,
    }));
    if (!compactArticle.hero || compactArticle.footer || compactArticle.slideCount < 2) {
      fail('the selected presentation did not replace the article layer: '
        + JSON.stringify(compactArticle));
    }

    await presentationPage.locator('#navNext').click();
    const beforeSwitch = await presentationPage.evaluate(() => ({
      hash: window.location.hash,
      activeDot: document.querySelector('.nav-dots a.active')
        ? document.querySelector('.nav-dots a.active').getAttribute('href') : '',
    }));
    await presentationPage.keyboard.press('c');
    await presentationPage.locator('#themeOptions .theme-option[data-theme="print-ink"]').click();
    const explicitTheme = await presentationPage.evaluate(() => ({
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
    }));
    await presentationPage.keyboard.press('c');
    await presentationPage.locator('#presentationOptions .presentation-option').first().click();
    const afterSwitch = await presentationPage.evaluate(() => ({
      hash: window.location.hash,
      activeDot: document.querySelector('.nav-dots a.active')
        ? document.querySelector('.nav-dots a.active').getAttribute('href') : '',
      hero: !!document.querySelector('.lwp-doc-cover-hero'),
      footer: document.querySelector('section.slide').textContent
        .includes('LIGHTWEBPRES / OFFICIAL DOCUMENTATION'),
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
    }));
    if (afterSwitch.hash !== beforeSwitch.hash
        || afterSwitch.activeDot !== beforeSwitch.activeDot
        || afterSwitch.hero || !afterSwitch.footer
        || afterSwitch.ink !== explicitTheme.ink) {
      fail('switching presentation did not preserve the slide or restore the primary layer: '
        + JSON.stringify({ beforeSwitch, afterSwitch, explicitTheme }));
    }

    await presentationPage.keyboard.press('c');
    await presentationPage.locator('#themeOptions .theme-option[data-theme-mode="preset-default"]').click();
    const primaryDefault = await presentationPage.evaluate(() => ({
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
      hero: !!document.querySelector('.lwp-doc-cover-hero'),
    }));
    await presentationPage.keyboard.press('c');
    await presentationPage.locator('#presentationOptions .presentation-option').nth(1).click();
    const compactDefault = await presentationPage.evaluate(() => ({
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
      hero: !!document.querySelector('.lwp-doc-cover-hero'),
    }));
    if (primaryDefault.hero || !compactDefault.hero
        || primaryDefault.ink === compactDefault.ink) {
      fail('Preset default did not follow each presentation base theme: '
        + JSON.stringify({ primaryDefault, compactDefault, compactArticle }));
    }

    await presentationPage.keyboard.press('c');
    await presentationPage.locator('#identityOptions [data-identity="builtin"]').click();
    await presentationPage.selectOption('#themeSource', 'identity');
    const nativeThemes = await presentationPage.evaluate(() => Array.from(
      document.querySelectorAll('#themeOptions [data-theme]'),
      (button) => button.getAttribute('data-theme')));
    if (nativeThemes.join('|') !== 'print-ink|kit:builtin/light'
        || !await presentationPage.locator('#identityAxisTitle').isVisible()
        || !await presentationPage.locator('#presentationOptions').isVisible()) {
      fail('native identity must include globals, exclude kit themes and retain multi-identity axes: '
        + JSON.stringify(nativeThemes));
    }
    await presentationPage.selectOption('#themeSource', 'applicable');
    await presentationPage.locator(
      '#presentationOptions .presentation-option[data-presentation="builtin/standard"]',
    ).click();
    const defaultPresentation = await presentationPage.evaluate(() => ({
      hero: !!document.querySelector('.lwp-doc-cover-hero'),
      footer: document.querySelector('section.slide').textContent
        .includes('LIGHTWEBPRES / OFFICIAL DOCUMENTATION'),
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
    }));
    if (defaultPresentation.hero || defaultPresentation.footer) {
      fail('the native Standard preset kept kit markup: '
        + JSON.stringify(defaultPresentation));
    }

    await presentationPage.keyboard.press('c');
    await presentationPage.locator('#themeOptions .theme-option[data-theme="print-ink"]').click();
    const defaultExplicit = await presentationPage.evaluate(() => ({
      hero: !!document.querySelector('.lwp-doc-cover-hero'),
      footer: document.querySelector('section.slide').textContent
        .includes('LIGHTWEBPRES / OFFICIAL DOCUMENTATION'),
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
    }));
    await presentationPage.keyboard.press('c');
    await presentationPage.locator('#identityOptions [data-identity="lightwebpres-docs@0.1.0"]').click();
    const identitySelection = await presentationPage.evaluate(() => ({
      preset: document.querySelector('#presentationOptions .active').getAttribute('data-presentation'),
      theme: document.querySelector('#themeOptions .active').getAttribute('data-theme'),
      focus: document.activeElement.getAttribute('data-identity'),
    }));
    if (identitySelection.preset !== 'lightwebpres-docs@0.1.0/docs'
        || identitySelection.theme !== 'print-ink'
        || identitySelection.focus !== 'lightwebpres-docs@0.1.0') {
      fail('identity selection did not choose the first published preset, keep theme and restore focus: '
        + JSON.stringify(identitySelection));
    }
    await presentationPage.locator(
      '#presentationOptions .presentation-option[data-presentation="lightwebpres-docs@0.1.0/compact"]',
    ).click();
    const compactExplicit = await presentationPage.evaluate(() => ({
      hero: !!document.querySelector('.lwp-doc-cover-hero'),
      footer: document.querySelector('section.slide').textContent
        .includes('LIGHTWEBPRES / OFFICIAL DOCUMENTATION'),
      ink: getComputedStyle(document.documentElement)
        .getPropertyValue('--color-ink').trim(),
    }));
    if (!compactExplicit.hero || compactExplicit.footer
        || compactExplicit.ink !== defaultExplicit.ink) {
      fail('an explicit theme did not stay independent from Standard presentation: '
        + JSON.stringify({ defaultExplicit, compactExplicit }));
    }

    await presentationPage.goto(presentationBase + '/index.html', { waitUntil: 'load' });
    await presentationPage.keyboard.press('c');
    const rememberedPresentation = await presentationPage.evaluate(() => ({
      active: document.querySelector('#presentationOptions .presentation-option.active')
        .getAttribute('data-presentation'),
    }));
    if (rememberedPresentation.active !== 'lightwebpres-docs@0.1.0/compact') {
      fail('the alternate presentation selection was not persisted across pages: '
        + JSON.stringify(rememberedPresentation));
    }
    await presentationPage.keyboard.press('Escape');

    await presentationPage.goto(presentationBase + '/other-deck/index.html',
      { waitUntil: 'load' });
    await presentationPage.keyboard.press('c');
    const isolatedPresentation = await presentationPage.evaluate(() => ({
      active: document.querySelector('#presentationOptions .presentation-option.active')
        .getAttribute('data-presentation'),
    }));
    if (isolatedPresentation.active !== 'lightwebpres-docs@0.1.0/docs') {
      fail('presentation selection leaked into a different deck on the same origin: '
        + JSON.stringify(isolatedPresentation));
    }
    await presentationPage.keyboard.press('Escape');
    await presentationPage.goto(presentationBase + '/index.html', { waitUntil: 'load' });
    await presentationPage.keyboard.press('c');
    const rememberedAfterIsolation = await presentationPage.evaluate(() => ({
      active: document.querySelector('#presentationOptions .presentation-option.active')
        .getAttribute('data-presentation'),
    }));
    if (rememberedAfterIsolation.active !== 'lightwebpres-docs@0.1.0/compact') {
      fail('the original deck lost its persisted presentation after another deck opened: '
        + JSON.stringify(rememberedAfterIsolation));
    }
    await presentationPage.keyboard.press('Escape');
    await presentationContext.close();

    const englishContext = await browser.newContext({
      locale: 'en-US',
      viewport: { width: 1280, height: 800 },
    });
    const englishPage = await englishContext.newPage();
    await englishPage.goto(presentationBase + '/index.html', { waitUntil: 'load' });
    const englishInitial = await englishPage.evaluate(() => ({
      read: document.querySelector('.article-cta [data-lwp-i18n="series_read"]')
        .textContent,
      standardLabel: JSON.parse(document.getElementById('lwp-presentation-data').textContent)
        .presets.find((preset) => preset.selector === 'builtin/standard').label,
      identityLabel: document.getElementById('identityAxisTitle').textContent,
      sourceLabel: document.querySelector('#themeSource option[value="identity"]').textContent,
    }));
    await englishPage.keyboard.press('c');
    await englishPage.locator('#presentationOptions .presentation-option').nth(1).click();
    const englishAlternate = await englishPage.evaluate(() => ({
      read: document.querySelector('.article-cta [data-lwp-i18n="series_read"]')
        .textContent,
    }));
    if (englishInitial.read !== 'Read the article'
        || englishInitial.standardLabel !== 'Standard'
        || englishInitial.identityLabel !== 'Identity'
        || englishInitial.sourceLabel !== 'Current identity'
        || englishAlternate.read !== 'Read the article') {
      fail('runtime presentation fragments did not retain the browser locale: '
        + JSON.stringify({ englishInitial, englishAlternate }));
    }
    await englishContext.close();
    if (presentationErrors.length) {
      fail('Presentation page errors: ' + presentationErrors.join(' | '));
    }
  }

  if (staticBase) {
    for (const [locale, showLabel, origins] of [
      ['en-US', 'Show themes', ['Built-in', 'Installed', 'User', 'Series-local']],
      ['fr-FR', 'Afficher les thèmes', ['Intégré', 'Installé', 'Utilisateur', 'Local à la série']],
    ]) {
      const originContext = await browser.newContext({ locale });
      const originPage = await originContext.newPage();
      originPage.on('pageerror', (error) => errors.push(String(error)));
      await originPage.goto(staticBase + '/origins/index.html', { waitUntil: 'load' });
      await originPage.keyboard.press('c');
      const raw = await originPage.locator('#lwp-theme-data').textContent();
      const data = JSON.parse(raw);
      if (data.version !== 1) fail('origin labels changed the runtime schema');
      const sourceLabel = originPage.locator('label[for="themeSource"]');
      if (!await sourceLabel.isVisible() || await sourceLabel.textContent() !== showLabel) {
        fail(locale + ' theme filter label did not describe the displayed choices');
      }
      for (const filter of ['applicable', 'identity', 'all']) {
        await originPage.selectOption('#themeSource', filter);
        for (const [slug, family, owner, collection, identity, origin, label] of [
          ['print-ink', 'print', 'Commons', 'Commons', null, 'embedded', origins[0]],
          ['kit:builtin/light', 'desk', 'LightWebPres', 'builtin', 'builtin', 'builtin', origins[0]],
          ...['installed', 'user', 'series'].map((scope, i) =>
            ['origin-' + scope, 'print', 'Commons', 'Commons', null, scope, origins[i + 1]]),
        ]) {
          const theme = data.themes.find((item) => item.slug === slug);
          if (!theme || theme.origin !== origin || theme.collection !== collection
              || theme.identity !== identity) {
            fail('localized display changed raw theme ownership/origin: ' + JSON.stringify(theme));
          }
          const subtitle = originPage.locator('#themeOptions [data-theme="' + slug + '"] small');
          const expected = [family, owner, label].join(' / ');
          if (!await subtitle.isVisible() || await subtitle.textContent() !== expected) {
            fail(locale + '/' + filter + '/' + slug + ' subtitle is not ' + expected);
          }
        }
      }
      if (await originPage.locator('#lwp-theme-data').textContent() !== raw) {
        fail('rendering localized origins mutated the runtime payload');
      }
      const presets = await originPage.locator('#lwp-presentation-data').textContent();
      const native = JSON.parse(presets).presets[0];
      if (native.selector !== 'builtin/standard' || native.identity !== 'builtin'
          || native.identity_label !== 'LightWebPres' || native.collection !== 'builtin'
          || native.origin !== 'builtin') {
        fail('origin labels changed the native preset metadata: ' + presets);
      }
      await originContext.close();
    }
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
    await page.goto(staticBase + '/single-preset/index.html', { waitUntil: 'load' });
    await page.keyboard.press('c');
    const singlePreset = await page.evaluate(() => {
      const data = JSON.parse(document.getElementById('lwp-presentation-data').textContent);
      return {
        open: document.getElementById('themeMenu').classList.contains('open'),
        axes: document.querySelectorAll('#identityOptions, #presentationOptions, .appearance-axis-title').length,
        presets: data.presets.length,
        variants: Object.keys(data.variants).length,
        reset: !!document.querySelector('#themeOptions [data-theme-mode="preset-default"]'),
        active: document.querySelector('#themeOptions .active')?.getAttribute('data-theme'),
      };
    });
    if (!singlePreset.open || singlePreset.axes !== 0 || singlePreset.presets !== 1
        || singlePreset.variants !== 0 || singlePreset.reset
        || singlePreset.active !== 'print-oldpress') {
      fail('native single-preset build must expose only themes with its primary selected: '
        + JSON.stringify(singlePreset));
    }
    const noJsContext = await browser.newContext({ javaScriptEnabled: false });
    const noJsPage = await noJsContext.newPage();
    await noJsPage.goto(presentationBase + '/index.html', { waitUntil: 'load' });
    if (!await noJsPage.locator('.lwp-doc-index-frame').isVisible()
        || !await noJsPage.locator('a.article-card').first().isVisible()) {
      fail('the primary kit index needs JavaScript to display its content');
    }
    await noJsPage.goto(presentationBase + '/first.html', { waitUntil: 'load' });
    if (!await noJsPage.locator('section.slide').first().isVisible()) {
      fail('the primary kit article needs JavaScript to display its content');
    }
    await noJsContext.close();
  }

  if (staticBase) {
    for (const [mobile, locale] of [
      [false, 'en-US'], [false, 'fr-FR'], [true, 'en-US'], [true, 'fr-FR'],
    ]) {
      for (const [name, rawTheme] of [['native', 'kit:builtin/light'], ['commons', 'dracula']]) {
        const regressionContext = await browser.newContext({
          locale, isMobile: mobile, hasTouch: mobile,
          viewport: mobile ? { width: 390, height: 844 } : { width: 1280, height: 800 },
        });
        const regressionPage = await regressionContext.newPage();
        regressionPage.on('pageerror', (error) => errors.push(String(error)));
        const palette = () => regressionPage.evaluate(() => {
          const style = getComputedStyle(document.documentElement);
          return ['--color-page', '--page-bg'].map((name) => style.getPropertyValue(name).trim());
        });
        await regressionPage.goto(staticBase + '/' + name + '-raw/index.html');
        const rawPalette = await palette();
        await regressionPage.goto(staticBase + '/' + name + '-pinned/index.html');
        const pinnedPalette = await palette();
        if (pinnedPalette.some((value) => value !== '#123456FF')) {
          fail('fixture did not resolve the shared page role: ' + JSON.stringify({ name, mobile, pinnedPalette }));
        }
        await regressionPage.keyboard.press('c');
        const nativePicker = await regressionPage.evaluate(() => {
          const data = JSON.parse(document.getElementById('lwp-theme-data').textContent);
          return {
            primary: data.primary,
            published: data.themes.map((theme) => theme.slug),
            visible: Array.from(document.querySelectorAll('#themeOptions [data-theme]'),
              (button) => button.getAttribute('data-theme')),
            axes: document.querySelectorAll('#identityOptions, #presentationOptions, .appearance-axis-title').length,
            reset: !!document.querySelector('[data-theme-mode="preset-default"]'),
            active: document.querySelector('#themeOptions .active')?.getAttribute('data-theme'),
            title: document.getElementById('themeMenuTitle').textContent,
            menu: document.querySelector('[data-menu-action="theme"] .presenter-menu-label').textContent,
            help: document.querySelector('.theme-menu-help').textContent,
          };
        });
        const english = locale === 'en-US';
        if (nativePicker.axes || nativePicker.reset || nativePicker.active !== nativePicker.primary
            || nativePicker.title !== (english ? 'Choose a theme' : 'Choisir un thème')
            || nativePicker.menu !== (english ? 'Change theme' : 'Changer de thème')
            || nativePicker.help !== (english ? 'The primary theme is selected by default.'
              : 'Le thème principal est sélectionné par défaut.')
            || JSON.stringify(nativePicker.visible) !== JSON.stringify(nativePicker.published)) {
          fail('no-kit deck must expose only themes, including its effective primary: '
            + JSON.stringify({ name, mobile, locale, nativePicker }));
        }
        for (const source of ['identity', 'all', 'applicable']) {
          await regressionPage.selectOption('#themeSource', source);
          const visible = await regressionPage.locator('#themeOptions [data-theme]')
            .evaluateAll((buttons) => buttons.map((button) => button.getAttribute('data-theme')));
          if (JSON.stringify(visible) !== JSON.stringify(nativePicker.published)) {
            fail('native source filter omitted published global/native themes: '
              + JSON.stringify({ name, mobile, locale, source,
                expected: nativePicker.published, actual: visible }));
          }
        }
        await regressionPage.locator('#themeOptions [data-theme="' + rawTheme + '"]').click();
        const switchedPalette = await palette();
        if (JSON.stringify(switchedPalette) !== JSON.stringify(rawPalette)) {
          fail('raw theme retained a reference-derived settings pin: '
            + JSON.stringify({ name, mobile, rawPalette, switchedPalette }));
        }
        await regressionPage.keyboard.press('c');
        await regressionPage.locator('#themeOptions [data-theme="' + nativePicker.primary + '"]').click();
        const restoredPalette = await palette();
        if (JSON.stringify(restoredPalette) !== JSON.stringify(pinnedPalette)) {
          fail('primary theme did not restore the static cascade: ' + JSON.stringify({ name, mobile, restoredPalette }));
        }
        await regressionPage.keyboard.press('c');
        await regressionPage.locator('#themeFilter').pressSequentially('print-ink');
        await regressionPage.keyboard.press('Enter');
        const searched = await regressionPage.evaluate(() => ({
          open: document.getElementById('themeMenu').classList.contains('open'),
          theme: document.querySelector('#themeOptions .active').getAttribute('data-theme'),
        }));
        if (searched.open || searched.theme !== 'print-ink') {
          fail('search Enter applied reset instead of the matching theme: ' + JSON.stringify({ name, mobile, searched }));
        }
        await regressionPage.keyboard.press('c');
        await regressionPage.locator('#themeFilter').fill('no-such-theme');
        await regressionPage.keyboard.press('Enter');
        const noMatch = await regressionPage.evaluate(() => ({
          open: document.getElementById('themeMenu').classList.contains('open'),
          options: document.querySelectorAll('#themeOptions .theme-option').length,
        }));
        if (!noMatch.open || noMatch.options !== 0) {
          fail('an unmatched search reset the selected theme: ' + JSON.stringify({ name, mobile, noMatch }));
        }
        if (!noMatch.open) await regressionPage.keyboard.press('c');
        await regressionPage.locator('#themeFilter').fill(nativePicker.primary);
        await regressionPage.keyboard.press('Enter');
        if (JSON.stringify(await palette()) !== JSON.stringify(pinnedPalette)) {
          fail('primary theme was not accessible through search');
        }
        const storedThemes = await regressionPage.evaluate(() =>
          Object.keys(sessionStorage).filter((key) => key.startsWith('lwp-theme:')));
        if (storedThemes.length) fail('selecting the primary theme did not clear the explicit choice');
        if (name === 'commons') {
          await regressionPage.evaluate(() => {
            const data = JSON.parse(document.getElementById('lwp-presentation-data').textContent);
            const path = location.pathname.slice(0, location.pathname.lastIndexOf('/') + 1);
            const key = 'lwp-presentation:' + path + ':' + data.catalog_digest + ':'
              + data.presets.map((preset) => preset.selector).join(',');
            sessionStorage.setItem(key, 'commons/day');
          });
        }
        await regressionPage.reload();
        if (JSON.stringify(await palette()) !== JSON.stringify(pinnedPalette)) {
          fail('a hidden Commons preset selection overrode the primary theme after reload');
        }
        await regressionPage.keyboard.press('h');
        const helpLine = await regressionPage.locator('#helpList').textContent();
        if (!helpLine.includes(english ? 'Change theme during the presentation'
          : 'Changer de thème pendant la présentation')) {
          fail('no-kit shortcut help advertised appearance instead of theme');
        }
        await regressionPage.keyboard.press('Escape');
        await regressionPage.keyboard.press('c');
        await regressionPage.locator('#themeOptions [data-theme="print-ink"]').click();
        const explicitPalette = await palette();
        await regressionPage.goto(staticBase + '/' + name + '-pinned/first.html');
        if (JSON.stringify(await palette()) !== JSON.stringify(explicitPalette)) {
          fail('theme-only explicit selection did not persist to the article');
        }
        await regressionContext.close();
      }
      const kitContext = await browser.newContext({
        locale, isMobile: mobile, hasTouch: mobile,
        viewport: mobile ? { width: 390, height: 844 } : { width: 1280, height: 800 },
      });
      const kitPage = await kitContext.newPage();
      kitPage.on('pageerror', (error) => errors.push(String(error)));
      await kitPage.goto(presentationBase + '/multi-identity/index.html');
      await kitPage.keyboard.press('c');
      const published = await kitPage.locator('#themeOptions [data-theme]')
        .evaluateAll((buttons) => buttons.map((button) => button.getAttribute('data-theme')));
      for (const [identity, expected] of [
        ['lightwebpres-docs@0.1.0', ['custom(kit:lightwebpres-docs@0.1.0/docs)',
          'kit:lightwebpres-docs@0.1.0/docs', 'kit:lightwebpres-docs@0.1.0/compact']],
        ['other@0.1.0', ['kit:other@0.1.0/docs']],
        ['builtin', ['print-ink', 'kit:builtin/light']],
      ]) {
        await kitPage.locator('#identityOptions [data-identity="' + identity + '"]').click();
        for (const source of ['identity', 'all', 'applicable']) {
          await kitPage.selectOption('#themeSource', source);
          const actual = await kitPage.locator('#themeOptions [data-theme]')
            .evaluateAll((buttons) => buttons.map((button) => button.getAttribute('data-theme')));
          if (JSON.stringify(actual) !== JSON.stringify(source === 'identity' ? expected : published)) {
            fail('multi-identity membership is wrong: '
              + JSON.stringify({ mobile, locale, identity, source, expected, actual }));
          }
        }
        if (!await kitPage.locator('#identityAxisTitle').isVisible()
            || !await kitPage.locator('#presentationAxisTitle').isVisible()) {
          fail('a multi-identity deck hid its axes when selecting ' + identity);
        }
      }
      await kitContext.close();
    }
  }

  await browser.close();
  if (errors.length) fail('page errors: ' + errors.join(' | '));
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exit(1);
});
