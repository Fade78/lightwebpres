# LightWebPres — Guide

This is the walkthrough: install it, build your first site, make it look
the way you want, write your own content, and ship it. For what each
command *exactly* does in every edge case, see `specifications.md`; for
the precise LWP article format, see `SKILL.md`. This guide is the path
through all of it in the order you'll actually need it.

## 1. What LightWebPres is

LightWebPres turns an extended Markdown format into self-contained,
scrollable HTML "slide deck" articles — a cover, a handful of fact-card
slides, an optional long-form piece, cross-article navigation — with zero
runtime dependencies. One executable, `lightwebpres`, does the whole job:
scaffold a project, generate demo content, build, verify, and keep
templates current.

**This guide is written for a person working from a terminal — but you
don't have to be the one typing every command.** LightWebPres ships a
packaged skill (`SKILL.md`, in `agent/skills/lightwebpres/`) that teaches
an LLM/agent the article format directly, and every command in this guide
runs unattended — nothing here ever blocks on an interactive prompt. So
if you'd rather describe what you want and have an agent write the
Markdown and run the build, that works from minute one: point your agent
at `SKILL.md` and skip to [section 4](#4-writing-your-own-articles). If
you're doing this yourself, keep reading from the top. A second skill,
`sourced-presentation`, ships alongside it — a method for one kind of
content rather than a rule about the format, described in
[section 9](#9-going-further); take it or leave it.

## 2. Install & your first build

```bash
./lightwebpres install my-series
./lightwebpres demo my-series
./lightwebpres build my-series
open my-series/public/index.html
```

`install` scaffolds a working project — `articles/` (empty, for your
`.md` files), `templates/` (your customization surface: `settings.conf`,
`custom.css`, `nav.js` — see section 3), `language/` (both
the French and English packs — typography rules + interface strings), a
starter `series.json` (series-wide metadata, empty article list), and a
copy of the `lightwebpres` executable itself, so the project directory is
self-sufficient. Language is chosen **per build**, not stored in the
project (both packs are always installed): pass `--lang fr|en` to
`build`/`demo` (or set `LWP_LANG`), French by default. At install time,
`--lang` only sets the language baked into the generated
`.gitlab-ci.yml` build command — so `--gitlab-ci --lang en` produces a
pipeline that builds in English. `--force` lets you install into a
non-empty directory; `--gitlab-ci` also writes that `.gitlab-ci.yml`
(opt-in — `install` never assumes a GitLab deployment on its own, see
section 7).

`demo` only works after `install` and refuses to overwrite existing
work — both its own example files and a `series.json` that already lists
articles. It drops three example articles (first, middle, last position
in the series navigation) plus a captioned demo image, exercising every
slide type and field, so you have something real to look at and copy
from before writing your own.

`build` reads `series.json` and every article it lists, and writes
`public/*.html` plus a `public/index.html` and a generated `README.md`
listing the series (title, intro, and a link per article, from
`series.json`'s `series_meta`). Open `public/index.html` in a browser —
no server needed, every page is a single self-contained file.

## 3. Choosing a look

Thirty-three named color themes ship pre-configured — too many to pick
from a list, so you find one by facet: light or dark background, how loud
it is, and what hue the page itself carries.

```bash
./lightwebpres themes                              # all 33, with their facets
./lightwebpres themes --polarity dark --intensity sober  # just the ones you mean
```

Apply one at install time, or change your mind later:

```bash
./lightwebpres install my-series --theme evergreen
./lightwebpres set-theme my-series --theme crimson
```

A theme is just a word in a data file: `set-theme` rewrites the one
`theme:` line of `templates/settings.conf` and nothing else. No CSS is
touched — the stylesheet is composed in memory at every build. What it
prints (real output):

```
Theme changed: evergreen -> crimson
  my-series/templates/settings.conf
  Your uncommented values are untouched and still apply on top.
  (Commented values still show the previous theme; audit notes it.)

Run build again to apply the new theme.
```

Asking for the theme already in place writes nothing and says so
(`Theme unchanged`). `set-theme` has no `--force` anymore: nothing the
tool writes can collide with anything you wrote.

Preview every theme, rendered against real slide content and filterable
by those same facets, with:

```bash
./lightwebpres themes-gallery
open themes-gallery.html
```

**Beyond the presets: typed properties.** Every visual decision is a
typed property, `component.axis: value`, and `templates/settings.conf`
lists **all** of them, commented out, at the values of the theme you
chose — the complete surface is under your eyes, no documentation
needed. Uncomment a line to **pin** it: it survives every theme change
and every executable upgrade, because `lightwebpres` never rewrites your
file. For example, to paint the slide tags in the theme's
attention-calling color, change:

```
# tag.fg: ink-quiet
```

to:

```
tag.fg: call
```

and rebuild. A bare word like `call` is looked up among the theme's
shared values (`color.call` here, since `fg` is a color axis); a literal
like `#8A4B00` works anywhere a color does. A mistyped key or value is a
**named build error** pointing at the file and key — never a silent
no-op. This pinned `tag.fg` keeps applying after a `set-theme`, on top of
the new palette (that's what "still apply on top" means above; `audit`
reminds you the scaffold's *comments* now show stale values;
`refresh-templates --scaffold` realigns them to the current theme while
keeping every pinned line).

**Rules, as opposed to values, go in `templates/custom.css`** — full
CSS, no subset, appended after the composed stylesheet so your rules win
ties. New selectors, media queries, `@font-face` (name the family at the
head of a stack in `settings.conf`, declare the face here). The composed
sheet's `--component-axis` variables are usable in it
(`border-color: var(--color-mark)`), and that's the recommended way to
follow the theme. `templates/nav.js` still overrides the navigation
behavior wholesale; the page/index HTML structure itself is fixed, not a
template.

> **If your series predates the typed-properties engine**, its
> `templates/style.css` is **no longer read** — values belong in
> `settings.conf`, rules in `custom.css`, and no variable aliases were
> kept. Run `lightwebpres audit my-series`: it names every retired
> variable still referenced (in the legacy file or in your
> `custom.css`), each with its replacement — e.g. `--yellow` and
> `--marker` both became `--color-mark`. `refresh-templates` (section 7)
> creates the missing `settings.conf`/`custom.css` for such a series;
> moving your values into them is yours to do, then delete `style.css`.

## 4. Writing your own articles

Each article is one `.md` file: a metadata block, then a sequence of
"slides" separated by `---`.

```markdown
<!-- lwp:meta -->
page_title: The apple pie
nav_title: The apple pie
nav_desc: Pastry, baking, and plating
---

<!-- lwp:slide:cover -->
tag: Recipe
# The apple pie
summary: Nine things that make or break a homemade apple pie.

---

<!-- lwp:slide:full-article -->
article: apple-pie_article.md
```

That's enough to get the shape of it, but the exact rules — the four
slide types and their fields, the one-way switch from structured fields
to free Markdown text within a slide, the automatic non-breaking-space
typography and how to turn it off per article, `series.json` wiring — are
`SKILL.md`'s job, not this guide's: it's written precisely so an agent
(or you) can follow it without guessing, and duplicating it here would
just give the two a chance to drift apart. Read `SKILL.md` directly, or
point an agent at it.

Register every article that should appear in navigation in
`series.json` — see the next section.

## 5. Organizing a series

`series.json` lists the articles and holds series-wide metadata:

```json
{
  "series_meta": {
    "title": "My article series",
    "subtitle": "Series subtitle",
    "intro": "Series introduction."
  },
  "articles": [
    {"page_source": "apple-pie.md"}
  ]
}
```

`page_source` — a bare filename, no path — is the only field ever
required directly here. Each article is self-described: `page_dest` (the
output HTML name), `page_title`/`page_desc`,
`card_title`/`card_desc`/`card_label`, `nav_title`/`nav_desc`, and the
editorial fields (`author`/`license`/`date`, defaulting series-wide from
`series_meta`) all resolve from the article's own meta block and cover
slide, and any of them can be overridden per entry here when you want
`series.json` to have the final say. `draft: true` keeps an article out
of the build until it's ready (`--include-drafts` previews it, with a
banner). The array order is the navigation and index order. The full
fallback chain for each field is covered in `GLOSSARY.md`.

## 6. Verifying before you ship

Two different checks, for two different moments:

```bash
lightwebpres audit my-series   # editorial warnings, never blocks
lightwebpres check my-series   # rebuilds in memory, diffs against public/
```

`audit` flags things worth a second look — no cover slide, a
`settings.conf` scaffold whose comments predate your current theme, a
retired CSS variable still referenced in `custom.css`, that kind of
thing — but never fails; it's a nudge, not a gate. `check` is the
opposite: it rebuilds every article in memory and compares it byte-for-
byte against what's already in `public/`, exiting non-zero the moment
anything differs. That non-zero exit is what makes it a real CI gate —
wire it into a pipeline step before `build` to catch a `public/` that
was hand-edited or never rebuilt after a source change.

## 7. Keeping templates current

`lightwebpres` is a single file you copy into each project (`install`
does this automatically). When you drop in a newer copy, the built-in
CSS/JS baked into your project's `templates/` doesn't update on its
own — run:

```bash
lightwebpres refresh-templates my-series
```

There is less to refresh than there used to be: the stylesheet is
composed in memory from the current executable at every build, so it is
always fresh by construction, and your `settings.conf`/`custom.css` are
yours — never touched. The one tool-owned file on disk is `nav.js`:
`refresh-templates` replaces it if it differs from the built-in version
(saving the old one as `templates/nav.js.bak` in case you'd customized
it) and reports `already up to date` otherwise. On a series installed
before the typed-properties engine, it also creates the missing author
surface — a default `settings.conf` scaffold and an empty `custom.css` —
and warns if a legacy `templates/style.css` is still around: that file
is no longer read and is never migrated automatically (its values are
your decisions); `audit` names each retired variable with its
replacement to make the move mechanical. Your theme choice needs no
reapplying — it's the `theme:` line of `settings.conf`, which an upgrade
cannot revert.

## 8. Beyond the CLI

`web/index.html`, one page with two tabs, runs the exact same engine as
the CLI — unmodified — inside Pyodide (CPython compiled to WebAssembly),
so the output is identical either way:

- **Upload a zip** — drop a zip of your series, get back a zip of
  `public/`. Nothing leaves the browser tab.
- **Sync with GitLab** — pull a series straight from a GitLab repository,
  build it, and push the result back as a single commit.

Both tabs share one Pyodide load at page start, so switching between them
is instant. The page needs to be **served over http(s)**, not opened as a
`file://` page — browsers block Pyodide's asset loading under that
origin. For local testing:

```bash
python3 -m http.server 8000 --directory /path/to/lightwebpres
# then open http://localhost:8000/web/index.html
```

For unattended builds, `install --gitlab-ci` also writes a `.gitlab-ci.yml`
that runs `lightwebpres build .` on every push and publishes `public/` as
an artifact — opt-in, not written by a plain `install` — add a `check`
step before it if you want drift caught before it merges (see section 6).

## 9. Going further

- **`SKILL.md`** (`agent/skills/lightwebpres/`) — the precise mechanics
  of the LWP article format: every slide type and field, the meta block,
  the field/free-text parsing switch, typography rules and their
  opt-outs, `series.json` wiring. Read this before writing or debugging
  an article by hand, or point an agent at it to do the same.
- **`SKILL.md`** (`agent/skills/sourced-presentation/`) — a method for
  one kind of content, not a requirement of the format. A **sourced
  presentation** is a deck of short cards, each readable on its own,
  backed by a fully referenced long-form article; the skill covers that
  whole chain, from commissioning the research to verifying every fact at
  its source and cross-checking the deck against the article. It's the
  content type LightWebPres was originally shaped around, so it's a fast
  start if that's what you're writing — and entirely ignorable if it
  isn't. The format takes whatever you put in it. Series-specific
  settings (audience, lengths, numbering) stay in your own series
  specification and override the skill.
- **`specifications.md`** — the complete, authoritative reference:
  exact algorithms, every parser edge case, the full `series.json` and
  language-file schemas, the browser-based tool's internals. Consult it for
  anything this guide or the skill doesn't cover.
- **`lightwebpres --help`** — the terse, always-current version of all
  of the above: every command, every flag, every environment variable.
