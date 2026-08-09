#!/usr/bin/env python3
"""Regenerates theme gallery.png, the still that README.md embeds.

Two things this has to get right, and both were found the hard way.

The gallery's iframes carry `loading="lazy"`, so a plain full-page
screenshot captures BLANK panels for every row below the fold: the frames
never enter the viewport, and Playwright's full-page mode re-lays-out the
page rather than scrolling it. They are switched to eager and their
srcdoc reassigned to force a load before anything is captured.

And the board is ~32 000 px tall at 33 themes. A still of the whole thing
is a 1.7 MB image nobody reads. What a reader needs from a README is what
a ROW looks like, so this captures the masthead and the first few rows and
points at the live file for the rest.

Usage: python3 tools/gallery_screenshot.py [rows]
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
GALLERY = ROOT / 'theme gallery.html'
OUT = ROOT / 'theme gallery.png'
WIDTH = 1520


def main(rows=4):
    if not GALLERY.exists():
        sys.exit(f'{GALLERY} not found — run `lightwebpres theme gallery` first')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        page = browser.new_page(viewport={'width': WIDTH, 'height': 1200})
        page.goto(GALLERY.as_uri())
        page.evaluate("""() => {
            document.querySelectorAll('iframe').forEach(f => {
                f.loading = 'eager';
                f.srcdoc = f.srcdoc;   // reassigning is what forces the load
            });
        }""")
        page.wait_for_timeout(4000)
        height = page.evaluate(
            """(n) => {
                const rows = [...document.querySelectorAll('.theme-row')];
                const last = rows[Math.min(n, rows.length) - 1];
                return Math.ceil(last.getBoundingClientRect().bottom + window.scrollY + 24);
            }""", rows)
        page.set_viewport_size({'width': WIDTH, 'height': min(height, 30000)})
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT), clip={'x': 0, 'y': 0, 'width': WIDTH,
                                             'height': height})
        browser.close()
    print(f'Wrote {OUT} ({rows} rows, {WIDTH}x{height})')


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
