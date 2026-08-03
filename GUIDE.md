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
you're doing this yourself, keep reading from the top.

## 2. Install & your first build

```bash
./lightwebpres install my-series
./lightwebpres demo my-series
./lightwebpres build my-series
open my-series/public/index.html
```

`install` scaffolds a working project — `articles/` (empty, for your
`.md` files), `templates/` (default CSS/JS, editable), `language/`
(French and English packs — typography rules + interface strings), an
empty `series.json`, and a copy of the `lightwebpres` executable itself,
so the project directory is self-sufficient. `--lang fr|en` picks the
default language (French unless
told otherwise); `--force` lets you install into a non-empty directory;
`--gitlab-ci` also writes a `.gitlab-ci.yml` (opt-in — `install` never
assumes a GitLab deployment on its own, see section 7).

`demo` only works after `install` and refuses to overwrite existing
files — it drops three example articles (first, middle, last position in
the series navigation) that exercise every slide type and field, so you
have something real to look at and copy from before writing your own.

`build` reads `series.json` and every article it lists, and writes
`public/*.html` plus a `public/index.html` and a generated `README.md`
listing the series (title, intro, and a link per article, from
`series.json`'s `series_meta`). Open `public/index.html` in a browser —
no server needed, every page is a single self-contained file.

## 3. Choosing a look

Nine named color themes ship pre-configured — Nord, Dracula, Solarized,
Gruvbox, Catppuccin, Tokyo Night, Monokai, Everforest, Rosé Pine — pick
one at install time:

```bash
./lightwebpres install my-series --theme nord
```

`--theme` substitutes the six CSS custom properties the default
stylesheet exposes (`--yellow --dark --grey --light --accent --green`);
nothing else changes, and the choice survives an executable upgrade —
`refresh-templates` (section 7) reapplies the same theme instead of
silently reverting to default. Preview every theme, rendered against real
slide content, with:

```bash
./lightwebpres themes-gallery
open themes-gallery.html
```

Beyond the nine presets, `templates/style.css` and `templates/nav.js` are
read back on every build if present, replacing the built-in defaults —
the page/index HTML structure itself is fixed, not a template, so a
malformed override can't break the build's structure, only its styling.
Put your own CSS after the `Personnalisations locales` marker comment
near the end of `style.css`; that's what lets `refresh-templates` update
the built-in part later without touching what you added.

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

`audit` flags things worth a second look — no cover slide, that kind of
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

For `style.css`, this updates only the built-in part and leaves anything
you wrote after the `Personnalisations locales` marker untouched — and if
you'd picked a theme (section 3), that theme's colors are reapplied to
the refreshed CSS automatically, so an upgrade never quietly reverts you
to the default look. If the marker is missing (a file that predates it,
or one where it was removed by accident), `refresh-templates` refuses to
guess: it leaves the file alone and tells you the exact line to add
first. `nav.js` has no such split-and-preserve mechanism — it gets fully
replaced, with the previous version saved as `nav.js.bak` in case you'd
customized it.

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
- **`specifications.md`** — the complete, authoritative reference:
  exact algorithms, every parser edge case, the full `series.json` and
  language-file schemas, the browser-based tool's internals. Consult it for
  anything this guide or the skill doesn't cover.
- **`lightwebpres --help`** — the terse, always-current version of all
  of the above: every command, every flag, every environment variable.
