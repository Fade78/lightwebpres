---
name: lightwebpres
description: >
  Write or edit an article in the LightWebPres (LWP) extended Markdown
  format — the slide-deck article format used by the lightwebpres static
  site generator (meta block, cover/standard/series-nav/full-article
  slides, highlight figures, fact-boxes, series.json). Use this skill
  whenever the user asks to write, draft, edit, or add an article for a
  LightWebPres series, mentions "LWP format", "slide deck article",
  "highlight field", "fact-box", or asks to add an entry to a
  lightwebpres series.json — even if they just say "write an article for
  my site" while already working inside a lightwebpres project (a
  `series.json` and a `lightwebpres` executable in the directory tree are
  a strong signal this skill applies). Do NOT use this for generic
  Markdown or blog-post writing unrelated to lightwebpres.
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
file: apple-pie.html
h1: The apple pie<br>What shortcrust pastry actually changes
series_title: The apple pie
series_desc: Pastry, baking, and plating
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

Almost entirely a recap for the human/tooling, not read by the build
engine — with one exception: `h1` is used for the `<title>` tag (falling
back to the output filename if absent). Everything else, **including
`file`**, is decorative: the actual output filename comes from
`series.json`'s `file` entry (see below), not from the meta block. Keep
`file` and the other fields (`series_title`, `series_desc`,
`index_number`, `index_title`, `index_desc`) matching the `series.json`
entry anyway — nothing enforces that they match, so a mismatch won't
error, it'll just be confusing to the next person reading the file.

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
(`[^1]` + `[^1]: definition`), lists, tables, and raw HTML passed through
as-is (so an author can drop in a hand-written `<figure>` or similar if
the situation calls for it — nothing here gets escaped).

Raw HTML at the start of a line is either an inline usage or a block,
decided per line: `<strong>Word</strong> opens a sentence.` — an inline
tag (`<a>`, `<strong>`, `<em>`, `<span>`, `<sup>`...) closed on that same
line — is ordinary paragraph text, merges with the next line like
anything else. Leave it unclosed (`<a href="..." class="card">` opening
a multi-line card, closed by `</a>` several lines later) and every line
in between is raw HTML verbatim until the matching close, even a line
that would look like a self-contained inline usage on its own
(`<span class="caption">...</span>` alone on its line, say).

## Adding an article to a series

Every article that should appear in navigation/index needs a matching
entry in `series.json`'s `articles` array:

```json
{"file": "apple-pie.html", "source": "apple-pie.md",
 "series_title": "The apple pie", "series_desc": "Pastry, baking, and plating"}
```

`file` and `source` must be **bare filenames** — no `/`, no `..`. The
array order is the navigation/index order. `index_title`/`index_desc` are
optional per-entry overrides for the index card, falling back to
`series_title`/`series_desc` when absent; `index_number` is independent
(a label like "Article 1") and simply doesn't appear on the card at all
if you leave it out — there's nothing for it to fall back to.

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

## Deeper reference

If `specifications.md` is present alongside this project, it's the
complete, authoritative specification (sections 4 and 6 for the format
itself, section 22 for every parser edge case) — consult it for anything
this skill doesn't cover.
