---
name: lightwebpres
description: >
  The exact LWP article syntax the lightwebpres tool parses: the lwp:meta
  block, the four slide types and their fields, series.json wiring, and the
  automatic non-breaking-space typography. Format mechanics, not editorial
  advice. Use when writing, editing or debugging a lightwebpres .md article
  or series.json entry — including when nobody names this skill, if a
  series.json and a lightwebpres executable are present, or the text
  mentions LWP format, a slide deck article, fact-box, highlight,
  series-nav or full-article. Not for generic Markdown or blog writing, and
  not for deciding what an article says.
---

# Writing LightWebPres (LWP) articles

LWP is a Markdown dialect for one specific job: a scrollable article made
of "slides" (cover, fact-cards, cross-article nav) followed by an
optional long-form piece. One `.md` file per article. The tool that
builds it (`lightwebpres`) is a single stdlib-only Python script — if
it's not obviously present in the project, ask before assuming it is.
It is published at <https://github.com/Fade78/lightwebpres>; that is
where to download it from, and the only address to trust for it.

## The one idea that matters most

LWP text is **two different grammars stitched together**, and mixing them
up is the single most common way to lose content silently:

1. **Structural fields** (`kicker: ...`, `tags: ...`, `summary: ...`, `highlight: ...`,
   etc.) — each scalar field is **exactly one physical line**. The two
   review/presenter fields `comment:` and `note:` may have indented
   continuation lines; no other field does.
2. **Free Markdown text** — a standard slide's trailing body (fact-box or
   bare paragraphs, see "Slide types" below) and the full-article file.
   Ordinary CommonMark rules apply here: consecutive non-blank lines
   merge into one paragraph, a blank line starts a new paragraph.

The switch from (1) to (2) is **one-way and permanent within a slide**:
the moment a line in a slide's header isn't a recognized field, the
parser stops looking for fields entirely for the rest of that slide —
even a later line that looks exactly like `kicker: something` is just text
from then on. So: put every field before any body text, one per line,
and never expect a field to wrap.

**And a field is a value, not Markdown.** `summary: un **gras**` publishes
the five characters. What misleads is that a field passes **raw HTML**
through untouched (`page_title: A<br>B`), so markup appearing to "work"
there says nothing about Markdown. `audit` names a field carrying a
`**bold**` pair, an `*italic*` pair, a backtick pair or a `[text](url)`
link; `build` says nothing. Write the emphasis in the free text below, or
in the full-article file.

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
kicker: Recipe
# The apple pie
summary: Nine things that make or break a homemade apple pie.

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
  other value is a fatal error. `audit` is the exception to all of it: it
  excludes nothing, drafts least of all, and renders them like the rest —
  so keeping an article in `draft` while you work on it costs you no
  checking.

**Notes fields**, settable here or in `series_meta` (the article wins):

- `notes_placement: local | page` — where note bodies land. `local`
  (default) puts them at the foot of the unit that called them: the foot
  of that card, the end of the long-form article. `page` collects every
  body on the page into one notes section at the end. An unknown value is
  a fatal build error naming the article.
- `notes_tooltip: on | off` — `on` also puts the body's text on the call
  as a tooltip. It composes with either placement and is never the only
  carrier: the body stays in the document regardless. Off by default.

**Slide-number field** (opt-in, off by default):

- `slide_page_numbers: true | false` — shows the engraved top-right
  `<span class="slide-num">NN / NN</span>` on every slide. Resolves down
  the same cascade shape as the other article fields: the article's
  front-matter wins over the `--slides-page-numbers on|off` CLI flag, which
  wins over `series_meta.slide_page_numbers` in `series.json`, which wins
  over the built-in default (`off`). An invalid value is a fatal build
  error naming the article. This is **not** the always-on bottom-left live
  `X / N` counter — that one needs no setting and is never suppressed.

**A key this block does not recognize has no effect, and the build says
nothing.** `page-title:` instead of `page_title:` builds cleanly and
falls back as though you had written nothing. This is the opposite of a
mistyped *slide* field, which becomes free text and is loud on a cover
slide.

`audit` is what catches it: it names the key, says nothing reads it, and
offers the nearest real field name. It warns and never blocks, so the
build stays silent either way — run `audit` after editing a meta block.
`comment:` and `style.*` keys are never reported *as unknown keys*:
nothing resolves the first, and the second is the article property layer,
which has its own vocabulary and its own fatal errors. `style.*` is not
out of `audit`'s reach, though: a key and a value that are both valid but
compose an unreadable page — text the colour of its ground, a size under
the readability floor — get named, under this article's filename.

