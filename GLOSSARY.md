# LWP field glossary

Every `key: value` line of the article format — series, article and slide
level: where it can be set, what it falls back to when absent, what it
renders as. Reference only; `specifications.md` is authoritative, each row
links to its own §. The theme properties (`component.axis`) are a separate
vocabulary and are not listed here: `templates/settings.conf` carries them
all, commented, at the current theme's values — see `specifications.md` §9,
whose §9.1 also explains why no count of them is written by hand anywhere,
including in this sentence.
Excludes LWP's structural markers (`<!-- lwp:meta -->`, `<!-- lwp:slide:TYPE
-->`, `---`) — see `specifications.md` §4.1 for those.

## Naming conventions

**A name's shape says what level it is set at.** Settled in v0.7.0 and
guaranteed from 1.0 on, for every future field too (§13.9: a frozen name
can only change in a MAJOR release). `specifications.md` §20.0 is
authoritative:

- Slide-level fields: kebab-case (`fact-label`, `highlight-caption`).
- Article/series-level fields: snake_case (`page_title`, `nav_desc`,
  `notes_placement`, `typo_units`).
- Theme properties: dotted `component.axis` (`card.title.size`,
  `verdict.yes.fg`).
- The `page_*` family covers everything about the compiled page: its
  source (`page_source`), its output file (`page_dest`), its title
  (`page_title`), its description (`page_desc`).

This is not decoration. Putting a field at the wrong level produces **no
error** — it is simply ignored — so a legible cue is worth more than a
diagnostic that will never exist. And it is what lets `resolve` take any
field name and know which cascade to consult, with no disambiguation
table: the shape answers that.

So a new field is named after its **level**, never after what looks
natural beside it. A test holds every name here to the shape its level
requires — the rule was broken four times before there was one.

Bare single words carry no shape, so they are looked up rather than
read. Every one of them belongs to exactly one level except `comment`,
which belongs to all of them and is why `resolve` refuses it: it is
parsed everywhere and read nowhere, so it has no resolved value to
report (below).

## `comment` — review notes

`comment` is recognized at every level below — a `series.json` entry, the
`series_meta` object, an article's meta block, and the header of a slide
of **any** type (cover, standard, series-nav, full-article) — but never
read by any renderer: parsed, then discarded. For leaving an editorial note in the source (a reviewer flag,
a TODO) without it ever reaching the built output, not even in the page's
raw HTML source (unlike an HTML comment, which LWP passes through
verbatim — §6.2 — and would still ship, just invisible on screen). Free
text, no constraints, not listed again per section below.

## Series-level fields

Once per series, in `series.json`'s `series_meta` object.

| Field | Default | Description |
|---|---|---|
| `title` | `strings.series_untitled_fallback` (§7.3) — `series_meta` itself is optional | Series title on `index.html` and `README.md` |
| `subtitle` | `''` — omitted from the page if absent | Series subtitle on `index.html` |
| `version` | `''` — omitted from the page if absent | Version tag shown on `index.html` (e.g. `v0.13`) |
| `intro` | `''` — omitted from the page if absent | Intro paragraph on `index.html` and `README.md` |
| `author` | `''` — nothing shown | Series-wide default author (§20.3.1); shown in the index page's footer, and on every article that doesn't override it |
| `license` | `''` — nothing shown | Series-wide default license; same display as `author`; raw HTML allowed (a link) |
| `lang_tags` | `{}` — no tag selects a language pack | Object mapping a slide variant tag to a typography/UI pack name, e.g. `{"fr": "fr", "en": "en"}`; the first mapped tag on a slide selects its engine (§20.5) |

## Article-level fields

One entry per article in `series.json`'s `articles[]` array. Most also
default from that article's own `<!-- lwp:meta -->` block, `series.json`
taking priority when both are set (§20.3.1).

| Field | Where it can be set | Default | Description |
|---|---|---|---|
| `page_source` | `series.json` only | None — required (§20.3) | Filename of the article's `.md` source, in `articles/`. (Named `source` until v0.7.0 — the old key gets an explicit migration error) |
| `page_dest` | `series.json`, meta block | `series.json` > meta `page_dest:` > `page_source` (`.md` → `.html`) (§20.3.1) | Output HTML filename. (Named `file` until v0.7.0) |
| `page_title` | `series.json`, meta block | `series.json` > meta `page_title:` > the cover slide's own `slide_title` > the resolved `page_dest` (§20.3.1) | The article's own page `<title>` tag |
| `page_desc` | `series.json`, meta block | `series.json` > meta `page_desc:` > the cover slide's own `summary` > tag omitted (§20.3.1) | The page's `<meta name="description">` (SEO/share preview). Deliberately NOT chained with `card_desc` — invisible metadata never leaks onto visible index cards |
| `card_title` | `series.json`, meta block | `series.json` > meta `card_title:` > the resolved `page_title` (§20.3.1) | Title on this article's card on the index page |
| `card_desc` | `series.json`, meta block | `series.json` > meta `card_desc:` > the cover slide's own `summary` (§20.3.1) | Description on this article's card on the index page |
| `card_label` | `series.json`, meta block | `series.json` > meta `card_label:` > `''` — nothing to extrapolate it from (§20.3.1) | Free label (not a number) shown on the index card **and** on the "This series" nav card on every article's own page |
| `nav_title` | `series.json`, meta block | `series.json` > meta `nav_title:` > the resolved `card_title` (§20.3.1) | Title shown when this article appears in the navigation card embedded in a *different* article's page |
| `nav_desc` | `series.json`, meta block | `series.json` > meta `nav_desc:` > the resolved `card_desc` (§20.3.1) | Description shown in that same cross-article navigation context |
| `author` | `series.json`, meta block | `series.json` > meta `author:` > `series_meta.author` > `''` (§20.3.1) | Article author; shown in the page footer byline and as `<meta name="author">` |
| `license` | `series.json`, meta block | `series.json` > meta `license:` > `series_meta.license` > `''` (§20.3.1) | Content license; shown in the page footer; raw HTML allowed (a link) |
| `date` | `series.json`, meta block | `series.json` > meta `date:` > `''` — never derived from file mtime (§20.3.1) | Free-text date shown verbatim in the footer byline |
| `status` | `series.json`, meta block | `active` (§20.6) | What this article is worth to the series. `active`: built, carded, navigated, counted. `draft`: still an article of the series and counted as one, but kept out of the output unless `--include-drafts`, which builds it with a centered "draft" banner. `ignored`: out of the chain entirely — never built whatever the flags, never listed, never counted — so an article can be set aside without deleting the entry that carries all its settings. Case-insensitive; any other value is a fatal error naming the article |
| `notes_placement` | `series.json` `series_meta`, meta block | `local` (§6.5.1) | Where note bodies land. `local`: at the foot of the unit that called them — that card, or the end of the long-form article; numbering restarts in each card. `page`: every body on the page collected into one notes section at the end, numbered continuously. The article's meta block wins over `series_meta`; an unknown value is a fatal build error naming the article |
| `notes_tooltip` | `series.json` `series_meta`, meta block | `off` (§6.5.3) | `on` also puts the body's text on the call as a tooltip. Composes with either placement and is never the only carrier — the body stays in the document, because a tooltip does not exist on a touch screen, in print, or in the reading order |
| `typo` | meta block only | Unset — typography stays on | `off` disables every typography rule (§4.5), for this article's own page only |
| `typo_units` | meta block only | Unset — rule stays on | `off` disables only the units/`×`/`≈` typography rule, for this article only |
| `typo_thousands` | meta block only | Unset — rule stays on | `off` disables only the thousands-grouping typography rule, for this article only |
| `slide_page_numbers` | meta block, `series_meta`, or `--slides-page-numbers` | `off` (§3.3.5) | Engraves the top-right `NN / NN` slide number on every slide; cascade: meta block > CLI flag > `series_meta` > `off` |

## Cover slide fields

A `<!-- lwp:slide:cover -->` slide's own header. No fact-box: free text
after these fields is a fatal error (§22.12).

| Field | Default | Description |
|---|---|---|
| `kicker` | `''` — omitted from the render if absent | Small editorial label above the slide's own heading |
| `tags` | `default` when absent or empty | Space-separated variant tags used for runtime filtering; `excluded` removes the slide at build time (§4.3.1) |
| `note` | `''` — nothing shown | Speaker note, multi-line; never rendered, surfaced by the presenter panel |
| `slide_title` — written `# Heading`, no literal field form | None. Only the first `#` before any content sets it (§22.2) | The slide's own heading, rendered `<h1>` |
| `summary` | `''` — omitted from the render if absent | One-line summary paragraph under the heading |

