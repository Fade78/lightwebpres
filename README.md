# LightWebPres

A single-file, dependency-free Python tool that turns an extended Markdown
format into self-contained, scrollable HTML "slide deck" articles — with
series navigation, an index page, and a generated README — deployable to
any static host.

```bash
python3 lightwebpres install my-series
python3 lightwebpres demo my-series
python3 lightwebpres build my-series
# -> my-series/public/index.html
```

No `pip install`, no build step beyond the tool itself, no JavaScript
framework in the output. Every generated page is inline CSS + inline JS,
one `.html` file, opens straight from disk or any static host.

## Why

- **Zero dependencies.** Python 3 standard library only — one file,
  `lightwebpres`, works anywhere Python 3 runs. `install` even copies
  itself into your series directory so the whole thing is self-contained.
- **Readable by humans and LLMs alike.** The format is plain Markdown with
  a small, explicit metadata convention (`key: value` lines, `<!-- lwp:slide:TYPE -->` markers) — designed so an LLM can generate or edit a complete
  article in one pass, and a CI pipeline can build it unattended.
- **Fails loudly, never silently.** Malformed input (a missing required
  field, a duplicate slide, an unsafe file path, broken HTML from a
  rendering bug) stops the build with a clear error instead of publishing
  something broken.
- **Three ways to build**, all sharing the exact same core engine:
  the CLI, a fully local browser build (upload a zip, download a zip —
  nothing leaves the tab), and a browser build that pulls/pushes straight
  to a GitLab repository.

## Quickstart

```bash
python3 lightwebpres install my-series --lang en   # scaffold a series directory
python3 lightwebpres demo my-series                # generate + build 3 example articles
open my-series/public/index.html
```

Then write your own `.md` files in `my-series/articles/`, list them in
`my-series/series.json`, and run `build` again.

## The format

Each article is one Markdown file: a metadata block, then a sequence of
"slides" separated by `---`.

```markdown
<!-- lwp:meta -->
file: apple-pie.html
h1: The apple pie<br>What shortcrust pastry actually changes
series_title: The apple pie
series_desc: Pastry, baking, and plating
---

<!-- lwp:slide:cover -->
tag: Recipe
# The apple pie
summary: Nine things that make or break a homemade apple pie, from pastry to bake.

---

<!-- lwp:slide -->
tag: Baking
## Temperature changes everything
summary: An oven that's too hot cooks the surface before the center is ready.
fact-label: The takeaway
highlight: 180 °C
highlight-caption: recommended baking temperature for shortcrust pastry
source: Baking guide, 2024 edition.

An oven that's too hot browns the crust while the center stays raw — the
most common mistake in a homemade pie.

---

<!-- lwp:slide:full-article -->
article: apple-pie_article.md
```

That builds into a scrollable page: a dark cover slide, a fact-card slide
with a highlighted figure, and a full long-form article appended at the
end — plus keyboard/scroll navigation, a "copy link to this slide" button,
and (if there's more than one article) a cross-article navigation block,
all generated automatically.

## Commands

| Command | What it does |
|---|---|
| `install [dir]` | Scaffolds a series directory (`articles/`, `templates/`, `language/`, `series.json`, `.gitlab-ci.yml`, a copy of the executable) |
| `demo [dir]` | Generates and builds 3 example articles, exercising every slide type and field |
| `build [dir]` | Builds `public/` from `series.json` + `articles/*.md` |
| `check [dir]` | Rebuilds in memory and diffs against `public/` — non-zero exit on drift, usable as a CI gate |
| `audit [dir]` | Non-blocking editorial warnings (e.g. "no cover slide") — never fails the build |
| `--help` | Full reference: options, environment variables, slide types, recognized fields |

## Slide types

- **`cover`** — title slide: tag, `# Title`, summary. Free position and
  count — `build` doesn't enforce a layout, `audit` just flags it if you
  want a reminder.
- **`standard`** — tag, `## Title`, summary, an optional highlighted
  figure (`highlight`/`highlight-caption`), and a Markdown fact-box.
- **`series-nav`** — cross-article navigation, generated from
  `series.json` (at most one per article).
- **`full-article`** — includes a separate long-form Markdown file,
  converted with full support for headings, bold/italic, links,
  footnotes, lists, tables, and inline raw HTML (at most one per article).

## Language & typography

Built-in French and English packs (typography rules — non-breaking
spaces, etc. — plus every UI string: nav button tooltips, "copy link",
series navigation labels). `--lang fr|en` picks one; a
`language/{lang}.json` file lets you override just the keys you care
about, falling back to the built-in pack for the rest. English is the
ultimate fallback for any language without a pack.

## Templates

`templates/style.css` and `templates/nav.js` are read back on every build
if present, replacing the built-in defaults — the page/index HTML
structure itself is fixed, not a template, so a build can't be broken by
a malformed structural override.

## Two browser-based tools

Both load the exact same `lightwebpres` executable, unmodified, running
inside [Pyodide](https://pyodide.org) (CPython compiled to WebAssembly) —
one build engine, three front-ends. Both need to be **served over
http(s)** from the repo root, not opened directly as a `file://` page —
browsers block Pyodide's asset loading under that origin, and the pages
also fetch `../lightwebpres` and their own `vendor/`/`app.py`/`git_sync.py`,
so serving `web/` alone isn't enough either:
`python3 -m http.server 8000 --directory /path/to/lightwebpres` (the
folder containing both `lightwebpres` and `web/`), then open
`http://localhost:8000/web/index.html` (see specifications.md §23.6 — if
you open a page as `file://` anyway, it now shows this exact command
computed from where you actually put the files).

- **`web/index.html`** — upload a zip of your series, get back a zip of
  `public/`. Nothing ever leaves the browser tab; Pyodide runs vendored
  locally, not from a CDN.
- **`web/git-sync.html`** — pull a series straight from a GitLab
  repository, build it, push the result back as a single commit. Talks
  directly to the GitLab instance you configure (no third-party proxy in
  the request path); never deletes a file on push, only creates/updates.

## Safety

- Fatal validation for every structurally dangerous input: duplicate or
  missing required slides, unsafe file paths in `series.json`/`article:`
  (rejects anything that isn't a plain filename — no directory traversal),
  malformed JSON.
- Typography rules are applied to already-assembled HTML but can never
  touch tag syntax — text and markup are split before any rule runs.
- Every generated page is checked for HTML tag balance before being
  written; a rendering bug never silently ships a broken page.

## Testing

```bash
python3 tests/run_tests.py
```

87 black-box tests exercising the CLI as a subprocess, plus real headless-
Chromium end-to-end tests (via Playwright, skipped cleanly if unavailable)
for both browser tools.

## Project layout

```
lightwebpres          # the executable — the only thing you need to run this
specifications.md     # full reference specification (French)
web/                  # the two browser-based build tools
tests/                # regression suite
```

## Reference

`specifications.md` is the complete, detailed specification (in French) —
directory layout, `series.json` schema, parser edge cases, full
placeholder reference, and more.

## License

Not yet set. `web/vendor/pyodide/` is vendored third-party code (Mozilla
Public License 2.0) — see `web/vendor/NOTICE.md`.
