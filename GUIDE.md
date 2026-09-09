# LightWebPres — Guide

Choose the route for what you want to do: write a first page, organize a
collection, design its appearance, use a presentation, publish it, or automate
the work. Readers can go straight to route 4 without installing anything;
authors and agents can use the same source files and commands in every route.

1. [Create content](#1-create-content)
2. [Organize a documentary collection](#2-organize-a-documentary-collection)
3. [Design and compose identities](#3-design-and-compose-identities)
4. [Read, present and share](#4-read-present-and-share)
5. [Publish and maintain](#5-publish-and-maintain)
6. [Integrate and automate](#6-integrate-and-automate)

<p align="center">
  <img src="generated/product-responsive.png" alt="The same Nebula content card shown in real landscape and emulated portrait browser viewports" width="100%">
</p>

The same article becomes a landscape presentation and a portrait reading
page. These are Chromium viewports, not photographs of devices. The source
is the first personal article below. For exact syntax use the
[format reference](agent/skills/lightwebpres/SKILL.md); normative contracts
are in [specifications.md](specifications.md) (French).

## 1. Create content

Start with a working example, replace its content, then check what a reader
receives. Use a text editor yourself or ask an agent to edit the same Markdown;
neither path requires a separate authoring format.

### Start with a working site

Download the single `lightwebpres` executable from the
[official repository](https://github.com/Fade78/lightwebpres), or use the copy
in a checkout. You need Python 3.8+ with its standard library, no additional
packages. In the directory containing the executable, run:

```bash
python3 lightwebpres init my-series --lang en
python3 lightwebpres demo my-series --lang en
```

`demo` already builds the site; open `my-series/public/index.html`. Do not run
`build` again until you change something. If you prefer a browser builder,
[route 6](#build-in-the-browser) explains zip and GitLab input; it runs the same
engine, not an alternative format.

Commands in this guide run from the directory containing `lightwebpres` and
`my-series/`. On Windows, use `python lightwebpres` (or `py lightwebpres`).
Examples using `./lightwebpres` assume Unix and `chmod +x lightwebpres`;
`python3 lightwebpres` works without the executable bit.

`init` scaffolds a working project — `sources/` (empty, for your `.md`
files), `templates/` (your customization surface: `settings.conf` and
`custom.css`, plus optional versioned `themes/*.conf`, see route 3), empty
`interface/`, `typography/` and legacy `language/` directories, an empty `public/`
for the build to write into, a starter `series.json`, and a copy of the
`lightwebpres` executable itself with its `COPYING` and
`COPYING.EXCEPTION` beside it, so the project directory is self-sufficient
and the copy travels with its licence.

The navigation script and built-in language packs stay inside the executable
so upgrades reach the series without refreshing local copies. For deliberate
overrides, use `template show`/`template write` (route 5). `init --preset`
can also install an Identity Kit and its declared starter (route 3).

The quickstart uses `--lang en` explicitly. Without it or `LWP_LANG`, the
browser chooses the interface language; typography is already fixed at build
time. [Languages and typography](#set-languages-and-typography) explains the
two layers and custom packs.

`demo` only works after `init` and refuses to overwrite existing
work. It drops three example articles (first, middle and last position in
the navigation) plus a captioned image, so you have something real to
look at before writing your own.

With `demo --dry-run`, the files and build are only journaled as a plan;
the existing on-disk series is not built in place of the planned demo.

`build` reads `series.json` and every article it lists, and writes
`public/*.html` plus `public/index.html`. A generated `README.md` lands
beside `series.json`, at the root of the series rather than in `public/`
— it describes the series to whoever opens the repository, not to
whoever visits the site.
Open the index locally; no server is needed. Referenced images are separate
assets by default. The publication chapter covers single-file delivery,
output switches and cleanup; start by adding your own article below.

<!-- example:first-article -->

### Make your first personal article

Keep the demo as a reference and add one article beside it. The following
small example describes the output files, so it needs no external image or
second Markdown file. Its tracked source also produces this manual's captures:
[examples/first-article/sources/first-page.md](examples/first-article/sources/first-page.md).

#### Create the source

Create `my-series/sources/first-page.md` in your editor with this content:

```markdown
<!-- lwp:meta -->
page_title: My first page
---

<!-- lwp:slide:cover -->
slug: first-page
kicker: Getting started
# My first page
summary: A small site I can read, present and share.

---

<!-- lwp:slide -->
slug: travels-with-the-page
kicker: Portable output
## The runtime travels with the page
summary: Open the HTML without installing LightWebPres.
highlight: 1 HTML
highlight-caption: per article, with CSS and JavaScript inside
fact-label: Keep the assets too

Local images stay beside the page in **img/**.
Publish the whole **public/** directory, not just its index.

---

<!-- lwp:slide:series-nav -->
slug: explore-the-series
```

#### Register it in the series

Open `my-series/series.json`. Append this object to its existing `articles`
array, adding a comma after the preceding object:

```json
{"page_source": "first-page.md"}
```

Keep the demo entries and `series_meta`; do not replace the whole file with
that one object. Only a bare filename belongs in `page_source`, not
`sources/first-page.md`. The array order is the index and navigation order.

For a series containing **only** your article, this is a complete alternative
`series.json` (the unused demo sources can stay on disk):

```json
{
  "series_meta": {"title": "My first series"},
  "articles": [{"page_source": "first-page.md"}]
}
```

#### Build, open and verify

```bash
python3 lightwebpres build my-series --lang en --open
python3 lightwebpres audit my-series --lang en
python3 lightwebpres verify my-series --lang en
```

If automatic opening is unavailable, open `my-series/public/index.html`
manually, then select **My first page**. Its direct file is
`my-series/public/first-page.html`; the content card is
`first-page.html#travels-with-the-page`. Check the title, the content card and
the links to the demo articles. `audit` reports warnings; read them even when
its exit code is zero. `verify` should report no drift after this build.

Edit the title or body and repeat this loop. Keep each published `slug:`
stable: changing a title does not change its address. Once you no longer
want the demo in the site, remove its entries from `articles`, build again,
then review `clean` before removing old output (route 5).

<!-- /example:first-article -->

### Preview while writing

After your first build, keep a local preview running while you edit:

```bash
python3 lightwebpres watch my-series --lang en --serve --port 8000 --open
```

`watch` builds once, then polls sources, `series.json`, templates, presentation
dependencies, and split or legacy language packs. It notices new files and
keeps watching after a failed rebuild. Save a correction and read the next
build result. **Refresh the browser yourself: there is no automatic browser
reload.** Stop with Ctrl+C. Serving is opt-in on `127.0.0.1`; change `--port`
if 8000 is occupied. This is an author preview, not a public deployment server.

### Understand page anatomy

A page is a sequence of **slides**, separated by `---`, preceded by one
metadata block. There are four slide types, and inside a standard slide a
small set of named components. This section names them and says how you
reach each one; `agent/skills/lightwebpres/SKILL.md` carries the exact
syntax and every edge case.

**The four slide types.**

| Type | Carries | How many |
|---|---|---|
| `cover` | `slug`, `kicker`, `tags:`, `# Title`, `summary`, `slide-layout`, `slide-header`, `slide-footer`, `comment`, `note` | any number, anywhere — it is a look, not a structural marker |
| standard *(the default)* | `slug`, `kicker`, `tags:`, `## Title`, `summary`, `highlight`, `highlight-caption`, `fact-label`, `fact-variant`, `source`, `slide-layout`, `slide-header`, `slide-footer`, `comment`, `note`, then free Markdown | as many as you want |
| `series-nav` | `slug`, `tags:`, `slide-layout`, `slide-header`, `slide-footer`, `comment:` — the navigation itself is generated from `series.json` | 0 or 1 per article |
| `full-article` | `slug`, `article: filename.md`, `tags:`, `slide-layout`, `slide-header`, `slide-footer` and `comment:` | any number, each with its own file |

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
| **figure** | a captioned image | `![alt](img/x.png "Caption")` alone on its line; add `{50%}` for general image zoom or `{width=50% align=right}` for the extended format |
| **headings** | structure within the fact-box body | `#` `##` `###` `####` `#####` `######` — up to level 6; `#`–`###` are true headings, `####` renders as a bold-font paragraph (not `<strong>` emphasis), `#####`/`######` as plain paragraphs |
| **quote, code, list** | ordinary prose furniture | ordinary Markdown |
| **note** | a reference the reader can reach | `[^label]` in the text, `[^label]: body` on its own line |
| **long-form article** | the piece the cards summarise | a `full-article` slide pointing at a second `.md` file |

Keep these parser boundaries in mind:

- **Images have a short and an extended display suffix.** Put `{50%}` after
  the image for general image zoom, or use validated pairs such as
  `{width=50% height=auto align=right}`. `width` and `height` accept safe CSS
  lengths; `zoom` accepts a percentage; `align` is for standalone figures. An
  inline image can use the size values but not `align`.

- **The switch from fields to free text is one-way, within a slide.**
  Once a line is not a `field:` line, everything after it is prose — so a
  `highlight:` placed after a paragraph is published as the literal text
  `highlight: 3 000 W`. Fields first, prose after.
- Structural fields occupy one physical line, except `note:` and `comment:`:
  an indented continuation line belongs to the preceding note/review field.
- **A field is a value, not Markdown.** `summary: un **gras**` publishes
  the asterisks. The border is not where you would guess, either: a field
  passes raw HTML straight through, so finding that `<br>` works there
  says nothing about `**`. `audit` names fields carrying Markdown markup
  that they will not render.
- **A fact box appears only with `fact-label:`.** Free text without it
  renders as plain paragraphs — which is often what you want.
- A cover accepts no free body text. Standard-only fields such as `highlight`
  and `source` on a cover are parsed but not rendered; the build warns. Use a
  standard slide for evidence and put the citation in its `source:` field.
- Repeating a field keeps its last value, without a warning. An unknown meta
  key has no effect; `audit` catches it. A successful build alone will not
  tell you that `page-title` should have been `page_title`.
- A bare `---` always separates slides in an LWP source. Use `<hr>` for a
  divider within body text. Raw HTML passes through, including scripts;
  review or sanitize external content before building (route 5).

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

Both note settings can be set in `series_meta`; article metadata wins over
that series default. The built-in defaults are `notes_placement: local` and
`notes_tooltip: off`. Calls and note bodies link in both directions.

**What a card's link is.** Every card has its own address —
`article.html#barrage-de-vajont` — and the share button in the corner
copies it, or shows it as a QR code you can point a phone at or print.
The share action is on the index too, where slide scope is disabled:
there is no slide to share, and the series scope already names
the page you are on. That address is the `slug:` line you write on the
card, and nothing
else: it is not the card's position and not its title, so you can
reorder the deck, insert a card, rewrite a heading, or drop a card with
`tags: excluded`, and the links you have already given out still land
where they did.

`slug:` is required. A card without one stops the build, which names the
command that fixes it in one pass: `lightwebpres series slug set` writes
a slug into every card that has none. It is the only command that edits
your articles — a build never rewrites its own inputs — and what it
writes is a random eight-character name, because a name derived from the
title would look as though it still followed the title. Rename it to
something readable before you publish: `slug: barrage-de-vajont` is
worth more than `slug: 3f7c1a9e`, and the value is the identity from
then on.

Two cards on one slug is a build error, not a `-2` appended in silence.
`slug_prefix:` in the meta block (or in `series_meta`) puts a namespace
in front of every address on the page, which is what a series whose
pages reuse card names (`intro`, `sources`) needs.

`lightwebpres series slug` lists every card of the series and the name
it is published under, without building anything.

Register every article that should appear in navigation in
`series.json`; route 2 explains collection structure and metadata.

`comment:` is a source-only review field, accepted on every slide and in
article/series metadata. It is never published, not even in the HTML source.
`note:` is different: on a cover or standard slide it is embedded in the HTML
for the speaker panel (route 4). Both support indented continuation lines.

For editor or agent integrations, `lightwebpres contract --format text`
describes the versioned `lightwebpres.slide-draft/1` contract: accepted and
required fields, cardinalities, source order, empty-value rules, reserved IDs
and parseable skeletons. JSON is the default. `--article first-page.md` avoids
slugs already declared in that source. It writes nothing.

A `full-article` slide needs `article: filename.md`, pointing to a separate
plain Markdown file under `sources/`, with no LWP metadata or slide markers.
Omitting `article:` is fatal; an explicitly empty `article:` warns and omits
that unfinished slide. A non-empty reference to a missing file is fatal.

Markdown supports lists, tables, blockquotes, inline/fenced code and raw HTML.
A linked standalone image, `[![alt](img/x.png "Caption")](https://example.org)`,
keeps its caption outside the link; a mid-sentence image stays inline and its
title is a tooltip. Relative Markdown links are not converted: use raw
`<a href="other.html">Other page</a>` for local links. Headings at levels 4-6
render as paragraphs, not semantic headings. See the format reference for
converter limits; this is not a general CommonMark implementation.

For comparison tables, wrap a cell value in `<span class="yes">Yes</span>`,
`no` or `partial` to add a verdict treatment with a shape marker, not color
alone. A `col-signal` class on a header emphasizes its column; that requires
a raw HTML table because Markdown cannot attach a class to a header cell.

### Review a draft with another person or an agent

Set `status: draft` in the article metadata while it is under review. Ask the
reviewer to leave `comment:` fields before body prose, not HTML comments in
the prose: only `comment:` is guaranteed absent from published HTML.

```text
status: draft
comment: Check the source date before publication.
  Confirm that the chart and the text use the same period.
```

Preview with `python3 lightwebpres build my-series --lang en --include-drafts`.
The banner distinguishes the draft from a publication. Resolve each comment,
check the claims and links, then set `status: active` and build without
`--include-drafts`. If a `series.json` entry overrides the status, change that
entry instead. `ignored` is not a review stage: it never builds, even with
draft flags. Neither draft status nor a filtered variant secures files already
published; see route 5 for cleanup.

For an agent-assisted article:

- Give the agent the format reference, source evidence, intended audience and
  the exact article and long-form files it may edit.
- Keep existing slugs and citations unless the mission explicitly changes
  them. Ask for `comment:` where a claim still needs human review.
- Require `audit`, a successful build, and a report of unresolved warnings.
  A syntactically valid article is not evidence that its claims are true.
- Inspect the rendered cards, long article and source notes before making
  the article active. Route 6 gives a reusable mission contract.

## 2. Organize a documentary collection

A **corpus** is your collection of source material and articles, not a managed
LightWebPres database. A **series** selects and orders articles for one reading
context. Each article becomes a **page** containing slides and, optionally,
one or more long-form Markdown texts. The long article supplies detail without
making every presentation card carry it.

```text
corpus/                         your author-owned collection
  articles/                     canonical Markdown and supporting assets
  briefings/                    a series for a short presentation
    series.json                 selection, order, context-specific metadata
    sources/                    bare filenames visible to this series
    templates/                  this series' appearance
    public/                     generated index and article pages
      water.html                cover, cards, navigation, long article
  reading-room/                 another series using selected corpus articles
```

Create each series with `init`, put or link its inputs under `sources/`, and
edit its `series.json` directly. There is no implicit CMS, corpus index, or
article add/remove command. Navigation comes from the array, not from scanning
every Markdown file in the directory.

### One article in two contexts

Keep the canonical title, author, date, citations and long-form reference in
`water.md`. For example, a briefing can register it as
`{"page_source":"water.md","card_label":"Briefing 2","nav_title":"Water use"}`,
while a reading series uses
`{"page_source":"water.md","card_label":"Background reading"}`. The latter
inherits its navigation title rather than maintaining a second copy.

Make that same canonical file visible as `sources/water.md` in each series,
through a deliberate copy/synchronization step or a filesystem symlink. Do the
same for its `article: water_article.md` target and referenced `img/` assets.
`page_source` and `article:` must still be **bare filenames**; writing
`../corpus/water.md` into either field is not a reference mechanism. The native
tool follows symlinks and `audit` reports ones leaving logical roots. For zip
handoff or browser builds, include actual files and assets rather than relying
on links to another machine. Back up the canonical targets, not just symlinks.

Keep an entry override only when it expresses that series' context. Otherwise
let the article describe itself, so a canonical correction reaches both
contexts. Build and inspect both series after a shared edit; LightWebPres does
not discover consumers or rebuild another series for you.

For an agent reorganizing a collection, name the series it may edit, protect
canonical article bodies and published destinations, and compare `status` and
`series tags` before and after. Reordering an array should not rename slugs or
silently change which language is visible.

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

#### Work through French, English and shared content

Create a separate series with
`python3 lightwebpres init variant-series --lang en`, then create
`variant-series/sources/variants.md` with this complete example:

```markdown
<!-- lwp:meta -->
page_title: Two reading languages
---

<!-- lwp:slide:cover -->
slug: shared-introduction
# Two reading languages
summary: Choose a language; this introduction stays visible in both.

---

<!-- lwp:slide -->
slug: lecture-fr
tags: fr
## Lire en français
summary: Cette fiche apparaît avec le choix fr.

Le texte français utilise son propre jeu de règles typographiques.

---

<!-- lwp:slide -->
slug: reading-en
tags: en
## Read in English
summary: This card appears with the en selection.

The English text uses its own typography rules.

---

<!-- lwp:slide -->
slug: discarded-note
tags: excluded
## Not published
```

Use this complete `series.json`. It starts a fresh reader on French and maps
the language tags to typography packs:

```json
{
  "series_meta": {
    "title": "Two reading languages",
    "default_tag": "fr",
    "lang_tags": {"fr": "fr", "en": "en"}
  },
  "articles": [{"page_source": "variants.md"}]
}
```

Run these commands, replacing `variant-series` with that series directory:

```bash
python3 lightwebpres series tags variant-series --format json
python3 lightwebpres audit variant-series --lang en
python3 lightwebpres build variant-series --lang en --open
```

With one active article, the expected normal output is:

| Selected tag | Visible active articles | Visible slides | Which slides |
|---|---|---|---|
| `default` | 1 | 1 | Shared introduction only |
| `fr` (initial) | 1 | 2 | Shared introduction and French card |
| `en` | 1 | 2 | Shared introduction and English card |

The excluded card contributes to none of these rows and is not in the HTML.
Choose each tag in **L** to check the result. `--lang en` fixes the interface
language here, not the selected content variant. A saved valid reader choice
can override the initial `fr` selection.

Now consider adding `tags: fr` to the **article metadata**. It gates the whole
article: `fr` still sees two slides, but `en` and `default` see zero articles
and zero slides, even though a shared card exists. Remove that gate to offer
both languages. A draft changes the report's status counts but contributes
nothing to normal `output`; an ignored article never contributes output.

The first mapped language tag on a slide selects its typography pack. A slide
without a mapped language tag uses the build's `--lang`/`LWP_LANG` fallback.
The built-in `fr` and `en` packs come from the executable; another pack name
refers to `typography/<name>.json`, or to the legacy
`language/<name>.json`, in your series. The browser locale does not
change this typography choice. `audit` reports invalid tags and missing packs
without blocking, while `build` rejects malformed declarations.

### Register articles and inspect resolved metadata

`series.json` lists the articles and holds series-wide metadata:

```json
{
  "series_meta": {
    "title": "My article series",
    "subtitle": "Series subtitle",
    "intro": "Series introduction.",
    "scroll_duration": 200,
    "lang_tags": {"fr": "fr", "en": "en"}
  },
  "themes": ["essential", "family:terrain"],
  "articles": [
    {"page_source": "apple-pie.md"}
  ]
}
```

`page_source` — a bare filename, no path — is the only field ever
required here. Each article is self-described: `page_dest` (the output
HTML name), `page_title`/`page_desc`, `card_title`/`card_desc`/
`card_label`, `nav_title`/`nav_desc`, and the editorial fields
(`author`/`license`, defaulting series-wide from `series_meta`, and `date`)
all resolve from the article's own meta block and cover slide, and any of
them can be overridden per entry here when you want `series.json` to have
the final say. `status` says what each article is worth to the series:
`active` (the default), `draft` — still an article of the series, kept
out of the output until `--include-drafts` previews it with a banner — or
`ignored`, which takes it out of the chain entirely without deleting the
entry and everything you configured on it. The array order is the
navigation and index order. The full fallback chain per field is in
`GLOSSARY.md`.

`lightwebpres status my-series --format json` also carries the tag inventory
used by the build. For the focused view, use
`lightwebpres series tags my-series`: it reports effective article and slide
visibility by tag, separates `active`, `draft`, and `ignored`, and shows what
the default selection will actually publish. Add `--tag fr` to keep one row.

`status` lists articles in array order, each resolved value and where it came
from: JSON entry, article metadata, content, derived field or built-in default.
An unreadable source remains listed with fallback values and a stderr warning.
Neither `status` nor `series tags` builds or writes anything.

Article metadata can also declare `tags: fr`: that gate must match the selected
tag **and** at least one non-excluded slide must accept it. Untagged articles
have no article gate. `series_meta.default_tag` sets the initial selection
(default: `default`); a valid saved reader choice wins. Selecting `default`
shows only shared slides, not every variant. `build` and `audit` warn if a
selectable tag has no effective slide, or an article has no non-excluded slide.
Use `series tags --format json` for status totals, shared slides and default
output; `--tag fr` narrows the tag rows without changing series totals.

### Set languages and typography

Interface strings and typography are independent domains:
`interface/{lang}.json` and `typography/{lang}.json`. French and English are
embedded in the executable. Without `--lang` or `LWP_LANG`, pages embed both
interface vocabularies: the browser chooses French for `fr-*` locales and
English otherwise. An explicit language locks the interface. Typography is
applied at build time and never re-run when the browser locale changes.

```bash
./lightwebpres build my-series --lang en
./lightwebpres template show interface/fr.json
./lightwebpres template write typography/fr.json my-series
```

Write only a domain you intend to customize. Interface strings merge key by
key; typography `rules` replace the base rules wholesale. Legacy unified
`language/{lang}.json` files remain supported; split files win for their own
domain. `--language-file path` on `build`/`verify` explicitly selects a unified
pack at the highest priority. `LWP_INTERFACE_DIR`, `LWP_TYPOGRAPHY_DIR` and
`LWP_LANGUAGE_DIR` relocate the domains; specifications.md §2.3 and §19 give
the schemas and installed-pack lookup.

For multilingual slides, `series_meta.lang_tags`, such as
`{"fr": "fr", "en": "en"}`, maps tags to typography packs. The first mapped
tag on the slide wins; otherwise `--lang`/`LWP_LANG` supplies the fallback.
An unknown language ultimately falls back to English. Add rules for another
language in its pack, not by changing the engine.

Typography upgrades existing spaces to non-breaking ones; it never invents
spacing or thousands grouping, and preserves existing non-breaking spaces.
French handles `; : ! ?`, guillemets, `%`, spaced incise dashes, grouped
thousands (`170 000`), number/unit words including millions and dollars, and
`×`/`≈` before a number. English has its own smaller set: metric units, unit
words, initials, operators and spaced dashes. Rules affect text, not HTML tag
syntax.

To disable selected categories for one article, set metadata:

```text
typo_units: off
typo_thousands: off
```

Use `typo: off` for every rule on that article, or `--no-typography` on
`build`/`verify`/`watch` for the entire run. A category switch acts on the pack
in force; English has no thousands rule to disable. The full rule lists are
in specifications.md §4.5, §7.5 and §19.6.

## 3. Design and compose identities

Choose the smallest surface that meets the design goal. A reader can switch
among already-published choices without changing sources; an author selects
the initial preset and available alternatives; a designer creates reusable
themes or a complete Identity Kit.

![The same first article rendered with native LightWebPres, the documentation identity and the composed Field Notes identity](generated/appearance-choices.png "Three actual Chromium views of the same article with different presentation choices, not photographs of devices.")

### Choose a design task

| Goal | Start here | What you deliver |
|---|---|---|
| Change colors and typography | `theme create`, then edit one typed property | A complete `.conf` theme snapshot |
| Tune this series | `templates/settings.conf` pins | Series-local value overrides |
| Set initial reading and fitting choices | `series_meta.reading` in `series.json` | Table handling, text fitting and bounded optional shrinking |
| Change one page or phrase | Article `style.*` or instance tags | An intentional local exception |
| Reuse native layouts with a theme | A Commons preset | A descriptor and any external theme snapshot |
| Deliver layouts, logo, chrome and presets together | An Identity Kit | An autonomous `id/version/` directory |
| Combine resources from several kits | `kit compose` | A new autonomous kit, not a dependency chain |

### Set initial reading choices

Readers can change table handling and text fitting in **Menu > Size and tables**,
alongside presentation zoom. Set their starting choices in `series.json`, not
in a theme or article style. This complete `series_meta` fragment shows the
defaults; merge it into the existing object rather than replacing other metadata:

```json
{
  "reading": {
    "table_mode": "clip",
    "text_fit": "fixed",
    "table_shrink": false,
    "object_shrink": false,
    "min_text_scale": 0.75,
    "min_table_scale": 0.85,
    "min_object_scale": 0.85
  }
}
```

Omitting `reading`, or using `{}`, gives the same defaults. Partial objects
fill omitted keys from these defaults. For a series with wide comparison
tables, `"reading": {"table_mode": "scroll", "text_fit": "per-slide"}`
starts with local table scrolling and independent text reduction on each slide.
The other table modes are `clip` and `overflow`; the other text modes are
`fixed` and `uniform`. The
[reader controls](#adjust-zoom-tables-and-text) explain each choice.

`fixed` retains the theme's native responsive sizes; it disables content-based
text fitting, not responsiveness. `uniform` measures all slides currently
visible under the active tag, including a visible long-form article, and uses
one shared reduction factor. `per-slide` solves each visible slide separately.
Fitting measures actual browser layout at the current viewport and repeats
after resize, theme/preset or tag changes, font loading and image loading.
It never enlarges content above its chosen baseline.

The two booleans independently enable shrinking tables and supported
images/figures. They do not turn fitting into a general resizer for iframes,
media players or buttons. Each minimum scale must be a finite JSON number from
`0.5` to `1`, inclusive; text reduction also stops at 12 CSS pixels for text
originally at least that large. Smaller authored text is not enlarged.
Unknown keys, wrong types and invalid values are errors. A floor can leave a
slide too large, especially a long-form article; its content remains available
to scroll rather than being removed. See specifications.md §9.3.9.

For author review, `audit` warns about likely wide Markdown tables with an
**ESTIMATE**, before reader scaling, at `1024x768`, `768x1024`, `1280x720` and
`1680x720`. It accounts for resolved size/font-size settings, longest tokens
and cell padding, not exact glyph metrics or browser layout; custom CSS can
change the result. Neither a warning nor its absence guarantees fit. Inspect
the real page with its intended theme, viewport and reader settings.

### Create, measure and try a theme

Start from a complete theme rather than reconstructing its property list:

```bash
python3 lightwebpres theme create field-theme --from evergreen
python3 lightwebpres theme path
```

Open `field-theme.conf` in the reported user catalogue. Change one property,
for example `kicker.transform: none`, to stop uppercasing kickers. Then measure
and use it in your series:

```bash
python3 lightwebpres theme show field-theme
python3 lightwebpres theme vendor my-series --themes field-theme
python3 lightwebpres series theme set my-series --theme field-theme
python3 lightwebpres series theme my-series --format json
python3 lightwebpres audit my-series --lang en
python3 lightwebpres build my-series --lang en --open
```

Check a cover, dense card, source note, long article and print preview. Contrast
reports measure typed properties per category; they neither design the palette
nor certify custom CSS. For the next iteration, edit the vendored
`my-series/templates/themes/field-theme.conf`, or deliberately replace it using
`theme vendor --force` after editing the catalogue copy. A nearer complete
snapshot shadows the global one; do not expect edits in the latter to pass
through it.

For an agent, specify the allowed `.conf` or kit directory, the properties to
change and the pages to inspect. Require measured before/after values and a
build. Do not authorize changes to article claims as a shortcut to making the
layout fit, and do not treat a contrast report as a blanket accessibility grade.

### Identities, presets and themes

**Identity** groups presentation choices. The native identity, **LightWebPres**, provides
`builtin/standard` and the minimal **Light** theme. **Commons** contains the
global theme catalogue and presets that bind those themes to native layouts.
An **Identity Kit** is a self-contained versioned collection of layouts,
headers, footers, assets, typed themes and constrained structural CSS.
**Preset** selects a layout/chrome configuration and a base **Theme**; it does
not generate every possible combination of those resources.

LWP owns the page shell, navigation and JavaScript. Kit fragments have
`{{content}}`, `{{slide_header}}` and `{{slide_footer}}` slots; the index
receives only `{{content}}`. A kit can use local files or native references
`builtin:standard` for layouts and `builtin:light` for themes. A native layout
inside a kit keeps that kit's chrome. Kits cannot depend on Commons or other
kits, extend them, or declare provenance, parentage or authenticity. Resource
origins are computed by the loaders.

The only persisted selection is `series_meta.presentation_preset`:
`builtin/standard`, `commons/<id>` or `id@MAJOR.MINOR.PATCH/preset`.
The identity is inferred from this reference. The selection belongs neither
in article metadata nor in an `articles[]` entry. Omission selects
`builtin/standard` implicitly. `init --preset builtin/standard` and
`series preset set --preset builtin/standard` persist that explicit reference;
plain `init` leaves the field absent. Neither native choice vendors resources.

```json
{
  "series_meta": {
    "presentation_preset": "corporate@1.0.0/brief"
  }
}
```

The kit manifest's `label` names the identity, not whichever preset happens
to be initial. Its optional `default_preset` names a local preset, otherwise
the first preset in manifest order is used. `slide_layouts` and `slide_chrome`
declare preset defaults in that manifest only.

`slide-layout`, `slide-header` and `slide-footer` work on all four slide types.
They override the selected preset's defaults for one slide, not through an
author JSON cascade. The preset's theme supplies the typed base unless
`settings.conf` explicitly selects another theme. Precedence is: base theme
< `settings.conf` pins < article `style.*` < instance styles;
`templates/custom.css` remains the final advanced CSS layer. Assets are
published under `public/assets/presentations/<id>/<version>/...`, or embedded
by `--inline-images`.

For a kit offering the `hero` variant, place overrides before the slide body:

```text
slide-layout: hero
slide-header: Internal briefing
slide-footer: ""
```

`slide-layout` names a supported variant; `default` retains the preset's
default. Chrome accepts text or a supported JSON model. Exactly `""` removes
inherited chrome; an unquoted empty value is fatal, as is an empty layout.
Do not move manifest-only `slide_layouts` or `slide_chrome` into author
metadata; there is no article-level preset selection.

```bash
./lightwebpres preset list
./lightwebpres preset show builtin/standard
./lightwebpres series preset my-series
./lightwebpres series preset set my-series --preset builtin/standard --use-preset-theme
./lightwebpres init my-series --preset builtin/standard
```

`series preset set` vendors and selects without applying a starter. It
preserves pins and `custom.css`; with an explicit `theme:` in `settings.conf`,
it requires `--keep-theme` or `--use-preset-theme`, which removes that line.
`--keep-theme` requires an explicit `theme:`. Kits live under
`kits/<id>/<version>/` in a catalogue and
`templates/kits/<id>/<version>/` once vendored.
`LWP_IDENTITY_KITS_DIR` replaces the user catalogue location; an
id/version collision shadows the entire kit. See `specifications.md`
§9.9 for manifest, validation and security details.

For a kit preset, `init --preset` validates and vendors the complete kit, writes the
selector and generates settings from its theme. It applies the declared
starter unless `--no-starter` is passed. Neither option changes the meaning
of the `template` commands. Choose an installed selector from `preset list`;
`corporate@1.0.0/brief` is illustrative, not a supplied kit. Native selection
needs no files. Both `init` and `series preset set` vendor a Commons descriptor
and its selected external theme snapshot, if any; a native or embedded theme
needs no snapshot copy. An identical local dependency is reused, while a
conflicting file is refused.

The guide itself uses the tracked kit
`examples/kits/lightwebpres-docs/0.1.0/`. `tools/build_guide.py` vendors it
into a temporary series and publishes its assets with the guide. It is an
inspectable kit example, not another source of this manual.

### Add a Commons preset

Commons themes use the global `themes/` catalogue, `LWP_THEMES_DIR` and a
series' `templates/themes/`. Preset descriptors use a separate Commons root:
installed `commons/presets/` beside the executable or below
`<prefix>/share/lightwebpres/`, then the user root `LWP_COMMONS_DIR`, then
`templates/commons/presets/` in the series. User defaults are
`$XDG_DATA_HOME/lightwebpres/commons/` (normally under `~/.local/share`) or
`%APPDATA%/lightwebpres/commons/`. A nearer descriptor replaces the whole entry.

For example, `templates/commons/presets/reading.json` contains:

```json
{
  "schema": "lightwebpres.commons-preset/1",
  "id": "reading",
  "label": "Reading",
  "description": "Native layouts with a light reading theme.",
  "theme": "builtin:light"
}
```

All five keys are required; no other key is accepted, including `starters`.
The `id` matches the filename; `theme` is a global theme slug or `builtin:light`.
Select it with `./lightwebpres series preset set my-series --preset commons/reading`.
If the series has an explicit theme, also choose `--keep-theme` or
`--use-preset-theme`.

### Grow a kit from native layouts

Start with the minimal composition recipe below: its layouts and theme are
native references, and its footer is plain text. Validate this small kit before
adding custom fragments. Use the tracked
[documentation kit](examples/kits/lightwebpres-docs/0.1.0/manifest.json) as an
inspectable example of each richer surface, not as a file to edit in place.

1. Keep `builtin:standard` for all four slide layouts and the index, and
   `builtin:light` for the first theme. Give your kit its own `id`, version and
   fixed identity `label`.
2. Add a logo under `assets/`, declare it with `kind: image` in the manifest,
   and reference it from a header model in `chrome.json`. The documentation
   kit's [chrome models](examples/kits/lightwebpres-docs/0.1.0/chrome.json)
   show `presentation:mark`, its alt text and a text slot. Select that model
   in the preset's `slide_chrome`; do not put an image into a layout fragment.
3. Add a second preset, for example `brief` beside the minimal kit's `reading`.
   Both can reuse the native layouts while choosing different themes or chrome.
   Declare each preset's four `slide_layouts` and theme explicitly. Pick one
   `default_preset`; it is a default selection, not the identity's name.
4. When those views work, add a starter. The documentation kit's
   [starter manifest](examples/kits/lightwebpres-docs/0.1.0/starters/blank/starter.json)
   lists Markdown sources and article entries. Register the starter in the kit
   manifest and name it in the preset. `init --preset` applies it;
   `--no-starter` skips it, and selecting a preset on an existing series never
   applies it.
5. Validate in a fresh disposable series, inspect both presets and deliver the
   complete kit directory with instructions naming its selector. Test delivery
   using only that directory, without the recipe's source kits available.

For a supplied, richer kit you can inspect immediately, run from this
repository root with a fresh output directory:

```bash
LWP_IDENTITY_KITS_DIR="$PWD/examples/kits" python3 lightwebpres init /tmp/lwp-docs-preview --preset lightwebpres-docs@0.1.0/docs --lang en
python3 lightwebpres audit /tmp/lwp-docs-preview --lang en
python3 lightwebpres build /tmp/lwp-docs-preview --lang en --open
```

The copy under `/tmp/lwp-docs-preview/templates/kits/` belongs to that preview;
the tracked example is unchanged. A delivered kit has no extension chain,
authentication claim or lineage metadata. Local references must stay inside
it. The full manifest, allowed fragment tags, structural CSS restrictions and
starter restrictions are in specifications.md §9.9.2 through §9.9.4.

### Compose a minimal kit

`kit compose` builds an autonomous kit from an explicit recipe. This complete
`recipe.json` needs no source files:

```json
{
  "schema": "lightwebpres.kit-composition/1",
  "sources": {},
  "manifest": {
    "schema": "lightwebpres.identity-kit/1",
    "id": "brief",
    "version": "1.0.0",
    "label": "Brief",
    "default_preset": "reading",
    "layouts": {
      "cover": {"default": "builtin:standard"},
      "standard": {"default": "builtin:standard"},
      "series-nav": {"default": "builtin:standard"},
      "full-article": {"default": "builtin:standard"},
      "index": "builtin:standard"
    },
    "themes": {"light": "builtin:light"},
    "structure_css": "structure.css",
    "presets": {
      "reading": {
        "label": "Reading",
        "description": "Native layouts with a fixed editorial footer.",
        "theme": "light",
        "slide_layouts": {
          "cover": "default",
          "standard": "default",
          "series-nav": "default",
          "full-article": "default"
        },
        "slide_chrome": {"all": {"footer": "Brief"}}
      }
    }
  },
  "files": {
    "structure.css": {"text": ".lwp-presentation--brief { gap: 1rem; }\n"}
  }
}
```

```bash
./lightwebpres kit compose recipe.json --output kits --dry-run
./lightwebpres kit compose recipe.json --output kits
LWP_IDENTITY_KITS_DIR="$PWD/kits" ./lightwebpres init my-brief --preset brief@1.0.0/reading
```

The result is `kits/brief/1.0.0/`. The recipe requires exactly `schema`,
`sources`, `manifest` and `files`. To reuse declared source files, `sources`
maps an alias to a relative kit path contained below the recipe directory;
`files` maps a destination to `{"source":"alias","path":"local/path"}`,
`{"file":"local/path"}` or `{"text":"content"}`. A `.css` destination also
accepts `{"parts":[...]}` with a non-empty list of those descriptors; files
read by `parts` must also have a `.css` extension. A source kit's declared
`structure_css` file is recognized by its manifest role regardless of suffix.
Only matching class tokens in its selectors are rebound to the target kit's
scope, including escaped tokens; comments, strings, attribute values and
declarations are preserved. Other copied files are not rebound.
The full final manifest must name all final local references explicitly:
there is no guessed remapping or dependency closure.

Publication is staged outside the output catalogue on the same filesystem;
`--dry-run` validates in disposable system temporary storage and creates no output.
An output catalogue at a filesystem or mount root is refused: choose a
subdirectory within that filesystem. Existing kit destinations are refused.
The composed kit needs no source kit at build time and carries no provenance record.

### Compose resources from several kits

The worked [composition example](examples/kit-composition/README.md) uses three
recipe aliases: `frames` supplies layouts, `marks` supplies visual marks and
chrome, and `ink` supplies the typed theme. Its
[recipe](examples/kit-composition/recipe.json) names the final files and
manifest explicitly. Unlike the minimal recipe above, it demonstrates actual
resource reuse rather than only native references.

![Layouts, visual marks and a typed theme from three source kits form the Field Notes identity](generated/identity-composition.png "The composition recipe produces one autonomous Field Notes kit; the source kits are not needed when an author builds with it.")

From the repository root, choose a fresh output catalogue outside the example:

```bash
python3 lightwebpres kit compose examples/kit-composition/recipe.json --output /tmp/lwp-composed-kits --dry-run
python3 lightwebpres kit compose examples/kit-composition/recipe.json --output /tmp/lwp-composed-kits
LWP_IDENTITY_KITS_DIR=/tmp/lwp-composed-kits python3 lightwebpres init /tmp/lwp-field-notes --preset field-notes@1.0.0/brief --lang en
python3 lightwebpres demo /tmp/lwp-field-notes --lang en
python3 lightwebpres audit /tmp/lwp-field-notes --lang en
python3 lightwebpres verify /tmp/lwp-field-notes --lang en
```

This composed kit has no starter, so `demo` supplies and builds content for
the preview. Open `/tmp/lwp-field-notes/public/index.html`. To compare exactly
the first personal article instead, follow the example README's source-copy
steps; do not copy its Nebula settings over the preset's theme.

The result is `/tmp/lwp-composed-kits/field-notes/1.0.0/`. Use an author-owned
catalogue instead of `/tmp` for a durable delivery. Composition refuses an
existing destination; choose a fresh directory for another trial rather than
overwriting inputs. Keep the recipe with your design sources for future edits,
but distribute the complete resulting kit. Neither a source alias nor a
recipe filename becomes a runtime dependency.

### Keep alternate presentations available

A series has one primary presentation, but a build can carry other named
presets for the reader to choose without rebuilding. A kit or Commons primary
also makes the compatible native `builtin/standard` available automatically, after
the declared alternatives. Put other alternatives at the root of
`series.json`, or pass them for one build:

```json
{
  "series_meta": {
    "presentation_preset": "lightwebpres-docs@0.1.0/docs"
  },
  "presentation_presets": [
    "builtin/standard"
  ]
}
```

```bash
./lightwebpres build my-series --presentation-presets builtin/standard
```

The primary preset is always emitted first and remains the no-JavaScript
fallback. The CLI list overrides the JSON list; it adds alternatives rather
than replacing the primary. Duplicate selectors are removed, and an unknown
selector fails before output is written. The preset must be available in the
effective catalogue. Listing `builtin/standard` explicitly is optional for a
kit or Commons preset. If a slide uses a kit-only `slide-layout`, `slide-header` or
`slide-footer`, the implicit default is omitted with a warning; explicitly
requesting `builtin/standard` keeps the normal validation error.

When a real Identity Kit is published, **C** opens the Appearance picker with
**Identity**, **Preset** and **Theme** controls. These axes remain available
when the reader selects native `builtin/standard`. Without a published kit,
even with Commons presets, **C** offers only **Theme**, with theme-specific
labels and help. Preset metadata alone does not expose Identity/Preset axes,
and hidden Commons preset choices are not restored from the browser session.

An available preset choice changes the whole deck, including the index, and
lasts across pages in the current browser session. It
does not edit the series. If `settings.conf` names an explicit `theme:`, that
theme remains fixed; otherwise the preset's typed theme follows the selected
presentation until the reader chooses an explicit theme. In kit-aware mode,
**Follow preset** resets that explicit runtime choice. In theme-only mode,
there is no Follow preset option: the actual theme is selected, and choosing
the primary theme restores the author's base appearance. All themes of every
selected kit are published under kit-qualified names, even if no selected
preset uses them.

For example, a runtime theme ID is
`kit:lightwebpres-docs@0.1.0/docs`, distinct from a global theme slug. An asset
reference inside that kit is `presentation:mark`, not a filesystem path or a
reference into another kit. Keep those namespaces separate from the persisted
preset selector `lightwebpres-docs@0.1.0/docs`.

The **Applicable**, **Current identity** and **All** filters only narrow
published choices. Applicable means typed compatibility, not brand matching.
For native LightWebPres, Current identity includes published Commons/global
themes, Light and native custom variants, but excludes foreign kit themes.
For a real kit, it includes that kit's qualified themes and custom variants,
not unowned global themes or another kit's themes. Commons availability to
native `builtin` does not declare kit membership or make Commons an identity.
Identity labels stay fixed when the preset or theme changes. The initial/default
marker describes a selection, not another identity. The picker does not invent
a cross-product of presets and themes or fetch additional catalogue entries.

For color and typography changes, choose the smallest value override that
does the job before adding CSS rules.

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

The Commons theme catalogue combines the embedded themes with complete UTF-8 `.conf`
snapshots from the installed and user roots; a series can add its own
`templates/themes/` snapshots on top. `LWP_THEMES_DIR` replaces the user root.
The order is embedded, installed, user, series, and a collision replaces the
whole lower entry rather than inheriting it. Use `builtin:<slug>` to select an
embedded theme hidden by a local file.

Installed themes live under `<prefix>/share/lightwebpres/themes/` for FHS
installations, or a sibling `themes/` beside a standalone executable. The
user root is `$XDG_DATA_HOME/lightwebpres/themes/` on Unix (normally under
`~/.local/share`) or `%APPDATA%/lightwebpres/themes/` on Windows. Only direct
`.conf` files are loaded. `theme path` reports the roots. Global `theme`
reports do not include a series' vendored layer; `series theme` does.

Apply one at init time, or change your mind later:

```bash
./lightwebpres init my-series --theme evergreen
./lightwebpres series theme set my-series --theme crimson
```

A theme is a word in a data file: `series theme set` rewrites the one `theme:`
line of `templates/settings.conf` and nothing else. No CSS is touched —
the stylesheet is composed in memory at every build.

By default, the build embeds the essential runtime theme bundle for the
reader; `--no-essential-theme` opts out, while explicit selections add to or
shape the catalogue:

```bash
./lightwebpres build my-series --lang en --themes print-ink,print-grey
./lightwebpres build my-series --lang en --themes all
```

Or keep the selection in the root of `series.json`:

```json
"themes": ["essential", "background:light", "bgh:red"]
```

`essential` embeds Monochrome, Monochrome Night and Print Ink. A selector
`X:Y` can use `background`/`bg`, `family`/`fam`, or
`background hue`/`bgh`; each selector adds its matching themes and duplicates
are removed. An explicit CLI `--themes` overrides the JSON list.

Create or make a theme portable explicitly:

```bash
./lightwebpres theme create my-theme --from evergreen
./lightwebpres theme migrate my-series
./lightwebpres theme vendor my-series --themes my-theme,evergreen
./lightwebpres theme path
```

`theme create` writes a complete editable snapshot, `theme migrate` keeps only
the selected theme and explicit pins in an old scaffold, and `theme vendor`
copies complete snapshots into the series. No theme file uses `extends`.

The effective theme in `templates/settings.conf` is always included as the
first base choice, even if it is not in the list. When that file has property
pins, the first runtime choice is named `custom(<theme>)` and the raw base
theme is also present; those settings pins apply only to the custom choice.
The setting is read at build time, so an author's edit remains the source of
truth. `style.*` page properties and theme variables declared in `custom.css`
are left alone while a reader switches. **C** opens the searchable Appearance
picker when the build carries presentation or theme alternatives, and otherwise
has nothing to open.
**M** opens the global presenter menu; the same menu is available from the
bottom-right navigation button. The selection lasts for the other pages of
the same deck in the current browser session. The session key includes the
deck identity and catalogue digest, so another deck on the same origin or a
changed local snapshot cannot reuse an old choice.
Each theme choice previews its
resolved background, including its gradient, with matching foreground ink.
The menu actions carry icons and their keyboard shortcuts, including **I** on
Scroll. In the theme
picker and that presenter menu, focus starts at the first useful control.
In the presenter menu, left/right stay on the current row while up/down move
to the nearest control on the adjacent rendered row. `Tab`, `Home` and `End`
still move through the controls, and `Enter`/`Space` activate the focused one.

These commands inspect and select existing theme values. They do not design,
retune or repair a palette. Use `theme show` to read the measured contrast of
the shipped theme, or of the effective theme after the series' pins. `audit`
reads the same resolved sheet without being asked, and speaks only when
something has stopped working — a navigation control you cannot see, text the
colour of its own ground, a size under the readability floor. It warns; it
never refuses, and no shipped theme trips it.

```bash
./lightwebpres theme show evergreen
./lightwebpres series theme my-series --format json
```

The report gives WCAG levels **per category**, with the measured pairs and
ratios, not a blanket accessibility grade. It measures the resolved typed
properties, not arbitrary rules in `custom.css`. No palette is rewritten,
hidden or refused for its score, and the scores are not put on published
pages. Inspect the actual page after customization.

The catalogue includes original palettes and ports such as Nord, Dracula,
Solarized, Gruvbox and Catppuccin. `family` uses `desk`, `light`, `terrain`,
`heat`, `pop`, `ported`, `print`; polarity and background hue are computed.
The [compact catalogue](generated/themes-gallery.png) gives an overview;
open [the HTML gallery](generated/themes-gallery.html) in a browser to filter
real covers, cards with notes, page-wide notes and long-form text.

### Why essential themes ship by default

Every build embeds the `essential` bundle on its own — Monochrome, Monochrome
Night and Print Ink — so the picker is functional on any page without the
author opting in. Three reasons, in order:

- **Accessibility.** Monochrome is high-contrast ink with no hue; Monochrome
  Night is the same on a dark ground, for low-vision or light-sensitive
  readers; Print Ink is pure black on white, the highest contrast the page
  carries. A reader who cannot read the deck as drawn has an alternative
  that does not depend on the author having planned for them.
- **Print.** Print Ink is drawn for paper — pure white ground, black ink —
  and is available without an author-supplied theme selection. Press **C**,
  select **Print Ink**, then print with `Ctrl`/`Cmd`+`P`. Printing preserves
  the active theme; it does not select Print Ink automatically.
- **Sobriety.** Monochrome and Print Ink carry no hue, so the essential set
  never clashes with a series built around one. The author's chosen theme
  remains primary; the three are alternatives, never a replacement.

Opt out of the automatic essential-theme bundle:

```bash
./lightwebpres build my-series --lang en --no-essential-theme
./lightwebpres verify my-series --lang en --no-essential-theme
./lightwebpres watch my-series --lang en --no-essential-theme
```

The flag removes only that automatic bundle. Explicit `--themes` or
`series.json["themes"]` choices, published preset alternatives and selected
kits' themes remain available. An Identity Kit can therefore still offer the
Appearance picker with this flag. Without it, the essential three ship on
every build, deduplicated against the primary theme, so a series whose
effective theme is already one of them does not see it twice.

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
error pointing at the file and key. An empty value on a known property,
such as `page.bg:`, removes that pin and lets the selected theme provide
the value; an unknown key is still an error.

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

Shared theme values are `color.page`, `color.ink`, `color.ink-quiet`,
`color.mark`, `color.call`, `color.affirm`, `color.nav` and the four font
stacks `font.text`, `font.display`, `font.ui`, `font.mono`. Change a component
property rather than its shared color when only that component should move:

```conf
verdict.partial.fg: #8A4B00
summary.fg: #10151B
link.decoration-color: mark
```

`color.nav` controls navigation furniture, not body text. Body and source
links retain surrounding ink and use an underline; `link.decoration-color`
changes that underline. Glyph-owning components expose `shadow.fg`, `blur`,
`dx`, `dy` for halos (for example `title1.shadow.fg: #33FF8866`). An inherited
text shadow resolves its size at the ancestor, not separately for each glyph.
Raised components expose elevation color, blur, offsets and spread, with
hover axes on interactive cards/buttons. Use the generated settings scaffold
for exact names rather than inventing CSS variables.

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

## 4. Read, present and share

Open the link your author sent, or extract the complete published folder and
open its `index.html`. You need a browser, not Python or LightWebPres. Keep
the supplied images and assets beside the HTML. Scroll to read normally;
use the controls below to present it one slide at a time. The index uses the
same controls, stepping one article card at a time.

Use **H** for help, or open Menu in the bottom-right corner on touch. **L**
selects an available content variant; **C** opens Appearance when a kit was
published, or Theme in a native/Commons-only publication with theme alternatives.
These choices change your view without editing the author's files. In
Appearance, **Follow preset** undoes a separate theme choice; in Theme, choose
the primary theme to restore the author's base appearance. No control fetches
a theme or preset the author did not publish.

### Adjust zoom, tables and text

Open **Menu** with **M** or the bottom-right Menu button, then choose
**Size and tables** (**Taille et tableaux** in French). This opens a dedicated
submenu; **Back to main menu** or **Escape** returns to the main menu with focus on that
item, while clicking outside closes the submenu. These controls work with a
mouse, keyboard or touch; no source edit or rebuild is needed:

| Control | What it changes |
|---|---|
| Presentation zoom: **-**, **+**, **Reset** | Reduce or enlarge presentation text and images, or return to 100%, without scaling the slide frame or controls; the current percentage is shown. Keyboard equivalents are **-**, **+**, **=**. |
| Wide tables | **Hide what does not fit** (`clip`, default), **Allow overflow** (`overflow`), or **Scroll inside the table** (`scroll`). **O** cycles in that order. |
| Text size | **Keep the chosen size** (`fixed`, default), **Reduce all slides together** (`uniform`), or **Reduce each slide as needed** (`per-slide`). **A** cycles in that order. |
| Reduce tables as needed | Independently allow bounded table shrinking; off by default. |
| Reduce images as needed | Independently allow bounded shrinking of supported images/figures; off by default, not a control for arbitrary embedded widgets. |

The author can choose different starting settings and reduction limits.
Your table mode, text fitting, table/image shrink switches and presentation
zoom are saved in browser `localStorage` for this output directory on the
same origin. They follow you between articles and the index and survive
reloads; another output directory has separate preferences. Author-defined
minimum reduction limits are not saved as reader preferences. No choice
rewrites `series.json` or other author files. Invalid saved data or unavailable
storage falls back to the author's initial settings and 100% zoom; controls
still work in the loaded page if saving is blocked. Persistence depends on
browser storage availability, and `file:` URLs can behave differently from
served HTTP(S) pages and across browsers. Appearance choices keep their
separate browser-session contract.

Choose **Scroll inside the table** to read every column of a wide table within
its own viewport. Focus that region to use arrow keys, or scroll it horizontally
with a touch gesture, trackpad or Shift+wheel. Keys and gestures inside the
scrolling table do not accidentally navigate the deck, even at its edges.
Move focus or the pointer outside the table to resume normal deck navigation.
The default clipping is visual only: all table content is still in the HTML.
Allow overflow removes that local clipping but may extend beyond the slide.

Text fitting starts from the chosen theme's responsive sizes. **Keep the chosen
size** means no content-based reduction, not a fixed pixel size at every
viewport. Shared reduction considers every currently visible slide under the
active tag, not just the slide on screen; a visible long-form article can drive
the whole group to its floor. Independent reduction affects only slides that
need it. Both use actual browser measurements and recalculate when the viewport,
theme, preset, tags, fonts or loaded images change. If the minimum size still
does not fit, the slide remains readable by scrolling; fitting never removes
text or table cells to make a slide pass.

When fitting or shrinking is enabled, Size and tables reports how many visible
slides still need scrolling. It does not put a warning over the presentation itself.

Presentation zoom changes content font sizes, line heights and images, not
the page root's CSS zoom. Frame widths, padding, borders and minimum heights
keep their normal responsive geometry; the controls neither shrink nor grow
with presentation zoom. At 100%, native responsive sizing remains in effect.
Long content can still grow a slide or require scrolling. Fitting is calculated
at 100% before the manual zoom factor is applied, so zooming in can create
overflow rather than being silently cancelled by fitting. Ctrl/Cmd+plus/minus
and native browser pinch remain browser zoom, not a custom LWP pinch gesture.
Browser emulation is not verification on a physical device.

### Keyboard

| Key | Action |
|---|---|
| ↓ / PageDown / → | Next slide — on the index, next article card |
| ↑ / PageUp / ← / Backspace | Previous slide — on the index, previous article card |
| Home | Beginning of the page — first slide on an article; top on the index |
| Ctrl/Cmd+Home | Back to the series index — on the index: top of the page |
| End or Ctrl/Cmd+End | Last slide. On the index: last article card |
| + / - / = | Enlarge / reduce / reset presentation content zoom; Ctrl/Cmd +/- remains browser zoom |
| O | Cycle wide tables: clip, overflow, local scroll |
| A | Cycle text fitting: fixed, uniform, per-slide |
| F | Fullscreen (Esc to exit) |
| I | Toggle between the configured smooth slide glide and an instant jump |
| C | Open Appearance when a kit is published, otherwise Theme; published choices only |
| M | Open the presenter menu |
| S | Open sharing for the series, article or current slide |
| B | Black pause screen (press again to dismiss) |
| W | White pause screen (press again to dismiss) |
| T | Theme-background pause screen (press again to dismiss) |
| N | Toggle the speaker panel: the current slide's notes and the next slide's title (no panel content on the index, which has no slides) |
| 0–9 then Enter | Jump straight to slide N (1-based) — for decks of ten slides and up; inert on the index, which has no slides |
| L | Open the variant menu when the article carries at least two tags across its slides |
| H | Open the help overlay, which lists every key on this table |
| Esc | Leave fullscreen; also closes the speaker panel |

Every navigation action leaves its selected target visible. An index card or a
series-navigation card is kept entirely inside the viewport when it fits. A
slide taller than the screen is the necessary exception: it enters with its
top aligned to the top of the viewport, then its bounded reading steps finish
with its top or bottom aligned to the corresponding viewport edge.

When the help overlay is open, its scrollable foreground owns the arrow,
PageUp/PageDown, Home/End and Space keys. The same is true of the speaker
panel when it has focus; while that panel is merely open and unfocused, the
arrows keep navigating the deck.

The B/W/T pause screens hide the slide so the audience's eye comes back
to the speaker — the same feature PowerPoint and Keynote call "blank".
T uses the theme's own background colour, so a dark theme pauses on a
dark screen rather than flashing white.

### Speaker panel and slide counter

A small `X / N` counter sits in the bottom-left corner and fades out with
the other chrome when the mouse is idle. Type a slide number and press
**Enter** to jump there — handy once a deck passes ten slides and the
arrow-key walk becomes a slog. That live counter is **always** shown —
except on the index, where there is nothing to count — and is
independent of the engraved top-right `NN / NN` slide number, which is
opt-in (off by default) and turned on only by `--slides-page-numbers on`,
the article front-matter `slide_page_numbers`, or `series_meta.slide_page_numbers`
(see specifications.md §3.3.5). Press **N** to open the speaker panel: it
shows the current slide's `note:` field (the speaker note you wrote for
that slide, see below) and the title of the next slide. The panel opens in
the same page, so anyone watching the projected or shared screen sees it
too. It follows navigation; press **N** again to close it. There is no
separate private presenter window.

A speaker note is a `note:` field on the slide — distinct from a `[^n]`
footnote, which is a *source* note printed for the reader:

```markdown
<!-- lwp:slide -->
slug: speaker-example
kicker: Two
## Slide two
note: Mention the 2020 study — the audience asked for it last time.
  Follow up with the 2023 replication.
  If time runs short, skip the appendix.
```

The `note:` value is embedded in the HTML as a hidden element and displayed
by the presenter panel. Anyone with the page can open the panel or inspect
its source: do not put confidential content in `note:`.

A `note:` may run over several lines:
any line that starts with whitespace continues the note, and an indented
blank line marks a paragraph break. The block ends at the first
non-indented, non-empty line (the next field or the slide's body), so the
continuation lines are never captured as slide content.

### Printing and PDF

**Print** from the browser (Ctrl/Cmd+P) and choose "Save as PDF". Slides start
on separate sheets, navigation chrome is stripped, and print styles preserve
the active theme colors. Print content is not constrained to the screen's
viewport height; a long slide can span several sheets. Table viewports expand
without screen clipping or local scroll limits, and runtime fitting scales and
presentation zoom are cleared for print. The screen choices return afterwards;
print expansion does not guarantee that a wide table fits the physical paper.

For black ink on white, press **C** and select **Print Ink** before opening
the print dialog. It is included by default in the essential theme bundle;
printing does not switch to it automatically.

Check print preview before sending the PDF: the selected variant, the longest
card and its notes, a wide table, image captions and long-form page breaks.
Browser paper size, margins, scaling and background-printing settings affect
the result. If a card overflows, try another orientation or scale; ask the
author to shorten or split it if essential text still does not fit. Do not
assume a long-form article fits on one physical sheet.

### Mouse

| Gesture | Action |
|---|---|
| Single click on content | Next slide (configured glide, 200ms default) |
| Right-click on content | Previous slide (configured glide, 200ms default) |
| Click during the glide | Jump straight to that click's target |
| Middle button anywhere | Exit fullscreen on its own; to enter, press the middle button, then click left inside the window |
| Click in the bottom-right corner | Toggle the navigation buttons (hide/show) |

Clicks on links, images, buttons, and the share popover are not
intercepted — they keep working. The right-click to go back is the
remote-mouse use case: the speaker with a wireless mouse in hand
left-clicks to advance, right-clicks to go back — two distinct buttons,
no aiming. The native context menu is suppressed on slide content so
right-click is a clean back gesture. A click lands instantly on the
next card and glides to it over the configured duration (200 ms by default);
a click that arrives while the
deck is still gliding does not wait — it jumps straight to its target,
so two clicks in quick succession land two pages on, and a right-click
during the glide returns you to the card you left. The middle button
only leaves fullscreen by itself: browsers refuse `requestFullscreen()`
from any non-left event, so entering is a two-step gesture — middle
button to arm the intent, then a left click inside the window (a right
click in the same window goes to the index instead). The wheel itself
keeps scrolling; the ⛶ button and F stay direct entries. Esc exits
fullscreen. The cursor hides after 1 second of idleness in fullscreen.
A left click on an existing selection just dismisses the highlight —
no step — and a right-click on a selection opens the browser's own
menu, the deck stepping aside. Two clicks in quick succession are two
steps: the deck never treats a double click as anything else.

### Touch (phone, tablet)

| Gesture | Action |
|---|---|
| Swipe left | Next slide — on the index, next article card |
| Swipe right | Previous slide — on the index, previous article card |
| Tap on content | Next slide — on the index, next article card |
| Double tap | Show or hide the navigation immediately |
| Press and hold | Select text and open the copy menu — the deck does not take it |
| Pinch | Native browser zoom; not presentation zoom or slide navigation |

In a table set to **Scroll inside the table**, touch gestures scroll the table
instead of changing slides. Browser touch emulation can check event handling;
it is not evidence of pinch behavior on a physical phone or tablet.

### Navigation buttons

The round buttons in the bottom-right corner form one column: from bottom to
top, Menu, down, up and fullscreen. The arrows are grayed when they cannot
move further. The series-index action, share, Scroll (also **I**) and the
variant filter are
actions in the presenter menu, which also carries the themes, help, notes and
pause screens. The same controls sit on the index, where previous and next step
one article card at a time.
After 3 seconds of mouse
idleness they fade out, and the cursor goes with them: the speaker does
not want chrome on the wall. In fullscreen both go after 1 second. Move
the mouse to bring the buttons back; the cursor waits for 250ms of
continuous movement, so a knock against the desk does not put it on the
wall.

On a phone or a tablet they fade after the same three seconds. A **double tap**
toggles them immediately: visible navigation disappears at once; hidden
navigation returns and starts a fresh countdown. If the first tap has already
started a slide or scroll, recognizing the pair cancels that movement and
restores the slide and position from before the first tap. A touch or a scroll
restarts the countdown while the controls are still up, so they never vanish
under your finger; once they are gone they no longer answer a touch at all, so
the corner of your own text is safe to touch. Fullscreen is the ⛶ button in
that bar rather than the middle button: the middle button alone only exits
fullscreen — entering is the two-step, middle button then a left click. With
a mouse, clicking the corner (not a button) toggles their current visibility.

Text selection, long press and the copy menu remain the browser's. The
navigation double tap is recognized from touch events themselves, not from
the delayed clicks a browser synthesizes, so those clicks cannot advance the
deck after the first tap has been restored.

### Share a series, an article or a slide

Press **S** or choose Share in **M**. Select the scope, then copy the link or
show its locally generated QR code. Series points to `index.html`, article to
the current page, and slide to the current `slug:` anchor. On the index,
article points to the index itself and slide scope is disabled. Slugs, not
slide positions or headings, keep previously shared addresses stable.

QR sharing needs an HTTP(S) address reachable from the receiving phone. A
local file or loopback URL is not such an address; the UI explains the local
address instead of offering a misleading QR link. Publish first, then test
the hosted address. No QR service receives the link.

Fullscreen is a deliberate **F**/button gesture, not a consequence of
rotating a phone. It requests a screen wake lock where supported; otherwise
the operating system may still dim the display. The scrollbar fades with
the navigation without changing layout. Entering/leaving fullscreen and
clicking in the button corner reveal the controls immediately.

The configured slide glide defaults to `200` ms. Set
`series_meta.scroll_duration` or pass `--scroll-duration milliseconds` on
`build`/`verify`/`watch`; `0` is instant. The Scroll action in **M**, also **I**,
switches between that configured duration and `0` and shows the active value.

### Solve a reading problem

| Symptom | Reader action |
|---|---|
| The controls vanished | Move the mouse or double-tap on touch; idle controls fade intentionally. |
| The text is hard to read | Open Theme or Appearance and try Monochrome, Monochrome Night or Print Ink if supplied; use presentation or browser zoom. |
| A table loses its rightmost columns | Open **Menu > Size and tables** and choose **Scroll inside the table**, or press **O** until that mode is selected; the HTML still contains every cell. |
| A slide is too tall | Try **Reduce each slide as needed** in **Menu > Size and tables**; optionally enable table/image shrinking. Scroll any content that still exceeds the author's reduction floor. |
| Every slide became smaller | **Reduce all slides together** includes all visible slides, even a long-form article. Choose independent reduction or **Keep the chosen size** instead. |
| Enlarging presentation content causes overflow | Zoom is independent of fitting. Use **Reset** to return presentation zoom to 100%, or keep magnification and scroll. |
| A language or article seems missing | Open the variant menu; a saved selection may differ from the author's initial choice. |
| Arrow keys scroll a panel instead of the deck | Close help, or move focus out of the speaker panel. |
| A numeric jump does nothing | It works on article decks of at least ten slides, not the index; there is no touch-number jump control. |
| Notes appeared on the projected screen | Close the speaker panel with **N**; it is the same public page, not a private display. |
| A phone cannot open the shared address | A local file or loopback address is not a published URL; ask for a reachable HTTP(S) link. |
| Fullscreen or wake lock is unavailable | Continue in a normal browser window; device/browser support varies. |
| The PDF loses colors or clips a table | Check background printing, paper orientation, scale and the active theme in print preview. |

If an agent prepares a presentation handoff, ask it to provide the exact hosted
page and slide links, selected variant and any known print issues. The speaker
should still rehearse navigation, panel visibility and PDF output on the
device that will be used.

## 5. Publish and maintain

Publish the generated site, but preserve the inputs needed to rebuild it.
Before uploading, inspect it as a reader using route 4, then run the checks
below. A successful build validates structure, not source credibility or the
appearance on every device.

### Audit sources and verify output

Two different checks, for two different moments:

```bash
./lightwebpres audit my-series --lang en    # source and render warnings
./lightwebpres verify my-series --lang en   # does output match the sources?
```

`audit` renders the series in memory and writes nothing. It checks every
listed article, including drafts and `ignored` entries; it does not need an
`--include-drafts` option. Read three kinds of report:

- **Sources and overrides:** missing covers, instance tags, malformed metadata
  or tags, missing language packs, ignored cover fields, legacy `style.css`,
  retired CSS variables with their replacements, stale scaffold comments and
  symlinks that leave their logical roots.
- **Resolved styles:** an invisible navigation control, text matching its
  background, or a size below the readability floor after theme, settings and
  article styles compose. Valid individual values can still combine badly.
- **Rendered output:** build failures and an image inventory with inline/figure
  counts, unused sources and missing referenced assets. If rendering fails,
  unknown usage is reported as unavailable, not falsely called unused.

Plain `audit` exits zero even when rendering fails. `--strict` makes warnings
and render failures non-zero CI results. `--templates` limits the check to
the presentation layer, including resolved styles, without rendering or
per-article checks. It is cheaper than the full audit, which costs about a build.

`verify` asks the other question: it rebuilds every article in memory and
compares it against `public/` (ignoring build stamps and surrounding
whitespace), exiting non-zero when output differs. Run it before `build` to
catch a `public/` that was hand-edited or never rebuilt after a source change.

Use the same supported rendering options as the build, including `--lang`,
`--themes` and `--no-essential-theme`. **`verify` does not accept
`--inline-images`** and cannot reproduce that build mode: embedded images or
presentation assets can therefore report drift even with unchanged sources.
Use a separate, non-inline build output for this CI check.

### Asking why a value is what it is

Most of what ends up on a page was never written on that page: a title
falls back through `series.json`, the meta block and the cover slide, a
colour falls through `settings.conf`, the theme and the built-in
defaults. When the result surprises you, ask:

```bash
./lightwebpres resolve my-series page_title --article first-page.md
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

### Publish the output, not the project

Upload the contents of `public/` to a static host: the article HTML files,
`index.html`, referenced `img/` files and any `assets/presentations/` files.
The generated series README lives beside `series.json`, not inside `public/`.
No Python server or LightWebPres runtime is needed on the host. Reopen the
hosted index, follow an article link and test a slide link from another device.
Local `file://` viewing works, but does not make an address reachable by a phone.

By default, only referenced images are copied from `sources/img/`; unused
source files are not published and existing output assets are left in place.
`--inline-images` embeds Markdown images from cards and included long-form
files as data URIs, with no copied `img/` directory. Base64 adds roughly a
third to image size before serving compression. Raw HTML images with relative
paths cannot be inlined: the build names and rejects them rather than leaving
references to an absent asset directory. Keep a non-inline output for `verify`.

Output switches on `build` and `watch`: `--no-index` skips `index.html`,
`--no-readme` skips the series README, `--no-nav` leaves a placed `series-nav`
without generated links, `--drafts-only` previews only drafts, and `--open`
opens the result. `build --include-drafts` includes drafts alongside active
articles; `verify` supports that selection too. `--slides-page-numbers on`
engraves top-right numbering (off by default, independent of the live counter).

A single article can set `page_dest: index.html` to become the directory's
landing page; no redundant one-card index is then generated. In a multi-article
series that name is reserved when an index is generated. `--no-index` leaves
it available. Duplicate destinations (case-insensitive), unsafe filenames,
malformed JSON, missing slugs and duplicate slugs are fatal. Generated HTML
is checked for tag balance before writing; that is not a security sanitizer.

Removing an article from the array, marking it draft/ignored, or dropping an
image reference does not erase an old published file. Review the manifest-based
cleanup after a build:

```bash
./lightwebpres clean my-series          # preview orphan removal
./lightwebpres clean my-series --force  # remove the listed orphan output
```

Review the host's stale files too: uploading new files alone does not remove
old ones. In particular the browser GitLab push never deletes files. It may
also finish only part of a multi-commit push; inspect the remote branch before
calling the publication complete or retrying. Route 6 covers that workflow.

The native CLI builds files; it does not upload a site. A CI artifact is not
automatically a hosting deployment either. Deploying the browser **builder**
is a separate operation: it needs HTTP(S), Pyodide and its Python files, unlike
the static articles it produces. Use [Serve the browser tool](#serve-the-browser-tool)
only if you intend to offer that builder.

### Trust and licensing

Build only trusted content. Raw HTML, including scripts, passes through;
`custom.css` and a local `nav.js` are author-controlled code. Sanitize upstream
CMS exports, translations or other untrusted inputs before building. Symlinks
out of source roots are followed and reported by `audit`, not sandboxed.
Tags filter views, not access: only `excluded` slides are omitted at build
time. Speaker notes are public HTML; `comment:` fields are not published.

The program is GPL v3 or later, with the [Output Exception](COPYING.EXCEPTION).
Your generated presentations may use your chosen terms, commercially or not;
the exception does not cover a generator using output as templates. The
executable copied by `init` is still GPL code: keep `COPYING` and
`COPYING.EXCEPTION` with it when distributing a series repository. See the
[README licence summary](README.md#license) and
[third-party notices](THIRD-PARTY-NOTICES.md).

### Back up and restore the authoring project

`public/` is a delivery, not a backup. It does not preserve your Markdown,
review comments, preset recipes or editable settings. The browser's
`public.zip` is not a project backup either. LightWebPres has no backup or
restore command; use your normal archive, filesystem backup or version-control
tools for the inputs.

1. Archive the complete series directory before a release or upgrade. Preserve
   `series.json`, all of `sources/` including long-form files and images,
   `templates/` including pins, custom CSS, local navigation and vendored
   themes/kits/Commons descriptors, and `interface/`, `typography/`, `language/`.
2. Keep the exact executable and its two licence files. Record
   `python3 lightwebpres --version`, the build command and all rendering flags,
   plus any `LWP_*` path or language overrides. Back up external catalogue
   dependencies and canonical symlink targets, or vendor/materialize them
   first. Preserve kit recipes and their sources separately if you will revise
   the design, even though the resulting kit does not need them to build.
3. Restore into a **new** directory, not over the only working copy. Recreate
   intended external paths or remove obsolete environment overrides. If the
   backup contains published output, run `verify` before rebuilding with the
   same supported options. Keep an old published snapshot for rollback, but
   do not mistake it for the inputs.
4. Audit, rebuild with the restored executable and inspect the result. Confirm
   titles, variant counts, images, logo, notes, navigation and a shared slug.
   Only replace the live site after this restore test succeeds.

For a backup restored as `restored-series/`, built in English with default
rendering options, these are the native engine commands:

```bash
python3 restored-series/lightwebpres audit restored-series --lang en
python3 restored-series/lightwebpres verify restored-series --lang en
python3 restored-series/lightwebpres build restored-series --lang en --output /tmp/lwp-restored-public --open
```

Skip the initial `verify` if the backup has no generated output. An inline
publication cannot be checked by `verify`; rebuild a separate non-inline
output instead. Match any original theme, preset-alternative or typography
flags rather than assuming the defaults in this example. `.lwp-cache/` is
rebuildable state; retain output manifests with a published tree if you want
`clean` to know which files it owns.

### Upgrade the executable and templates

Replace the project's executable with a newer release, read `CHANGELOG.md`,
then audit, rebuild and inspect the output. The composed stylesheet and
built-in navigation/language packs follow the executable. Your theme choice,
property pins and `custom.css` remain yours.

A tool-owned file installed by `template write` takes precedence over the
built-in copy. Builds warn when it differs, even with `--quiet`; the tool
cannot tell a stale override from an intentional customization. Older series
(before v0.40.0) received copies automatically. To resume following built-ins:

```bash
./lightwebpres template update my-series
./lightwebpres template update my-series --scaffold
```

An identical tool-owned copy is removed. A differing `nav.js` is backed up as
`nav.js.bak` and removed. If that backup already contains different bytes, or
is a directory or symlink, the update refuses before changing files. Keep or
move that backup deliberately before retrying; an identical regular backup
can be reused. Differing interface or typography packs are kept and
reported; compare against `template show` before deleting them. Packs for
languages not shipped by the tool are left alone. Missing `settings.conf`
and `custom.css` are created. `--scaffold` also refreshes the commented
settings surface while keeping every pinned line.

`template show nav.js`, `template show interface/en.json` and
`template show typography/en.json` print built-ins without a series. Use
`template write <file> my-series` to install a copy to modify, and `--force`
only to replace an existing copy. Legacy `fr.json`/`en.json` remain supported.

For an agent handling publication or an upgrade, separate permission to build
from permission to upload or delete. Require a backup location, exact engine
version and flags, audit warnings, drift results, and the proposed `clean`
list. Publishing, remote cleanup and retrying partial pushes need their own
explicit authorization; a local build is not proof of a complete deployment.

## 6. Integrate and automate

Use the native CLI in scripts, the browser builder for zip/GitLab workflows,
or an agent that edits the documented input files and invokes the same engine.
These are ways to use the product; none requires modifying its executable.

### Give an agent a bounded mission

An agent uses the same articles, `series.json`, presets and commands as a
person. Give it a concrete task and a small write surface, not a general role
to redesign the project. For example:

```text
Mission: add an English variant to the existing water article.
Inputs: the supplied translation, the existing French source, the local
        format reference, and the contract from the installed executable.
May edit: my-series/sources/water.md and the lang_tags entry in series.json.
Must preserve: French wording, all published slugs, output filenames,
               article order, status and presentation settings.
May run: read-only reports, audit, and a build into the agreed preview output.
Must not: publish, push, delete files, change the executable or install tools.
Handoff: changed files, FR/EN/shared visibility before and after, commands and
         exit codes, warnings, and anything still requiring human review.
```

Provide the files as inputs, not just their names. Treat third-party Markdown
and an agent's generated HTML as untrusted until reviewed or sanitized.
`comment:` is appropriate for a source-only question; `note:` is public
speaker material, not a place to hide uncertainty or credentials.

Before editing, query the installed engine rather than maintaining a second
grammar in the agent:

```bash
python3 lightwebpres contract my-series --article first-page.md --format json
python3 lightwebpres status my-series --format json
python3 lightwebpres series tags my-series --format json
python3 lightwebpres series slug my-series --format json
python3 lightwebpres resolve my-series page_title --article first-page.md --format json
```

`contract` returns `lightwebpres.slide-draft/1`, with required fields, allowed
order, cardinality and parseable skeletons. Its generated slugs avoid those
already declared in the named article; that is not a request to rename existing
slides. Only run `series slug set` if filling missing slugs is authorized,
starting with `--dry-run` and reviewing the proposed source edits.

### Consume reports, warnings and exit codes

Capture stdout, stderr and the exit code separately. For JSON report commands,
parse stdout as one JSON document, not a stream of human log lines. Keep stderr
for warnings and errors; do not concatenate it into JSON. `--quiet` suppresses
progress, not requested values or warnings. Check the returned `schema` and
`lightwebpres_version` before interpreting fields, and reject an unsupported
schema rather than guessing its meaning.

| Interface | Contract or result | Consumer obligation |
|---|---|---|
| `contract --format json` | `lightwebpres.slide-draft/1` | Use the engine's field rules and skeletons. |
| `status --format json` | `lightwebpres.series-info/4` | Preserve article order and inspect `source_read`, not only the exit code. |
| `series tags --format json` | `lightwebpres.series-tags/1` | Check `default_output` and active-only per-tag `output`, not just tag names. |
| `series preset --format json` | `lightwebpres.series-preset/2`, containing a `lightwebpres.presentation-preset/2` object | Read the nested `preset` selector and resources; `native_renderer` describes rendering, not the initial selection. |
| `build` | Non-zero on fatal structural/render errors | Read warnings too; exit 0 is not editorial approval. |
| `audit` | Reports warnings and render failures; normally exits 0 | Read the report, or use `--strict` for a failing gate. |
| `verify` | Non-zero on drift or failure | Match supported rendering flags; it cannot verify inline-image mode. |

`status` can succeed with **incomplete source information**. A missing,
unreadable or non-UTF-8 article stays in the report with `source_read: false`,
fallback field values and a stderr warning. That is useful inventory, not a
successful validation. Do not let fallback titles overwrite canonical metadata.
Its field inventory covers eight display fields; query `author`, `license` or
`date` with `resolve` when needed. Precise report contracts are in
specifications.md §11.11, §11.11.1, §11.12, §11.17 and §11.18.

After the edit, rerun the affected reports, audit and build. Compare expected
visibility and stable addresses, then give a human the preview and unresolved
questions. Do not silently turn warnings into success or claim browser checks
that were not performed.

### Build in the browser

`web/index.html` runs the same executable, unmodified, inside vendored
[Pyodide](https://pyodide.org) (CPython compiled to WebAssembly). Two tabs
share one engine load:

- **Upload a zip:** select a series archive and download a zip of `public/`.
  The build stays in the tab. Archives over 500 MiB compressed or uncompressed
  are refused before extraction; Pyodide loads locally, not from a CDN.
- **Sync with GitLab:** configure your instance, repository and credentials,
  pull the series, build and push. Requests go directly to GitLab, without a
  third-party proxy. Push creates/updates files and never deletes them.
  Up to 100 file actions are batched per commit; larger pushes create several
  commits. This is a local precaution, not a GitLab file-count limit. The REST
  client does not supply automatic throttling/retries; instance request-size
  and rate limits still apply.

#### Build from a zip

1. Prepare a zip of the authoring series with `series.json`, `sources/` and its
   assets, plus any templates, kits, themes and language overrides it needs.
   Include real files rather than dependencies outside the archive.
2. Open the served builder, choose **Upload a zip**, select the archive and
   language, then choose **Build**. Wait for the engine to load and read the log.
3. Download and extract `public.zip`, open its index, and inspect the article
   and asset links before uploading the contents to your host. Preserve the
   original input archive separately; the downloaded output is not a backup.

The tab is a build workspace, not durable authoring storage or a file editor.
Do not rely on its in-memory files surviving a reload or closing the tab.

#### Pull, build and push with GitLab

1. Enter the GitLab instance URL, project ID or `namespace/project`, branch and
   personal access token. Use HTTPS; plain HTTP is accepted only for localhost
   testing. Verify the destination before entering a token: requests go to
   that instance directly.
2. Choose **Pull**, then the build language and **Build**. Read the log before
   proceeding. Pull downloads repository inputs; the local browser engine
   builds them without sending content to a separate build service.
3. Enter a useful commit message and choose **Push** only when you intend to
   modify that remote branch. Push sends sources and settings as well as
   `public/`, excluding derived build-state files. It does not merge changes
   or detect edits made on the branch since Pull: an old browser snapshot can
   overwrite a colleague's newer source. Avoid concurrent branch edits during
   this workflow; if remote inputs changed, save any local work separately,
   pull again and rebuild before pushing. Inspect the resulting commits and,
   if configured, the hosting pipeline and published site. A push itself is
   not proof that hosting deployed successfully.

The instance must allow the builder's origin through CORS on its API,
including preflight requests. For an immediate network failure, check the
browser console and ask the GitLab administrator to configure the allowed
origin and headers; do not disable browser security or send the token through
an unknown proxy. See specifications.md §23.10 for the reverse-proxy example
and §23.11 for token permissions: `api` is required for Push through the REST
Commits API; `read_api` supports read-only Pull. `write_repository` covers Git
over HTTP, not REST commit creation, so `read_api` + `write_repository` is
insufficient for this workflow. The `api` scope grants broader API read/write
access within the token owner's GitLab permissions; use it deliberately.

Connection data, including the token, is stored **in clear text** in the tab's
session storage. **Remember this token on this device** additionally writes
it to persistent local storage. Anyone with access to the browser profile can
read it. Leave remembering off on shared devices; uncheck it to remove the
persistent copy, or use **Clear connection data** to clear stored connection
data. Revoke a token in GitLab if it may have been exposed.

Push is **not an all-or-nothing transaction** across a large change. It makes
batches of at most 100 file actions, and an earlier commit remains if a later
batch fails. Inspect the remote branch and the error before retrying; a fresh
pull/build can reconcile with what reached the server. The client does not
roll back those commits or automatically retry rate limits. It never sends
delete actions, so stale published pages need deliberate remote cleanup.
Keep your input backup and verify remote state rather than treating a failed
push as "nothing changed" (specifications.md §23.12).

### Serve the browser tool

Unlike generated articles, the builder must be served over HTTP(S), not
opened with `file://`, because browsers block Pyodide asset loading there.
From a source checkout, serve the directory containing both `lightwebpres`
and `web/`:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory /path/to/lightwebpres
```

Open `http://localhost:8000/web/index.html`. A mistaken `file://` opening shows
a fix command computed from the page's location, with a Copy button.

For deployment, keep `vendor/`, `app.py` and `git_sync.py` with the page. It
looks for the executable first at `./lightwebpres`, then `../lightwebpres`.
The first layout serves the contents of `web/` as a site root with the
executable alongside; the second is the repository layout above. Missing
executable and `.mjs` MIME errors are covered in specifications.md §23.6 and
§23.7. `web/.htaccess` supplies Apache MIME handling where overrides are
allowed. This lightweight builder is not the separate `lightwebpres-gui`
editor project.

### Run commands unattended

Every CLI command runs unattended. `verify` fails on output drift;
`audit --strict` fails on warnings, including render failures. Plain `audit`
reports without failing. The CLI has no third-party dependency or network
requirement at build time, so a Python runner can build upstream Markdown.
Sanitize untrusted upstream HTML first (route 5).

### Build in CI

`init --gitlab-ci` optionally writes this build-and-artifact job. It does not
configure a public hosting deployment; a plain `init` emits no CI file.

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

The Python command works on other runners too. If `public/` is committed,
check it **before** rebuilding, so build does not erase evidence of drift:

```yaml
  script:
    - python3 lightwebpres verify . --lang fr
    - python3 lightwebpres build . --lang fr
```

A fresh checkout with no committed output needs a build, not that initial
drift gate. Match rendering options in `verify`, including language, themes
and `--no-essential-theme`. It cannot reproduce `--inline-images`.

### Target builds and record build stamps

```bash
./lightwebpres build my-series --lang en --only first-page.md
```

For the author's rebuild-and-preview loop, use [watch](#preview-while-writing)
in route 1; it does not reload the browser.

`--only` targets one article only when the navigation cache is safe. It still
refreshes derived outputs (index, README and assets according to options,
manifest and cache); changes affecting index/navigation trigger a full build.
The cache is bound to its output directory. Switching output directories, or
losing retained pages or declared assets, also triggers a full build rather
than producing a partial site under a successful exit code.
`--nav-cache path` relocates the fingerprint, normally `.lwp-cache/nav.json`.
That cache is derived state and can be deleted, not hand-edited.
`--build-stamp` records version and time on the pages; `--build-stamp-minimal`
keeps a marker without either and takes precedence. `status: draft` and
`ignored` control which articles enter normal output (route 2).

### Paths and CLI conventions

| Variable | Replaces |
|---|---|
| `LWP_SERIES_DIR` | Default series directory when no directory argument is given |
| `LWP_SOURCES_DIR`, `LWP_TEMPLATES_DIR`, `LWP_OUTPUT_DIR` | Source, customization and output roots |
| `LWP_INTERFACE_DIR`, `LWP_TYPOGRAPHY_DIR`, `LWP_LANGUAGE_DIR` | Split or legacy language roots |
| `LWP_LANG` | Build language fallback and explicit interface language |
| `LWP_THEMES_DIR`, `LWP_IDENTITY_KITS_DIR`, `LWP_COMMONS_DIR` | User theme, Identity Kit and Commons preset catalogues |

Default series subdirectories live under the selected series root.
An explicit relative `--output path` is relative to the current working
directory, **not** to the series argument. Use absolute paths in pipelines
when the working directory is not fixed.

`--lang`, `--quiet`, `--verbose`, `--no-color`, `--timestamp` and `--dry-run`
can precede the command; the value nearest the command wins. `--quiet`
suppresses progress, not warnings or requested report values. `--verbose`
adds detail; `--timestamp` prefixes logs with RFC 3339 timestamps.
`--dry-run` journals writes without touching disk. `--option=value` and
`--option value` are equivalent. Unknown or misplaced options are fatal.
`--version` is a leading action, not a command modifier.

Shortcuts such as `build` also have canonical forms such as `series build`.
Retired spellings (`install`, `check`, `themes`, `theme-info`, `set-theme`,
`series-info`, `refresh-templates`, `themes-gallery`) fail with the replacement
command; do not use them in scripts. Run `python3 lightwebpres --help` for the
full command/option matrix, or `python3 lightwebpres build --help` for context.

### Shell completion

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

### When something does not work

| Symptom | Check or fix |
|---|---|
| `lightwebpres: command not found` | Use `python3 lightwebpres`, `./lightwebpres` or its actual path; a bare name needs `PATH` configuration. |
| `Permission denied` on Unix | `chmod +x lightwebpres`, or invoke through Python. |
| Windows cannot launch the file | Use `python lightwebpres` or the `py lightwebpres` launcher; Windows does not use the shebang. |
| `python3: command not found` | Try `python` or `py` and check its version; install Python 3.8+ if absent. |
| Target directory is not empty | Prefer a new directory. Inspect existing files before deliberately choosing `init --force`. |
| Interface language surprises you | Without an explicit language the browser chooses; use `--lang en` or `fr` to lock it (route 2). |
| A `field:` line is literal text | Fields must precede body prose (route 1). |
| A note definition is literal text | Move it out of a raw HTML block; labels allow letters, digits and underscores, not hyphens. |
| A note marker is not a link | Define it in the same locality; `audit` names unmatched calls. |
| A title or color ignores your edit | `resolve my-series page_title --article first-page.md` or `resolve my-series kicker.fg` shows the winning and losing levels. |
| An article is absent | Check registration, `status`, article tags and effective slides with `status` and `series tags`. |
| An old page remains online | Review local `clean`, then remove stale files on the host too (route 5). |
| `verify` reports drift after an unchanged build | Match rendering options; inline-image builds need a separate non-inline verification output. |
| Builder fails under `file://` or on `.mjs` | Serve the builder and check executable placement/MIME types (route 6). |

### Command routes

| Task | Commands and chapter |
|---|---|
| Create and preview | `init`, `demo`, `build`, `watch` (route 1) |
| Inspect content and names | `status`, `series tags`, `series slug`, `resolve`, `contract` (routes 1, 2, 5, 6) |
| Fill missing slide identities | `series slug set --dry-run`, then `series slug set` (route 1) |
| Select a presentation | `preset list/show`, `series preset`, `series preset set` (route 3) |
| Choose or carry themes | `theme list/show/gallery/create/migrate/vendor/path`, `series theme`, `series theme set` (route 3) |
| Compose an identity | `kit compose --dry-run`, then `kit compose` (route 3) |
| Check and remove stale output | `audit`, `verify`, `clean` (route 5) |
| Manage overrides | `template show/write/update` (route 5) |
| Discover syntax | `--help`, contextual `--help`, `--version`, `completion` (route 6) |

`theme create` additionally accepts `--label`, `--family`, `--source`,
`--note`, `--output` (a `<slug>.conf` destination) and `--force`.
`theme show --all` describes the catalogue; `--format json` makes reports
machine-readable. `theme vendor --force` replaces existing vendored snapshots.
`theme gallery --output path` chooses its HTML destination. These catalogue
operations are explicit: a normal build does not overwrite your theme files.

### Deeper reference

- **`SKILL.md`** (`agent/skills/lightwebpres/`) — the precise mechanics
  of the article format: every slide type and field, the meta block, the
  field/free-text switch, typography and its opt-outs, `series.json`
  wiring. Read it before writing or debugging an article by hand, or
  point an agent at it.
- [Guest sourced-presentation skill](agent/skills/sourced-presentation/SKILL.md)
  is an optional, independent editorial method, not a product requirement.
- **`specifications.md`** (in French) — the complete, authoritative
  reference: exact algorithms, every parser edge case, the full
  `series.json` and language-file schemas, the browser tool's internals.
- **`lightwebpres --help`** — every command, every flag, every
  environment variable.

- [GLOSSARY.md](GLOSSARY.md) lists field meanings, defaults and fallback chains.
