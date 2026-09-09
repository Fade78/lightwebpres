# Article Format

Read this when creating or changing an LWP source file. For free-text syntax
read [Text and Style](text-and-style.md); for registration, tags and presets
read [Series and Appearance](series-and-appearance.md). Return to the
[mission entry](SKILL.md) for scope and verification.

## Fields Before Prose

LWP joins two grammars. Structural scalar fields (`kicker:`, `summary:`,
`highlight:`, etc.) each occupy exactly one physical line. On slides,
`comment:` and `note:` accept indented continuation lines; no other field does.
Free text follows the limited converter described in Text and Style, not
generic CommonMark. Consecutive non-blank lines merge into a paragraph;
a blank line starts another paragraph.

The switch from fields to prose is **one-way and permanent within a slide**.
The first unrecognized non-blank header line starts the body. A later
`kicker: something` is text, not a field. Put all fields before body text.
Only the first `#` on a cover or `##` on a standard slide captures its title,
and only before the body begins. A second heading, or the wrong level, becomes
content. A bare `#` or `##` still declares an empty title.

A field is a value, not Markdown: `summary: some **bold**` publishes literal
markup. Raw HTML in field values passes through, which can disguise that
distinction. `audit` names paired bold, italic, backticks and Markdown links
in fields; `build` says nothing. Put Markdown emphasis in the body instead.
A duplicate field in the same header silently takes the last value; headings
do not share that override rule.

## File Anatomy

```markdown
<!-- lwp:meta -->
page_title: The apple pie<br>What shortcrust pastry actually changes
nav_title: The apple pie
nav_desc: Pastry, baking, and plating
---

<!-- lwp:slide:cover -->
slug: apple-pie-cover
kicker: Recipe
# The apple pie
summary: Nine things that make or break a homemade apple pie.

---

<!-- lwp:slide -->
slug: temperature
kicker: Baking
## Temperature changes everything
summary: An oven that's too hot cooks the surface before the center is ready.
fact-label: The takeaway
highlight: 180 °C
highlight-caption: recommended baking temperature for shortcrust pastry
source: Baking guide, 2024 edition.

An oven that's too hot browns the crust while the center stays raw.

A second paragraph, separated by a blank line, stays a second paragraph.

---

<!-- lwp:slide:series-nav -->
slug: series-links

---

<!-- lwp:slide:full-article -->
slug: apple-pie-long
article: apple-pie_article.md
```

The file must start with `<!-- lwp:meta -->`, followed by `key: value` lines
and a bare `---` closing the block. No non-blank content may precede it.
An empty meta block is valid. A bare `---` separates slides everywhere in
this file, including inside body text or a code example. Use `<hr>` for a
visual rule. `<!-- lwp:slide:TYPE -->` opens a typed slide; the standard
spelling is `<!-- lwp:slide -->` (explicit `<!-- lwp:slide:standard -->`
also works). A misspelt type is fatal and names the rank, token and four types.

## Metadata And Cascades

Every meta field is optional. An `articles[]` entry in `series.json` only
needs to repeat a field to override this file or its content-derived fallback.
The following chains run from strongest to weakest:

- `page_dest`: series entry > meta > `page_source` with `.md` replaced by `.html`.
- `page_title` (HTML title): series entry > meta > cover `# Heading` > resolved `page_dest`.
- `card_title` (index card): series entry > meta > resolved `page_title`.
- `card_desc` (index card): series entry > meta > cover `summary`.
- `card_label` (index card and this-series navigation): series entry > meta > empty.
- `nav_title` / `nav_desc` (cards embedded in other articles): series entry > meta > resolved `card_title` / `card_desc`.

Invalid `page_dest` values are fatal: not ending in `.html`/`.htm`, not a bare
filename (`sub/x.html` is rejected), a case-insensitive collision with another
article's destination, or `index.html` in a multipage series of several articles
when an index is generated. `--no-index` removes that last collision; single-page
mode has no separate index file and keeps `page_dest` as an article route key.
In multipage output, a series of exactly one article may choose `index.html`;
no series index is then generated and `build` prints `[no index]`. Leave the default article
filename when another page or generator owns that directory's index.
The normative cascade is in specifications.md §20.3.1; index ownership is
in §11.3.3. Single-page routes and restrictions are in §11.3.8 and
[Operations](operations.md).

