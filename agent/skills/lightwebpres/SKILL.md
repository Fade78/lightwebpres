---
name: lightwebpres
description: >
  Reference for the exact LightWebPres (LWP) Markdown syntax lightwebpres
  parses: the lwp:meta comment block, the four slide types (cover,
  standard, series-nav, full-article) and their fields (tag, h1/h2,
  summary, highlight, fact-label, source), the one-way field/free-text
  parsing switch, series.json wiring, and automatic non-breaking-space
  typography with its opt-outs (typo, typo-units, typo-thousands).
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

- `file` (output HTML filename) — `series.json` entry > this meta
  block's `file:` > `source` with `.md` swapped for `.html`.
- `page_title` (the `<title>` tag) — `series.json` > `page_title:` here >
  the cover slide's own `# Heading` > the resolved `file`.
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

Nothing in this chain is fatal — every field always resolves to
*something*, `card_label` included (it just ends up empty). See
`specifications.md` §20.3.1 for the authoritative version of this
cascade.

## Slide types

| Type | Fields | Cardinality |
|---|---|---|
| `cover` | `tag`, `h1` (or `# Title`), `summary` | Any number, anywhere — it's a layout style, not a structural marker. No fact-box: don't put free text after its fields, that's a fatal error. |
| standard (default, or explicit `<!-- lwp:slide -->`) | `tag`, `h2` (or `## Title`), `summary`, `highlight`, `highlight-caption`, `fact-label`, `source`, then free Markdown text | As many as you want |
| `series-nav` | none — generated from `series.json` | 0 or 1 per article |
| `full-article` | `article: filename.md` (required) | 0 or 1 per article |

`tag`, `summary`, `fact-label`, `source`, `highlight`/`highlight-caption`
are all optional — simplest to just omit the line if you don't need it
(an empty value behaves the same as omitting it, but there's no reason
to write it). `highlight` is a short standalone figure (a number, a
stat, a quote) with an optional caption underneath; it renders above the
free text, not instead of it.

The free Markdown text on a standard slide has two possible renderings,
picked automatically: with a `fact-label:` line, it's wrapped in a
labeled fact-box (`<div class="fact-box">` / `<div class="fact-label">`);
without one, it renders as plain paragraph(s) — no box, no label. Use
`fact-label:` when you want the highlighted-callout look, omit it for
ordinary body text.

`series-nav` and `full-article` are **at most one each** per article —
having two is a fatal build error, not "the second one wins."

## The full-article file

Referenced by `article:`, it's a separate `.md` file (by convention
`{name}_article.md`) with **no LWP structure at all** — just standard
Markdown: headings, `**bold**`/`*italic*`, `[links](url)`, footnotes
(`[^1]` + `[^1]: definition`), lists, tables, blockquotes (`> text`),
inline code (`` `code` ``), fenced code blocks (` ```lang ` ... ` ``` `,
the language optional and purely informational — no syntax
highlighting), and raw HTML passed through as-is (so an author can drop
in a hand-written `<figure>` or similar if the situation calls for it).

Code is the one exception to "nothing gets escaped": text inside
`` `...` `` or a ` ``` ` block is HTML-escaped and shown exactly as
written, even if it looks like a tag — the opposite of how raw HTML
elsewhere in this file passes through untouched. A `>` at the very start
of a line or a backtick that isn't meant to open a blockquote/code span
can be written literally by prefixing it with `\` (`` \> ``, `` \` ``) —
the only escaping this format supports, and only needed in that
position; a `>` anywhere else never triggers a blockquote and needs no
escaping.

Raw HTML at the start of a line is either an inline usage or a block,
decided per line: `<strong>Word</strong> opens a sentence.` — an inline
tag (`<a>`, `<strong>`, `<em>`, `<span>`, `<sup>`...) closed on that same
line — is ordinary paragraph text, merges with the next line like
anything else. Leave it unclosed (`<a href="..." class="card">` opening
a multi-line card, closed by `</a>` several lines later) and every line
in between is raw HTML verbatim until the matching close, even a line
that would look like a self-contained inline usage on its own
(`<span class="caption">...</span>` alone on its line, say).

## Typography: automatic non-breaking spaces (French only)

Under `--lang fr` (the default), `build` silently upgrades certain plain
spaces already present in the text to non-breaking ones: before
`; : ! ?`, after an opening `«`, before `%`, between groups of 3 digits
in a number you've already spaced out (`170 000`), between a number and
`million(s)`/`milliard(s)`/`dollar(s)`/`$`, and after `×`/`≈` before a
number. Nothing to do on your end — write ordinary spaces, the build
handles the rest. It never *inserts* spacing or digit grouping that
wasn't already there (don't add a space just to trigger the rule), and a
non-breaking space you type yourself always passes through unchanged.
`--lang en` has no typography rules at all — this is French-only.

This alters generated content, so it can be turned off per article, in
that article's meta block: `typo-units: off` (numbers/units and `×`/`≈`
rules only), `typo-thousands: off` (thousands-grouping rule only), or
`typo: off` (every rule, this article only). Leave these out unless
specifically asked to disable something — the default is what most
articles want.

## Adding an article to a series

Every article that should appear in navigation/index needs a matching
entry in `series.json`'s `articles` array — at minimum, just one
structural field:

```json
{"source": "apple-pie.md"}
```

`source` must be a **bare filename** — no `/`, no `..` — and is the only
field ever required directly in `series.json`. The array order is the
navigation/index order. `file`, if you give one, must be a bare filename
too; leave it out and it's derived from `source` (see "The meta block"
above for the full cascade).

Every other field — `file`, `page_title`, `card_title`/`card_desc`,
`card_label`, `nav_title`/`nav_desc` — is read from the article's own
meta block and content by default; add one to the `series.json` entry
only to override it for this particular article without touching the
file, e.g.:

```json
{"source": "apple-pie.md", "card_label": "Article 3 (corrected)"}
```

Nothing here is ever a fatal build error — every field resolves to
*something* down the cascade, `card_label` included (it just ends up
empty if it's absent everywhere).

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
- A bare `---` inside body text, expecting a visual divider — it splits
  the slide instead.
- Two `full-article` or two `series-nav` slides in one file.
- `file`/`source` values with a path (`articles/x.md` instead of `x.md`)
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
