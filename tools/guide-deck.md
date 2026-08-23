<!-- lwp:meta -->
page_title: LightWebPres — the guide
page_desc: The guide to LightWebPres, built with LightWebPres.
nav_title: Guide
nav_desc: Setup, anatomy of a page, series, look, shipping
---

<!-- lwp:slide:cover -->
slug: lightwebpres
kicker: Guide
# LightWebPres
summary: Markdown in, self-contained HTML out. This deck is the short version; the article below it is the guide itself, and both were built by the tool they describe.

---

<!-- lwp:slide -->
slug: ce-qu-il-fait
kicker: Scope
## What it does, and what it leaves to you

fact-label: The line

LightWebPres renders. It does **not** teach writing — it is for people who already know how, and it takes whatever you put in it.

A second skill, `sourced-presentation`, ships alongside as a courtesy for anyone who would like a method. It is an offered interface, not the core of this.

---

<!-- lwp:slide -->
slug: trois-commandes
kicker: Setup
## Three commands to a built site

fact-label: The whole loop
source: Guide, section 2

`init` scaffolds, `demo` fills it with something real to look at, `build` writes `public/`. Every page is a single self-contained file — no server, no external runtime dependency, nothing to load. `build --themes` can optionally embed a theme picker without changing that standalone property; the same selection can live in the root `series.json` `themes` list.

`--lang en` chooses the build-wide fallback. For one article to carry several
languages, `tags:` selects a variant and `series_meta.lang_tags` can select a
typography pack per slide.

---

<!-- lwp:slide -->
slug: anatomie
kicker: Anatomy
## A page is slides, a slide has components

highlight: 4
highlight-caption: slide types — cover, standard, series-nav, full-article

fact-label: What is in a standard slide

A fact box, a key figure, a source line, a comparison table, a figure. Each is reached by a named field or by ordinary Markdown; none of them needs CSS.

The switch from fields to free text is **one-way within a slide**: once a line is not a `field:` line, everything after it is prose.

A note[^note] is reached the standard way, and its number is a position rather than the label you wrote. Notes are not a full-article feature: this is a standard card, and the note below is on it.

[^note]: `[^label]` calls it, `[^label]: text` defines it. `notes_placement: local` — the default — lands the body at the foot of the unit that called it, which is why this one is here rather than at the end of the page. Set `notes_placement: page` to gather every note of an article into one section instead, and `notes_tooltip: on` to put the text in the call's tooltip as well. Both cascade: built-in default, then `series_meta`, then the article's own meta block. A label is word characters only — letters, digits, `_`, accents included, no `-`, no space, no punctuation; anything else is neither a note nor an error, and `audit` is the only thing that says so.

---

<!-- lwp:slide -->
slug: variantes
kicker: Variants
## Several versions, one HTML page

fact-label: The variant axis

`tags: fr` and `tags: en` put adjacent language versions in one source file.
A slide without tags is `default`, shared by every selection; `excluded` is
removed at build time. Press **L** to select a tag without reloading. The
choice is stored in `localStorage['lwp-active-tag']`, and counts/navigation
follow the visible subset.

Declare `series_meta.lang_tags: {"fr": "fr", "en": "en"}` when typography
must follow the selected language. The first mapped tag on a slide wins; the
build's `--lang` remains the fallback.

---

<!-- lwp:slide -->
slug: gestes
kicker: Look
## Four value overrides, then CSS rules

fact-label: Pick the smallest one that does the job

A **theme** repaints the series from one word. An **instance tag** changes one phrase. A `style.` line in a page's meta block changes that page. `settings.conf` changes the series, and `custom.css` adds rules rather than values.

The stylesheet is composed in memory at every build, so nothing the tool writes can collide with anything you wrote.

---

<!-- lwp:slide -->
slug: themes
kicker: Look
## Themes, found by facet

highlight: 3
highlight-caption: facets — family, polarity, hue — narrowing a catalogue too long to read

fact-label: Why facets rather than a list

A list of names tells you nothing. What the theme is for, light or dark, and what hue the page carries will get you to a shortlist of three.

`theme gallery` renders every one of them against real slide content.

`build --themes print-ink,print-grey` embeds a searchable picker: **C** opens
it, and **M** opens the global presenter menu. The same list can be written as
`"themes": ["essential", "family:terrain", "bgh:red"]` at the root of
`series.json`; `essential` means Monochrome, Monochrome Night and Print Ink.
The effective theme from `templates/settings.conf` is always the first choice,
and an explicit CLI value overrides the JSON list. Author pins remain in force
while the reader switches.

Every build embeds that `essential` bundle by default — Monochrome, Monochrome
Night and Print Ink — so **C** works on any page without the author opting in.
Accessibility: Monochrome is high-contrast ink with no hue, Monochrome Night is
the same on a dark ground, Print Ink is pure black on white. Print: Print Ink is
drawn for paper, so a PDF handout at `Ctrl`/`Cmd`+`P` is clean without a theme
choice. Sobriety: none of the three carries a hue, so the set never clashes
with a series built around one. `--no-essential-theme` (build/verify/watch) opts
out; the page then carries no runtime picker unless `--themes` or
`series.json["themes"]` adds one.

---

<!-- lwp:slide -->
slug: pipeline
kicker: Automation
## A step in a content pipeline

highlight: 0
highlight-caption: dependencies to install — the Python standard library is all it uses

fact-label: What makes it pipeline-shaped

Every command runs unattended and returns a meaningful exit code. `verify` fails on drift and `audit --strict` fails on anything worth reporting — two gates, two questions. Plain `audit` never fails, whatever it finds. Every path is an environment variable, so a runner lays the pieces out as it likes.

The Markdown can come from anywhere — a CMS export, a database, a generator, an agent upstream. LightWebPres is the step that turns it into publishable pages.

---

<!-- lwp:slide -->
slug: verifications
kicker: Shipping
## Two checks, two different moments

fact-label: A nudge and a gate

`audit` flags what is worth a second look and **normally does not fail** — a missing cover, a stale scaffold comment, a retired variable still referenced, a composed stylesheet whose navigation control or body text has gone invisible. It also **renders the whole series in memory**, throws the HTML away, and keeps what composing it had to say — including that the series does not build at all. Nothing is left out: drafts and `ignored` articles are looked at too, because work in progress is what an authoring tool is for. Pass `--strict` when those warnings must fail CI.

`verify` rebuilds in memory and diffs against `public/`, exiting non-zero on any difference. That exit code is what makes it a CI gate.

---

<!-- lwp:slide:series-nav -->
slug: la-serie

---

<!-- lwp:slide:full-article -->
slug: guide-complet
article: guide_article.md
