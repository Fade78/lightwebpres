<p align="center">
  <img src="web/lwp_banner.svg" alt="LightWebPres — Markdown in, publish-ready pages out" width="100%">
</p>

# LightWebPres

A single-file, dependency-free Python tool that turns an extended Markdown
format into self-contained, scrollable HTML "slide deck" articles — with
series navigation, an index page, and a generated README — deployable to
any static host.

```bash
./lightwebpres init my-series
./lightwebpres demo my-series
./lightwebpres build my-series
# -> my-series/public/index.html
```

No `pip install`, no build step beyond the tool itself, no JavaScript
framework in the output. Python 3.8+ (standard library only); on
Windows, run `python lightwebpres <command>`. Every generated page is inline CSS + inline JS,
one `.html` file, opens straight from disk or any static host.

**Every page is a presentation deck.** Open it in a browser and you have
a full-screen presenter experience: keyboard (↑/↓, Home, F for
fullscreen, B/W/T for pause screens), mouse (click to advance,
right-click to go back, double-click for fullscreen, middle-click to
exit), and touch (swipe) all work out of the box. Navigation buttons fade
after 3 seconds of idleness (1 second in fullscreen) — the speaker sees
only slides. The cursor hides on the same clock, and both come back on
the same condition: 250 ms of continuous mouse movement, so a knock
against the desk puts nothing back on the wall. The scroll bar goes with
them — it is navigation too, and it fades rather than being removed, so
the page never reflows. The mouse becomes a
remote: left-click advances, right-click goes back, two distinct buttons,
no aiming. Fullscreen also neutralizes OS power-saving so the screen never
dims mid-talk. A `X / N` counter and a direct number-jump (type the slide
number, press Enter) keep you oriented in long decks; **N** opens a speaker
panel with the current slide's notes and the next slide's title, so you can
read ahead unseen. And every page prints one slide per sheet — a clean PDF
handout at Ctrl/Cmd+P.

## Features

- **Typography handled for you.** Non-breaking spaces before punctuation,
  `%`, thousands, and units — applied automatically, never touching what
  you've already written, switchable off per article or globally when
  you don't want it. French and English ship built-in; the mechanism
  isn't French-specific, so adding a language is a matter of writing
  rules, not touching the engine.
- **Nothing you make here can stop opening.** The output is one
  self-contained HTML file: no runtime, no viewer, no proprietary
  container that has to still be supported for the words to come back.
  A deck built today opens in any browser that exists now and in any
  that follows, on a machine with none of this installed — the file
  alone, without the tool that made it. The source behind it is plain
  Markdown, so it outlives the tool as well. A presentation is often the
  only surviving record of a talk; this one cannot become unreadable
  because something stopped being maintained.
- **A simple, three-level structure.** Series → article → slide. Nothing
  to design: pick a slide type (cover, standard, cross-article nav, full
  article), fill in the fields.
- **Styled by typed properties, not by CSS.** Every visual decision is a
  named, typed property (`component.axis: value`) in one plain-text
  settings file that drives the whole series — the stylesheet is composed
  at build time, and a mistyped key or value is a named build error,
  never a silent no-op.
- **Every page stands alone, yet belongs to its series.** Each article is
  one self-contained HTML file — but it carries its own cross-article
  navigation block, generated from the series, so a reader can always get
  back to "the rest of the series" without a framework stitching pages
  together at runtime.
- **Share in one click, at whatever scope you need.** Copyable link or QR
  code, for the whole series, the current article, or the exact slide
  being read — generated entirely client-side. A slide's address is the
  `slug:` its author declared, never where it sits and never its title,
  so reordering the deck, rewriting a heading or dropping a slide does
  not repoint the links you have already given out — including the
  printed ones.
- **Built-in presentation mode.** Every generated page is a full-screen
  presenter deck: keyboard (↑/↓, Home, F fullscreen, B/W/T pause
  screens), mouse (click advance, right-click back, double-click
  fullscreen, middle-click exit), touch (swipe, double tap). Navigation
  chrome fades after 3s idle (1s in fullscreen) on every device; with a
  pointer the cursor hides on the same clock and both return after 250ms
  of continuous movement, and on a touch screen a double tap is the
  switch, both ways. The mouse becomes
  a remote — left-click advances, right-click goes back, two distinct
  buttons, no aiming. Fullscreen neutralizes OS power-saving so the
  screen never dims mid-talk.
- **Speaker aids for long decks.** A `X / N` counter, a type-a-number
  jump (Enter to land on slide N), and a speaker panel (**N**) that shows
  the current slide's `note:` field (a speaker note withheld from the
  audience) with the next slide's title — all fighting for the speaker's
  attention, not the audience's. Every page also prints one
  slide per sheet (Ctrl/Cmd+P → PDF) with the theme colours kept and the
  navigation chrome stripped.
