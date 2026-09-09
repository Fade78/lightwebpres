# Text And Style

Read this for free Markdown text, images, notes, typography and styling hooks.
[Article Format](article-format.md) describes the one-way header/body switch;
[Series and Appearance](series-and-appearance.md) covers series-wide choices.
The converter is an LWP subset, **not generic CommonMark**.

## The Full-Article File

The file referenced by `article:` is a separate `.md`, conventionally
`{name}_article.md`, with **no LWP structure**. Its converter also processes
standard-slide bodies, with or without a fact-box. It supports headings,
`**bold**`, `*italic*`, `[links](url)`, source notes, lists, tables,
blockquotes, images, inline code and fenced code blocks. Consecutive
non-blank text lines merge into one paragraph; blank lines separate paragraphs.

Images use `![alt](img/pic.png)`. Alone on a line, an image becomes a centered
`<figure>`. A title, `![alt](src "Caption")`, becomes a small centered caption.
Wrapping the whole image in a link, `[![alt](src "Caption")](https://example.org)`,
makes it clickable while keeping the caption outside the link; its accessible
name is the alt text alone. Mid-paragraph images are plain inline `<img>`
elements with no caption.

Append `{50%}` for general image zoom, or an extended suffix such as
`{width=50% height=auto align=right}`. The keys are `width`, `height`, `zoom`,
and (standalone figures only) `align`. Width/height accept safe CSS lengths;
zoom accepts a percentage. Values are validated before becoming CSS.
Inline images accept size keys but not `align`. Relative images live under
`sources/img/`; only images referenced by rendered pages are copied into
`public/img/` by the normal build.

Inline code uses backticks (`` `code` ``). Fenced code uses ` ```lang `,
body lines and a matching ` ``` `; the language is optional and informational,
not syntax highlighting. Raw HTML passes through unchanged, permitting a
hand-written `<figure>` or other structure when needed.

**Ampersands are escaped in ordinary text.** An entity typed as `&rarr;` or
`&nbsp;` is published literally, not interpreted. Only a raw-HTML block
bypasses inline conversion and preserves entities. Write the actual character
(`→`) in ordinary text; the format is UTF-8.

Code spans and fences fully HTML-escape their contents and display them
as written, even tags. At the start of a line, a `>` or backtick not intended
to start a blockquote/code construct can be prefixed with `\` (`` \> ``,
`` \` ``). These are the only supported escapes. A `>` elsewhere does not
start a blockquote and needs no escape.

## Converter Limits

- Markdown links must use `http://` or `https://`. `[text](page.html)` or a `mailto:` link stays literal without warning. Use raw `<a href="...">` for other targets.
- Headings extend to level 6: `#` through `###` are headings; `####` is a bold-font paragraph, not `<strong>` emphasis; `#####` and `######` are plain paragraphs.
- Consecutive `>` lines merge into one paragraph inside a blockquote. Nested and multi-paragraph blockquotes are unsupported.
- Table alignment colons (`|:---|---:|`) parse but do nothing. Ragged rows are emitted as written without a cell-count check.
- A bare `---` in a full-article file is silently dropped, not rendered as `<hr>`. In an LWP deck it splits slides. Use `<hr>` for a rule in either file.
- An unclosed code fence swallows following lines as code and leads to a fatal unclosed-tag build error. Close fences explicitly; a deck's `---` still splits slides even inside an example.

## Tables And Reader Sizing

The build keeps every table cell in HTML. Wide tables are visually clipped by
default, not shortened or summarized. Readers can use
**Menu > Display settings > Wide tables** or **O** to choose clipping, overflow
or local scrolling. Back or Escape returns from the sizing submenu to its
main-menu item with focus restored; clicking outside closes it. In scroll mode,
focused keys, wheel and touch interactions stay inside the table viewport
instead of accidentally navigating the deck. Print expands tables without
screen clipping or local scroll limits; check physical paper width separately.

Text fitting is a reader setting, not a Markdown conversion or an article
`style.*` key. `fixed` keeps the native responsive sizes without content fitting;
`uniform` fits all tag-visible slides in the current article together by
default. In single-page output only, **Uniform fit scope** in Display settings
can extend that group to tag-eligible slides across the entire series, using
the smallest measured factor. Long-form and series-navigation slides participate
even if they still overflow at the floor. `per-slide` fits each independently,
without propagating reductions; `fixed` does not fit content. Scope is a
separate saved reader preference, defaulting to the current article, not a
source style or reading field; multipage output is unaffected. See
[Series and Appearance](series-and-appearance.md) for its storage contract.
Optional shrinking applies separately to tables and supported images/figures,
not arbitrary iframes or
buttons. Runtime scales are cleared for print. Exact author defaults and
limits belong to `series_meta.reading` in
[Series and Appearance](series-and-appearance.md); do not shorten source data
merely to imitate visual clipping.

