# LightWebPres — Guide

This is the map of the tool: init it, see what a page is made of, wire
a series, adjust the look, ship it. For what each command *exactly* does
in every edge case, see `specifications.md`; for the precise article
syntax, see `agent/skills/lightwebpres/SKILL.md`. This guide is the path
through all of it in the order you'll actually need it.

**What this guide does not do is teach you to write.** LightWebPres is
for people who already know how; it renders what you give it. Nothing
here says what makes a good card, how to structure an argument or when a
claim needs a source. A second skill, `sourced-presentation`, ships
alongside as a courtesy for people who would like a method — an offered
interface, not the core of what this does. Take it or leave it:
[section 11](#11-going-further).

## 1. What LightWebPres is

LightWebPres turns an extended Markdown format into self-contained,
scrollable HTML articles — a cover, a handful of fact-card slides, an
optional long-form piece, cross-article navigation — with zero runtime
dependencies. One executable, `lightwebpres`, does the whole job:
scaffold a project, generate demo content, build, verify, and keep
templates current.

**Three ways it gets used, and the tool does not care which.**

- **A person at a terminal**, which is how this guide is written.
- **An agent**, given the packaged skill (`SKILL.md`, in
  `agent/skills/lightwebpres/`) that carries the article format. Point it
  there and it can write the Markdown and run the build from minute one.
- **A step in a content pipeline**, where the Markdown comes from
  somewhere else entirely — a CMS export, a database, a generator, an
  agent upstream — and LightWebPres is what turns it into publishable
  pages.

The third is not an afterthought; the tool is shaped for it. **Every
command runs unattended** — nothing ever blocks on an interactive prompt.
**Every command has a meaningful exit code**: `verify` exits non-zero the
moment the built output differs from the sources, which is a real gate;
`audit --strict` exits non-zero on anything worth reporting — two gates,
two questions. Plain `audit` never fails, whatever it finds: it reports
and gets out of the way. **There is nothing to
install**: one file, nothing beyond the Python standard library,
no wheel, no lockfile, no network at build time — any image with
`python3` in it can run it. And **every path is an environment
variable** (`LWP_SERIES_DIR`, `LWP_ARTICLES_DIR`, `LWP_OUTPUT_DIR`,
`LWP_TEMPLATES_DIR`, `LWP_LANGUAGE_DIR`, `LWP_LANG`), so a pipeline can
lay the pieces out however it likes without passing a single flag.

**Every page is also a presentation deck.** Open the generated HTML in a
browser and you have a full-screen presenter experience: keyboard (↑/↓,
Home, F for fullscreen, B/W/T for pause screens), mouse (click to
advance, right-click to go back, double-click for fullscreen, middle-click
to exit), and touch (swipe) all work out of the box. The navigation
buttons fade after 3 seconds of idleness (1 second in fullscreen) — the
speaker sees only slides. The cursor hides on that same clock, and
neither comes back until the mouse has moved continuously for 250 ms — a
brush past the sensor flashes nothing back onto the wall. The scroll bar
counts as navigation and follows the same state: it fades to transparent
rather than being removed, so nothing on the page moves. Entering or
leaving fullscreen, and clicking in the button corner, reveal the chrome
at once: those are deliberate gestures, not stray movement. The mouse becomes
a remote: left-click advances, right-click goes back, two distinct
buttons, no aiming. Fullscreen also neutralizes the OS power-saving so the
screen never dims mid-talk.

Section 8 has the shape of a pipeline that uses all of it.

## 2. Set up & your first build

```bash
./lightwebpres init my-series
./lightwebpres demo my-series --lang en      # French by default
./lightwebpres build my-series --lang en
xdg-open my-series/public/index.html         # `open` on macOS
```

`init` scaffolds a working project — `articles/` (empty, for your `.md`
files), `templates/` (your customization surface: `settings.conf` and
`custom.css`, see section 5), an empty `language/`, an empty `public/`
for the build to write into, a starter `series.json`, and a copy of the
`lightwebpres` executable itself with its `COPYING` and
`COPYING.EXCEPTION` beside it, so the project directory is self-sufficient
and the copy travels with its licence.

What it does *not* scaffold is the tool's own files — the navigation
script and the typography/interface language packs. Those live inside the
executable and are read from there, so a fix in a new version reaches
your series the moment you upgrade. You can still have them: `template
show nav.js` prints one, `template write nav.js` installs one to modify
(section 7).

**Language is chosen per build, not stored in the project** — both packs
are always inside the executable. Pass `--lang fr|en` to `build`/`demo`, or set
`LWP_LANG`. French is the default, which is why the commands above say
so explicitly.

`demo` only works after `init` and refuses to overwrite existing
work. It drops three example articles (first, middle and last position in
the navigation) plus a captioned image, so you have something real to
look at before writing your own.

`build` reads `series.json` and every article it lists, and writes
`public/*.html` plus `public/index.html`. A generated `README.md` lands
beside `series.json`, at the root of the series rather than in `public/`
— it describes the series to whoever opens the repository, not to
whoever visits the site.
Open `public/index.html` in a browser — no server needed, every page is a
single self-contained file.

`--inline-images` embeds images as base64 data URIs so the HTML needs
no `img/` directory at all — useful for emailing a single file or
hosting where only static HTML is served. The HTML grows about a third
per image; a serving gzip recovers the overhead. It covers images in a
card and images in a file a `full-article` card pulls in, alike.

One thing it cannot inline: an `<img>` you write as raw HTML rather than
in Markdown. The converter passes raw HTML through untouched by design,
so such an image would keep a relative path to a directory this option
does not create. The build refuses rather than shipping a page with a
dangling reference, and names the file and the path.

`build` also accepts a handful of switches that change what it writes:
`--no-index` (skip `index.html`), `--no-readme` (skip the generated
`README.md`), `--no-nav` (omit the cross-article navigation block),
`--drafts-only` (build only `status: draft` articles), `--open` (open the
result in the browser), and `--slides-page-numbers on` to engrave the
top-right `NN / NN` slide number — **off by default** (the article
front-matter `slide_page_numbers` and `series_meta.slide_page_numbers`
also turn it on; see specifications.md §3.3.5). `watch` takes the same
output switches and adds `--serve` (opt-in HTTP server on `127.0.0.1`,
`--port 8000`).

## 3. What a page is made of

A page is a sequence of **slides**, separated by `---`, preceded by one
metadata block. There are four slide types, and inside a standard slide a
small set of named components. This section names them and says how you
reach each one; `agent/skills/lightwebpres/SKILL.md` carries the exact
syntax and every edge case.

**The four slide types.**

| Type | Carries | How many |
|---|---|---|
| `cover` | `kicker`, `tags:`, `# Title`, `summary`, `comment`, `note` | any number, anywhere — it is a look, not a structural marker |
| standard *(the default)* | `kicker`, `tags:`, `## Title`, `summary`, `highlight`, `highlight-caption`, `fact-label`, `fact-variant`, `source`, `comment`, `note`, then free Markdown | as many as you want |
| `series-nav` | `tags:`, `comment:` — the navigation itself is generated from `series.json` | 0 or 1 per article |
| `full-article` | `article: filename.md`, optional `tags:` and `comment:` | any number, each with its own file |

Four, and only four. Mistype one — `<!-- lwp:slide:covre -->` — and the
build stops and tells you which slide, what you wrote, and what the four
names are. You will not find out from the page.

**The components inside a standard slide.**

| Component | What it is for | How you reach it |
|---|---|---|
| **fact box** | the slide's claim, set off from the page | free Markdown text after a `fact-label:` line |
| **key figure** | one number that carries the slide | `highlight:` (+ optional `highlight-caption:`) |
| **source** | where the claim comes from | `source:` |
| **comparison table** | a grid of verdicts read at a glance | a Markdown table; cells take `yes` / `no` / `partial` classes via inline HTML |
| **figure** | a captioned image | `![alt](img/x.png "Caption")` alone on its line |
| **headings** | structure within the fact-box body | `#` `##` `###` `####` `#####` `######` — up to level 6; `#`–`###` are true headings, `####` renders as a bold-font paragraph (not `<strong>` emphasis), `#####`/`######` as plain paragraphs |
| **quote, code, list** | ordinary prose furniture | ordinary Markdown |
| **note** | a reference the reader can reach | `[^label]` in the text, `[^label]: body` on its own line |
| **long-form article** | the piece the cards summarise | a `full-article` slide pointing at a second `.md` file |

Two things are worth knowing before you write, because they surprise
people:

- **The switch from fields to free text is one-way, within a slide.**
  Once a line is not a `field:` line, everything after it is prose — so a
  `highlight:` placed after a paragraph is published as the literal text
  `highlight: 3 000 W`. Fields first, prose after.
- Structural fields occupy one physical line, except `note:` and `comment:`:
  an indented continuation line belongs to the preceding note/review field.
- **A field is a value, not Markdown.** `summary: un **gras**` publishes
  the asterisks. The border is not where you would guess, either: a field
  passes raw HTML straight through, so finding that `<br>` works there
  says nothing about `**`. `audit` names any field carrying markup it will
  not render — a check that exists because 32 such fields, `source:` lines
  among them, once accumulated unnoticed across one series.
- **A fact box appears only with `fact-label:`.** Free text without it
  renders as plain paragraphs — which is often what you want.

**Notes.** `[^label]` calls a note, `[^label]: text` on its own line is
its body. The label is a key, and a valid one is never displayed — the
reader sees a position — so you never renumber when you insert one. Valid
means word characters only: letters, digits and `_`, accents and
non-Latin scripts included, but no `-`, no space, no punctuation. A label
outside that is neither a note nor an error: the call ships as literal
text, the body renders as an ordinary paragraph, and the label is the one
thing on the page the reader was never meant to see. By default a body
lands at the foot of the unit that called it (the card, or the end of the
long-form article) and numbering restarts in each card, because a card is
shareable on its own and a reader may arrive at it having read nothing
else. `notes_placement: page` in the meta block instead collects every
body into one notes section at the end of the page; `notes_tooltip: on`
additionally puts the text on the call. `audit` names a label outside the
pattern, a call with no body, a body nothing calls, and a body written
inside a raw HTML block (where it ships as literal text).

Register every article that should appear in navigation in
`series.json` — next section.

### Variants in one article

`tags:` is a slide header field, not an instance styling tag. Its value is a
space-separated list of case-insensitive variant names. Unicode letters,
digits, `-`, and `_` are allowed, except that a name cannot start with `_`.
The field is one physical line, like every structural field.

- No `tags:` (or an empty value) means `default`, the shared content.
- `tags: excluded` removes the slide during the build; it is never emitted.
- Other tags are written to the section's `data-tags` attribute and filtered
  in the browser.
- Press **L** to open the variant menu. It is hidden for a single-variant
  article and persists the choice in `localStorage['lwp-active-tag']`.
- The selected tag shows its own slides and shared `default` slides; counts,
  navigation, anchors, and the presenter panel use the visible slides.

`tag:` is not a field, and not an alias for one. Use `kicker:` for the label
above a slide title, and `tags:` for variant filtering. A `tag:` line becomes
body text on a standard slide; on a cover, `build` reports the unknown field
and prints the two choices.

For language-specific typography, map tags to packs in `series_meta`:

```json
{
  "series_meta": {
    "lang_tags": {"fr": "fr", "en": "en"}
  },
  "articles": [{"page_source": "guide.md"}]
}
```

The first mapped language tag on a slide selects its pack. A slide without a
mapped language tag uses the build's `--lang`/`LWP_LANG` fallback. The built-in
`fr` and `en` packs come from the executable; another pack name refers to
`language/<name>.json` in your series. `audit` reports invalid tags and missing packs without
blocking, while `build` rejects malformed declarations.

## 4. Organizing a series

`series.json` lists the articles and holds series-wide metadata:

```json
{
  "series_meta": {
    "title": "My article series",
    "subtitle": "Series subtitle",
    "intro": "Series introduction.",
    "lang_tags": {"fr": "fr", "en": "en"}
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
the final say. `status` says what each article is worth to the series:
`active` (the default), `draft` — still an article of the series, kept
out of the output until `--include-drafts` previews it with a banner — or
`ignored`, which takes it out of the chain entirely without deleting the
entry and everything you configured on it. The array order is the
navigation and index order. The full fallback chain per field is in
`GLOSSARY.md`.

## 5. Adjusting the look

Four gestures, from the smallest to the largest. Pick the smallest one
that does the job.

### Pick a theme (the whole series)

Dozens of colour themes are preconfigured — too many to pick from a list,
so you find one by facet: which family it belongs to, whether its
background is light or dark, and what hue that background carries.

```bash
./lightwebpres theme list                                     # the whole catalogue, with facets
./lightwebpres theme list --family terrain                    # one editorial family
./lightwebpres theme list --polarity dark --hue green          # just the ones you mean
./lightwebpres theme gallery                             # every theme, rendered
```

Apply one at init time, or change your mind later:

```bash
./lightwebpres init my-series --theme evergreen
./lightwebpres series theme set my-series --theme crimson
```

A theme is a word in a data file: `series theme set` rewrites the one `theme:`
line of `templates/settings.conf` and nothing else. No CSS is touched —
the stylesheet is composed in memory at every build.

These commands inspect and select existing theme values. They do not design,
retune or repair a palette. Use `theme show` to read the measured contrast of
the shipped theme, or of the effective theme after the series' pins. `audit`
reads the same resolved sheet without being asked, and speaks only when
something has stopped working — a navigation control you cannot see, text the
colour of its own ground, a size under the readability floor. It warns; it
never refuses, and no shipped theme trips it.

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

Two properties control the fact-box bold (`**text**` in a fact-box):

- `fact.strong.pad` — the side padding of the highlight box around the
  bold text (default `max(3px, 0.375vmin)`, automatically 0 on themes
  with no highlight ground).
- `fact.strong.absorb-punct` — `on` (default) absorbs the punctuation
  that follows a bold run into the highlight (`**2000**,` → the comma is
  highlighted too); `off` leaves the Markdown as written.

```
# kicker.fg: ink-quiet      ← the scaffold, showing the theme's value
kicker.fg: call             ← uncommented: yours, and it stays
```

A bare word like `call` is looked up among the theme's shared values
(`color.call`, since `fg` is a colour axis); a literal like `#8A4B00`
works anywhere a colour does. A mistyped key or value is a named build
error pointing at the file and key.

Three properties people look for by name: **`page.content-max`** is the
text column width, `84vw` by default — proportional to the window, with
no ceiling, so a deck shown full screen uses the screen. Every type size
is proportional too — the kicker, the fact label, the key figure's caption
and the slide number as much as the title — which is what keeps the line
length steady and the proportions between them fixed as the screen
grows. Each size has a floor in pixels, and the floor is what governs a
phone. **`page.block-max`** is the width of the things that are not
running text — a table, a code block, a figure — sized by what they hold
rather than by a count of characters; it carries a floor as well as a
ceiling — `min(84vw, max(1100px, 102vmin))` — so a table grows with the
text inside it and still stops before the window edge.
**`page.hyphens`**
(`manual | auto`) controls whether words break at end of line; it is
`manual`, and nothing turns it on for you.

After a `series theme set`, `audit` will note that the scaffold's *comments*
show the old theme's values; `template update --scaffold` realigns them
while keeping every pinned line.

### Rules rather than values (`templates/custom.css`)

Full CSS, no subset, appended after the composed stylesheet so your rules
win ties. `init` creates it strictly empty, because "appended" means
appended verbatim: anything the tool wrote in there as advice to you
would be published to every reader of every page. `settings.conf` can
carry five hundred comment lines precisely because it is parsed and this
file is not. New selectors, media queries, `@font-face` (name the family at
the head of a stack in `settings.conf`, declare the face here). The
composed sheet's `--component-axis` variables are usable in it
(`border-color: var(--color-mark)`), and that is the recommended way to
follow the theme.

Behaviour is the third surface, and it isn't in your series by default:
the navigation script lives in the executable. `template write nav.js`
puts a copy under `templates/` if you want to change it, and it then
overrides the navigation wholesale — there is no partial override. The
page and index HTML structure is fixed, not a template.

## 6. Verifying before you ship

Two different checks, for two different moments:

```bash
./lightwebpres audit my-series    # is anything wrong with this series?
./lightwebpres verify my-series   # is public/ the one these sources make?
```

`audit` renders the whole series in memory — throwing the HTML away,
writing nothing — and reports three different kinds of thing. What the
**sources** say: no cover slide, the instance tags in each article, a
scaffold whose comments predate your current theme, a retired CSS
variable still referenced in `custom.css`, an image symlink that would
not be published. What the **resolved stylesheet** says once the theme,
your `settings.conf` and a page's own `style.*` lines are merged — a
navigation control nobody can see against its own rail, text painted the
colour of the ground it sits on, a size under the readability floor. That
one is worth its own sentence: those faults are correct at every layer
and only exist once composed, so nothing that reads what you *wrote* can
find them; a size you never touched can go invisible because a colour it
inherits from did.

Nothing is filtered out of any of that. `audit` looks at every article
`series.json` lists — drafts included, and `ignored` ones named on a
`[NOTE]` line, since this is the only place in the tool that will ever
mention them again. A build's `--include-drafts` has no counterpart here
and needs none: work in progress is exactly what an authoring tool should
be looking at, and a fault that only shows once a page is composed is no
less real on a draft. And what only **composing** can say: a missing
language pack, fields you wrote on a cover that a cover never renders —
and, when the render cannot finish at all, the fact that no page would be
produced. It still never fails on its own: exit 0 every time, even then.
Pass `--strict` and every one of those becomes a non-zero exit; that is
the CI gate. Because it renders, it costs about what a build costs — the
deliberate trade: a build is fast on a human scale, a missed audit is
not. `--templates` skips the render and the per-article checks when you
only want the presentation layer; the stylesheet is still judged.

`verify` asks the other question: it rebuilds every article in memory and
compares it byte-for-byte against `public/`, exiting non-zero the moment
anything differs — wire it in before `build` to catch a `public/` that
was hand-edited or never rebuilt after a source change.

### Asking why a value is what it is

Most of what ends up on a page was never written on that page: a title
falls back through `series.json`, the meta block and the cover slide, a
colour falls through `settings.conf`, the theme and the built-in
defaults. When the result surprises you, ask:

```bash
./lightwebpres resolve my-series page_title --article apple-pie.md
./lightwebpres resolve my-series kicker.fg
```

Nothing tells it what kind of name you passed — the name does. A dot
means a theme property, an underscore an article or series field, a
hyphen a slide field.

The answer shows the level that decided **and every level that didn't**,
strongest first:

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

That second half is the one that solves problems. A line you wrote that
changed nothing shows up here as a level holding nothing — still
commented out, or beaten by a `series.json` entry you had forgotten.

A slide field has no cascade, so `resolve fact-label` answers with the
list of slides that set it instead — across the series, or within one
article with `--article`. Add `--format json` for a machine, and pass
`--article` to a theme property to fold that page's own `style.*` lines
into the chain.

## 7. Keeping templates current

`lightwebpres` is a single file you copy into each project (`init` does
this). Dropping in a newer copy is the whole upgrade: the stylesheet is
composed in memory at every build, the navigation script and the language
packs are read out of the executable, and your `settings.conf` and
`custom.css` are yours — never touched. Your theme choice needs no
reapplying either: it's the `theme:` line of `settings.conf`, which an
upgrade cannot revert.

That leaves one thing an upgrade cannot reach: a copy of a tool-owned
file sitting in your series. `template write` puts one there, and a
series scaffolded before v0.40.0 was given three without being asked.
Such a copy is used in preference to the executable's own, so it keeps
whatever behaviour it was frozen with — and a build warns when it differs
from the built-in version, at warning level, so `--quiet` doesn't silence
it in a pipeline. The build can't tell *stale* from *customised*, so it
says `differs` and uses your file either way.

```bash
./lightwebpres template update my-series
```

That is the command that clears them. A copy identical to the built-in
one is removed — it was doing nothing but freezing you. A `nav.js` that
differs is saved as `nav.js.bak` and removed, so you keep your version
and the build follows the tool again. A language pack that differs is
left alone and reported: its `rules` replace the base set wholesale, so
overwriting it would erase whatever you added — compare with `template
show fr.json` and delete it when you're ready. A pack for a language the
tool doesn't ship — `de.json`, say — is your work, and nothing is said
about it.

`--scaffold` additionally regenerates `settings.conf`'s commented block
against the current theme and the current property registry, keeping
every line you uncommented.

## 8. Automation, CI/CD, and the browser

### As a pipeline step

The generated `.gitlab-ci.yml` (`init --gitlab-ci`, opt-in — a plain
`init` never assumes a deployment) is one stage and one command:

```yaml
stages:
  - build

build:
  stage: build
  image: python:3.12-slim
  script:
    - python3 lightwebpres build . --lang fr
  artifacts:
    paths:
      - public/
```

Nothing here is GitLab-specific — that one command is the whole job on
any runner.

If your `public/` is committed rather than built from scratch, put
`verify` in front of `build`:

```yaml
  script:
    - python3 lightwebpres verify .    # fails if public/ is stale
    - python3 lightwebpres build . --lang fr
```

That ordering catches a `public/` that was hand-edited or never rebuilt
after a source change, **before** the build overwrites the evidence. It
is left out of the generated file because a pipeline that builds into a
fresh checkout has nothing stale to catch, and a job that fails on its
first run teaches the reader to delete the line rather than to trust it.

For a pipeline where content arrives from upstream, three more things
matter. `--only page` rebuilds a single article rather than the series,
with `--nav-cache` holding the fingerprint that tells it whether the
navigation still needs regenerating. `--build-stamp` marks every
generated page with the version and time it came from, which is what you
want when a page is published by a machine and questioned by a human
three months later. And `status` in `series.json` decides what enters the
build at all: `draft` until something upstream flips it, `ignored` for an
article you want kept and not published.

### In the browser

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

## 9. Presenting

Every page the build writes is a self-contained deck — keyboard, mouse,
and touch all work. The controls below let the speaker drive the deck
without looking at the screen.

### Keyboard

| Key | Action |
|---|---|
| ↓ / PageDown / → | Next slide |
| ↑ / PageUp / ← / Backspace | Previous slide |
| Home | Back to the index |
| F | Fullscreen (Esc to exit) |
| B | Black pause screen (press again to dismiss) |
| W | White pause screen (press again to dismiss) |
| T | Theme-background pause screen (press again to dismiss) |
| N | Toggle the speaker panel: the current slide's notes and the next slide's title |
| 0–9 then Enter | Jump straight to slide N (1-based) — for decks of ten slides and up |
| L | Open the variant menu when the article carries at least two tags across its slides |
| H | Open the help overlay, which lists every key on this table |
| Esc | Leave fullscreen; also closes the speaker panel |

The B/W/T pause screens hide the slide so the audience's eye comes back
to the speaker — the same feature PowerPoint and Keynote call "blank".
T uses the theme's own background colour, so a dark theme pauses on a
dark screen rather than flashing white.

### Speaker panel and slide counter

A small `X / N` counter sits in the bottom-left corner and fades out with
the other chrome when the mouse is idle. Type a slide number and press
**Enter** to jump there — handy once a deck passes ten slides and the
arrow-key walk becomes a slog. That live counter is **always** shown and
is independent of the engraved top-right `NN / NN` slide number, which is
opt-in (off by default) and turned on only by `--slides-page-numbers on`,
the article front-matter `slide_page_numbers`, or `series_meta.slide_page_numbers`
(see specifications.md §3.3.5). Press **N** to open the speaker panel: it
shows the current slide's `note:` field (the speaker note you wrote for
that slide — see below) and the title of the next slide, so you can read
ahead without the audience seeing it. The panel rides along as you
navigate; press **N** again to close it.