Ask the engine rather than calculating a cascade by hand:

```bash
lightwebpres resolve <series-dir> page_title --article apple-pie.md
```

The report shows the deciding level and losing levels. A dotted name selects
a theme property, an underscore an article field, a hyphen a slide field.
Slide fields have no cascade: their report lists where they are set.
`--format json` is available for this report.

Editorial fields can be set in meta or in the series article entry:

- `author`: falls back to `series_meta.author`; appears in the footer byline and `<meta name="author">`.
- `license`: falls back to `series_meta.license`; appears as a footer licence line only.
- `date`: free text with no imposed format; joins the author in the footer only.
- `page_desc`: series entry > meta > cover `summary`; feeds `<meta name="description">`. `audit` warns if it resolves empty.
- `status: active` is the default participation state, not editorial approval.
- `status: draft` keeps the article out of normal pages, index and navigation, but in the inventory. `build --include-drafts` includes it with a preview banner.
- `status: ignored` keeps its settings but removes it from normal output under every build flag. Reports still count it in the ignored inventory; it cannot make output visible.

Only `active`, `draft` and `ignored` are valid status values; anything else
is fatal. `series.json` wins over meta. `audit` examines every listed article,
including ignored entries and drafts, rendering what it can without output.
Article-level `tags:` belongs in meta, not in the series article entry;
its visibility gate is explained in Series and Appearance.

The following settings belong in article meta or `series_meta`, **not** in
an `articles[]` entry:

- `notes_placement: local | page`: `local` (default) places bodies at the foot of the calling card or end of each long-form article. `page` collects them into a page-end section. Unknown values are fatal.
- `notes_tooltip: on | off`: `on` also puts the note body's text on the call as a tooltip; it never removes the body. Default `off`; combines with either placement. Unknown values are fatal.
- `slide_page_numbers: true | false`: opt-in engraved top-right `<span class="slide-num">NN / NN</span>`, except on generated `series-nav` furniture. Meta > `--slides-page-numbers on|off` > `series_meta.slide_page_numbers` > off. Invalid values are fatal. The always-on bottom-left live `X / N` counter is independent.
- `slug_prefix:`: a namespace before every card ID on the page; the article overrides the series value.

Unknown meta keys silently do nothing during `build`: `page-title:` does
not mean `page_title:`. `audit` names the unused key and suggests the nearest
field. `comment:` is recognized but never read or published. `style.*` is
the article property layer with its own fatal key/value validation, not an
unknown-meta warning. Valid properties can still compose unreadable output;
`audit` reports that under the article's filename. Text and Style covers this
layer and the `typo`, `typo_units`, `typo_thousands` opt-outs.

## Slide Types

| Type | Fields | Cardinality |
|---|---|---|
| `cover` | `slug`, `kicker`, `tags`, `# Title`, `summary`, `slide-layout`, `slide-header`, `slide-footer`, `comment`, `note` | Any number, anywhere; a layout style, not a structural marker. No free body: text after its fields is fatal. |
| standard (default, or explicit `<!-- lwp:slide -->`) | `slug`, `kicker`, `tags`, `## Title`, `summary`, `highlight`, `highlight-caption`, `fact-label`, `fact-variant`, `source`, `slide-layout`, `slide-header`, `slide-footer`, `comment`, `note`, then free Markdown text | As many as you want |
| `series-nav` | `slug`, `tags`, `slide-layout`, `slide-header`, `slide-footer`, `comment` | 0 or 1 per article; navigation generated from `series.json` |
| `full-article` | `slug`, `article: filename.md`, `tags`, `slide-layout`, `slide-header`, `slide-footer`, `comment` | Any number, each with its own file; `article` is required for publication. Explicit empty `article:` warns and omits the unfinished slide. |

All fields other than `slug` and `full-article`'s `article` are optional.
Ordinary empty scalars behave as absent; empty `tags:` receives `default`.
The three presentation fields have stricter empty-value rules in Series and
Appearance. An empty `article:` is an omitted draft slide; an absent line is
fatal. Several `full-article` slides are valid; under local placement each
numbers its own notes from 1. A second `series-nav` is fatal, never an override.
Neither type accepts free body text or a title; unrecognized non-blank lines
are fatal. `note:` is only for cover and standard slides.