`comment:` here works too, for an article-wide note — same rule as the
per-slide one below: recognized, never read, never published.

## Slide variants: `tags:`

`tags:` is a slide-level variant field, separate from the inline instance tags
described later. Its value is one physical line containing space-separated
names. Names are normalized case-insensitively; Unicode word characters,
digits, `-`, and `_` are accepted, except a name may not begin with `_`.

- No `tags:` or an empty value assigns `default`, the shared variant.
- `tags: excluded` removes the slide during build, after its slide type has
  been validated but before the rest of the slide is validated and before
  numbering or anchors are generated.
- Other values are emitted as `data-tags="..."` on the slide section.
- In the generated page, press **L** to choose a tag when at least two exist.
  The selected tag keeps its own slides and `default` slides, and is persisted
  in `localStorage['lwp-active-tag']`.

The former visible-label field `tag:` is not an alias. Use `kicker:` for the
label above a slide title, and `tags:` for variant filtering. On a standard
slide an old `tag:` line becomes body text; on a cover, `build` reports the
unknown field and prints the two current choices.

If tags select different languages, declare their typography packs in
`series.json`:

```json
{
  "series_meta": {
    "lang_tags": {"fr": "fr", "en": "en"}
  },
  "articles": [{"page_source": "guide.md"}]
}
```

The first mapped language tag on a slide selects its pack. Slides without one
use the build-wide `--lang`/`LWP_LANG` fallback. `audit` warns about malformed
slide tags and missing mapped packs; it does not block the build.

## Slide types

| Type | Fields | Cardinality |
|---|---|---|
| `cover` | `kicker`, `tags`, `# Title`, `summary`, `comment`, `note` | Any number, anywhere — it's a layout style, not a structural marker. No fact-box: don't put free text after its fields, that's a fatal error. |
| standard (default, or explicit `<!-- lwp:slide -->`) | `kicker`, `tags`, `## Title`, `summary`, `highlight`, `highlight-caption`, `fact-label`, `fact-variant`, `source`, `comment`, `note`, then free Markdown text | As many as you want |
| `series-nav` | `tags`, `comment` — navigation generated from `series.json` | 0 or 1 per article |
| `full-article` | `article: filename.md` (required), `tags`, `comment` | Any number — each carries its own file. Under `notes_placement: local` each one numbers its notes from 1, as a card does. |

`kicker`, `tags`, `summary`, `fact-label`, `fact-variant`, `source`,
`highlight`/`highlight-caption`, `comment`, and `note` are all optional — omit
the line if you don't need it. An empty value
behaves like omitting it everywhere **except on a cover slide**, where
the parser tests whether a field was *set*, not whether it has content:
a bare `fact-label:` on a cover raises a warning that omitting the line
would not. `highlight` is a short standalone figure (a number, a stat, a
quote) with an optional caption underneath; it renders above the free
text, not instead of it.

**The `source` field on a standard slide** is the designated place for
the slide's citation. Write the reference there (e.g. `source: Baking
guide, 2024 edition.`). You may optionally refer to it in the fact-box
text with a short callout (e.g. `[see source]` or a note marker `[^1]`),
but **do not write the full citation inline in the fact-box body**. The
rendered page displays the `source` field in a consistent, styled location
separate from the fact content — inline citations break that layout and
are not accessible in the same way. For longer references, use a note
(`[^1]`) whose body goes to the foot of the card (default) or the page
end (`notes_placement: page` in the meta block).

A cover slide **accepts** `fact-label`, `fact-variant`, `source`, `highlight`
and `highlight-caption` without failing, and then never renders them — you
get a `[WARNING]` — from `build`, and from `audit` too, which
renders — exit code 0, and a page missing what you wrote. Only
free *text* on a cover is fatal.

**Cover slides only accept** `kicker`, `tags`, `# Title`, `summary`,
`comment`, and `note` as their own header fields. Any standard-slide field
(`highlight`, `highlight-caption`, `fact-label`, `fact-variant`, `source`)
is parsed but **never rendered** on a cover — the build warns and continues.
This is deliberate so you can toggle a slide between `cover` and `standard`
while drafting without a build failure. When the slide is a cover, remove
those standard-only fields; they do nothing.

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

