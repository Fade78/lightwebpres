<p align="center">
  <img src="web/lwp_banner.svg" alt="LightWebPres — Markdown in, publish-ready pages out" width="100%">
</p>

# LightWebPres

A single-file, dependency-free Python tool that turns an extended Markdown
format into self-contained, scrollable HTML "slide deck" articles — with
series navigation, an index page, and a generated README — deployable to
any static host.

```bash
./lightwebpres install my-series
./lightwebpres demo my-series
./lightwebpres build my-series
# -> my-series/public/index.html
```

No `pip install`, no build step beyond the tool itself, no JavaScript
framework in the output. Every generated page is inline CSS + inline JS,
one `.html` file, opens straight from disk or any static host.

## Features

- **Zero dependencies.** Python 3 standard library only — one file,
  `lightwebpres`, works anywhere Python 3 runs. `install` even copies
  itself into your series directory so the whole thing is self-contained.
- **Readable by humans and LLMs alike.** The format is plain Markdown with
  a small, explicit metadata convention (`key: value` lines,
  `<!-- lwp:slide:TYPE -->` markers) — designed so a person can write it
  directly, or an LLM can generate or edit a complete article in one pass.
- **Fails loudly, never silently.** Malformed input (a missing required
  field, a duplicate slide, an unsafe file path, broken HTML from a
  rendering bug) stops the build with a clear error instead of publishing
  something broken.
- **Works by hand or in a pipeline.** Edit Markdown and run the CLI
  yourself, or wire `build`/`check` into CI — `check`'s non-zero exit on
  drift makes it a usable merge gate. Same engine, same output, either
  way.
- **Three ways to build**, all sharing the exact same core engine:
  the CLI, a fully local browser build (upload a zip, download a zip —
  nothing leaves the tab), and a browser build that pulls/pushes straight
  to a GitLab repository.
- **Companion web tools, no server required.** `web/index.html` and
  `web/git-sync.html` bring that same engine to a browser tab — for
  teammates who'd rather not touch a terminal.
- **Agent friendly.** Markdown in, scripted generation via the CLI, and a
  packaged skill for agent workflows — lightwebpres was built to be
  driven by an agent as naturally as by a person.

## Quickstart

```bash
./lightwebpres install my-series --lang en   # scaffold a series directory
./lightwebpres demo my-series                # generate + build 3 example articles
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
| `refresh-templates [dir]` | Updates the built-in CSS/JS in `templates/` after an executable upgrade, keeping local customizations |
| `themes-gallery [path]` | Generates a self-contained HTML page previewing every built-in color theme (default: `themes-gallery.html`) |
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

The French pack automatically upgrades an existing space to a
non-breaking one before `; : ! ?`, after `«`, before `%`, between
thousands-grouped digits (`170 000`, only if the source already spaces it
out), between a number and `million(s)`/`milliard(s)`/`dollar(s)`/`$`, and
after `×`/`≈` before a number — it never inserts spacing or digit
grouping that wasn't already there, and a non-breaking space already in
your source always passes through unchanged. This alters generated
content, so it's controllable at three levels: per-article meta fields
`typo-units: off` / `typo-thousands: off` (just those rules) or `typo:
off` (every rule, that article's page only), and the CLI flag
`--no-typography` on `build`/`check` (every rule, the whole run). See
`--help` or specifications.md §4.5/§7.5/§19.6 for the full list.

## Templates

`templates/style.css` and `templates/nav.js` are read back on every build
if present, replacing the built-in defaults — the page/index HTML
structure itself is fixed, not a template, so a build can't be broken by
a malformed structural override.

Nine named color themes ship pre-configured — Nord, Dracula, Solarized,
Gruvbox, Catppuccin, Tokyo Night, Monokai, Everforest, Rosé Pine — pick
one at scaffold time:

```bash
./lightwebpres install my-series --theme nord
```

`--theme` substitutes the six CSS custom properties (`--yellow --dark
--grey --light --accent --green`) the default stylesheet exposes; nothing
else in the CSS changes, and the substitution survives an executable
upgrade — `refresh-templates` reapplies the same theme to the refreshed
built-in CSS instead of silently reverting to the default.

![Preview of the nine built-in color themes](themes-gallery.png)

That's [`themes-gallery.html`](themes-gallery.html) in this repo,
rendered — open it directly in a browser for the live, interactive
version (each card previews the theme against real slide content: tag,
title, summary, a highlighted figure, a fact-box, a table). It's
generated straight from the tool's own `THEMES` data with
`./lightwebpres themes-gallery`, so it can never drift from what
`install --theme` actually applies.

## Two browser-based tools

Both load the exact same `lightwebpres` executable, unmodified, running
inside [Pyodide](https://pyodide.org) (CPython compiled to WebAssembly) —
one build engine, three front-ends. Both need to be **served over
http(s)**, not opened directly as a `file://` page — browsers block
Pyodide's asset loading under that origin (see specifications.md §23.6 —
if you open a page as `file://` anyway, it shows the exact fix command,
with a one-click Copy button, computed from where you actually put the
files).

They also need their own `vendor/`/`app.py`/`git_sync.py`, plus a copy of
`lightwebpres` itself — never duplicated by default, since it stays the
single source of truth — found in one of two conventional spots relative
to the page, tried in that order: **`./lightwebpres`** (dropped alongside
`web/`'s own contents — the layout for a real site that serves `web/` as
its own URL root, no extra path segment needed) or **`../lightwebpres`**
(the repo's own layout, one level up, for a deployment that's just a
straight copy of the repo). Local testing from the repo, both covered by
one command: `python3 -m http.server 8000 --directory /path/to/lightwebpres`
(the folder containing both `lightwebpres` and `web/`), then open
`http://localhost:8000/web/index.html`. Self-hosting on a real web server
(Apache/nginx) can also hit a `.mjs` MIME type issue — see
specifications.md §23.7 for the fix (`web/.htaccess` handles it
automatically on Apache where allowed).

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

100+ black-box tests exercising the CLI as a subprocess, plus real headless-
Chromium end-to-end tests (via Playwright, skipped cleanly if unavailable)
for both browser tools.

## Project layout

```
lightwebpres          # the executable — the only thing you need to run this
specifications.md     # full reference specification (French)
themes-gallery.html   # preview of the nine built-in color themes (generated, see below)
themes-gallery.png    # a rendered snapshot of the above, for this README
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

## Troubleshooting

**`./lightwebpres: Permission denied`** (Linux/macOS)
The executable bit didn't survive however you got the file (some zip
tools, some transfer methods). Fix it once:

```bash
chmod +x lightwebpres
```

**`./lightwebpres: command not found`** (Linux/macOS)
`lightwebpres` isn't installed system-wide, so it needs either the `./`
prefix when run from the directory it's in, or its full/relative path.
Running it by bare name only works if that directory is on your `PATH`.

**Windows**
Windows doesn't understand the `#!/usr/bin/env python3` line at the top
of the file, so `lightwebpres` (or `.\lightwebpres`) won't launch on its
own. Run it through Python explicitly instead:

```powershell
python lightwebpres install my-series
```

If that's not found, try the `py` launcher (bundled with most Windows
Python installs):

```powershell
py lightwebpres install my-series
```

**`python3: command not found`**
Some systems only have `python` on `PATH`, not `python3` (common on
Windows, occasionally macOS). Use `python` instead of `python3` in any
command above that invokes it explicitly — e.g. `python -m http.server`
when serving the [browser tools](#two-browser-based-tools).
