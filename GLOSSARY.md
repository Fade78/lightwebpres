# LWP field glossary

Every `key: value` line LightWebPres recognizes — where it can be set,
what it falls back to when absent, what it renders as. Reference only;
`specifications.md` is authoritative, each row links to its own §.
Excludes LWP's structural markers (`<!-- lwp:meta -->`, `<!-- lwp:slide:TYPE
-->`, `---`) — see `specifications.md` §4.1 for those.

## Naming conventions

Frozen at v1.0, for every future field too:

- Slide-level fields: kebab-case (`fact-label`, `highlight-caption`).
- Article/series-level fields: snake_case (`page_title`, `nav_desc`).
- The `page_*` family covers everything about the compiled page: its
  source (`page_source`), its output file (`page_dest`), its title
  (`page_title`), its description (`page_desc`).

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

## Article-level fields

One entry per article in `series.json`'s `articles[]` array. Most also
default from that article's own `<!-- lwp:meta -->` block, `series.json`
taking priority when both are set (§20.3.1).

| Field | Where it can be set | Default | Description |
|---|---|---|---|
| `page_source` | `series.json` only | None — required (§20.3) | Filename of the article's `.md` source, in `articles/`. (Named `source` before v1.0 — the old key gets an explicit migration error) |
| `page_dest` | `series.json`, meta block | `series.json` > meta `page_dest:` > `page_source` (`.md` → `.html`) (§20.3.1) | Output HTML filename. (Named `file` before v1.0) |
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
| `draft` | `series.json`, meta block | Not a draft. Only `true` (bool or string, case-insensitive) marks one; `series.json` wins even with an explicit `false` (§20.6) | Draft article: fully excluded from the build (no page, no card, no nav entry) unless `--include-drafts`, which builds it with a centered "draft" banner |
| `typo` | meta block only | Unset — typography stays on | `off` disables every typography rule (§4.5), for this article's own page only |
| `typo-units` | meta block only | Unset — rule stays on | `off` disables only the units/`×`/`≈` typography rule, for this article only |
| `typo-thousands` | meta block only | Unset — rule stays on | `off` disables only the thousands-grouping typography rule, for this article only |

## Cover slide fields

A `<!-- lwp:slide:cover -->` slide's own header. No fact-box: free text
after these fields is a fatal error (§22.12).

| Field | Default | Description |
|---|---|---|
| `tag` | `''` — omitted from the render if absent | Small label above the slide's own heading |
| `slide_title` — written `# Heading`, no literal field form | None. Only the first `#` before any content sets it (§22.2) | The slide's own heading, rendered `<h1>` |
| `summary` | `''` — omitted from the render if absent | One-line summary paragraph under the heading |

## Standard slide fields

A standard slide's own header (default, or explicit `<!-- lwp:slide -->`).

| Field | Default | Description |
|---|---|---|
| `tag` | `''` — omitted from the render if absent | Small label above the slide's own heading |
| `slide_title` — written `## Heading`, no literal field form | None. Only the first `##` before any content sets it (§22.2) | The slide's own heading, rendered `<h2>` |
| `summary` | `''` — omitted from the render if absent | One-line summary paragraph under the heading |
| `highlight` | None — the whole highlight block is omitted if absent | Large standalone figure (a number, a stat, a quote) |
| `highlight-caption` | `''` | Caption under the `highlight` figure |
| `fact-label` | None — without it, the trailing free text renders as a bare paragraph instead of a labeled fact-box (§4.3) | Label on the fact-box wrapping the slide's trailing free text |
| `source` | `''` — omitted from the render if absent | Citation text, rendered `Source: <value>` (the standard academic word — unrelated to `page_source`, which is the compilation's own source file) |

## Full-article slide field

A `<!-- lwp:slide:full-article -->` slide's own header.

| Field | Default | Description |
|---|---|---|
| `article` | None — required on this slide type | External `.md` file included as the article's long-form body |

## See also

- `specifications.md` — the authoritative behavioral spec; every §
  reference above points there.
- `GUIDE.md` — task-oriented walkthrough (install, write, verify, ship).
- `agent/skills/lightwebpres/SKILL.md` — LWP syntax reference for an
  agent writing or editing `.md` articles.
