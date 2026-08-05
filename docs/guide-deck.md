<!-- lwp:meta -->
page_title: LightWebPres — the guide
page_desc: The guide to LightWebPres, built with LightWebPres.
nav_title: Guide
nav_desc: Install, anatomy of a page, series, look, shipping
---

<!-- lwp:slide:cover -->
tag: Guide
# LightWebPres
summary: Markdown in, self-contained HTML out. This deck is the short version; the article below it is the guide itself, and both were built by the tool they describe.

---

<!-- lwp:slide -->
tag: Scope
## What it does, and what it leaves to you

fact-label: The line

LightWebPres renders. It does **not** teach writing — it is for people who already know how, and it takes whatever you put in it.

A second skill, `sourced-presentation`, ships alongside as a courtesy for anyone who would like a method. It is an offered interface, not the core of this.

---

<!-- lwp:slide -->
tag: Install
## Three commands to a built site

fact-label: The whole loop
source: Guide, section 2

`install` scaffolds, `demo` fills it with something real to look at, `build` writes `public/`. Every page is a single self-contained file — no server, no runtime dependency, nothing to load.

Language is chosen **per build**, never stored: pass `--lang en` or you get French.

---

<!-- lwp:slide -->
tag: Anatomy
## A page is slides, a slide has components

highlight: 4
highlight-caption: slide types — cover, standard, series-nav, full-article

fact-label: What is in a standard slide

A fact box, a key figure, a source line, a comparison table, a figure. Each is reached by a named field or by ordinary Markdown; none of them needs CSS.

The switch from fields to free text is **one-way within a slide**: once a line is not a `field:` line, everything after it is prose.

A note[^note] is reached the standard way, and its number is a position rather than the label you wrote. Notes are not a full-article feature: this is a standard card, and the note below is on it.

[^note]: `[^label]` calls it, `[^label]: text` defines it. `notes-placement: local` — the default — lands the body at the foot of the unit that called it, which is why this one is here rather than at the end of the page. Set `notes-placement: page` to gather every note of an article into one section instead, and `notes-tooltip: on` to put the text in the call's tooltip as well. Both cascade: built-in default, then `series_meta`, then the article's own meta block.

---

<!-- lwp:slide -->
tag: Look
## Four gestures, smallest first

fact-label: Pick the smallest one that does the job

A **theme** repaints the series from one word. An **instance tag** changes one phrase. A `style.` line in a page's meta block changes that page. `settings.conf` changes the series, and `custom.css` adds rules rather than values.

The stylesheet is composed in memory at every build, so nothing the tool writes can collide with anything you wrote.

---

<!-- lwp:slide -->
tag: Look
## Thirty-three themes, found by facet

highlight: 33
highlight-caption: themes, filtered by polarity, intensity and hue

fact-label: Why facets rather than a list

Thirty-three names tell you nothing. Light or dark, loud or sober, and what hue the page carries will get you to a shortlist of three.

`themes-gallery` renders every one of them against real slide content.

---

<!-- lwp:slide -->
tag: Automation
## A step in a content pipeline

highlight: 11
highlight-caption: standard-library modules, and nothing else to install

fact-label: What makes it pipeline-shaped

Every command runs unattended and returns a meaningful exit code. `check` fails on drift, `audit` never fails because it is advice. Every path is an environment variable, so a runner lays the pieces out as it likes.

The Markdown can come from anywhere — a CMS export, a database, a generator, an agent upstream. LightWebPres is the step that turns it into publishable pages.

---

<!-- lwp:slide -->
tag: Shipping
## Two checks, two different moments

fact-label: A nudge and a gate

`audit` flags what is worth a second look and **never fails** — a missing cover, a stale scaffold comment, a retired variable still referenced.

`check` rebuilds in memory and diffs against `public/`, exiting non-zero on any difference. That exit code is what makes it a CI gate.

---

<!-- lwp:slide:series-nav -->

---

<!-- lwp:slide:full-article -->
article: guide_article.md
