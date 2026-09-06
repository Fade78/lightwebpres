# First Article Example

This is the personal article from GUIDE.md, with an Evergreen theme selection.
The capture script copies it into a temporary directory and builds it with
the repository's executable. It never builds over these tracked sources.

From the repository root, with an existing Playwright and Chromium:

```bash
node tools/screenshot-product.cjs
node tools/screenshot-product.cjs --check
python3 tools/build_guide.py
```

If Playwright is installed globally but not found by Node, use
`NODE_PATH="$(npm root -g)" node tools/screenshot-product.cjs`.
Chromium's normal Playwright cache is the default; `PW_CHROMIUM_PATH` can
select an existing executable. `PYTHON` can select Python instead of `python3`.
Nothing is downloaded or installed by this script.

Outputs are `generated/product-landscape.png` (960 by 540 CSS pixels) and
`generated/product-mobile.png` (390 by 844 CSS pixels, touch/mobile emulation).
Both show the same content slide in the same HTML and theme, at device scale
factor 1. No device frame, content replacement or presentation CSS override
is applied. The script checks browser errors, horizontal overflow and text
bounds before capturing. Inspect the images after regeneration too.

`generated/product-captures.json` records hashes of the inputs and PNGs,
viewport settings and Chromium version. `--check` and the Python tests catch
stale inputs or changed PNGs without comparing screenshots across browser
versions. Pixel identity across operating systems and fonts is not promised.
Regenerate the guide after captures: it publishes copies of both images.