- **Comes with a companion web page, not just a CLI.** One browser-based
  tool, nothing to install: one tab builds a zip you drop in, the other
  pulls, builds, and pushes straight to a GitLab repository — both
  running the exact same engine as the command line, entirely inside the
  tab.
- **Agent friendly, without being agent-only.** Written and run by hand
  just as naturally as it's scripted: articles are plain Markdown, the
  CLI never blocks on an interactive prompt, and a bundled skill teaches
  the format to any skill-aware agent — so a person with an editor and an
  agent driving a pipeline get the same tool, not two different ones. A
  second skill ships alongside for one editorial method the format suits
  well; it is offered, not required — the format takes whatever you put
  in it.
- **Made to sit in a content pipeline.** Every command runs unattended
  and returns a meaningful exit code — `verify` fails on drift and
  `audit --strict` fails on anything worth reporting, two real CI gates
  for two different questions. Plain `audit` never fails, whatever it
  finds: it renders the series in memory and reports, it does not stop.
  Nothing to
  install: one file, the Python standard library only, no wheel, no
  lockfile, no network at build time, so any image with `python3` runs
  it. Every path is an environment variable (`LWP_SERIES_DIR`,
  `LWP_OUTPUT_DIR`, …), and `--only page` rebuilds a single article. The
  Markdown can come from anywhere — a CMS export, a database, a
  generator, an agent upstream — but see the trust boundary below: raw
  HTML in such markdown passes through, so untrusted sources must be
  sanitized before the build.
  Markdown can come from a CMS export, a database, a generator or an
  agent upstream; this is the step that turns it into publishable
  pages.

## Quickstart

```bash
./lightwebpres init my-series             # scaffold a series directory
./lightwebpres demo my-series --lang en      # generate + build 3 example articles (English UI)
open my-series/public/index.html
```

Then write your own `.md` files in `my-series/articles/`, add a `{"page_source":
"apple-pie.md"}` entry per article to `my-series/series.json` (that's the
only field it needs — see below), and run `build` again.

## The format

Each article is one Markdown file: a metadata block, then a sequence of
"slides" separated by `---`. An article is self-describing — its own
`page_title`/`card_title`/`card_desc`/`nav_title`/`nav_desc` all fall back
to sensible content-derived defaults if left out, and `series.json` only
needs `page_source` per article (see specifications.md §20.3.1); every field
below can be omitted or overridden from `series.json` instead.

```markdown
<!-- lwp:meta -->
page_title: The apple pie<br>What shortcrust pastry actually changes
nav_title: The apple pie
nav_desc: Pastry, baking, and plating
---

<!-- lwp:slide:cover -->
kicker: Recipe
# The apple pie
summary: Nine things that make or break a homemade apple pie, from pastry to bake.

---

<!-- lwp:slide -->
kicker: Baking
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

The last slide points at a **second** file, `articles/apple-pie_article.md`,
holding the long-form text — `build` fails if it isn't there. Drop the
`full-article` slide if you don't want one.

### Variants in one page

Use the slide-level `tags:` field when one article must carry several
languages, audiences, or detail levels. Tags are space-separated, normalized
case-insensitively, and may contain Unicode letters, digits, `-`, and `_` (but
not a leading `_`). A slide without tags belongs to `default`, which is the
shared content shown with every selected variant.

```json
{
  "series_meta": {
    "lang_tags": {"fr": "fr", "en": "en"}
  },
  "articles": [{"page_source": "apple-pie.md"}]
}
```

```markdown
<!-- lwp:slide:cover -->
kicker: Guide
tags: fr
# La tarte aux pommes
summary: Version française.

---

<!-- lwp:slide:cover -->
kicker: Guide
tags: en
# The apple pie
summary: English version.

---