A speaker note is a `note:` field on the slide — distinct from a `[^n]`
footnote, which is a *source* note printed for the reader:

```markdown
<!-- lwp:slide -->
kicker: Two
## Slide two
note: Mention the 2020 study — the audience asked for it last time.
  Follow up with the 2023 replication.
  If time runs short, skip the appendix.
```

The `note:` value is parsed and withheld from the slide the reader sees;
only the presenter panel surfaces it. A `note:` may run over several lines:
any line that starts with whitespace continues the note, and an indented
blank line marks a paragraph break. The block ends at the first
non-indented, non-empty line (the next field or the slide's body), so the
continuation lines are never captured as slide content.

### Printing and PDF

Each page is print-ready. **Print** from the browser (Ctrl/Cmd+P) and
choose "Save as PDF": every slide lands on its own sheet, the navigation
chrome is stripped, and the theme colours are kept. A short slide no
longer blanks a page — each sheet sizes to its own content.

### Mouse

| Gesto | Action |
|---|---|
| Single click on content | Next slide |
| Right-click on content | Previous slide |
| Double-click on content | Enter fullscreen |
| Middle-click anywhere | Exit fullscreen (if in fullscreen) |
| Click in the bottom-right corner | Toggle the navigation buttons (hide/show) |

Clicks on links, images, buttons, and the share popover are not
intercepted — they keep working. The right-click to go back is the
remote-mouse use case: the speaker with a wireless mouse in hand
left-clicks to advance, right-clicks to go back — two distinct buttons,
no aiming. The native context menu is suppressed on slide content so
right-click is a clean back gesture. Double-click enters fullscreen
(the 250ms delay on the first click is the cost of detecting it);
middle-click exits fullscreen (entering via middle-click is not
possible on Firefox, which blocks requestFullscreen from non-left
clicks — use double-click, the ⛶ button, or F instead). In fullscreen,
left and right clicks are instant (no double-click to detect anymore).
Esc exits fullscreen. The cursor hides after 1 second of idleness in
fullscreen.

A left-click that lands while the deck is still scrolling from a previous
click cancels the pending double-click timer and advances immediately —
the speaker who clicks again to skip the wait is taken straight to the
next slide without the 250 ms hold.

### Touch (phone, tablet)

| Gesto | Action |
|---|---|
| Swipe left | Next slide |
| Swipe right | Previous slide |
| Tap on content | Next slide |

### Navigation buttons

The round buttons in the bottom-right corner — previous, home, next,
share, fullscreen, and a sixth for the variant menu that appears only
when the article carries at least two tags. After 3 seconds of mouse
idleness they fade out, and the cursor goes with them: the speaker does
not want chrome on the wall. In fullscreen both go after 1 second. Move
the mouse to bring the buttons back; the cursor waits for 250ms of
continuous movement, so a knock against the desk does not put it on the
wall. Touch devices keep the buttons visible (there is no cursor to wake
them). Clicking the corner (not a button) toggles them on or off for
good.

## 10. Shell completion (tab in the terminal)

`lightwebpres completion --shell bash` (or `zsh`) prints a script that
makes your shell complete commands, subcommands, and options when you
press Tab. Install it by adding this line to your `~/.bashrc` or
`~/.zshrc`:

```bash
eval "$(lightwebpres completion --shell bash)"
```

Then `lightwebpres <Tab>` proposes `init`, `build`, `verify`, `audit`,
`theme`, `series`, etc.; `lightwebpres series <Tab>` proposes `build`,
`theme`, `status`, `resolve`...; and `lightwebpres build --<Tab>`
proposes `--lang`, `--output`, `--no-typography`, etc.

The script is generated from the tool's own command tables, so it stays
in sync with whatever commands the version you are running knows about.

## 11. Going further

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

## 12. When something doesn't work

| Symptom | Cause |
|---|---|
| `lightwebpres: command not found` | it isn't on your `PATH` — run it as `./lightwebpres` |
| `Permission denied` | `chmod +x lightwebpres` |
| `… is not empty. Use an empty or new directory, or pass --force` | installing into a directory that already has files — `init . --force` is the normal in-place case |
| the site is in French | `--lang en` on `build`/`demo`; French is the default |
| `open: command not found` | macOS-only — use `xdg-open` on Linux |
| a `field:` line published as literal text | it came after prose in the same slide; the switch to free text is one-way (section 3) |
| `[^1]: …` published as literal text | the body sits inside a raw HTML block, which is passed through verbatim — move it outside |
| a note marker that isn't a link | nothing defines that label in the same locality; `audit` names it |
| a value is not what you wrote | another level of the cascade won — `resolve <name>` shows which, and what every other level held (section 6) |
| a `settings.conf` line that changes nothing | it is probably still commented out; `resolve <property>` shows that level holding nothing |