Presentation zoom (**-**, **+**, **=**) changes content fonts, line heights
and images after fitting has been solved at 100%. It does not zoom the page
root, frame widths, padding, borders, minimum heights or foreground controls.
At 100%, normal responsive sizing remains; long content can still grow or
scroll, and fitting does not cancel manual magnification. Native pinch remains
browser zoom. Browser emulation alone does not verify a physical device.

Reading modes, shrink switches and presentation zoom are reader preferences
saved in `localStorage` per output directory path on the same origin, across
articles, the index and reloads. Author minimum limits are not saved there,
and controls never rewrite `series.json` or Markdown. Invalid or inaccessible
stored data falls back to author defaults and 100% zoom; blocked saving leaves
controls usable in the page. Persistence depends on browser storage policy,
with `file:` behavior differing from HTTP(S) and between browsers. Appearance
keeps its separate browser-session persistence.

## Raw HTML Blocks

At the start of a line, a closed inline tag such as
`<strong>Word</strong> opens a sentence.` is ordinary paragraph text and
merges with the next line. Inline tags include `<a>`, `<strong>`, `<em>`,
`<span>`, `<sup>`. Leave one open, as in `<a href="..." class="card">`,
and every line through its matching close is raw HTML verbatim, including
a self-contained `<span class="caption">...</span>` line inside it.
Markdown and note definitions inside that block do not convert.

A field value may also contain inline HTML. For example,
`page_title: The apple pie<br>What pastry changes` gives an index card a
two-line title. Text-only destinations (`<title>`, description meta) strip
tags and replace them with a space; visible destinations such as the index
card's `<div>` keep the HTML. This is not sanitization: an unclosed tag in
a field can still enter the page.

**Trust boundary:** raw HTML, including `<script>`, reaches published pages.
LWP trusts author-controlled text; `templates/custom.css` is also appended
verbatim, and `template write nav.js` can hand over the page script.
Single-page mode requires that script to match the built-in runtime; arbitrary
widget script lifecycles are unsupported. Use multipage output for those
extensions; see [Operations](operations.md).
Sanitize untrusted CMS exports, database text, translations or another
agent's output **upstream**. LightWebPres does not filter raw HTML. An HTML
comment in body text is shipped even when invisible on screen; source-only
review material belongs in the `comment:` field instead.

## Source Notes

```markdown
The kettle draws about 3 kW[^kwh] on a domestic ring.

[^kwh]: Measured at 230 V, 13 A. See the appliance's rating plate.
```

This works in slide bodies and full-article files. Labels are keys, not
displayed content; readers see positions, so inserting a note does not
require manual renumbering. The call links to the body, which links back.
Two calls to one label produce one body with two return links.

A label contains **only word characters**: letters, digits and `_`,
including accents and non-Latin scripts. `[^kwh]`, `[^1]`, `[^a]`, `[^clé]`
are valid. `[^a-b]`, `[^note 2]`, `[^réf.]` are not. Invalid labels are
neither calls nor definitions; they ship as literal prose with the label
showing. `build` is silent; `audit` names the defect. Wrap a label in
backticks if it should be shown literally.

Numbering restarts in the unit holding the bodies. With default
`notes_placement: local`, each card starts at 1 and each long-form file
numbers continuously through itself. Cards are individually shareable:
a reader arriving at card 5 should not have to hunt for six earlier notes.
`notes_placement: page` instead collects and numbers bodies page-wide.
`notes_tooltip: on` adds a tooltip, never replaces the body.

`audit` reports these non-fatal conditions:

- A non-word-character label, separately for calls and definitions.
- A call with no body: the marker renders without a link.
- An uncalled body: it still renders at the end of its block, without a return link.
- A definition inside a raw HTML block (often `<div class="refs">`): it ships literally. Move definitions outside raw HTML.

Local footnotes take room on a card; several may force scrolling. They are
reader-visible source notes, not speaker cues. The separate `note:` field
in Article Format is hidden in normal view but is also **public HTML**.

## Fact Variants