<!-- lwp:slide -->
kicker: Common
## Shared slide
summary: Visible in every variant because it has no `tags:` field.
```

Press **L** in the generated page to choose a variant. The menu appears only
when at least two tags exist; the choice is retained in
`localStorage['lwp-active-tag']`. Navigation, slide counts, anchors, and the
presenter panel operate on the visible subset. `tags: excluded` removes a
slide at build time and never emits it in the HTML — and, since a slide's
anchor is derived from what it says rather than from its rank, excluding
one no longer repoints the anchors of the slides after it. `audit` reports malformed
tags and language tags whose declared pack is missing without blocking the
build.

That builds into a scrollable page: a cover slide inverted against the
page, a fact-card slide
with a highlighted figure, and a full long-form article appended at the
end — plus keyboard/scroll navigation, a "copy link to this slide" button,
and (if there's more than one article) a cross-article navigation block,
all generated automatically.

Each page is also a presentation deck: click to advance, right-click to
go back, double-click or middle-click for fullscreen, swipe on touch,
B/W/T for pause screens (black, white, or the theme's background — the
speaker's remote-mouse use case). See the GUIDE's "Presenting" section
for the full control list.

Since so much of that is derived rather than written, there is a way to
ask what a series actually resolves to, without building it:

```bash
./lightwebpres status my-series
./lightwebpres status my-series --format json
```

It lists the articles in `series.json` order — the order that fixes the
cross-article navigation — with each field resolved exactly as the build
resolves it, each article's status and a count per status, and, for every value,
which level decided it: the `series.json` entry, the article's meta
block, the article's own content, another field it was derived from, or
the built-in default. An article whose file can't be read is still
listed, with its fields fallen back and a warning on stderr; nothing is
built and nothing is written.

When the question is about **one** name rather than the whole series —
and especially when the answer is a surprise — `resolve` says what that
name is worth here, which level decided it, and what every other level
held:

```bash
./lightwebpres resolve my-series page_title --article apple-pie.md
./lightwebpres resolve my-series kicker.fg
./lightwebpres resolve my-series fact-label
```

No option says which kind of thing you are asking about, because the
name already does: a dot means a theme property, an underscore an
article or series field, a hyphen a slide field. The losing levels are
the point — a value on its own never explains why the line you just
wrote changed nothing, and a chain showing your `settings.conf` entry
still commented out does.

```
kicker.fg — theme property
  value: #BF616AFF
  from:  settings
  via:   color.call

  cascade, strongest first:
    instance  —
    article   —
  > settings  call
    theme     —
    default   ink-quiet