`slug` is required on every card. It is a stable URL identity, not a rank or
title, and survives reordering, inserted/excluded cards and changed headings.
Use a readable name such as `slug: barrage-de-vajont`. The exact pattern is
`^[A-Za-z0-9][A-Za-z0-9._-]*$`; duplicate or reserved IDs are fatal, not silently
suffixed. The current reserved vocabulary is in the live `contract` report.
`series slug` lists effective names including `slug_prefix`, the addresses a
reader or printed QR code receives. `series slug set` writes random slugs
only where missing; it is the tool's article-editing command, unlike `build`.
Only run it within authorized source-edit scope and rename generated slugs
to readable identities before publication.

`highlight` is a short standalone number, statistic or quotation above the
body; `highlight-caption` adds its caption. Neither replaces body text.
`source:` renders a citation in a separate styled location. Prefer it for a
short reference and `[^1]` for a longer source note unless local conventions
say otherwise. Inline body citations are also legal; this is a layout
recommendation, not a parser restriction.

Cover slides parse standard-only `fact-label`, `fact-variant`, `source`,
`highlight` and `highlight-caption` but never render them. `build` and
rendering `audit` warn; the build still exits 0. Remove those fields when
using a cover. Only free text on a cover is fatal. A retired `tag:` field is
not an alias: use `kicker:` for the visible label or `tags:` for filtering.
On a standard slide `tag:` becomes body text; on a cover the error names
the two current choices.

On standard slides, `fact-label:` wraps the body in a labeled fact-box:
`<div class="fact-box">`, `<div class="fact-label">`, `<div class="fact-content">`.
Without it the body renders as plain paragraphs, not a box. Both use the
same converter as the full-article file: tables, verdict classes, notes,
blockquotes, code, links and raw HTML all work. Body headings are smaller
than the card's own title. Once the body starts, a heading is body content,
not a redefinition of that title (specifications.md §22.2).

## Comments And Speaker Notes

`comment:` is a source-only review note, accepted on every slide, in meta,
in a series entry and in `series_meta`. No renderer reads it. Unlike an
HTML comment in free text, it never reaches even the built HTML source.
This is suitable for a TODO or a source-check reminder, but publishing
the source repository would still expose it.

`note:` is a speaker cue, **published in hidden HTML**, not a source footnote:

```markdown
<!-- lwp:slide -->
slug: slide-two
kicker: Two
## Slide two
note: Mention the 2020 study; the audience asked for it last time.
  Follow up with the 2023 replication.

  If time runs short, skip the appendix.
```

On cover/standard slides a `note:` or `comment:` continuation begins with
whitespace. An indented blank line preserves a paragraph break; the first
non-indented non-empty line ends the block. Extra lines stay in the field,
not the visible body. Other fields are single-line values. In the example
above the blank line is unindented, so it does not itself add a paragraph
break to the note; indent it as well when a paragraph break is intended.

Press **N** to open the presenter panel with this slide's cue and the next
slide's title; press it again to close. The panel follows navigation in the
same page, not a private presenter window. A projected/shared screen shows
it too, and anyone with the HTML can read the notes. Never put confidential
content there. Ctrl/Cmd+P prints one slide per sheet with navigation chrome
removed and theme colours retained; inspect the PDF rather than assuming fit.

## Live Draft Contract

`lightwebpres contract [directory]` is the read-only authoring-client
interface. Its default JSON uses `lightwebpres.slide-draft/1`, generated
from the parser registry: four types, fields and order, required fields,
cardinalities, empty rules, reserved IDs and a draft source per type.
Skeletons include non-empty generated slugs; `--article file.md` avoids
slugs declared by an existing source. `--format text` gives a readable view.
Consume this contract rather than maintaining a second parser registry.
These are drafting scaffolds, not ready-to-publish examples: fill or remove
empty presentation fields, and supply the `article:` target when publishing
a full-article slide. Follow [Operations](operations.md) to validate the result.
