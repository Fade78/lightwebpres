# First Article Example

This is the personal article from GUIDE.md, with a Nebula theme selection.
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

The output is `generated/product-responsive.png`, a 1280 by 760 comparison
image containing the same content slide at 960 by 540 CSS pixels in landscape
and 390 by 844 CSS pixels in portrait, with touch/mobile emulation. Both views
use the same HTML and Nebula theme at device scale factor 1. The montage adds
labels and a neutral canvas around the real captures; it does not replace
content or override presentation CSS. The script checks browser errors,
horizontal overflow and text bounds before capturing. Inspect the image after
regeneration too.

`generated/product-captures.json` records hashes of the inputs and the
composite PNG, its two viewport settings and Chromium version. `--check` and
the Python tests catch stale inputs or changed PNGs without comparing
screenshots across browser versions. Pixel identity across operating systems
and fonts is not promised. Regenerate the guide after captures: it publishes a
copy of the composite image.
