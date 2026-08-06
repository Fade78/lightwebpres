---
name: lightwebpres
description: >
  Reference for the exact LightWebPres (LWP) Markdown syntax lightwebpres
  parses: the lwp:meta comment block, the four slide types (cover,
  standard, series-nav, full-article) and their fields (tag, summary,
  highlight, highlight-caption, fact-label, source, comment — the title is
  written as a heading, there is no title field), the one-way
  field/free-text parsing switch, the editorial fields and the article
  status (active/draft/ignored), the
  comparison-table verdict classes, series.json wiring, and automatic
  non-breaking-space typography with its opt-outs (typo, typo_units,
  typo_thousands).
  Format mechanics only, not editorial writing — it doesn't decide what
  an article says, only how to encode it correctly. Use whenever someone
  writes, edits, or debugs a lightwebpres .md article or series.json
  entry, or mentions "LWP format", "slide deck article", "highlight
  field", "fact-box", "series-nav", "full-article", or
  typography/non-breaking spaces for a lightwebpres article — even
  without naming the skill, if series.json and a lightwebpres executable
  are present. Do NOT use for generic Markdown/blog-post writing or
  deciding an article's content.
---

# Writing LightWebPres (LWP) articles

LWP is a Markdown dialect for one specific job: a scrollable article made
of "slides" (cover, fact-cards, cross-article nav) followed by an
optional long-form piece. One `.md` file per article. The tool that
builds it (`lightwebpres`) is a single stdlib-only Python script — if
it's not obviously present in the project, ask before assuming it is.

## The one idea that matters most

LWP text is **two different grammars stitched together**, and mixing them
up is the single most common way to lose content silently:

1. **Structural fields** (`tag: ...`, `summary: ...`, `highlight: ...`,
   etc.) — each one is **exactly one physical line**. No wrapping, no
   continuation. If a value needs a line break, that's not a field
   anymore.
2. **Free Markdown text** — a standard slide's trailing body (fact-box or
   bare paragraphs, see "Slide types" below) and the full-article file.
   Ordinary CommonMark rules apply here: consecutive non-blank lines
   merge into one paragraph, a blank line starts a new paragraph.

The switch from (1) to (2) is **one-way and permanent within a slide**:
the moment a line in a slide's header isn't a recognized field, the
parser stops looking for fields entirely for the rest of that slide —
even a later line that looks exactly like `tag: something` is just text
from then on. So: put every field before any body text, one per line,
and never expect a field to wrap.

A **duplicated field** in the same header is not an error: the last
occurrence wins, silently — deliberate override semantics (like CSS or
Make) so a build system can assemble a slide by concatenating a base
fragment and an overriding one. Headings differ: only the first `#` (on
a cover) / `##` (elsewhere) is captured as the slide's title, later ones
fall through to content.

## Anatomy of a file

```markdown
<!-- lwp:meta -->
page_title: The apple pie<br>What shortcrust pastry actually changes
nav_title: The apple pie
nav_desc: Pastry, baking, and plating
---

<!-- lwp:slide:cover -->
tag: Recipe
# The apple pie
summary: Nine things that make or break a homemade apple pie.

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
most common mistake in a homemade pie. A second paragraph, separated by
a blank line, stays a second paragraph.

---

<!-- lwp:slide:series-nav -->

---

<!-- lwp:slide:full-article -->
article: apple-pie_article.md
```

- The file **must** start with `<!-- lwp:meta -->`, immediately followed by
  `key: value` lines, then a bare `---` line closing the block. Nothing
  else is allowed before it.
- `---` alone on its own line separates slides everywhere in the file —
  including inside a fact-box's free text, where it still means "new
  slide," not "horizontal rule." Use inline `<hr>` if you actually want a
  rule inside body text.
- `<!-- lwp:slide:TYPE -->` opens a slide; omit `TYPE` (just `<!-- lwp:slide -->`)
  for a standard slide.

## The meta block

Every field here is optional and falls back to something derived from
the article's own content, so a minimal article needs none of them at
all. `series.json`'s `articles` entry for this file only needs to repeat
a field when you want it to win over what's set here (or over the
content-derived fallback) — not as a rule for every entry. The full
chain, cheapest to most specific:

- `page_dest` (output HTML filename) — `series.json` entry > this meta
  block's `page_dest:` > `page_source` with `.md` swapped for `.html`.
