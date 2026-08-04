// Shared console-error collector for the Playwright drivers.
//
// Every driver treats "any console error" as a failure, which is the
// right rule — a generated page that logs an error has a defect. But
// Chromium requests /favicon.ico on its own for any page that declares
// no icon, and logs the resulting 404 as a console error. The page never
// asked for it: nothing in a generated article references a favicon, and
// the same 404 appears against any static host. Counting it as a page
// defect makes every driver fail on a browser build that asks for it,
// which is exactly what happened.
//
// So this filters that one request, by URL, and nothing else. Any other
// console error still fails the run.

function collectConsoleErrors(page, sink) {
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const loc = msg.location();
    const url = (loc && loc.url) || '';
    if (/\/favicon\.ico(\?|$)/.test(url)) return;
    sink.push(msg.text());
  });
}

module.exports = { collectConsoleErrors };