```

A slide field has no cascade — it is written on a slide or it is not —
so `resolve fact-label` answers with every slide that sets it, across
the series or within one article.

## Commands

| Command | What it does |
|---|---|
| `init [dir]` | Scaffolds a series directory (`articles/`, `templates/` with your `settings.conf` and `custom.css`, an empty `language/`, `series.json`, a copy of the executable, and `.gitlab-ci.yml` if `--gitlab-ci` is passed — opt-in, never assumed). The tool's own files — the navigation script, the language packs — stay in the executable and are read from there, so upgrading it is the whole upgrade |
| `demo [dir]` | Generates and builds 3 example articles, exercising every slide type and field |
| `build [dir]` | Builds `public/` from `series.json` + `articles/*.md`; `--only file.html` rebuilds just that one article, falling back to a full build automatically if anything that affects `index.html`/navigation changed (see specifications.md §11.3.1); `--inline-images` embeds images as base64 data URIs (self-contained pages, no `img/` directory) |
| `verify [dir]` | Rebuilds in memory and diffs against `public/` — non-zero exit on drift, usable as a CI gate |
| `audit [dir]` | Non-blocking warnings. It reads the sources (editorial — e.g. "no cover slide" — variant tags and language packs), judges the *resolved* stylesheet (a navigation control nobody can see, text painted the colour of its own ground, a size under the readability floor), checks the presentation layer (a legacy `style.css`, a retired CSS variable named with its replacement, a settings scaffold out of step with the theme), and renders the series in memory to report what only composing it can say. Exit 0 whatever it finds, unless `--strict` is passed |
| `template update [dir]` | Clears the tool's own files out of a series: a copy identical to the built-in one is removed (it did nothing but freeze you), a differing `nav.js` is saved as `.bak` and removed, a differing language pack is reported and kept. Also creates a missing `settings.conf`/`custom.css`; never touches a file you own |
| `template show <file>` | Prints one of the files the executable owns — `nav.js`, `fr.json`, `en.json` — on stdout. No series needed: the answer is inside the program |
| `template write <file> [dir]` | Installs one of them where the build reads it, to be modified. The build then prefers your copy to the built-in one and warns on every run that it no longer follows the tool's fixes — at warning level, so `--quiet` keeps it. `--force` to replace an existing file |
| `theme list` | Lists the built-in color themes with their facets; `--family`/`--polarity`/`--hue` narrow the list |
| `theme show <slug>` | Describes one theme — palette, fonts, facets, and the WCAG contrast level it actually reaches, measured, per category. `--format json` for machines |
| `series theme [dir]` | Same, for the *effective* theme of an installed series — after the values it pins in `templates/settings.conf` |
| `status [dir]` | Says what is in a series without building anything: its articles in `series.json` order, every field *resolved* the way a build resolves it, and which level of the cascade each value came from. `--format json` for machines |
| `series slug [dir]` | Lists every card of the series and the name it is published under — the anchor a shared link and a printed QR code point at. `status` answers by article; this answers by card. `--format json` for machines |
| `series slug set [dir]` | Writes a `slug:` into every card that has none, and only those. The one command that edits your articles — a build never rewrites its own inputs. What it writes is random and meant to be renamed to something readable; `--dry-run` says what it would write |
| `resolve [dir] <name>` | Says what ONE name is worth here and which level decided it, losing levels included. The shape of the name picks the cascade: dotted = theme property, `snake_case` = article/series field, `kebab-case` = slide field. `--article file.md` adds a page's own layer; `--format json` for machines |
| `series theme set [dir] --theme X` | Changes an existing series' theme by rewriting the one `theme:` line of `templates/settings.conf`; your pinned values stay and apply on top |
| `theme gallery [path]` | Generates a self-contained HTML page previewing every built-in color theme — one row per theme, four panels across (cover, card with a note, notes section, full article) — with facet filters (default: `themes-gallery.html`) |
| `clean [dir]` | Purges orphan files from `public/` using the build manifest (dry-run by default, `--force` to actually remove) |
| `watch [dir]` | Polls sources, rebuilds on change, optionally serves on `127.0.0.1` (`--serve`, `--port 8000`) |
| `completion --shell bash\|zsh` | Prints a shell completion script — install with `eval "$(lightwebpres completion --shell bash)"` (or `zsh`) to get tab-completion for commands, subcommands, and options |
| `--help` | Full reference: options, environment variables, slide types, recognized fields |
| `--version` | Prints the version (`LightWebPres vX.Y.Z`) and exits |

## Options

Global options (accepted before the command, like `git`): `--lang fr|en`,
`--quiet`, `--verbose`, `--no-color`, `--dry-run`, `--timestamp`,
`--version`, `--help`. The option nearest the command wins.

| Option | Command(s) | Effect |
|---|---|---|
| `--slides-page-numbers on\|off` | `build`, `watch` | engraves the top-right `NN / NN` slide number — opt-in, default `off`; the article front-matter `slide_page_numbers` and `series_meta.slide_page_numbers` also enable it (see specifications.md §3.3.5) |
| `--no-nav` | `build`, `watch` | omits the cross-article navigation block |
| `--no-index` | `build`, `watch` | skips `index.html` |
| `--no-readme` | `build`, `watch` | skips the generated `README.md` |
| `--drafts-only` | `build`, `watch` | builds only `status: draft` articles |
| `--open` | `build`, `watch` | opens the result in the browser |
| `--include-drafts` | `build`, `verify` | builds draft articles too |
| `--strict` | `audit` | exits non-zero on any warning — the complete gate: editorial warnings and everything the render raises alike, a failed render included |
| `--templates` | `audit` | restricts the audit to the presentation/template layer: it still judges the resolved stylesheet, but skips the per-article editorial checks and does not render, so it stays cheap |
| `--serve` / `--port N` | `watch` | serves on `127.0.0.1` (opt-in), port `N` (default 8000) |
| `--only file.html` | `build` | rebuilds a single article |
| `--inline-images` | `build` | embeds images as base64 data URIs |
| `--gitlab-ci` | `init` | emits a `.gitlab-ci.yml` |
| `--format json` | `resolve`, `status`, `theme show`, `series theme` | machine-readable output |

The spellings this tool used before the CLI was reorganised — `install`,
`check`, `themes`, `theme-info`, `set-theme`, `series-info`,
`refresh-templates`, `themes-gallery` — are not commands. Typing one is an
error that names what to type instead. They were deprecated aliases that
warned and then worked, which taught the old spelling as readily as the
new one.

## Slide types

- **`cover`** — title slide: kicker, optional `tags:`, `# Title`, summary. Free position and
  count — `build` doesn't enforce a layout, `audit` just flags it if you
  want a reminder.
- **`standard`** — kicker, optional `tags:`, `## Title`, summary, an optional highlighted
  figure (`highlight`/`highlight-caption`), and a Markdown fact-box.
- **`series-nav`** — cross-article navigation, generated from
  `series.json` (at most one per article); it accepts optional `tags:` and
  `comment:` fields but no free body.
- **`full-article`** — includes a separate long-form Markdown file, accepts
  `article:` plus optional `tags:` and `comment:`, and has no free body. A
  page may carry several of them, each naming its own file;
  converted with full support for headings (levels 1–6: `####` renders as
  a bold-font paragraph, `#####`/`######` as plain text), bold/italic,
  links, notes (see below), lists, tables, blockquotes, images with
  captions (`![alt](src "Caption")` — small, centered, themed; wrap it in
  a link, `[![alt](src "Caption")](url)`, and the picture becomes
  clickable while
  the caption stays outside the link, as text about it; mid-sentence the
  same image stays inline and its title becomes a tooltip),
  inline/fenced code, and inline raw HTML.
  A comparison table's cells can carry `yes` / `no` / `partial` — or
  `col-signal` on a whole column — to be coloured by verdict; written as
  inline HTML, since Markdown has no syntax for it.

These four are the whole list, and `build` says so: a marker naming
anything else — `<!-- lwp:slide:covre -->` — stops the build with the
slide's rank, the token you wrote, and the four names, rather than
publishing a slide of the wrong kind.

 Every slide (and `series.json`/the article's own meta block) also
 accepts `comment:` — a review note, recognized but never rendered, never
 published, not even in the page's raw HTML source. A `note:` field is the
 speaker note: also parsed and withheld from the slide the reader sees, but
  surfaced by the presenter panel (**N**) for the person presenting. `note:`
  is accepted on `cover` and standard slides. It is
 distinct from a `[^label]` footnote, which is a source note printed for the
 reader (see below). Both `note:` and `comment:` accept multi-line values:
 each continuation line starts with whitespace, and an indented blank line is a
  paragraph break; the block ends at the first non-indented, non-empty line.

`tag:` is not a field, and not an alias for one. Use `kicker:` for the label
above a slide title, and `tags:` for variant filtering. A `tag:` line becomes
body text on a standard slide; on a cover, `build` reports the unknown field
and prints the two choices.

## Notes

`[^label]` calls a note, `[^label]: text` defines it. The two are linked
both ways — the call jumps to the body, the body jumps back — and the
number a reader sees is the note's **position**, not the label you wrote,
so you can rename or reorder labels without renumbering anything.

A label is word characters only: letters, digits and `_`, accents and
non-Latin scripts included, but no `-`, no space and no punctuation.
`[^kwh]` and `[^clé]` are notes; `[^a-b]`, `[^note 2]` and `[^réf.]` are
not, and are not errors either — the call ships to the reader as literal
text and the body renders as an ordinary paragraph with the label
showing. `audit` names both; `build` says nothing.

Notes work on **any slide**, not only inside a `full-article`. A standard
card can carry one.

Two fields decide how they are presented. Both cascade the same way —
built-in default, then `series_meta` in `series.json`, then the article's
own meta block — so a series can set a house style and one article can
still depart from it:

| Field | Values | Default | Effect |
|---|---|---|---|
| `notes_placement` | `local`, `page` | `local` | `local` collects each note at the foot of the unit that called it. `page` gathers every note of the article into one notes section at the end. |
| `notes_tooltip` | `on`, `off` | `off` | `on` also puts the note's text in the call's `title`, so a pointer reveals it without leaving the line. |

```
<!-- lwp:meta -->
page_title: …
notes_placement: page
notes_tooltip: on
```

Which to choose is an editorial decision, not a cosmetic one: `local`
keeps the apparatus beside the claim it supports and suits cards read one
at a time; `page` reads like a printed article's endnotes and suits a
long argument the reader takes in as a whole.

## Language & typography

Built-in French and English packs (typography rules — non-breaking
spaces, etc. — plus every UI string: nav button tooltips, "copy link",
series navigation labels). Both live in the executable and
are read from there. `--lang fr|en` picks the build-wide fallback; a
`language/{lang}.json` file in your series overrides just the keys you
care about, falling back to the built-in pack for the rest —
`template write fr.json` gives you the built-in one to start from. `series_meta.lang_tags`
maps slide tags to packs so typography can change per slide, for example
`{"fr": "fr", "en": "en"}`. The first mapped language tag on a slide wins;
slides with no mapped language tag use `--lang`. English is the ultimate
fallback for any language without a pack.

The French pack automatically upgrades an existing space to a
non-breaking one before `; : ! ?` and a closing `»`, after an opening
`«`, before `%`, around the spaced em/en dashes of an incise, between
thousands-grouped digits (`170 000`, only if the source already spaces it
out), between a number and `million(s)`/`milliard(s)`/`dollar(s)`/`$`, and
after `×`/`≈` before a number — it never inserts spacing or digit
grouping that wasn't already there, and a non-breaking space already in
your source always passes through unchanged. The English pack carries its
own smaller rule set (metric units, unit words, initials, `×`/`≈`, the
two dash rules). This alters generated
content, so it's controllable at three levels: per-article meta fields
`typo_units: off` / `typo_thousands: off` (just those rules) or `typo:
off` (every rule, that article's page only), and the CLI flag
`--no-typography` on `build`/`verify` (every rule, the whole run). See
`--help` or specifications.md §4.5/§7.5/§19.6 for the full list.

## Theming & customization

Every visual decision is a **typed property**, `component.axis: value`.
`templates/settings.conf`, written once by `init`, lists **all** of
them commented out at your theme's values — the complete surface under
your eyes, no docs needed (the exact count is derived from the tool's
own registry; `--help` shows it live). Uncomment a line to pin it: it
survives every theme change and every executable upgrade, because the
tool never writes in your file. The stylesheet itself is composed in
memory at every build; a mistyped key or value is a named build error,
never a silent no-op. Three one-liners:

```conf
verdict.partial.fg: #8A4B00   # recolor one verdict — footnote calls and note markers don't move
summary.fg: #10151B           # darken card summaries — the "no" verdict stays put
link.decoration-color: mark   # tint link underlines — the text itself keeps the ink around it
```

Rules, as opposed to values, go in `templates/custom.css` — full CSS,
appended last so it wins ties. Effects are properties too: a halo is a
shadow with no offset, which is how the `terminal` theme gets its
phosphor glow (`title1.shadow.fg: #33FF8866`) on an all-monospace page —
three font lines and a halo in its theme layer, no special case in the
engine. Every component that paints its own glyphs carries the four halo axes
(`fg`, `blur`, `dx`, `dy`) — a container does not, because
`text-shadow` is inherited and a halo on a box reaches everything
inside it. That inheritance is also why an
inherited one resolves its `em` once at the root: it can tint a whole
site at a stroke, but it cannot be proportional to the glyph. Only a
component's own can. Depth is a property too: every component the sheet
lifts off the page — the fact box, index cards, series links,
navigation buttons, the slide counter and the four overlays — carries
five elevation axes (`fg`, `blur`, `dx`, `dy`, `spread`), with a second
set under the pointer for the three that lift when you point at them.
So a dark theme can tune a shadow that was black at an opacity chosen
against a white page. The
page/index HTML structure itself is fixed, not a template,
so a build can't be broken by a malformed structural override.

Dozens of colour themes are preconfigured. Some borrow known editor
palettes (Nord, Dracula, Solarized, Gruvbox, Catppuccin, Tokyo Night,
Monokai, Everforest, Rosé Pine); the rest are the project's own —
high-contrast and monochrome sets, skies at three hours, firelight, earth
and stone, and a Pop family whose backgrounds carry the colour
themselves. Every palette is measured and the measurement is published, so you can
see what a theme does before you pick it. There is no bar a palette has
to clear to be in the catalogue: a theme is a stance, and the ones with
the most character are the ones a threshold would flatten. The borrowed
palettes ship as their editors drew them, for **fidelity**; some of them —
Dracula, Tokyo Night, Monokai, Everforest — have since been returned to
the dark grounds they were made for. A theme's family — `desk`, `light`,
`terrain`, `heat`, `pop`, `ported` — states editorial intent, not a
colour-correction strategy.

That is far too many to pick from a list, so themes are found by facet —
**family**, the one facet a theme declares, against a closed vocabulary;
**polarity** (light or dark background); and **hue**, computed from the
background in CIELAB rather than declared, so neither can drift when a
colour is tweaked:

```bash
./lightwebpres theme list                                    # the whole catalogue, with its facets
./lightwebpres theme list --family terrain                   # one editorial family
./lightwebpres theme list --polarity dark --hue green       # just the ones you mean
```

Apply one when scaffolding, or change your mind later:

```bash
./lightwebpres init my-series --theme evergreen
./lightwebpres series theme set my-series --theme crimson
```

To read one out before committing to it — its palette, its fonts, its
facets, and the contrast level it actually reaches:

```bash
./lightwebpres theme show evergreen        # the theme as shipped
./lightwebpres theme show my-series        # the effective theme of a series
./lightwebpres theme show evergreen --format json
```

The level is **measured**, never declared: it is computed from the same
resolved properties the build emits, on grounds composited the way a
browser composites them, so it cannot claim something the palette does
not do. It comes per WCAG category rather than as a single letter — a
theme can score high on running text and low on its focus rings — and
each category is printed with the pairs behind it and their ratios,
because a number without its counter-examples is not something you can
act on.

Read it as a **design note about that theme**, not as a grade. Nothing in
this tool expects a theme to reach any level: `terminal`'s phosphor halo
measures what it measures, and lifting it would destroy the theme. No
palette value is ever rewritten, no theme is refused, reordered or hidden
for what it measures. The number is put in front of the person choosing,
and the choice is theirs.
One thing is not a matter of taste, though, and `audit` says so: a
composed stylesheet where a navigation control is invisible against its
own rail, where text is painted the colour of its ground, or where a size
falls under the readability floor. Those thresholds sit below everything
the shipped catalogue measures, so no theme as delivered can trip them —
they only fire on something worse than anything this project ships. And
they warn: `build` still exits 0, and so does plain `audit`.

The two targets answer different questions, and the difference is the
point: a series that pins three colors in `settings.conf` may have
dropped below the floor without anyone noticing, and the directory form
is what shows the whole picture, category by category. `audit` looks at
the same resolved sheet without being asked, but it only speaks when
something is broken outright. (`custom.css` is free CSS, outside the typed
surface, so it is not measured — the output says so when the file has
rules in it.)

None of this ever reaches a built page. No kicker, no class, no mention: the
reader of a presentation is never told the contrast level of the theme
chosen for them.

`series theme set` is one word in a data file: it rewrites the `theme:` line of
`templates/settings.conf` and nothing else, reports what it replaced
(`Theme changed: evergreen -> crimson`), and your pinned values stay in
place and apply on top of the new palette. No CSS is rewritten, so there
is nothing to force and no half-recolored file to fear.

A theme provides seven shared colors and four font stacks —
`color.page`, `color.ink`, `color.ink-quiet`, `color.mark`,
`color.call`, `color.affirm`, `color.nav`;
`font.text`/`display`/`ui`/`mono` — named for what they do, not for a
color. Every component property *defaults* to one of them,
so a theme restyles everything at once; but each use is its own
property, so overriding one sense never drags the others along (the
`verdict.partial.fg` line above moves the "partly" verdict and nothing
else, even though its default shares `color.call` with footnote calls
and note markers).

`color.nav` is the odd one out, and deliberately so: it paints the
hardware that moves you through a series — the active progress dot, the
two focus rings, the rule under a series-nav card — and nothing you
write. The other six carry editorial constraints (`color.mark` has to
stay pale enough to read *through*, like a highlighter), which the
navigation furniture kept inheriting and could not satisfy. Giving it
its own role is what let forty-one per-theme pins disappear.

A body link deliberately has no palette colour of its own. It keeps the
ink around it and is signalled by an underline, whose tint is the one
exposed axis (`link.decoration-color`, defaulting to the text ink, which
is the strongest thing on the page to point at). An underline is
non-text, so the standard asks 3:1 of it and has no AAA level to ask
for.
Measured across the catalogue before choosing: the browser's default blue
misses AA on well over half of the themes, and every palette colour that
could replace it either falls short on a large part of the catalogue too,
or is already one of the verdict colours.

> **Inherited a series whose `templates/` looks nothing like this?**
> `lightwebpres audit` reads it and names every variable it references
> that the registry does not define, each with the property that carries
> it now; `template update` writes `settings.conf` and `custom.css` if
> they are missing.

![Preview of the built-in color themes](generated/themes-gallery.png)

Above is every theme in the catalogue, each with its palette and the
command that starts a series on it. It is a contact sheet: one panel per
theme, the cover. [`generated/themes-gallery.html`](generated/themes-gallery.html) in this
repository is the full thing — **one theme per row, four panels across:**
the cover, a card carrying a note, the page-wide notes section, and the
long-form article, with the facets as live filters. Open it in a browser.

Every panel, here and there, is a real rendering at its true size — the
same parser, the same engine, the same stylesheet, in an iframe at the
width it claims. Not a mock and not a scaled-down miniature, so a 14px
note is 14px there too.
It's generated straight from the tool's own `THEMES` data with
`./lightwebpres theme gallery`, so it can never drift from what
`init --theme` actually applies.

## One browser-based tool, two tabs

For anyone who'd rather not touch a terminal: `web/index.html` is the
same tool as a page in a tab — pick a series (upload a zip, or connect a
GitLab repository), the page builds it, you get the result back, nothing
to install. It loads the exact same `lightwebpres` executable,
unmodified, running inside [Pyodide](https://pyodide.org) (CPython
compiled to WebAssembly) — one build engine, driven from a terminal or a
tab. It needs to be **served over http(s)**, not opened directly as a
`file://` page — browsers block Pyodide's asset loading under that origin
(see specifications.md §23.6 — if you open it as `file://` anyway, it
shows the exact fix command, with a one-click Copy button, computed from
where you actually put the files).

It also needs its own `vendor/`/`app.py`/`git_sync.py`, plus a copy of
`lightwebpres` itself — never duplicated by default, since it stays the
single source of truth — found in one of two conventional spots relative
to the page, tried in that order: **`./lightwebpres`** (dropped alongside
`web/`'s own contents — the layout for a real site that serves `web/` as
its own URL root, no extra path segment needed) or **`../lightwebpres`**
(the repo's own layout, one level up, for a deployment that's just a
straight copy of the repo). Local testing from the repo: `python3 -m
http.server 8000 --directory /path/to/lightwebpres` (the folder
containing both `lightwebpres` and `web/`), then open
`http://localhost:8000/web/index.html`. Self-hosting on a real web server
(Apache/nginx) can also hit a `.mjs` MIME type issue — see
specifications.md §23.7 for the fix (`web/.htaccess` handles it
automatically on Apache where allowed).

- **Upload a zip** — drop a zip of your series, get back a zip of
  `public/`. Nothing ever leaves the browser tab; Pyodide runs vendored
  locally, not from a CDN.
- **Sync with GitLab** — pull a series straight from a GitLab repository,
  build it, push the result back as a single commit. Talks directly to
  the GitLab instance you configure (no third-party proxy in the request
  path); never deletes a file on push, only creates/updates.

Both tabs share one Pyodide/`lightwebpres` load at page start, so
switching between them is instant — no separate page, no reload.

## Safety

- Fatal validation for every structurally dangerous input: duplicate or
  missing required slides, unsafe file paths in `series.json`/`article:`
  (rejects anything that isn't a plain filename — no directory traversal),
  malformed JSON.
- No page is ever written over another. Two articles resolving to the
  same output name is fatal, and so is an article named `index.html` in a
  series of several articles — that name belongs to the series index,
  which carries the article list. A series of **exactly one** article may
  take it: the article becomes the page the directory serves, no series
  index is generated (a list of one adds nothing), and `build` says so on
  a `[no index]` line.
- Typography rules are applied to already-assembled HTML but can never
  touch tag syntax — text and markup are split before any rule runs.
- Every generated page is checked for HTML tag balance before being
  written; a rendering bug never silently ships a broken page.

## Testing

```bash
python3 tests/run_tests.py
```

a black-box test suite exercising the CLI as a subprocess, plus real headless-
Chromium end-to-end tests (via Playwright, skipped cleanly if unavailable)
for both tabs of the browser-based tool.

## Project layout

```
lightwebpres          # the executable — the only thing you need to run this
CHANGELOG.md          # what changed between versions, in the release's own words
specifications.md     # full reference specification (French)
DECISIONS.md          # what has been decided and what has not, on six states
web/                  # the browser-based build tool (upload-a-zip and GitLab-sync tabs)
agent/skills/         # two packaged skills: the article format, and one optional editorial method
AGENTS.md             # the working rules for an agent editing this repository
generated/            # committed build output — regenerated by a command, never edited by hand
tools/                # maintenance scripts and their inputs: the guide deck, the gallery snapshot
docs/                 # dated audits: measurements with their conditions, kept as records
tests/                # regression suite
delete-before-1.0/    # out of the active tree, kept readable until 1.0 — what its name says
```

## Reference

| Document | What it is |
|---|---|
| [`GUIDE.md`](GUIDE.md) | **Start here.** The walkthrough, in English: init, build, choose a look, write, verify, ship |
| [`GLOSSARY.md`](GLOSSARY.md) | Every field, its default, and where it falls back from |
| [`agent/skills/lightwebpres/SKILL.md`](agent/skills/lightwebpres/SKILL.md) | The exact article format — written for an agent, readable by a person |
| [`agent/skills/sourced-presentation/SKILL.md`](agent/skills/sourced-presentation/SKILL.md) | One method the format suits — a sourced deck backed by a fully referenced article. Optional: nothing here is required to use LightWebPres |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed between versions. The entry under a version IS the body of that version's release, written once — not a second telling of it |
| [`DECISIONS.md`](DECISIONS.md) | What has been decided and what has not, on six states — with the measurement behind each |


`specifications.md` is the complete, detailed specification (in French) —
directory layout, `series.json` schema, parser edge cases, full
placeholder reference, and more.

## License

GNU General Public License v3 or later (`COPYING`), **with the LightWebPres
Output Exception** (`COPYING.EXCEPTION`).

In plain terms:

- **What you make with this tool is yours.** The series it scaffolds and the
  pages it builds — including the templates, stylesheets and scripts it
  writes into them — are covered by the Exception: publish them under any
  terms you like, commercially or not. Nothing in the GPL reaches your
  presentations. The Exception exists precisely because the tool copies
  parts of itself into its output, and that copying should cost you nothing.
- **The tool itself is copyleft.** Improve it and distribute your version,
  and your improvements ship with it. One caveat worth knowing: `init`
  places a copy of the executable in your series directory, and that copy
  is the program, not output — publish your series repository and you are
  distributing GPL code. That is why `init` writes `COPYING` and
  `COPYING.EXCEPTION` beside it for you.

Third-party code inside the executable is listed in
`THIRD-PARTY-NOTICES.md`. `web/vendor/pyodide/` is vendored under the
Mozilla Public License 2.0 — see `web/vendor/NOTICE.md`.

**The name.** "LightWebPres" identifies this project. The licenses above
cover the code, not the name: fork it freely, but don't present a modified
version as being this project.

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
python lightwebpres init my-series
```

If that's not found, try the `py` launcher (bundled with most Windows
Python installs):

```powershell
py lightwebpres init my-series
```

**`python3: command not found`**
Some systems only have `python` on `PATH`, not `python3` (common on
Windows, occasionally macOS). Use `python` instead of `python3` in any
command above that invokes it explicitly — e.g. `python -m http.server`
when serving the [browser-based tool](#one-browser-based-tool-two-tabs).
