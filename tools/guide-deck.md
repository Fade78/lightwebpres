<!-- lwp:meta -->
page_title: LightWebPres — the guide
page_desc: Create, customize, verify and publish a LightWebPres series.
nav_title: Guide
nav_desc: First article, page anatomy, series, presentation and publication
---

<!-- lwp:slide:cover -->
slug: lightwebpres
kicker: Product manual
slide-layout: hero
# LightWebPres
summary: One Markdown source for reading and presenting. Start with this overview, then use the complete operational manual below.

---

<!-- lwp:slide -->
slug: ce-qu-il-fait
kicker: Output
## Pages that carry their runtime
fact-label: What to publish
source: Guide, chapters 1 and 7

Each article is an HTML file with its CSS and JavaScript inside. The build
also derives a series index and navigation. Publish **public/**, including
referenced images and presentation-package assets, to a static host.

Readers need a browser, not Python or LightWebPres. The source remains plain
text; the manual describes how to operate the tool, not an editorial method.

---

<!-- lwp:slide -->
slug: trois-commandes
kicker: Start
## Two commands to see a working site
fact-label: Demo first, then your own article
source: Guide, chapters 1 and 2

Run `python3 lightwebpres init my-series`, then
`python3 lightwebpres demo my-series --lang en`.
**Demo already builds.** Open `my-series/public/index.html`.

Next, create `sources/first-page.md`, register its filename in `series.json`
and run `build --lang en --open`. The manual supplies the complete source and
JSON, followed by `audit` and `verify`. No extra build belongs before that edit.

---

<!-- lwp:slide -->
slug: anatomie
kicker: Anatomy
## Four slide types, one source file
highlight: 4
highlight-caption: cover, standard, series-nav and full-article
fact-label: Fields first, body after
source: Guide, chapter 3

A cover supplies the title. A standard slide accepts text, images, tables,
notes and optional named components. A series-nav slide generates links;
a full-article slide includes a separate plain Markdown file.

Every slide declares its stable `slug:`. Fields occupy one physical line,
except indented continuations of `note:` and `comment:`. Once free text
starts, later field-looking lines are text too.[^syntax]

[^syntax]: `lightwebpres contract` exposes accepted fields and parseable skeletons. `note:` is public HTML for the speaker panel; `comment:` is source-only. Footnotes such as this one are reader-visible references, not speaker notes.

---

<!-- lwp:slide -->
slug: tags
kicker: Series
## Order articles and inspect their visibility
fact-label: Registration and filtering are separate
source: Guide, chapter 4

The `articles` array in `series.json` fixes the index and navigation order.
Only `page_source` is required per entry. `status` shows resolved metadata;
`series tags` reports effective article and slide visibility without building.

Article tags gate the article, slide tags gate its content. Untagged slides
are shared with non-default selections. **L** opens the reader's tag menu;
`excluded` removes a slide at build time. Tags are not access control.

---

<!-- lwp:slide -->
slug: paquets-presentation
kicker: Layouts
## Select a preset for the series
fact-label: Inner structure, not a replacement runtime
source: Guide, chapter 5

A presentation package supplies layouts, headers, footers, assets and a typed
theme. LWP keeps the page shell, navigation and script. Select it through
`series_meta.presentation_preset`; absence means the built-in `default`.

Keep alternatives at the root of `series.json` with
`presentation_presets`, or pass `--presentation-presets` to `build`, `verify`
or `watch`. The primary stays first; **C** then opens the Appearance picker and
switches the whole deck without changing its sources. The session choice is
scoped to that deck as well as its catalogue.

Use `preset list`, `preset show` and `series preset set` to inspect or change
the choice. `init --preset` can also apply the package's starter.
Per-slide `slide-layout`, `slide-header` and `slide-footer` override defaults.

---

<!-- lwp:slide -->
slug: gestes
kicker: Customization
## Change the smallest layer that does the job
fact-label: Values first, advanced CSS when needed
source: Guide, chapter 5

A theme sets the base. `settings.conf` pins values for the series; `style.*`
metadata changes one page; instance tags change one phrase. The compiler
checks typed property names and values. `custom.css` adds unrestricted rules
after the composed stylesheet.

`resolve` explains a surprising value, including the levels that lost.
`series theme` measures the effective typed colors; it does not certify
arbitrary custom CSS or repair a palette.

---

<!-- lwp:slide -->
slug: themes
kicker: Reading and presenting
## Keep alternatives within reach
fact-label: The same page, a different viewing choice
source: Guide, chapters 5 and 8

**C** opens the theme picker. Monochrome, Monochrome Night and Print Ink ship
by default; `--no-essential-theme` opts out. Select Print Ink before printing
when you want black on white: printing keeps the active theme.

**M** opens the presenter menu, **F** requests fullscreen, **H** lists the
controls and **S** shares a link or QR code. A projected screen also shows an
open speaker panel: **N** is not a private presenter window.

---

<!-- lwp:slide -->
slug: pipeline
kicker: Automation
## One engine at the terminal or in a browser
fact-label: Build, inspect, maintain
source: Guide, chapters 6, 9 and 10

The CLI runs unattended with Python's standard library. `watch` rebuilds on
edits; `--only` targets an article when the navigation cache is safe. Language
packs separate interface strings from build-time typography.

The browser builder runs the same executable under Pyodide: upload a series
zip, or pull/build/push with GitLab. Serve the builder over HTTP(S).
Sanitize untrusted input upstream: raw HTML is passed through by the engine.

---

<!-- lwp:slide -->
slug: verifications
kicker: Publication
## Two checks answer different questions
fact-label: Match the check to the question
source: Guide, chapter 7

`audit` renders in memory and reports source and style warnings without
writing output. Plain audit exits zero; `--strict` turns warnings into a
gate. `verify` compares a fresh in-memory render with the files on disk and
fails on drift. Use the same supported rendering options as the build.

**Inspect the rendered page before publishing.** Verify cannot reproduce
`--inline-images`. Removing an article does not delete an old hosted file;
review `clean` locally and the host's stale files separately.

---

<!-- lwp:slide:series-nav -->
slug: la-serie

---

<!-- lwp:slide:full-article -->
slug: guide-complet
article: guide_article.md
