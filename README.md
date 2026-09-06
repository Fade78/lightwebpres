<p align="center">
  <img src="web/lwp_banner.svg" alt="LightWebPres: Markdown in, publish-ready pages out" width="100%">
</p>

# LightWebPres

**Write one Markdown source. Read it on a phone, present it in landscape,
publish it as a static site.**

LightWebPres is a single-file Python tool that builds scrollable HTML
articles with slide navigation, optional long-form text and a series index.
Each article carries its CSS and JavaScript: readers need a browser, not
LightWebPres, a viewer account or a presentation service.

## One page, two uses

The same content card and `evergreen` theme, rendered by LightWebPres in
Chromium. The text and layout below are actual output, not a design mockup.

**Landscape presentation, 960 × 540 CSS pixels**

![Evergreen content card in landscape: The runtime travels with the page; one HTML file per article, with CSS and JavaScript inside, plus an instruction to keep local image assets](generated/product-landscape.png)

**Emulated mobile viewport, 390 × 844 CSS pixels**

<img src="generated/product-mobile.png" alt="The identical card in a narrow portrait viewport: the title, one HTML highlight and asset reminder reflow vertically" width="390">

These are browser viewport captures, not photographs of physical devices.
The [source example](examples/first-article/sources/first-page.md) is tracked
and the [capture script](tools/screenshot-product.cjs) rebuilds it before
taking either image.

In portrait, scroll and swipe through the page. In landscape, use keyboard
or mouse navigation. Press **F** for fullscreen and **H** for help; rotating
the screen alone does not request fullscreen. Long content remains readable
by scrolling rather than being cut to fit a slide.

## Quickstart

