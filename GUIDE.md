# LightWebPres — Guide

This is the map of the tool: install it, see what a page is made of, wire
a series, adjust the look, ship it. For what each command *exactly* does
in every edge case, see `specifications.md`; for the precise article
syntax, see `SKILL.md`. This guide is the path through all of it in the
order you'll actually need it.

**What this guide does not do is teach you to write.** LightWebPres is
for people who already know how; it renders what you give it. Nothing
here says what makes a good card, how to structure an argument or when a
claim needs a source. A second skill, `sourced-presentation`, ships
alongside as a courtesy for people who would like a method — an offered
interface, not the core of what this does. Take it or leave it:
[section 9](#9-going-further).

## 1. What LightWebPres is

LightWebPres turns an extended Markdown format into self-contained,
scrollable HTML articles — a cover, a handful of fact-card slides, an
optional long-form piece, cross-article navigation — with zero runtime
dependencies. One executable, `lightwebpres`, does the whole job:
scaffold a project, generate demo content, build, verify, and keep
templates current.

**Written for a person at a terminal — but you needn't be the one
typing.** LightWebPres ships a packaged skill (`SKILL.md`, in
`agent/skills/lightwebpres/`) that gives an agent the article format
directly, and every command here runs unattended: nothing ever blocks on
an interactive prompt. Point an agent at `SKILL.md` and it can write the
Markdown and run the build from minute one.

## 2. Install & your first build

```bash
./lightwebpres install my-series
./lightwebpres demo my-series --lang en      # French by default
./lightwebpres build my-series --lang en
xdg-open my-series/public/index.html         # `open` on macOS
```

`install` scaffolds a working project — `articles/` (empty, for your
`.md` files), `templates/` (your customization surface: `settings.conf`,
`custom.css`, `nav.js` — see section 5), `language/` (both the French and
English packs — typography rules + interface strings), a starter
`series.json`, and a copy of the `lightwebpres` executable itself, so the
project directory is self-sufficient.

**Language is chosen per build, not stored in the project** — both packs
are always installed. Pass `--lang fr|en` to `build`/`demo`, or set
`LWP_LANG`. French is the default, which is why the commands above say
so explicitly.

`demo` only works after `install` and refuses to overwrite existing
work. It drops three example articles (first, middle and last position in
the navigation) plus a captioned image, so you have something real to
look at before writing your own.

`build` reads `series.json` and every article it lists, and writes
`public/*.html` plus `public/index.html` and a generated `README.md`.
Open `public/index.html` in a browser — no server needed, every page is a
single self-contained file.

## 3. What a page is made of

A page is a sequence of **slides**, separated by `---`, preceded by one
metadata block. There are four slide types, and inside a standard slide a
small set of named components. This section names them and says how you
reach each one; `SKILL.md` carries the exact syntax and every edge case.

**The four slide types.**

| Type | Carries | How many |
|---|---|---|
| `cover` | `tag`, `# Title`, `summary` | any number, anywhere — it is a look, not a structural marker |
| standard *(the default)* | `tag`, `## Title`, `summary`, `highlight`, `highlight-caption`, `fact-label`, `fact-variant`, `source`, then free Markdown | as many as you want |
| `series-nav` | nothing — generated from `series.json` | 0 or 1 per article |
| `full-article` | `article: filename.md` | 0 or 1 per article |

**The components inside a standard slide.**

| Component | What it is for | How you reach it |
|---|---|---|
| **fact box** | the slide's claim, set off from the page | free Markdown text after a `fact-label:` line |
| **key figure** | one number that carries the slide | `highlight:` (+ optional `highlight-caption:`) |
| **source** | where the claim comes from | `source:` |
| **comparison table** | a grid of verdicts read at a glance | a Markdown table; cells take `yes` / `no` / `partial` classes via inline HTML |
| **figure** | a captioned image | `![alt](img/x.png "Caption")` alone on its line |
| **quote, code, list** | ordinary prose furniture | ordinary Markdown |
| **long-form article** | the piece the cards summarise | a `full-article` slide pointing at a second `.md` file |

Two things are worth knowing before you write, because they surprise
people:

- **The switch from fields to free text is one-way, within a slide.**
  Once a line is not a `field:` line, everything after it is prose — so a
  `highlight:` placed after a paragraph is published as the literal text
  `highlight: 3 000 W`. Fields first, prose after.
- **A fact box appears only with `fact-label:`.** Free text without it
  renders as plain paragraphs — which is often what you want.

Register every article that should appear in navigation in
`series.json` — next section.

## 4. Organizing a series

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
required here. Each article is self-described: `page_dest` (the output
HTML name), `page_title`/`page_desc`, `card_title`/`card_desc`/
`card_label`, `nav_title`/`nav_desc`, and the editorial fields
(`author`/`license`/`date`, defaulting series-wide from `series_meta`)
all resolve from the article's own meta block and cover slide, and any of
them can be overridden per entry here when you want `series.json` to have
the final say. `draft: true` keeps an article out of the build until it's
ready (`--include-drafts` previews it, with a banner). The array order is
the navigation and index order. The full fallback chain per field is in
`GLOSSARY.md`.

## 5. Adjusting the look

Four gestures, from the smallest to the largest. Pick the smallest one
that does the job.

### Pick a theme (the whole series)

Thirty-three named colour themes ship pre-configured — too many to pick
from a list, so you find one by facet: light or dark background, how loud
it is, and what hue the page carries.

```bash
./lightwebpres themes                                     # all 33, with facets
./lightwebpres themes --polarity dark --intensity sober   # just the ones you mean
./lightwebpres themes-gallery                             # every theme, rendered
```

Apply one at install time, or change your mind later:

```bash
./lightwebpres install my-series --theme evergreen
./lightwebpres set-theme my-series --theme crimson
```

A theme is a word in a data file: `set-theme` rewrites the one `theme:`
line of `templates/settings.conf` and nothing else. No CSS is touched —
the stylesheet is composed in memory at every build.

### Change one phrase (an instance tag)

Inside any free text, for the one place that needs it:

```markdown
A {color:call}critical{/color} figure, set in {mono}fixed pitch{/mono}.
```

`{color:…}` and `{font:…}` take either a shared name (`mark`, `call`,
`mono`, …) or a literal; `{sc}`, `{u}`, `{strike}` and `{mono}` take no
value. A bad value is a build error naming the file, never a silent
no-op, and `audit` counts them per article so you know where to look when
you change theme.

**Alignment is the one block-level tag**, because `text-align` on an
inline span does nothing. Opener and closer each go alone on their line:

```markdown
{align:center}
This paragraph is centred, and so is the next one.
{/align}
```

Values: `left | center | right | justify`. Everything inside the block
aligns, table cells included.

### Change one page (`style.*` in its meta block)

Any property, scoped to that page only:

```
<!-- lwp:meta -->
page_title: The apple pie
style.cover.bg.angle: 90deg
style.page.content-max: 60ch
```

And `fact-variant: warning` on a standard slide gives that one fact box a
named look, rather than a hand-tuned colour.

### Change the whole series (`templates/settings.conf`)

Every visual decision is a typed property, `component.axis: value`, and
`settings.conf` lists **all** of them, commented out, at the values of
the theme you chose — the complete surface is under your eyes, no
documentation needed. Uncomment a line to **pin** it: it survives every
theme change and every executable upgrade, because `lightwebpres` never
rewrites your file.

```
# tag.fg: ink-quiet        ← the scaffold, showing the theme's value
tag.fg: call               ← uncommented: yours, and it stays
```

A bare word like `call` is looked up among the theme's shared values
(`color.call`, since `fg` is a colour axis); a literal like `#8A4B00`
works anywhere a colour does. A mistyped key or value is a named build
error pointing at the file and key.

Two properties people look for by name: **`page.content-max`** is the
text column width, `50ch` by default — a measure in characters, not a
pixel width, so it stays right at every type size. **`page.hyphens`**
(`manual | auto`) controls whether words break at end of line; it is
`manual`, and nothing turns it on for you.

After a `set-theme`, `audit` will note that the scaffold's *comments*
show the old theme's values; `refresh-templates --scaffold` realigns them
while keeping every pinned line.

### Rules rather than values (`templates/custom.css`)

Full CSS, no subset, appended after the composed stylesheet so your rules
win ties. New selectors, media queries, `@font-face` (name the family at
the head of a stack in `settings.conf`, declare the face here). The
composed sheet's `--component-axis` variables are usable in it
(`border-color: var(--color-mark)`), and that is the recommended way to
follow the theme. `templates/nav.js` overrides the navigation behaviour
wholesale; the page and index HTML structure is fixed, not a template.

## 6. Verifying before you ship

Two different checks, for two different moments:

```bash
./lightwebpres audit my-series   # editorial warnings, never blocks
./lightwebpres check my-series   # rebuilds in memory, diffs against public/
```

`audit` flags things worth a second look — no cover slide, a scaffold
whose comments predate your current theme, a retired CSS variable still
referenced in `custom.css`, the instance tags in each article — but never
fails; it's a nudge, not a gate. `check` is the opposite: it rebuilds
every article in memory and compares it byte-for-byte against `public/`,
exiting non-zero the moment anything differs. That non-zero exit is what
makes it a real CI gate — wire it in before `build` to catch a `public/`
that was hand-edited or never rebuilt after a source change.

## 7. Keeping templates current

`lightwebpres` is a single file you copy into each project (`install`
does this). When you drop in a newer copy, the built-in JS baked into
`templates/` doesn't update on its own:

```bash
./lightwebpres refresh-templates my-series
```

The stylesheet is composed in memory from the current executable at every
build, so it is fresh by construction, and your `settings.conf` and
`custom.css` are yours — never touched. The one tool-owned file on disk
is `nav.js`: `refresh-templates` replaces it if it differs from the
built-in version (saving the old one as `nav.js.bak`) and reports
`already up to date` otherwise. Your theme choice needs no reapplying:
it's the `theme:` line of `settings.conf`, which an upgrade cannot
revert.

`--scaffold` additionally regenerates `settings.conf`'s commented block
against the current theme and the current property registry, keeping
every line you uncommented.

## 8. Beyond the CLI

`web/index.html`, one page with two tabs, runs the exact same engine as
the CLI — unmodified — inside Pyodide (CPython compiled to WebAssembly),
so the output is identical either way:

- **Upload a zip** — drop a zip of your series, get back a zip of
  `public/`. Nothing leaves the browser tab.
- **Sync with GitLab** — pull a series straight from a GitLab repository,
  build it, and push the result back as a single commit.

Both tabs share one Pyodide load, so switching is instant. The page must
be **served over http(s)**, not opened as a `file://` page — browsers
block Pyodide's asset loading under that origin. For local testing:

```bash
python3 -m http.server 8000 --directory /path/to/lightwebpres
# then open http://localhost:8000/web/index.html
```

For unattended builds, `install --gitlab-ci` writes a `.gitlab-ci.yml`
that runs `lightwebpres build .` on every push and publishes `public/` as
an artifact — opt-in, never written by a plain `install`. Add a `check`
step before it to catch drift before it merges (section 6).

## 9. Going further

- **`SKILL.md`** (`agent/skills/lightwebpres/`) — the precise mechanics
  of the article format: every slide type and field, the meta block, the
  field/free-text switch, typography and its opt-outs, `series.json`
  wiring. Read it before writing or debugging an article by hand, or
  point an agent at it.
- **`SKILL.md`** (`agent/skills/sourced-presentation/`) — a method for
  one kind of content, not a requirement of the format. A **sourced
  presentation** is a deck of short cards, each readable on its own,
  backed by a fully referenced long-form article; the skill covers that
  chain, from commissioning research to verifying every fact at its
  source. It is **given, not required**: a facilitation for whoever wants
  a method, and entirely ignorable otherwise. The format takes whatever
  you put in it, and the tool has no opinion about how you got there.
- **`specifications.md`** (in French) — the complete, authoritative
  reference: exact algorithms, every parser edge case, the full
  `series.json` and language-file schemas, the browser tool's internals.
- **`lightwebpres --help`** — every command, every flag, every
  environment variable.

## 10. When something doesn't work

| Symptom | Cause |
|---|---|
| `lightwebpres: command not found` | it isn't on your `PATH` — run it as `./lightwebpres` |
| `Permission denied` | `chmod +x lightwebpres` |
| `… is not empty. Use an empty or new directory, or pass --force` | installing into a directory that already has files — `install . --force` is the normal in-place case |
| the site is in French | `--lang en` on `build`/`demo`; French is the default |
| `open: command not found` | macOS-only — use `xdg-open` on Linux |
| a `field:` line published as literal text | it came after prose in the same slide; the switch to free text is one-way (section 3) |
