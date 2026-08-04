# Backlog

The **permanent** register of things raised but not dealt with: bugs
with no urgency, change requests, format decisions still to be made.
Unlike `JOURNAL-1.0.md` (the 1.0 working memory, deleted at release),
this file outlives releases — anything that has to be findable "later"
goes here, not in the journal.

Every entry says what has been **verified** and what remains to be
**decided**.

---

## B1 — Mid-paragraph image with a title — FIXED in v0.12.0

**Type:** implementation bug (the expected behaviour was already
specified).
**Reported against:** v0.11.0, in a long-form article (`_article.md`).
**Status:** **fixed**. The inline pattern was given the optional title
group it was missing. A decision was made along the way: the title is
not thrown away but becomes a `title` attribute (a tooltip), never a
`<figcaption>` — and it goes through neither inline rendering nor
typography, which have no business inside an attribute value. Covered by
a test that exercises all four cases A/B/C/D **together**, since it was
testing them separately that let the hole through. Spec §6.1 updated.

The original analysis is kept below: it documents the cause.

### The four cases

| Case | Shape | Expected | Actual |
|---|---|---|---|
| A | alone on its line, no title | `<figure>` | OK |
| B | alone on its line, with a title | `<figure>` + `<figcaption>` | OK |
| C | mid-paragraph, no title | inline `<img>` | OK |
| D | mid-paragraph, **with a title** | inline `<img>`, title ignored | **literal text** |

### Cause, verified

Two distinct patterns read the same syntax, and only one accepts the
optional title:

- `_FIGURE_LINE_RE` (image alone on its line) —
  `^!\[([^\]]*)\]\(\s*([^)\s"]+)(?:\s+"([^"]*)")?\s*\)$`: the
  `(?:\s+"([^"]*)")?` group reads the title.
- the inline pattern in `md_inline()` —
  `!\[([^\]]*)\]\(([^)\s"]+)\)`: **no** title group, and `[^)\s"]+`
  stops at the first space. An image with a title therefore matches
  nothing at all and passes through the conversion intact.

Direct reproduction (v0.11.0, `md_inline()` alone):

```
'text ![alt](img/x.jpg) text'
  -> 'text <img src="img/x.jpg" alt="alt"> text'
'text ![alt](img/x.jpg "Caption") text'
  -> 'text ![alt](img/x.jpg "Caption") text'      <- unchanged
```

**Secondary symptom, also confirmed**: the text left literal then goes
through the typography engine, which sees the `!` of `![alt]` as high
punctuation and inserts a non-breaking space in front of it. The output
therefore contains `text\xa0![alt](...)` — a non-breaking space in the
middle of an unconverted Markdown pattern. That's a good marker for
spotting the case in an already-published page.

### What was already settled

`specifications.md` §6.1 says: "An image **in the middle of a paragraph**
becomes a plain inline `<img>`, with no caption." The expected behaviour
was therefore not up for decision — the title must be **read then
ignored**, not leave raw Markdown behind. The skill says the same. All
that was left was to align the implementation.

### Suggested fix

Give the inline pattern the same optional title group as
`_FIGURE_LINE_RE`, and discard it on the rendering side. Careful not to
break the attribute escaping already in place on `src`/`alt` (`src` is an
attribute context, cf. the neighbouring comment in `md_inline`), nor the
anti-ReDoS bound (`[^<>]`, never `.*`). To be covered by a test of all
four cases A/B/C/D at once — the hole comes precisely from A/B and C
being tested separately.

---

## B2 — Visual verdict in a table cell — SETTLED in v0.12.0

**Status:** the question "gap or choice?" got an answer, and it was
neither. The default stylesheet **already** shipped `.yes` / `.no` /
`.partial` / `.col-signal` / `.col-snap` to everyone — undocumented, and
with no way whatsoever to produce them from the Markdown. `lightwebpres`
was therefore shipping styling hooks its own format could not reach: an
internal inconsistency, not a judgement call.

What was done (option 3 of the analysis below, the only one that doesn't
touch the input contract):

- **Inline HTML is now the documented route**, with the table of classes
  in spec §6.1 and a mention in the README. "Raw HTML is the intended
  route" was only a choice once written down; it is written down.
- **Two of the classes were unusable.** `yes` and `partial` had identical
  declarations — three verdicts, two appearances, so the existing
  comparison table already failed to distinguish "yes" from "partly".
  And `no` was the only one emphasized (bold green), against the natural
  reading. All three are now distinct and taken from the palette.
  **To check on your side**: your published comparison table will change
  appearance, and that is intended.
- Locked down by a test (the three declarations must differ and must come
  from the palette).

**Still open, post-1.0**: option 2, an in-cell marker syntax (`| +yes |`)
to reach those classes without HTML. That is an addition to the input
contract, so a minor version, never a fix. If it is adopted, handle the
column case in the same pass. The analysis of the three options is kept
below.

### The need