`series-nav` is **at most one** per article — having two is a fatal build
error, not "the second one wins." `full-article` has no such limit: a page
may pull in several long-form files, each `full-article` slide naming its
own (§22.8). Both also
accept `tags:` and `comment:` like every other slide; beyond that, any
unrecognized non-blank line inside either one is fatal, not ignored: a
`series-nav` slide takes no free body, and a `full-article` slide takes
`article:` plus those two optional fields.

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
- **Headings go up to level 6.** `#`–`###` are real headings; `####`
  renders as a bold-font paragraph (a sub-heading look, **not** `<strong>`
  markdown emphasis — it uses the bold typeface, not bold weight on
  emphasized text); `#####` and `######` render as plain paragraphs. None
  are left as literal text.
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
a key, not content** — what the reader sees is a position, so you never
have to renumber anything when you insert a note.

**A label is word characters only.** Letters, digits and `_`, accents and
non-Latin scripts included — and nothing else: no `-`, no space, no
punctuation. `[^kwh]`, `[^1]`, `[^a]`, `[^clé]` are labels. `[^a-b]`,
`[^note 2]`, `[^réf.]` are not, and they are not errors either: the
engine reads neither a call nor a body, so `[^réf.]` ships to the reader
inside the sentence as literal text and `[^réf.]: …` renders as an
ordinary paragraph with the label showing. `build` is silent and exits 0.
This is the one defect in this format that reaches the reader with
nothing raised anywhere — `audit` is what names it. If a label has to
read as it stands, wrap it in backticks.

The call becomes a link to the body; the body carries a link back to the
call. One label called twice gives one body with two return links.

**Numbering restarts with whatever unit holds the bodies.** Under the
default `local` placement that means each card starts again at 1, while
the long-form article runs continuously through itself. That is on
purpose: a card is individually shareable, so a reader can arrive at card
5 having seen nothing else, and a note numbered 7 there would send them
hunting for six that are not on their screen.

Four things `audit` will tell you about, none of them fatal:

- a label outside the word-character pattern above — reported separately
  for a call and for a body, because they do not repair the same way: one
  gets renamed, the other gets renamed *and* has been rendering a line of
  prose you never wrote;
- a call with no body — the marker still renders, but as no link at all;
- a body nothing calls — it still renders, at the end of the block,
  with no return link;
- a definition written inside a raw HTML block (a `<div class="refs">`,
  typically) — raw HTML is passed through verbatim, so it ships as the
  literal text `[^1]: …`. Put note bodies outside your raw HTML.

Practical note for `local`: notes at the foot of a card take room on a
screen that is already short. A card carrying five of them will scroll.

These footnotes are **source notes** — they are printed for the reader at
the foot of the card. They are not the speaker's cue; that is a separate
field (below).

## Speaker notes (`note:`)

A footnote (`[^x]:`) is a *source* note the reader sees. A speaker note is a
different thing: the line you say aloud, withheld from the slide the audience
sees. Write it as a `note:` field on the slide:

```markdown
<!-- lwp:slide -->
kicker: Two
## Slide two
note: Mention the 2020 study — the audience asked for it last time.
  Follow up with the 2023 replication.

  If time runs short, skip the appendix.
```

`note:` is parsed and **never rendered into the slide** — the reader gets no
marker, no footnote, nothing. It is held in the page and surfaced only by the
**presenter panel**: while presenting, press **N** and the panel shows the
current slide's `note:` text alongside the next slide's title, so you can read
ahead unseen. The panel rides along as you navigate; press **N** again to
close it. `note:` is accepted on `cover` and `standard` slides.

A `note:` may span several lines: each continuation line starts with
whitespace, and an indented blank line is a paragraph break. The block ends at
the first non-indented, non-empty line (the next field or the slide body), so
the extra lines never leak into the visible slide. `comment:` accepts the same
multi-line form (it stays a review note, never rendered).

The same deck prints one slide per sheet (Ctrl/Cmd+P → PDF), with the
navigation chrome stripped and the theme colours kept, so a footnote-heavy
card and a clean handout come from the same source.

## Per-slide look: `fact-variant`

`fact-variant: warning` on a standard slide adds `fact--warning` to that
slide's fact-box classes. The source names a *meaning*; what it looks like
is defined by the series (a `.fact--warning` rule in
`templates/custom.css`), so changing themes carries the variant along.
The name must match `[a-z][a-z0-9-]*` — anything else is a fatal build
error naming the file when the fact-box actually renders (a fact-label
**and** body text). Only meaningful together with `fact-label:` (no
fact-box, no class to hook); a variant on a slide with no fact-box body
is ignored in silence, since there is nothing to class.

## Instance tags: character-level styling beyond Markdown

Format-defined tags for one-off interventions inside any free text (slide
bodies and the full-article file). They go through the compiler: a bad
value is a fatal build error naming the file, and `audit` counts them per
article — they are author decisions that survive every theme change.