## Standard slide fields

A standard slide's own header (default, or explicit `<!-- lwp:slide -->`).

| Field | Default | Description |
|---|---|---|
| `kicker` | `''` — omitted from the render if absent | Small editorial label above the slide's own heading |
| `tags` | `default` when absent or empty | Space-separated variant tags used for runtime filtering; `excluded` removes the slide at build time (§4.3.1) |
| `note` | `''` — nothing shown | Speaker note, multi-line; never rendered, surfaced by the presenter panel |
| `slide_title` — written `## Heading`, no literal field form | None. Only the first `##` before any content sets it (§22.2) | The slide's own heading, rendered `<h2>` |
| `summary` | `''` — omitted from the render if absent | One-line summary paragraph under the heading |
| `highlight` | None — the whole highlight block is omitted if absent | Large standalone figure (a number, a stat, a quote) |
| `highlight-caption` | `''` | Caption under the `highlight` figure |
| `fact-label` | None — without it, the trailing free text renders as a bare paragraph instead of a labeled fact-box (§4.3) | Label on the fact-box wrapping the slide's trailing free text |
| `fact-variant` | None — the fact-box gets no extra class (§9.6.2) | Names a *meaning*, not a value: `fact-variant: warning` adds `fact--warning` to that fact-box, styled once per series by a `.fact--warning` rule in `custom.css`. Validated as a CSS class (`[a-z][a-z0-9-]*`); needs `fact-label`, without which there is no box to hang it on |
| `source` | `''` — omitted from the render if absent | Citation text, rendered `Source: <value>` (the standard academic word — unrelated to `page_source`, which is the compilation's own source file) |

## Full-article slide field

A `<!-- lwp:slide:full-article -->` slide's own header.

| Field | Default | Description |
|---|---|---|
| `tags` | `default` when absent or empty | Optional variant tags; `excluded` removes the generated slide before rendering |
| `article` | None — required on this slide type | External `.md` file included as the article's long-form body |

## Series-navigation slide fields

A `<!-- lwp:slide:series-nav -->` slide has no author-written body. Its
navigation cards are generated from `series.json`; it accepts the shared
`tags` field for variant filtering. `comment` is documented above because it
is accepted on every slide type and is never rendered.

The historical `tag:` field is not an alias for either current field. Use
`kicker:` for the visible label above a slide title, and `tags:` for variant
filtering. On a standard slide, an old `tag:` line becomes body text; on a
cover, `build` reports the unknown field and suggests the two current choices.

## Presentation vocabulary

The theme engine's terms of art — the shared vocabulary contract with
lightwebpres-gui. `specifications.md` §9 is the authoritative behavioral
description; the terms are fixed here, in English.

| Term | Meaning |
|---|---|
| **property** | One typed setting, named `component.axis` (`kicker.fg`, `cover.bg.angle`). The only vocabulary an author writes. |
| **component** | A thing the format names that the page renders — `kicker`, `summary`, `verdict.partial`. Properties belong to components; there is no intermediate semantic layer. |
| **axis** | The last segment of a property key: what it sets (`fg`, `size`, `weight`, `shadow.blur`). The axis fixes the type; the type fixes where a bare-word reference is looked up. |
| **halo** | A `text-shadow` a component sets on its own glyphs, in four axes (`shadow.fg/blur/dx/dy`). A halo is a shadow with no offset — the same mechanism, not a branch. Emitted only when a theme asks for one: `text-shadow` is inherited, so emitting it at its default would block what the page set rather than paint nothing. |
| **elevation** | A `box-shadow` a component sets on its own box, in five axes (`elevation.fg/blur/dx/dy/spread`), with an `elevation-hover` group where the component lifts under the pointer. Always emitted — `box-shadow` is not inherited, so its default paints nothing and blocks nothing. Never measured for contrast: a drop shadow falls outside the box, on a ground the theme does not own, and carries no information. |
| **shared value** | A palette colour (`color.*`) or font stack (`font.*`) themes provide and properties reference. Never read by an emitted rule directly. |
| **reference** | A word used as a value, resolved at merge time and never surviving into the output (§9.2). Bare (`kicker.fg: ink-quiet`) it is looked up in its type's namespace; dotted (`title1.fg: cover.fg`) it names another property. At most 3 hops; cycles are detected and named. |
| **layer** | One dictionary of properties in the cascade (§9.3): built-in defaults, theme, settings, article, instance — merged in that order before emission. |
| **theme** | A named layer of properties applied over the built-in defaults. |
| **settings** | The author's own property layer (`templates/settings.conf`), applied over the theme. Never written by the tool except on explicit request (`series theme set` rewrites only the `theme:` line). |
| **scaffold** | The generated form of `settings.conf`: every property present, commented out, at the chosen theme's values (§9.3.1). Generated once from the registry, never rewritten on the tool's initiative; `# scaffold-for:` records the theme it was generated under. |
| **pin** | Uncommenting a scaffold line (or writing one): the value now overrides every theme and survives theme changes and upgrades (§9.3.1). |
| **override** | The relation between layers: a value in a later layer covering an earlier one. |
| **customization** | The author's act of overriding — via settings, per-article properties, instance tags, or `custom.css`. |
| **theme construction** | The editorial and artistic choice of palette values, fonts, shadows, and their relationships. It is catalogue work outside the renderer. |
| **measurement** | The contrast reading taken from resolved properties and composited grounds, on named sites rather than on colours in the abstract. `theme show` and `series theme` print it in full, category by category; `audit` reuses it to name a composed sheet that has stopped working, and stays silent otherwise. It reports; it never rewrites or rejects a theme, and it never reaches a built page. |
| **renderer** | The part that resolves layers, composes properties, and emits CSS/HTML. It applies the values it receives and does not retune them. |
| **article properties** | `style.<property>: value` lines in an article's meta block — the same vocabulary, scoped to that page alone (§9.6.1). |
| **instance tag** | A format-defined tag in free text — the instance-scoped fifth layer, same types as everywhere, enumerated by `audit` (§9.6.3). Inline (`{color:mark}…{/color}`, `{sc}…{/sc}`) or, for alignment alone, **block-level**: `{align:center}` and `{/align}` each on their own line, because `text-align` on an inline span does nothing. |
| **variant** | A named look for a component instance (`fact-variant: warning` → class `fact--warning`), defined once per series in `custom.css` — the source carries meaning, not visual values (§9.6.2). |
| **slide variant tag** | A normalized word from `tags:`. `default` is the implicit shared variant; a selected tag keeps shared slides plus slides carrying that tag. This is unrelated to instance tags or the version tag. |
| **furniture** | Descriptive family, not a mechanism: the properties painting the page's apparatus rather than its content or signals — rules, surface veils, sunken and control grounds, the modal scrim. Ordinary properties; the word only lets one speak of them collectively. |
| **skeleton** | The static, layout-only CSS no property drives: flex, grid, spacing, media queries. Not an editable surface. |

## See also

- `specifications.md` — the authoritative behavioral spec; every §
  reference above points there.
- `GUIDE.md` — task-oriented walkthrough (init, write, verify, ship).
- `agent/skills/lightwebpres/SKILL.md` — LWP syntax reference for an
  agent writing or editing `.md` articles.