A comparison of three platforms across seven criteria, where each cell
carries a class colouring it by verdict: `yes` / `no` / `partial`. Thirty
class attributes. Markdown cannot express it, so that one table stays
hand-written in raw HTML, while the other tables in the same article
moved to native Markdown (`class="comparison-table"`, §6.1) as soon as
that became available.

The argument, and it holds: in a format designed for card-based articles
read at a glance, "does / doesn't / partly" is taken in at a glance when
it is coloured, and becomes a wall of text otherwise. The case looks
recurrent, not specific to one project.

A neighbouring case reported for information (same family, not the same
request): two other tables stay in raw HTML for a `col-signal` class that
emphasizes a whole **column**.

### Options, with their consequences

1. **A convention on content** — a cell containing only "yes" / "no" / a
   symbol automatically gets its class.
   *Against, seriously:* it depends on the language, while the format is
   i18n (`fr`/`en` packs, §17); and above all it **retroactively changes
   the meaning of existing content** — an already-published table whose
   cell says "no" suddenly turns red. Hard to square with the input
   contract's stability promised from 1.0 onwards (§13.9).
2. **An explicit marker at the head of the cell** (shape to be defined,
   e.g. `| +yes |`, `| -no |`, `| ~partial |`).
   *For:* explicit, language-independent, local to the cell, alters no
   existing content. *Against:* one more syntax to freeze — so an
   addition to the input contract, i.e. a **post-1.0 minor version**
   (§13.9), never a fix.
3. **Document that raw HTML is the intended route** for this case.
   *For:* zero format change, it already works — §6.2 explicitly allows
   inline HTML. *Against:* verbose (thirty attributes by hand), and
   leaves the need uncovered by the format itself.

The reporter notes that option 3 would suit them too: what matters is
**knowing**, not getting the feature.

### Recommendation (to be confirmed)

Rule out option 1: retroactive effect on already-written content is
disqualifying for a format that promises input stability. Between 2 and
3, decide explicitly and then write it into `specifications.md` §6.1 —
including if it's 3, because "raw HTML is the intended route" is only a
choice if it is written somewhere. If it's 2, plan the column case
(`col-signal`) at the same time rather than coming back to it separately.

In every case: **post-1.0**. This is not a release blocker.

## B3 — Body-text links are not themed — FIXED in v0.12.2

Noticed during the cross-review of 2026-08-04.

`TEMPLATE_STYLE` contains **no** rule colouring an `<a>` in body text.
`md_inline()` emits `<a href="…" target="_blank" rel="noopener">` with no
class, so a link takes the browser's default blue, on every theme.
Measured against the page background:

| Theme | default blue | with `var(--accent)` |
|---|---|---|
| Synthwave | 1.93:1 | 5.25:1 |
| Terminal | 2.05:1 | 5.63:1 |
| Graphite | 1.99:1 | 18.73:1 |
| Dread | 2.10:1 | 3.17:1 |
| Nord | **8.15:1** | 3.55:1 |

On the fourteen dark-background themes a link therefore sits at roughly
2:1 — unreadable. The spec, the help text and the comment shipped in
every `style.css` all claimed that `--accent` colours links; that was
false, and was fixed the same day.

**What it turned out to be.** Measuring all four candidate treatments
over the 33 themes moved the problem. The status quo is worse than the
table above records: fifteen themes fail AA, not fourteen, and
`pop-tangerine` is a **light** theme at 4.27:1 — a bright orange page
sinks the blue just as a dark one does. The six saturated Pop dark themes
sit at 1.03–1.22:1, not the ~2:1 quoted.

And `var(--accent)` is disqualified twice over: it fails AA on eleven
themes, and it **is** the "partial" verdict colour by identity (ΔE = 0)
on all 33. `--positive` and `--ink-muted` are the other two verdict
colours, so of the six roles only `--marker` is unspoken for — usable on
13 themes of 33, all dark.

Settled: the link keeps the ink around it and is signalled by an
underline. `--ink` on `--page` is the one pair every theme is admitted on
(§9.5.3), so the text is AA and AAA everywhere by construction, and
WCAG 1.4.1 is satisfied by shape rather than colour.
`--link-decoration-color` lets a theme tint the rule where it has
measured one that works; it defaults to `currentColor`, which cannot
fail. Measured on real pages after the fix: 13.92 (solarized), 13.36
(dracula), 8.19 (pop-violet), against 1.03 before.

Spec §9.5.5.

## B4 — Key-figure alignment, as an option — OPEN

Proposed by the owner on 2026-08-04, on noticing that the gallery preview
showed the "180 °C" block aligned left.

The observation was right, and worse than expected: the real article
stacks the figure and its caption in a **centred column** (`.highlight`:
`flex-direction: column`, `align-items: center`, `text-align: center`),
while the preview put them on one line, aligned left, with an arrow
between them that the engine never emits — `.highlight-arrow` was a dead
rule, shipped in every generated page. Fixed the same day: the preview
adopts the real composition, the dead rule is gone.