- `page_title` (the `<title>` tag) — `series.json` > `page_title:` here >
  the cover slide's own `# Heading` > the resolved `page_dest`.
- `card_title`/`card_desc` (this article's card on the **index page**) —
  `series.json` > `card_title:`/`card_desc:` here > resolved
  `page_title` (for the title) / the cover slide's own `summary:` (for
  the description).
- `card_label` (short label on the index card **and** the "This series"
  nav block on every article's own page) — `series.json` >
  `card_label:` here > empty (no error if it never resolves to anything).
- `nav_title`/`nav_desc` (this article's card when it appears in the
  cross-article navigation embedded in a **different** article's page)
  — `series.json` > `nav_title:`/`nav_desc:` here > resolved
  `card_title`/`card_desc`.

Every field in that chain resolves to *something*, `card_label` included
(it just ends up empty) — **except `page_dest`, which has four fatal
cases**: a value that doesn't end in `.html`/`.htm`, a value that isn't a
bare filename (`sub/x.html` is rejected wherever it comes from), two
articles resolving to the same output name (compared case-insensitively),
and — in a series of **several** articles — the name `index.html`, which
is where the series index goes (§11.3.3). Any of the four stops the build
with a named error. See `specifications.md` §20.3.1 for the authoritative
version of this cascade.

A series of **exactly one** article may take `index.html`, and that is
the way to make a single article the page a directory serves: the
article gets the name, no series index is generated (an index listing one
entry adds nothing), and `build` says so on a `[no index]` line. Leave
the default name instead when the article is a brick in a directory whose
`index.html` is kept some other way — by hand, by another generator, or
because other articles already live there. The name chosen is the
statement of intent, so choose it.

You never have to reason a cascade out by hand. `lightwebpres resolve
<dir> page_title --article this-file.md` prints the value in force, the
level that decided it, and every level that did not — which is the fast
way to see that the line you just wrote is being beaten by a
`series.json` entry. The shape of the name picks the cascade: a dot is a
theme property, an underscore an article field, a hyphen a slide field.
`--format json` if you are parsing it.

**Editorial fields**, settable here or in `series.json`, both displayed
and emitted as `<meta>` tags:

- `author`, `license` — fall back to `series_meta`'s values for the whole
  series. They render in the page footer as a byline and a licence line.
- `date` — free text, no format imposed; it joins the author in the
  byline.
- `page_desc` — feeds `<meta name="description">`. Cascade:
  `series.json` > here > the cover slide's `summary`. It is the one field
  `audit` actively complains about when it resolves to nothing.
- `status: active | draft | ignored` — what this article is worth to the
  series (`active` when absent; `series.json` wins over this file).
  `status: draft` keeps it out of the output — no page, no index card, no
  navigation entry — while it still counts as an article of the series;
  `build --include-drafts` builds it anyway, with a banner on the page so
  a preview is never mistaken for a publication. `status: ignored` takes
  it out of the chain altogether: never built whatever the flags, never
  listed, never counted, and the entry survives with every field on it —
  which is how you set an article aside without losing its settings. Any
  other value is a fatal error.

**Notes fields**, settable here or in `series_meta` (the article wins):

- `notes_placement: local | page` — where note bodies land. `local`
  (default) puts them at the foot of the unit that called them: the foot
  of that card, the end of the long-form article. `page` collects every
  body on the page into one notes section at the end. An unknown value is
  a fatal build error naming the article.
- `notes_tooltip: on | off` — `on` also puts the body's text on the call
  as a tooltip. It composes with either placement and is never the only
  carrier: the body stays in the document regardless. Off by default.

**A key this block does not recognize is accepted in silence** — no
error, no warning, and no effect. `page-title:` instead of `page_title:`
builds cleanly and falls back as though you had written nothing. This is
the opposite of a mistyped *slide* field, which becomes free text and is
loud on a cover slide. Check spelling against the list above; `audit`
will not catch it for you.

`comment:` here works too, for an article-wide note — same rule as the
per-slide one below: recognized, never read, never published.

## Slide types

| Type | Fields | Cardinality |
|---|---|---|
| `cover` | `tag`, `# Title`, `summary`, `comment` | Any number, anywhere — it's a layout style, not a structural marker. No fact-box: don't put free text after its fields, that's a fatal error. |
| standard (default, or explicit `<!-- lwp:slide -->`) | `tag`, `## Title`, `summary`, `highlight`, `highlight-caption`, `fact-label`, `fact-variant`, `source`, `comment`, then free Markdown text | As many as you want |
| `series-nav` | none — generated from `series.json` | 0 or 1 per article |
| `full-article` | `article: filename.md` (required) | 0 or 1 per article |

`tag`, `summary`, `fact-label`, `source`, `highlight`/`highlight-caption`
are all optional — omit the line if you don't need it. An empty value
behaves like omitting it everywhere **except on a cover slide**, where
the parser tests whether a field was *set*, not whether it has content:
a bare `fact-label:` on a cover raises a warning that omitting the line
would not. `highlight` is a short standalone figure (a number, a stat, a
quote) with an optional caption underneath; it renders above the free
text, not instead of it.

A cover slide **accepts** `fact-label`, `source`, `highlight` and
`highlight-caption` without failing, and then never renders them — you
get a `[WARNING]`, exit code 0, and a page missing what you wrote. Only
free *text* on a cover is fatal.

`<!-- lwp:slide:TYPE -->` is validated: a misspelt type
(`lwp:slide:standrd`) is a fatal build error naming the slide's rank, the
token, and the four types.

`comment` is a review note — recognized as a real field on any slide
(and in `series.json`/the article's own meta block too), but never read
by any renderer. It never reaches the built output, not even the page's
raw HTML source — unlike an HTML comment (`<!-- ... -->`) written in
free text, which passes through untouched (still shipped, just invisible
on screen). Use it for an editorial note, a TODO, a "verify this stat"
flag — anything that must stay in the source without ever publishing.

The free Markdown text on a standard slide has two possible renderings,
picked automatically: with a `fact-label:` line, it's wrapped in a
labeled fact-box (`<div class="fact-box">` / `<div class="fact-label">` /
`<div class="fact-content">`); without one, it renders as plain
paragraph(s) — no box, no label. Use `fact-label:` when you want the
highlighted-callout look, omit it for ordinary body text.

**That free text goes through the same Markdown converter as the
full-article file** — everything listed under "The full-article file"
below works here too: tables (including the verdict classes), notes,
blockquotes, code spans and fenced blocks, links, raw HTML. Headings are
styled smaller than the slide's own big title to fit the fact-box's
frame. One trap to know about: a heading opening
the free text directly (no paragraph before it) is still just content,
*not* a redefinition of the slide's own title — but only the first `#`
on a `cover` / first `##` on a non-`cover` slide is ever captured as the
slide's title at all; a second one, or the wrong level for that slide
type, always falls through to content (§22.2 in `specifications.md`).

`series-nav` and `full-article` are **at most one each** per article —
having two is a fatal build error, not "the second one wins." Any
unrecognized non-blank line inside either one is also fatal, not ignored:
a `series-nav` slide takes no fields at all, and a `full-article` slide
takes `article:` and nothing else.

Those four names are the whole list. A marker naming anything else is a
fatal build error citing the slide's rank, the token you wrote, and the
four names — `<!-- lwp:slide:covre -->` does not quietly become a
standard slide.

## The full-article file

Referenced by `article:`, it's a separate `.md` file (by convention
`{name}_article.md`) with **no LWP structure at all** — just standard
Markdown: headings, `**bold**`/`*italic*`, `[links](url)`, notes
(`[^label]` + `[^label]: body` — see "Notes" below), lists, tables,
blockquotes (`> text`),
images (`![alt](img/pic.png)` — alone on its line it becomes a centered
`<figure>` block, and a standard Markdown title, `![alt](src "Caption")`,
renders as a small centered caption under the image; wrap that whole line
in a Markdown link, `[![alt](src "Caption")](https://…)`, and the picture
becomes clickable while the caption stays outside the link — so the link's
accessible name is the alt text alone, not alt plus caption;
mid-paragraph it's a plain inline `<img>`, no caption; the path is
relative — images live in `articles/img/`, copied to `public/img/` at
build), inline code
(`` `code` ``), fenced code blocks (` ```lang ` ... ` ``` `, the
language optional and purely informational — no syntax highlighting),
and raw HTML passed through as-is (so an author can drop in a
hand-written `<figure>` or similar if the situation calls for it).

**`&` is escaped in all ordinary text**, not only in code — so an HTML
entity you type by hand (`&rarr;`, `&nbsp;`) is published as the literal
string `&rarr;`, not as an arrow. The only place one survives is inside a
raw-HTML *block* (see below), which bypasses inline conversion entirely.
Write the character itself (`→`) rather than an entity; the format is
UTF-8 throughout.

Code goes further: text inside `` `...` `` or a ` ``` ` block is fully
HTML-escaped and shown exactly as written, even if it looks like a tag —
the opposite of how raw HTML elsewhere in this file passes through
untouched. A `>` at the very start
of a line or a backtick that isn't meant to open a blockquote/code span
can be written literally by prefixing it with `\` (`` \> ``, `` \` ``) —
the only escaping this format supports, and only needed in that
position; a `>` anywhere else never triggers a blockquote and needs no
escaping.

Four limits the converter does not announce:

- **A Markdown link must be `http://` or `https://`.** `[text](page.html)`
  or a `mailto:` matches nothing and is published as that literal text,
  with no warning. Use a raw `<a href="...">` for anything else.
- **Headings stop at `###`.** `####` and deeper are published as literal
  paragraph text, hashes included.
- **Blockquotes are one paragraph.** Consecutive `>` lines merge into a
  single `<p>` inside one `<blockquote>`; multi-paragraph and nested
  quotes are not supported.
- **Table alignment colons are accepted and ignored.** `|:---|---:|`
  parses, and changes nothing. Ragged rows are emitted as written, with
  no cell-count check.

Raw HTML at the start of a line is either an inline usage or a block,
decided per line: `<strong>Word</strong> opens a sentence.` — an inline
tag (`<a>`, `<strong>`, `<em>`, `<span>`, `<sup>`...) closed on that same
line — is ordinary paragraph text, merges with the next line like
anything else. Leave it unclosed (`<a href="..." class="card">` opening
a multi-line card, closed by `</a>` several lines later) and every line
in between is raw HTML verbatim until the matching close, even a line
that would look like a self-contained inline usage on its own
(`<span class="caption">...</span>` alone on its line, say).

## Notes

Standard Markdown, nothing invented:

```markdown
The kettle draws about 3 kW[^kwh] on a domestic ring.

[^kwh]: Measured at 230 V, 13 A. See the appliance's rating plate.
```

Works in a slide's free text and in the full-article file. **The label is
a key, not content** — `[^kwh]`, `[^1]`, `[^a]` are all fine, none of them
reaches the page, and what the reader sees is a position. So you never
have to renumber anything when you insert a note.

The call becomes a link to the body; the body carries a link back to the
call. One label called twice gives one body with two return links.

**Numbering restarts with whatever unit holds the bodies.** Under the
default `local` placement that means each card starts again at 1, while
the long-form article runs continuously through itself. That is on
purpose: a card is individually shareable, so a reader can arrive at card
5 having seen nothing else, and a note numbered 7 there would send them
hunting for six that are not on their screen.

Three things `audit` will tell you about, none of them fatal:

- a call with no body — the marker still renders, but as no link at all;
- a body nothing calls — it still renders, at the end of the block,
  with no return link;
- a definition written inside a raw HTML block (a `<div class="refs">`,
  typically) — raw HTML is passed through verbatim, so it ships as the
  literal text `[^1]: …`. Put note bodies outside your raw HTML.

Practical note for `local`: notes at the foot of a card take room on a
screen that is already short. A card carrying five of them will scroll.

## Per-slide look: `fact-variant`

`fact-variant: warning` on a standard slide adds `fact--warning` to that
slide's fact-box classes. The source names a *meaning*; what it looks like
is defined by the series (a `.fact--warning` rule in
`templates/custom.css`), so changing themes carries the variant along.
The name must match `[a-z][a-z0-9-]*` — anything else is a fatal build
error naming the file. Only meaningful together with `fact-label:` (no
fact-box, no class to hook).

## Instance tags: character-level styling beyond Markdown

Format-defined tags for one-off interventions inside any free text (slide
bodies and the full-article file). They go through the compiler: a bad
value is a fatal build error naming the file, and `audit` counts them per
article — they are author decisions that survive every theme change.

| Tag | Effect |
|---|---|
| `{color:#E8A33D}…{/color}` | colour literal (3/4/6/8-digit hex, normalized to ARGB) |
| `{color:mark}…{/color}` | a shared colour by name (`page`, `ink`, `ink-quiet`, `mark`, `call`, `affirm`) |
| `{font:mono}…{/font}` | a shared stack by name (`text`, `display`, `ui`, `mono`), or a literal stack ending on a CSS generic |
| `{sc}…{/sc}` | small caps |
| `{strike}…{/strike}` | strikethrough |
| `{u}…{/u}` | underline |
| `{mono}…{/mono}` | monospace (the `font.mono` stack) |

**Alignment is the one block tag**, because `text-align` is a block
property: on the inline `<span>` every other tag produces it does nothing.
Opener and closer each go alone on their own line, and they wrap whole
paragraphs:

```
{align:center}
This paragraph is centred.

So is this one.
{/align}
```

Values are `left | center | right | justify`. Alignment sets alignment and
nothing else: breaking words at end of line is a separate axis,
`page.hyphens` (`manual | auto`, default `manual`), and it is never turned
on for you. Everything inside the block aligns, including table cells,
which is what makes the tag able to override a component's own alignment.
A closer with no opener stays literal text.

Tags nest, and Markdown inside them still converts. An opener without its
closer on the same line stays literal text — visible in the render. Inside
`` `code` `` spans nothing is ever a tag. Prefer a `fact-variant` or a
settings.conf property for anything that repeats; the tag is the tool for
the one place that needs it.

## Per-article style: `style.*` meta keys

Any `style.<property>: value` line in the lwp:meta block restyles that
page only, over the series' theme and settings — same vocabulary and
types as `templates/settings.conf` (e.g. `style.verdict.partial.fg:
#8A4B00`, `style.cover.bg.angle: 90deg`). A bad key or value is a fatal
build error naming the file.

## Styling hooks you reach with raw HTML

Some things the stylesheet renders have no Markdown syntax at all, and
inline HTML is the documented way to reach them (spec §6.1). They work in
a fact-box and in the full-article file alike.

**Comparison-table verdicts.** Every generated table carries
`class="comparison-table"`. Put one of these on a cell — or on a `<span>`
inside a Markdown cell — and it renders with a shape marker as well as a
colour, so the verdict survives greyscale and colour-vision deficiency:

| Class | Meaning | Marker |
|---|---|---|
| `yes` | does / holds | ● filled circle |
| `no` | does not | ○ empty circle |
| `partial` | partly, with conditions | ◐ half circle |

```markdown
| Feature | A | B |
|---|---|---|
| Offline | <span class="yes">Yes</span> | <span class="no">No</span> |
```

Two more emphasize a whole column rather than a cell, applied to the
`<th>`: `col-signal` (the column that carries the comparison's point) and
`col-snap` (a column meant to be read at a glance). Reaching those means
writing the whole table in raw HTML, since Markdown cannot put a class on
a header cell.

**`.refs`** — a small-print block for a reference list at the end of a
full-article file: `<div class="refs">…</div>`.

## Raw HTML inside a field value

A field value may contain inline HTML, and `page_title` is the usual
reason: `page_title: The apple pie<br>What pastry changes` gives the
index card a two-line title. Where that value is used as *text* rather
than markup — the `<title>` element, the `<meta name="description">`,
the index card's own `title` attribute — tags are stripped and replaced
by a space, so the same value reads correctly in both places. Nothing
else is stripped: an unclosed tag in a field value ends up in the page.

## Typography: automatic non-breaking spaces (French only)

Under `--lang fr` (the default), `build` silently upgrades certain plain
spaces already present in the text to non-breaking ones: before
`; : ! ?` **and before a closing `»`**, after an opening `«`, before
`%`, between groups of 3 digits
in a number you've already spaced out (`170 000`), between a number and
`million(s)`/`milliard(s)`/`dollar(s)`/`$`, and after `×`/`≈` before a
number. Nothing to do on your end — write ordinary spaces, the build
handles the rest. It never *inserts* spacing or digit grouping that
wasn't already there (don't add a space just to trigger the rule), and a
non-breaking space you type yourself always passes through unchanged.
`--lang en` has no typography rules at all — this is French-only.

This alters generated content, so it can be turned off per article, in
that article's meta block: `typo_units: off` (numbers/units and `×`/`≈`
rules only), `typo_thousands: off` (thousands-grouping rule only), or
`typo: off` (every rule, this article only). Leave these out unless
specifically asked to disable something — the default is what most
articles want.

## Adding an article to a series

Every article that should appear in navigation/index needs a matching
entry in `series.json`'s `articles` array — at minimum, just one
structural field:

```json
{"page_source": "apple-pie.md"}
```

`page_source` must be a **bare filename** — no `/`, no `..` — and is the
only field ever required directly in `series.json`. The array order is the
navigation/index order. `page_dest`, if you give one, must be a bare
filename too; leave it out and it's derived from `page_source` (see "The
meta block" above for the full cascade). The pre-v1.0 names
`source`/`file` are rejected with an explicit migration error.

Every other field — `page_dest`, `page_title`/`page_desc`,
`card_title`/`card_desc`,
`card_label`, `nav_title`/`nav_desc` — is read from the article's own
meta block and content by default; add one to the `series.json` entry
only to override it for this particular article without touching the
file, e.g.:

```json
{"page_source": "apple-pie.md", "card_label": "Article 3 (corrected)"}
```

Most of these resolve down the cascade and cannot fail — but four things
here are fatal, and they are the ones worth checking before you call a
file done:

- `page_source` must end in `.md`, and the file it names must exist in
  `articles/`.
- an explicit `page_dest` must end in `.html` or `.htm`, and must be a
  bare filename.
- two entries must not resolve to the same `page_dest` (case-insensitive).
- a `full-article` slide's `article:` target must be a bare filename too,
  must resolve inside `articles/`, and must exist. A symlink pointing out
  of that directory is refused.

Any non-string value for one of these fields is fatal as well.

`series_meta`, the object beside `articles`, holds what belongs to the
series rather than to one article: `title`, `subtitle`, `version`,
`intro`, `author`, `license`. The first four drive the generated index
page and `README.md`; the last two are the fallback for every article's
byline and licence line.

```json
{
  "series_meta": {"title": "My series", "intro": "What it is about."},
  "articles": [{"page_source": "apple-pie.md"}]
}
```

`comment` also works as a `series.json` entry key, or in `series_meta`
for a note about the series as a whole — same rule: recognized, never
read, never published.

## Always verify before calling it done

Writing valid-looking LWP is not the same as writing LWP that builds.
Run the tool on what you just wrote — this is the only reliable way to
know it's actually correct, and it catches the mistakes above
immediately instead of leaving them for a human to discover later:

```bash
lightwebpres audit <series-dir>   # non-blocking editorial warnings (e.g. no cover slide)
lightwebpres build <series-dir>   # fatal on real structural errors
```

A clean `build` (exit code 0) with no `[ERROR]` lines means the file
parses and renders. If the executable isn't available in this
environment, say so explicitly rather than presenting unverified output
as finished — don't guess at whether it would build.

## Common mistakes to avoid

- Wrapping a field value across two lines expecting it to join — it
  won't; the second line becomes free text instead (a fatal build error
  on a `cover` slide, since it has no fact-box for that text to go into
  — at least you'll get a clear error, not silent data loss).
- Writing `tag:`, `summary:`, etc. **after** the fact-box body has
  started — those lines are already free text at that point, not fields.
  Same for a `#`/`##` heading appearing after body content has started:
  it becomes a heading rendered *inside* the fact-box, not a rewrite of
  the slide's own title.
- A bare `---` expecting a visual divider. In the LWP `.md` it **splits
  the slide**. In the full-article `.md` it does something worse: the
  line is **dropped silently** — no `<hr>`, no split, nothing at all.
  Write `<hr>` in both cases.
- Typing an HTML entity (`&rarr;`, `&nbsp;`) in body text and expecting
  it to render — `&` is escaped, so the reader sees the source. Write the
  character.
- A Markdown link to anything that isn't `http(s)` — it stays literal.
- Two `full-article` or two `series-nav` slides in one file.
- `page_source`/`page_dest` values with a path (`articles/x.md` instead of `x.md`)
  or anything that isn't a plain filename.
- Opening a ` ``` ` code fence without a matching closing ` ``` ` —
  every line after it, including the rest of the file, is swallowed as
  code content instead of being parsed. A fatal build error catches
  this (an unclosed tag), not silent data loss, but it's easy to trigger
  by mistake when editing a code block's contents.

## Deeper reference

This skill covers only the LWP article format — writing and editing
`.md` files. It's deliberately kept narrow to stay light on context; it
does not cover installing, choosing a theme, building, verifying with
`check`/`audit`, refreshing templates, or deploying. For all of that, if
`GUIDE.md` is present alongside this project, read it — it's the full
walkthrough, in the order it's actually needed.

For the article format itself, if `specifications.md` is present
alongside this project, it's the complete, authoritative specification
(sections 4 and 6 for the format itself, section 22 for every parser
edge case) — consult it for anything this skill doesn't cover.