| Tag | Effect |
|---|---|
| `{color:#E8A33D}…{/color}` | colour literal (3/4/6/8-digit hex, normalized to ARGB) |
| `{color:mark}…{/color}` | a shared colour by name (`page`, `ink`, `ink-quiet`, `mark`, `call`, `affirm`, `nav`) — any name `N` for which `color.N` is in the registry |
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
build error naming the file. A good key and a good value that compose an
unreadable page are not an error — `audit` warns, naming this article and
the property, and the build still succeeds. Run `audit` after adding
`style.*` lines: it is the only thing that reads the sheet those lines
actually produce.

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

**Trust boundary.** Raw HTML — a `<script>` included — passes through to
the published page. That is the contract for the *author's own* text: the
author already owns the page (`templates/custom.css` is appended verbatim
to it, and `template write nav.js` hands over the navigation script too).
If the markdown you
are assembling comes from a source the author does not control (a CMS
export, a database, another agent's output, a third-party translation),
sanitize it upstream before the build — LightWebPres does not filter raw
HTML and does not claim to.

## Typography: automatic non-breaking spaces

Under `--lang fr` (the default), `build` silently upgrades certain plain
spaces already present in the text to non-breaking ones: before
`; : ! ?` **and before a closing `»`**, after an opening `«`, before
`%`, around the spaced em/en dashes of an incise, between groups of 3 digits
in a number you've already spaced out (`170 000`), between a number and
`million(s)`/`milliard(s)`/`dollar(s)`/`$`, and after `×`/`≈` before a
number. Nothing to do on your end — write ordinary spaces, the build
handles the rest. It never *inserts* spacing or digit grouping that
wasn't already there (don't add a space just to trigger the rule), and a
non-breaking space you type yourself always passes through unchanged.
`--lang en` has a smaller rule set of its own — the two dash rules, a
number followed by a metric unit or a unit word, initials, and `×`/`≈` —
it is **not** rule-free. To mix
languages in one article, map variant tags to packs with
`series_meta.lang_tags`, for example `{"fr": "fr", "en": "en"}`. The first
mapped language tag on a slide chooses that pack; a slide without one uses
the build-wide `--lang`/`LWP_LANG` fallback. Built-in `fr` and `en` packs are
available, and another pack name refers to `language/<name>.json`.

This alters generated content, so it can be turned off per article, in
that article's meta block: `typo_units: off` (the unit and operator
rules — numbers/units and `×`/`≈`), `typo_thousands: off` (the
thousands-grouping rules; the English pack has none, so the field does
nothing there), or `typo: off` (every rule, this article only). Each one
names a CATEGORY, so it reaches whichever language pack is in force. Leave these out unless
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
`intro`, `author`, `license`, and optional `lang_tags`. The first four drive the generated index
page and `README.md`; the last two are the fallback for every article's
byline and licence line.

```json
{
  "series_meta": {
    "title": "My series",
    "intro": "What it is about.",
    "lang_tags": {"fr": "fr", "en": "en"}
  },
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
lightwebpres audit <series-dir>   # renders in memory, reports everything, never fails
lightwebpres build <series-dir>   # fatal on real structural errors
```

`audit` renders the series the way a build does, writing nothing, so it
sees what only a render can say — including a series that cannot be built
at all, which it reports without stopping. It still exits 0 whatever it
finds: **read its output, not its exit code**, unless you pass
`--strict`. A clean `build` (exit code 0) with no `[ERROR]` lines is what
tells you the file parses, renders and ships. If the executable isn't available in this
environment, say so explicitly rather than presenting unverified output
as finished — don't guess at whether it would build.

## Common mistakes to avoid

- Wrapping a field value across two lines expecting it to join — it
  won't; the second line becomes free text instead (a fatal build error
  on a `cover` slide, since it has no fact-box for that text to go into
  — at least you'll get a clear error, not silent data loss).
- Writing `kicker:`, `summary:`, etc. **after** the fact-box body has
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
`verify`/`audit`, refreshing templates, or deploying. For all of that, if
`GUIDE.md` is present alongside this project, read it — it's the full
walkthrough, in the order it's actually needed.

For the article format itself, if `specifications.md` is present
alongside this project, it's the complete, authoritative specification
(sections 4 and 6 for the format itself, section 22 for every parser
edge case) — consult it for anything this skill doesn't cover.

Both of those documents, and the executable itself, live at
<https://github.com/Fade78/lightwebpres>. This skill may well be
installed somewhere the project isn't, so when neither file is beside
you, that's where they are.