Download a source archive from the
[GitHub releases](https://github.com/Fade78/lightwebpres/releases) and extract
the `lightwebpres` file. You need **Python 3.8+**, with no extra packages.
The archive also includes the browser builder, documentation, examples and
contributor tools; the single executable is enough for CLI use. Read the
documentation shipped with your chosen release: this checkout can describe
features not yet published in a release.

From the directory containing `lightwebpres`:

```bash
python3 lightwebpres init my-series
python3 lightwebpres demo my-series --lang en
```

Open **`my-series/public/index.html`** in your browser. `demo` creates three
example articles **and builds them**, so no extra `build` command is needed.
It refuses to overwrite existing work. No web server is required to view
the generated files locally.

On Windows, use `python lightwebpres` or `py lightwebpres` instead of
`python3 lightwebpres`. On Unix, invoking through Python avoids executable
permission issues; `chmod +x lightwebpres` also enables `./lightwebpres`.

**Next: [make your first personal article](GUIDE.md#2-make-your-first-personal-article).**
The guide gives you a complete source file, the exact `series.json` entry,
and the build/open/verify loop, while keeping the demo available as a reference.

## What you get

- **Portable pages.** One HTML file per article, with an embedded runtime and
  theme picker. Referenced local images remain files under `img/`; publish
  the whole output directory. `--inline-images` can embed Markdown images
  when a single-file delivery matters.
- **A small content model.** Series → articles → slides. Four slide types
  cover titles, content cards, cross-article navigation and long-form text.
  Plain Markdown sources can be edited by a person, an agent or a pipeline.
- **Series navigation without an application server.** `series.json` orders
  the articles; the build derives the index and cross-article links. Tags
  provide selectable variants within the same published pages.
- **Presentation controls included.** Keyboard, mouse and touch navigation,
  fullscreen, pause screens, slide counter, theme switching and speaker
  notes. Browser printing produces a slide-based handout or PDF.
- **Stable sharing.** Copy a link or show a locally generated QR code for the
  series, article or current slide. Explicit slide slugs keep links stable
  when titles or order change. QR codes need a reachable HTTP(S) page.
- **Customization with checked values.** Choose a theme or presentation
  preset, pin typed properties in `settings.conf`, and add advanced rules in
  `custom.css`. Invalid property names and values are build errors.
- **Automatic typography.** French and English packs upgrade existing spaces
  around punctuation, numbers and units to non-breaking spaces. Rules can
  be extended or disabled, independently of interface translation.
- **Checks for publishing.** `audit` reports source and rendered-style
  warnings; `audit --strict` makes them a CI gate. `verify` detects output
  drift. `watch` rebuilds on edits and can serve a local preview.
- **A browser builder too.** Build a series zip or pull/build/push a GitLab
  repository in a browser tab, using the same Python executable under
  Pyodide rather than a reimplementation.

## Choose a look

These existing previews show three real `640 × 360` landscape covers:
`lava`, `terminal` and `pop-lemon`.

![Three real landscape covers in the Lava, Terminal and Pop Lemon themes](generated/themes-featured.png)

Browse the [compact theme catalogue](generated/themes-gallery.png), or open
the [interactive HTML gallery](generated/themes-gallery.html) in a browser.
It shows a cover, a content card with a note, page-wide notes and long-form
text for each theme, with family, polarity and hue filters.

To change the quickstart series:

```bash
python3 lightwebpres series theme set my-series --theme evergreen
python3 lightwebpres build my-series --lang en
```

The command changes the theme selection, not your pinned property values.
The default runtime alternatives include Monochrome, Monochrome Night and
Print Ink. Readers can choose them with **C** without rebuilding; use
`--no-essential-theme` if you do not want that default bundle.

A theme's contrast report is a measurement, not an accessibility certification.
`theme show` reports the catalogue theme; `series theme` measures the effective
typed values after your pins. Advanced `custom.css` is outside that measurement.

For layouts, headers, footers and package assets, see
[presets and customization](GUIDE.md#5-choose-presets-themes-and-customization).
You do not need to design a package to use the built-in rendering.

## Find your route

The [GUIDE](GUIDE.md) is the operational product manual. This README is the
entry point, not a second command reference.

| I want to… | Go to |
|---|---|
| Understand the generated project | [Start with a working site](GUIDE.md#1-start-with-a-working-site) |
| Replace the demo with my content | [First personal article](GUIDE.md#2-make-your-first-personal-article) |
| Use slide fields, images and notes | [Page anatomy](GUIDE.md#3-understand-page-anatomy) |
| Order articles or select variants | [Series and tags](GUIDE.md#4-organize-a-series-and-tags) |
| Select layouts or change the appearance | [Presets, themes and customization](GUIDE.md#5-choose-presets-themes-and-customization) |
| Set interface language and spacing rules | [Languages and typography](GUIDE.md#6-set-languages-and-typography) |
| Check output and put it online | [Verify and publish](GUIDE.md#7-verify-and-publish) |
| Use fullscreen, PDF or QR sharing | [Present, print and share](GUIDE.md#8-present-print-and-share) |
| Build without a terminal | [Browser builder](GUIDE.md#9-build-in-the-browser) |
| Set up CI, watch or upgrade a series | [Automation and maintenance](GUIDE.md#10-automate-and-maintain) |
| Diagnose unexpected output | [Troubleshooting and references](GUIDE.md#11-troubleshooting-and-references) |

The guide is also [built as a LightWebPres article](generated/guide/guide.html).
Open the HTML in a browser to use its deck and full manual together.

## Browser or terminal

The CLI works offline with Python's standard library. Every command runs
unattended and returns an exit code. `python3 lightwebpres --help` lists the
commands, options and environment variables; command-specific help narrows
the reference, for example `python3 lightwebpres build --help`.

The browser builder lives in [`web/`](web/). Serve it over HTTP(S); unlike
generated articles, it cannot run from `file://`. It needs its vendored
Pyodide files and a copy of the executable in one of its supported locations.
The [browser chapter](GUIDE.md#9-build-in-the-browser) gives the local server
command and deployment layout.

Zip builds stay in the tab. GitLab sync talks directly to the configured
instance and only creates or updates files; it does not delete stale output.
The browser builder is distinct from the separate `lightwebpres-gui` editor.

## Safety

**LightWebPres is a renderer for trusted sources, not an HTML sanitizer.**
Raw HTML, including scripts, passes through. Sanitize untrusted CMS exports,
third-party translations or generated content upstream before building.
Filename validation and HTML tag-balance checks do not replace that boundary.

**Speaker notes are not private.** The `note:` field is embedded in the HTML,
and its panel opens in the same page that a projector or screen share shows.
Use `comment:` for source-only review notes; those are not published.
Tags are viewing filters, not access control.

Before publishing, inspect the output and use matching build/verify options.
`verify` cannot reproduce `--inline-images`; keep a separate non-inline
output if you need that CI gate. Removing an article or asset from the
sources does not itself delete an old published file. Review `clean` and
the host's stale files as described in [Verify and publish](GUIDE.md#7-verify-and-publish).

## Reference

| Document | Purpose |
|---|---|
| [GUIDE.md](GUIDE.md) | Operational manual in task order |
| [Format skill](agent/skills/lightwebpres/SKILL.md) | Exact article grammar, for people and agents |
| [GLOSSARY.md](GLOSSARY.md) | Field meanings, defaults and fallback chains |
| [specifications.md](specifications.md) | Normative format and behavior reference, in French |
| [CHANGELOG.md](CHANGELOG.md) | Version changes and release text |
| [DECISIONS.md](DECISIONS.md) | Decisions, rationale and outstanding work |

An optional guest [sourced-presentation method](agent/skills/sourced-presentation/SKILL.md)
ships alongside the format skill for people who want an editorial method.
It is independent of LightWebPres and is not required to use the tool.
The [skill index](agent/skills/README.md) distinguishes their roles.

## Contribute

Read [AGENTS.md](AGENTS.md) before changing this repository. The engine is
the single `lightwebpres` file; `tests/` holds CLI, internal-contract and
real-browser regression tests. Development and public releases use different
forges, as explained in the contributor rules.

Run the suite before and after a change:

```bash
python3 tests/run_tests.py
python3 -m py_compile lightwebpres
python3 tools/check_refs.py
```

Browser tests use Playwright and Chromium and skip when unavailable.
No browser tooling is needed to use the Python CLI.

`examples/` holds tracked inputs, including presentation packages and the
first-article example. `tools/` holds maintenance scripts and the guide deck.
`generated/` holds rebuildable output: edit its sources, never its files by
hand. The guide is regenerated with `python3 tools/build_guide.py`.
For product images, use `node tools/screenshot-product.cjs` with an installed
Playwright and Chromium; the [example instructions](examples/first-article/README.md)
document resolution and freshness checks. Existing gallery captures have
their own commands in AGENTS.md.

## License

The program is **GNU GPL v3 or later**, with the **LightWebPres Output
Exception**. The legal texts are [COPYING](COPYING) and
[COPYING.EXCEPTION](COPYING.EXCEPTION).

Your generated presentations may be distributed under the terms you choose,
commercially or not. The exception covers the tool's code copied into normal
output; it does not extend to a generator using that output as templates.

The executable remains copyleft. `init` copies it into the series with its
licence files: distributing that repository also distributes GPL software,
not just presentation output. Keep those notices with it.

Third-party code is listed in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
Vendored Pyodide uses MPL 2.0; see [web/vendor/NOTICE.md](web/vendor/NOTICE.md).
The licences cover code, not the LightWebPres name: fork the project, but do
not present a modified version as this project.