`fact-variant: warning` adds `fact--warning` to a standard slide's fact-box.
The source names a meaning; a `.fact--warning` rule in
`templates/custom.css` supplies the look, retained across theme changes.
Names must match `[a-z][a-z0-9-]*`. Invalid names are fatal when a fact-box
actually renders, meaning both `fact-label` and body text exist. Without
that box a variant is silently ignored: there is nothing to class.

## Instance Tags

These format-defined tags work inside any free text for one-off styling.
The compiler validates values with fatal named errors; `audit` counts
instances per article. These author choices survive theme changes.

| Tag | Effect |
|---|---|
| `{color:#E8A33D}…{/color}` | Literal 3/4/6/8-digit hex, normalized to RGBA with alpha last (`#RRGGBBAA`) |
| `{color:mark}…{/color}` | Shared colour: `page`, `ink`, `ink-quiet`, `mark`, `call`, `affirm`, `nav`, or any name `N` whose `color.N` is in the registry |
| `{font:mono}…{/font}` | Shared `text`, `display`, `ui`, `mono` stack, or a literal stack ending on a CSS generic |
| `{sc}…{/sc}` | Small caps |
| `{strike}…{/strike}` | Strikethrough |
| `{u}…{/u}` | Underline |
| `{mono}…{/mono}` | Monospace using `font.mono` |

Alignment is the one **block tag**; inline spans cannot apply block-level
`text-align`. Opener and closer each stand alone, wrapping whole paragraphs:

```text
{align:center}
This paragraph is centred.

So is this one.
{/align}
```

Values are `left | center | right | justify`. Alignment changes only
alignment, including table cells inside its block. Word breaking is a
separate property, `page.hyphens` (`manual | auto`, default `manual`),
and is never enabled by alignment. A closer without an opener stays literal.

Inline tags nest and allow Markdown conversion inside. An inline opener
without a closer on the same line stays literal; code spans never interpret
tags. Prefer a fact variant or a `settings.conf` property for a repeating
design choice; use an instance tag for the one place that needs it.

## Article Styles

`style.<property>: value` in `lwp:meta` restyles that page over the series
theme and settings, using the same vocabulary and types as
`templates/settings.conf`. Examples: `style.verdict.partial.fg: #8A4B00`,
`style.cover.bg.angle: 90deg`. Invalid keys or values are fatal and name
the file. Valid values that compose unreadable output are not fatal;
`audit` names the article and property. Run it after adding style keys,
then inspect the page; individual valid values do not prove readability.

## Raw HTML Styling Hooks

These hooks have no Markdown-only spelling (specifications.md §6.1).
They work in fact-boxes and full-article files.

Every generated table has `class="comparison-table"`. Put a verdict class
on a cell or a span inside a Markdown cell. Each has a shape as well as
a colour, retaining its distinction in greyscale or colour-vision deficiency:

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

For a whole column, put `col-signal` (the comparison's key column) or
`col-snap` (read at a glance) on its `<th>`. This needs a raw HTML table;
Markdown cannot attach a class to a header cell.

`.refs` provides small print for a reference list at the end of a long-form
article: `<div class="refs">…</div>`. Do not put Markdown note definitions
inside it: raw blocks bypass conversion.

## Automatic Typography

With `--lang fr` (default), build upgrades certain existing spaces to
non-breaking ones: before `; : ! ?` and closing `»`, after opening `«`,
before `%`, around spaced em/en dashes in an incise, between already-spaced
groups of three digits (`170 000`), between a number and
`million(s)`/`milliard(s)`/`dollar(s)`/`$`, and after `×`/`≈` before a number.
Write ordinary spaces: the tool never inserts absent spacing or digit
grouping. An existing non-breaking space passes through unchanged.

English is not rule-free. `--lang en` has the two dash rules, numbers
followed by metric units or unit words, initials, and `×`/`≈` rules.
For mixed languages, `series_meta.lang_tags`, such as
`{"fr": "fr", "en": "en"}`, maps the first matching tag on a slide to its
typography pack. Unmapped slides use `--lang`/`LWP_LANG`. Built-in `fr` and
`en` are available; other names use `typography/<name>.json`, falling back
to legacy `language/<name>.json`.

Opt-outs in an article's meta block apply to that article only:

```text
typo_units: off
typo_thousands: off
typo: off
```

`typo_units` disables number/unit and operator (`×`/`≈`) rules;
`typo_thousands` disables thousands grouping (English has none);
`typo` disables every rule. These name categories in the pack in force.
Only `off` disables them; other values or omission leave rules on.
Do not add opt-outs unless requested. For a whole run, supported
`build`/`verify`/`watch` options include `--no-typography`.
