# LWP field glossary

Every `key: value` line LightWebPres recognizes, in one table — where it's
allowed, what it falls back to when absent, and what it renders as. This
is an index for quick lookup, not the authoritative behavioral spec: for
the full rationale behind each rule, see `specifications.md` (linked per
field below). It does not cover LWP's structural markers (`<!-- lwp:meta
-->`, `<!-- lwp:slide:TYPE -->`, the `---` separator) — those aren't
`key: value` fields, see `specifications.md` §4.1.

We call these **fields**, not "tags": `tag` is itself the name of one
specific field (§ below), so using "tag" for the general concept would
collide with it — on top of the existing risk of confusing it with an
HTML tag, which LWP also produces plenty of.

## Scopes

Each field's **Scope** column lists every location where it is actually
read — not just where the parser tolerates the line without erroring.
Writing a field outside its scope (e.g. `highlight:` on a `cover` slide,
or `fact-label:` where a `series-nav` slide's header would be) is parsed
but silently has no effect: never a build error, never rendered either.

| Scope token | Where |
|---|---|
| `series.json (articles[])` | A per-article entry in `series.json`'s `articles` array |
| `series.json (series_meta)` | The series-wide `series_meta` object in `series.json` — once per series, not per article |
| `article meta block` | The `<!-- lwp:meta -->` block at the top of an article's `.md` file |
| `cover slide` | A `<!-- lwp:slide:cover -->` slide's own header |
| `standard slide` | A standard (default, or explicit `<!-- lwp:slide -->`) slide's own header |
| `full-article slide` | A `<!-- lwp:slide:full-article -->` slide's own header |

`series-nav` slides have no fields of their own — their content is
entirely generated from `series.json`, see the `nav_title`/`nav_desc`/
`card_label` rows below.

## ⚠ Homonym: `source`

`source` exists in two places with **no relation to each other** — same
name, unrelated meaning, disjoint scope:

- `series.json (articles[])`: the article's Markdown source filename
  (structural, required — specifications.md §20.2/§20.3).
- `standard slide`: a citation string, rendered as `Source: <value>`
  (specifications.md §4.3).

Nothing enforces they don't collide textually; they simply never interact
— resolving one never reads the other.

## Fields

| Field | Scope | Default (most specific first) | Description |
|---|---|---|---|
| `source` | `series.json (articles[])` | None — required (specifications.md §20.3) | Filename of the article's `.md` source, in `articles/` |
| `file` | `series.json (articles[])`, `article meta block` | `series.json` > meta `file:` > `source` (`.md` → `.html`) (§20.3.1) | Output HTML filename |
| `page_title` | `series.json (articles[])`, `article meta block` | `series.json` > meta `page_title:` > the cover slide's own `slide_title` > the resolved `file` (§20.3.1) | The article's own page `<title>` tag |
| `card_title` | `series.json (articles[])`, `article meta block` | `series.json` > meta `card_title:` > the resolved `page_title` (§20.3.1) | Title on this article's card on the index page |
| `card_desc` | `series.json (articles[])`, `article meta block` | `series.json` > meta `card_desc:` > the cover slide's own `summary` (§20.3.1) | Description on this article's card on the index page |
| `card_label` | `series.json (articles[])`, `article meta block` | `series.json` > meta `card_label:` > `''` — nothing to extrapolate it from (§20.3.1) | Free label (not a number) shown on the index card **and** on the "This series" nav card on every article's own page |
| `nav_title` | `series.json (articles[])`, `article meta block` | `series.json` > meta `nav_title:` > the resolved `card_title` (§20.3.1) | Title shown when this article appears in the navigation card embedded in a *different* article's page |
| `nav_desc` | `series.json (articles[])`, `article meta block` | `series.json` > meta `nav_desc:` > the resolved `card_desc` (§20.3.1) | Description shown in that same cross-article navigation context |
| `typo` | `article meta block` | Unset — typography stays on | `off` disables every typography rule (§4.5), for this article's own page only |
| `typo-units` | `article meta block` | Unset — rule stays on | `off` disables only the units/`×`/`≈` typography rule, for this article only |
| `typo-thousands` | `article meta block` | Unset — rule stays on | `off` disables only the thousands-grouping typography rule, for this article only |
| `title` | `series.json (series_meta)` | `strings.series_untitled_fallback` (§7.3) — `series_meta` itself is optional | Series title on `index.html` and `README.md` |
| `subtitle` | `series.json (series_meta)` | `''` — omitted from the page if absent | Series subtitle on `index.html` |
| `version` | `series.json (series_meta)` | `''` — omitted from the page if absent | Version tag shown on `index.html` (e.g. `v0.13`) |
| `intro` | `series.json (series_meta)` | `''` — omitted from the page if absent | Intro paragraph on `index.html` and `README.md` |
| `tag` | `cover slide`, `standard slide` | `''` — omitted from the render if absent | Small label above the slide's own heading |
| `slide_title` (written as `# Heading` on `cover`, `## Heading` on a non-`cover` slide — no literal `slide_title:` field form) | `cover slide`, `standard slide` | None. Only the first heading of the level matching the slide's own type is ever captured; a second one, or the wrong level for that type, is content instead (specifications.md §22.2) | The slide's own heading — `<h1>` on `cover`, `<h2>` on a non-`cover` slide, same underlying concept, output tag chosen by slide type |
| `summary` | `cover slide`, `standard slide` | `''` — omitted from the render if absent | One-line summary paragraph under the slide's heading |
| `highlight` | `standard slide` | None — the whole highlight block is omitted if absent | Large standalone figure (a number, a stat, a quote) |
| `highlight-caption` | `standard slide` | `''` | Caption under the `highlight` figure |
| `fact-label` | `standard slide` | None — without it, the slide's free text renders as a bare paragraph instead of a labeled fact-box (§4.3) | Label on the fact-box wrapping the slide's trailing free text |
| `source` ⚠ (see homonym above) | `standard slide` | `''` — omitted from the render if absent | Citation text, rendered `Source: <value>` |
| `article` | `full-article slide` | None — required on this slide type | External `.md` file included as the article's long-form body |

## See also

- `specifications.md` — the authoritative behavioral spec; every §
  reference above points there.
- `GUIDE.md` — task-oriented walkthrough (install, write, verify, ship).
- `agent/skills/lightwebpres/SKILL.md` — LWP syntax reference for an
  agent writing or editing `.md` articles.