**Still to decide**: should this block have an alignment option? Today it
is centred, with no recourse. A `--highlight-align` variable (`center` by
default, `start` possible) would be enough, and would follow the same
mechanics as the other variables — overridable after the customization
marker, and themable if wanted. To settle: a plain CSS variable, or a
real article field (which would make it a per-figure decision rather than
a per-series one).

## B5 — Three palette roles fail AA against their own page — OPEN

Found by rendering a series that exercises the whole format under all 33
themes and measuring, 2026-08-04. This is the residue of that sweep: what
is left once every stylesheet-level defect is fixed.

Three of the six roles are used to paint real text, and three of them are
below WCAG AA (4.5:1) against `--page` on a third of the catalogue:

| Role | What it paints | Below AA | Worst |
|---|---|---|---|
| `--ink-muted` | summary, caption, source, tag, byline, the "no" verdict | 9/33 | 2.48 (solarized) |
| `--positive` | the "yes" verdict | 11/33 | 1.29 (dracula) |
| `--accent` | footnote call and definition, the "partial" verdict | 11/33 | 2.05 (tokyo-night) |

**Not a stylesheet defect.** Every rule that dimmed text has been fixed
(§9.5.5); these are the palette values themselves. The admission criteria
in §9.5.3 promise "AA for secondary text and accents" — they were applied
to the twenty-four project-owned palettes and **never retro-applied to
the nine borrowed ones**, which predate them. Eight of the nine failures
in the first row are borrowed palettes.

**The root cause is deeper than a few values.** Seven of the nine
borrowed palettes are colour schemes designed for a *dark* background,
rendered here on a light one. Dracula's green `#50FA7B` is meant to sit
on `#282A36`; on `#F8F8F2` it measures 1.29:1. The theme notes record the
compromise honestly — `--page` "borrows the text-on-black here, for want
of an official light one" — but the consequence was never measured. The
accents keep their upstream brightness and the ground was inverted under
them.

**Options, none of them free.**

1. **Flip the mis-rendered palettes to `dark_background`.** Dracula,
   Monokai and Tokyo Night are dark schemes; giving them their real dark
   page would be *more* faithful to upstream, not less, and every accent
   would then measure against the ground it was designed for. Cost: those
   themes change completely for anyone using them.
2. **Re-tune the failing values.** Cheapest to describe, but it means
   departing from published palettes on eight of the nine — which is the
   one thing borrowing them was meant to avoid.
3. **Stop painting content text with signal colours.** The verdicts
   already carry a shape marker (WCAG 1.4.1), so the cell's text could
   take `--ink` and leave the colour on the marker; the same applies to a
   footnote call. Guarantees AA everywhere with no palette edit — the
   treatment already chosen for links in B3 — at the cost of the colour
   those cells currently carry. **Anyone with a published comparison
   table sees it change appearance a second time.**
4. **Declare it and scope it.** Record in §9.5.3 that the nine borrowed
   palettes are offered for fidelity rather than measured accessibility,
   and mark them in `themes` and the gallery.

Owner's call: 1 and 2 change what a theme looks like, 3 changes what
every article looks like, 4 changes nothing but what is promised.

**One user's input, recorded because it is the only one we have from
someone who actually uses the verdicts.** The team that reported B2 —
twenty-eight `yes`/`no` cells in a published series — was told option 3
would change those cells a second time, and answered that it suits them,
for a reason worth keeping:

> If the shape carries the information, the colour no longer has to
> carry it alone, and it stops having to clear a contrast threshold that
> a borrowed palette cannot guarantee.

That reframes option 3. It is not a loss of colour bolted on to fix a
number: it is the conclusion of the change already shipped when the
verdicts gained their shape markers for WCAG 1.4.1. Once meaning rests
on shape, a palette colour on that cell is decoration, and decoration is
not held to 4.5:1.

They also note the change costs them nothing, since their cells are
regenerated at every build. That is one user, not a mandate — but it
removes the objection the entry was weighing against option 3.

## B6 — The slide-progress dots are below 3:1 everywhere — OPEN

Same sweep. `.nav-dots a` paints `--rule-strong`, a translucent veil, and
it floats over two different grounds: a standard slide (the page) and a
cover slide (the inverted cover ground). Over a cover on a light theme, a
black veil on a dark ground is **1.00:1 on high-contrast** — the sampled
dot pixel and the cover pixel are byte-identical. Below 1.5:1 on 19
themes, below the 3:1 non-text threshold on all 33.

The active dot is separately weak: `--marker` against `--rule-strong`
measures 1.02:1 on high-contrast and under 1.5:1 on fourteen themes. It
is still distinguishable, because `scale(1.3)` gives it a non-colour cue
— which is what keeps this from being a 1.4.1 failure as well.

**Not fixed because the shape of the fix is a design decision.** The dots
need a known ground to sit on — a `--control` pill under the row would
give them one, at the cost of a visible chip that is not there today —
and then the active state needs a colour that works on it, which
`--marker` is not on a light theme (it is a highlighter yellow, chosen as
a highlight ground). Spec §9.1 currently lists "active nav dot" as a role
of `--marker`, so changing it is a documented-contract change, not a
tweak.
