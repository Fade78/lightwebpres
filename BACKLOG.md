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
contract, so a minor version, never a fix. The §9 rewrite changed the
styling side, not this: the `.yes`/`.no`/`.partial` hooks are kept as a
documented contract, and each verdict is now painted by its own typed
properties (`verdict.yes.fg`, `verdict.yes.mark`, ...), so a marker syntax
would bind to components that already exist — the parsing question is all
that remains. If it is adopted, handle the column case in the same pass.
The analysis of the three options is kept below.

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

**Carried into the §9 engine unchanged**: the underline treatment is now
the typed property `link.decoration-color` (default: the body ink, which
cannot fail), and `RETIRED_VARIABLES` maps the old name for legacy
sheets. Nothing left to decide.

## B4 — Key-figure alignment, as an option — DONE via B7

Proposed by the owner on 2026-08-04, on noticing that the gallery preview
showed the "180 °C" block aligned left.

The observation was right, and worse than expected: the real article
stacks the figure and its caption in a **centred column** (`.highlight`:
`flex-direction: column`, `align-items: center`, `text-align: center`),
while the preview put them on one line, aligned left, with an arrow
between them that the engine never emits — `.highlight-arrow` was a dead
rule, shipped in every generated page. Fixed the same day: the preview
adopts the real composition, the dead rule is gone.

**Absorbed by B7** (2026-08-04). Under the §9 engine, `highlight.align`
would be one enum axis in the registry and an alignment instance tag the
per-figure form — the exact per-series / per-figure pair this entry was
weighing. Alignment as a whole was deferred by owner decision; this entry
survives only as B7's first concrete case. See B7.

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
(§9.5.3); these are the palette values themselves. The admission criteria
in §9.5.2 promise "AA for secondary text and accents" — they were applied
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

**What the §9 rewrite changed (2026-08-04).** The finding still stands:
the default registry paints the verdicts and the footnote call with the
shared palette colours (`verdict.yes.fg: affirm`, `verdict.partial.fg:
call`, `verdict.no.fg: ink-quiet`, `footnote-call.fg: call`), so on the
borrowed palettes the measured ratios above are unchanged. What changed
is the cost and the blast radius of every option. Each verdict is its own
component now (E1): retinting one moves nothing else. Option 3 — text
takes the body ink, colour stays on the shape mark — is a **one-line
property** (`verdict.yes.fg: ink`), settable per theme, per series
(`settings.conf`) or as the shipped default, instead of a stylesheet
change forced on everyone at once. And the engine's own weight rule (only
`normal`/`bold` survive a generic family) means the shape mark already
carries the yes/partial distinction alone — the user's argument below is
now an architectural fact, not an opinion.

**What remains is editorial, not mechanical**: revise the nine borrowed
catalogue entries. Per entry, the coherent outcomes are unchanged — flip
the dark-designed schemes to `dark_background` (which CDC §6.3
established is a *restoration* of fidelity, not a loss), set their
verdict/footnote inks to `ink`, retune the values, or declare-and-mark
them (D6, still undone: nothing in `themes` or the gallery distinguishes
the nine borrowed palettes from the twenty-four measured ones). Owner's
call, one line per theme once made. The catalogue revision pass (B9) is
the natural vehicle.

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

**Narrowed by measurement (B9, 2026-08-04): there is no single-value fix,
for either dot.** The revision proposed one opaque grey (`#7A7A7A`) for
the resting dots, reported as clearing 3:1 on 31 themes of 33. Re-measured
against every theme's real page and cover ground, compositing the
translucent cover overlays properly, it **fails on 12 of 33**, worst
1.79:1 on `pop-lagoon`. The cause is structural and is the same one that
governs the borrowed accents: a mid-grey cannot clear 3:1 against a
*mid-luminance* ground, and the whole `pop` family has saturated
mid-luminance grounds. The active dot was already known to be insoluble
this way. So the only real fix is the one below — give the row a ground of
its own (`nav-dots.bg`, `nav-dots.rule-fg`, `nav-dots.pad`) — and the
alternative of one hand-picked value per theme is a 33-line patch that
would have to be re-derived every time a ground changes.

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

**The contract blocker is gone; the value choice remains.** Under the §9
engine the dots are ordinary typed properties — `nav-dot.bg`,
`nav-dot.bg-hover`, `nav-dot.bg-active` — with defaults transposed from
the old veils, so the measurements above still describe what ships.
`--marker` no longer exists as a documented role (its jobs were split per
component; `RETIRED_VARIABLES` maps it), so changing the active dot's
colour is no longer a documented-contract change: it is one default plus,
where needed, one line per theme. What remains to decide is pure design:
default values that clear 3:1 over **both** grounds the row floats on
(page and cover), and whether that requires giving the row a declared
ground of its own (which would now be two more properties, not a new
mechanism). Fold into the catalogue revision pass (B9) alongside B5.

## B7 — Text alignment axes (center, justify, per-component and per-block) — DONE

**Done.** Ten align axes (`title1`, `title2`, `summary`, `fact`, `cover`,
`table.head`, `table.cell`, `caption`, `article`, `highlight`), enum
`left | center | right | justify`, behaving like every other axis across
layers 1–4. What left the skeleton is layout by fiat: the key figure
centred with no recourse (**this closes B4**), table cells left, the
figure caption centred.

Two decisions worth keeping:

**`justify` drags `hyphens: auto` along, declared in the registry, not
left to the author.** The narrowest column this product renders is 45
characters (phone in portrait, measured — `ETUDE-VIEWPORT.md`), where
unhyphenated justification makes rivers. The tie is a new `companions`
field on `ThemeProp`: declarations a *particular resolved value* drags
with it. One case so far, and it is not a convenience.

**The instance layer gets block syntax, and CSS forced it.** `text-align`
on the inline `<span>` every other tag produces does nothing at any
viewport size, and a paragraph cannot be opened mid-flow. So the rule that
generalises is not "every property gets an inline tag" but *the tag's
scope matches the property's scope*. `{align:center}` and `{/align}` each
alone on their line, wrapping whole paragraphs.

The emitted class reaches descendants (`.align-center *`) on purpose:
`text-align` inherits, but a component declaring its own beats what it
inherits, so without the descendant selector an author's local choice
could never win over the theme — which is the whole point of an instance
tag. Consequence to know: everything inside the block aligns, table cells
included.

Original framing follows.


Owner's request, 2026-08-04, deliberately deferred to a later version:
expose alignment (center / justify / left / right) as typed enum axes on
text-bearing components, plus a block-level instance tag in article
sources. The §9 rewrite it depended on has landed, and everything it
needs now exists — enum property types, per-property selector overrides,
and the instance-tag layer of the cascade. What the work amounts to:
moving today's fixed `text-align` decisions out of the static skeleton
(where they are layout by fiat — the `.highlight` block is centred, table
cells are left-aligned) into registry axes, and adding one block-scoped
tag. Not designed yet — recorded so the intent survives.

Absorbs B4: `highlight.align` (the key-figure block, today centred with
no recourse) is the first concrete case and the acceptance test —
per-series via `settings.conf`, per-figure via the instance tag.

## B8 — `extends` for external theme files — NOTED

Recorded at the catalogue port (2026-08-04): the scaffold is generated
complete and no user-facing include mechanism exists — the one legitimate
include is the cascade itself, a settings file sitting on a theme. An
`extends` line stays a possibility **for the day external theme files
exist**, noted and not built. A theme already *being* a property layer,
nothing structural is missing; the work is a file format, its resolution
order, and its audit story. Do not build before the external-theme-format
question (out of scope of the §9 refactor by decision) is opened on its
own.

## B9 — Typographic revision of the 33-theme catalogue — PARTLY APPLIED

**Report delivered and verified** (`c4156e8`): `REVISION-THEMES.md`, with
31 validated property layers in `themes-revision/`.

**Two of the three decisions applied.** The catalogue keeps **33 themes**.

1. **Four borrowed palettes returned to their own ground.** `dracula`,
   `tokyo-night`, `monokai` and `everforest` are `dark_background`.
   Measured after: **zero text roles below AA on all four**, against
   1.29:1 and 1.41:1 before. `monokai` keeps its pink on rules and rings
   only (3.93:1), which its slug override enforces. Three entry notes
   that were factually false are rewritten.
2. **The serif-text / sans-UI default split adopted.** Verified the `ch`
   measure is font-independent as designed: characters per line are
   unchanged at 62 and 67 wherever the measure binds, and stay in band
   (48, 56) on the narrow phone where the padding binds instead.
3. **Dropping `pop-lagoon` and `pop-fuchsia`: rejected, and the report was
   wrong.** Its case was that lagoon is crowded between lime and cobalt.
   Measured on the hue wheel, lagoon's neighbours are *further away than
   average* — 36° and 49° — while the closest pair in the family is
   tangerine→lemon at **15°**, which reads as two plainly different
   colours. The criterion does not survive its own application. `fuchsia`
   and `red` are the closest dark pair at 26°, with different `mark` and
   `affirm`: not a duplicate. Nothing measured supports a removal.

**Still open from the report:** the per-theme typographic blocks (named
display faces, tracking, cover gradients, the two extra halos) and the
five project themes that miss the AA floor spec §9.5.2 promises. The
blocks are in `themes-revision/`, all 31 verified to resolve.

Original framing follows.



The engine gave themes fonts, shadows and per-component axes; only
`terminal` uses them (fixed pitch plus phosphor halo, the owner's
decision). The architecture records that all 33 entries are to be
reviewed under this light — theme-construction work, out of the engine's
scope. Natural vehicle for the per-theme value choices of B5 (verdict
inks on borrowed palettes) and B6 (nav-dot values), and for D6 (mark the
nine borrowed palettes as offered for fidelity, not measured
accessibility). 32 entries remaining.

## B10 — Gamut mapping for lightness-shifted inks — NOTED

The ink solver (kept as a prototype in `tools/ink_solver_prototype.py`;
the shipped engine deliberately computes no colour) shifts OKLCh
lightness at constant chroma and hue, and the shift sometimes leaves the
sRGB gamut, where per-channel clipping distorts chroma — `#008500` is the
recorded case. A real gamut map would reduce chroma instead. Only
relevant if a derivation/measurement pass is ever built for the catalogue
revision (B9); acceptable as clipping until then. Recorded here because
its previous home (a pre-rewrite section of ARCHI-TEMPLATES.md) no longer
exists.

## B11 — Dichromat separability is not verified — NOTED

The architecture explicitly does not guarantee separability under
dichromat vision; the verdicts' shape marks already serve it (and are now
load-bearing, since weight no longer separates partial from yes), but no
simulation exists and nothing measures the palettes. Assumed gap,
recorded at the owner's level: a check would belong to theme construction
(the catalogue side), never to the renderer.

## B12 — Box drop-shadow (elevation) axes — NOTED

Text shadows are properties (`shadow.fg/blur/dy`); the box shadows that
paint depth — cards, nav buttons, the share modal, series links — stay
fixed `rgba` values in the static skeleton, guarded as layout, so a theme
cannot tune its elevation (flatten it, tint it, or push it). By the
completeness rule this is a decision currently confiscated from the
theme; it was left out of the property inventory knowingly, as depth
rather than content. Deciding it means the same three-axis treatment as
text shadows, per elevation-bearing component.

## B13 — `--content-max` is the one themeless variable — DONE

**Done: exposed, not exempted.** `page.content-max` is an ordinary length
property, default **`50ch`** — a measure, not a pixel width. The old
`min(84vw, 1100px)` rendered 106 characters per line for the card summary
on a laptop and 127 for the article paragraph, against a WCAG 1.4.8 (AAA)
ceiling of 80; the article was the worst offender and was not even
governed by the variable, carrying its own `max-width: 800px`.

The design rests on one verified property: **a `ch` length inside a custom
property resolves against the CONSUMING element, not `:root`**, so one
declared value gives every component the right column for its own type
size. Measured across fifteen viewports, characters per line become
viewport-invariant.

Two things came with it, neither in the original entry, both found by
measuring rather than reasoning (`ETUDE-VIEWPORT.md`):

- **The fluid type clamps moved from `vw` to `vmin`.** On `vw`, rotating
  a phone shortens the viewport *and enlarges the type*, so 6 cards in 8
  overflowed in landscape against 1 in portrait. `vmin` alone would have
  made the measure worse (a smaller font in a fixed pixel box is *more*
  characters) — the two changes are a package.
- **A height breakpoint**, `@media (max-height: 520px)`, the first in a
  sheet whose every other breakpoint keys on width. That blind spot is
  why landscape went unnoticed. Declared last, deliberately — see B15.

Result: 45–127 characters per line before, **45–67 after**, on all
fifteen viewports; landscape phones from 6, 6 and 5 overflowing cards out
of 8 down to 3 each; portrait unchanged to the pixel.

`100svh` was added alongside `100vh` for the mobile URL bar and is
recorded as **untested**: headless Chromium has no browser chrome, so
`svh`, `lvh` and `vh` are all equal in the harness.

Original framing follows.


The only CSS variable the composed sheet still declares outside the
engine: the skeleton's own layout width (`min(84vw, 1100px)`), the single
`var()` the extraction gap-check tolerates. Pre-rewrite architecture
recorded it as outside the colour apparatus by nature. To settle someday:
expose it as a length property (`page.content-max`) like everything else,
or record the exemption as permanent — today the exemption lives only in
a code comment and the gap-check test.

## B14 — Literalize the skeleton; retire TEMPLATE_STYLE — DONE

**Done** (`19188d6`). `TEMPLATE_SKELETON` is the frozen extraction result,
450 lines, 113 rules; `extract_skeleton`, `_strip_driven`,
`_driven_declarations` and `SkeletonGapError` are gone. The composed sheet
was verified equivalent on all 33 themes plus the bare defaults, comments
and whitespace normalised. 442 tests.

Two things the freeze made visible, worth recording. **Twenty-one rules
had no representation at all in the shipped sheet** — `body`, all five
`.slide-cover*` rules, the verdict colour and `::before` rules, the three
`.series-status` rules, and the hover rules of the share chrome — so
editing them in the old constant was a pure no-op, forever. And
`_driven_declarations()` carried **a hand-written exemption for
`.slide-cover .summary`'s opacity**, sitting inside a function that
claimed to compute the driven set structurally; the fade it protected is
now measured per theme by a real test.

**Cost accepted:** the sheet grew 4.3 KB per page, of which 4.1 KB is the
re-authored comments, which now ship. Stripping them at composition would
re-introduce the very "the constant is not what ships" property this entry
existed to kill, so they were kept. Revisit only if page weight becomes a
real constraint.

The original analysis follows.

Audit finding (2026-08-04): about two thirds of the old sheet's 577 lines
are dead at runtime — 142 lines of comments, the 23-declaration :root, and
~180 engine-driven declarations, all stripped by `extract_skeleton()` on
every composition. The constant lies to its reader: editing a driven
declaration is a silent no-op, exactly the defect class this project kills
elsewhere. The extraction gap-check only protects against additions to the
OLD sheet, and the place where additions happen now is the registry.

Plan, in order (the order matters — doing step 2 first is churn):
1. Retarget the remaining tests that read `TEMPLATE_STYLE` directly onto
   the composed sheet or resolved properties: the anti-opacity scan
   (MEASURED_FADES — its `.slide-cover .summary` exemption is already
   vestigial, the declaration no longer ships), the body-link selector
   guard (duplicate it on the registry's `link` component, where a
   selector widening would today pass unseen), and the styling-hooks
   anchor.
2. Replace the constant with the frozen, re-prettified skeleton; keep the
   gap-check as a plain test (no var() but --content-max, no content hex).
3. Delete `extract_skeleton`, `_strip_driven`, `_driven_declarations`,
   `SkeletonGapError` — optionally keeping a driven-declaration collision
   test between skeleton and registry.

## B15 — The share popover's mobile overrides never apply — NOTED

Found by B14 while freezing the skeleton, pre-existing and untouched
there because fixing it is a visual change. The `@media (max-width: 600px)`
block sits **before** the `.share-popover` base rule in source order, and
both have specificity `(0,1,0)`. So on a narrow viewport the later base
rule wins and `bottom: 72px; right: 16px; max-width: calc(100vw - 32px)`
never take effect. The other four selectors in that media query
(`:root`, `.slide`, `.nav-dots`, `.nav-buttons`) are all declared above it
and work correctly, which is why this went unnoticed.

Now that the skeleton is a literal, the ordering is visible to whoever
reads it, and a comment above the block warns that anything declared below
still beats it. The fix is to move the media query after the rules it
overrides — one relocation, no new properties — but it changes what a
narrow viewport renders, so it wants a look before it lands.

Related, same family, also pre-existing: `.share-cell-head-disabled`'s
`opacity: 0.35` slips past the anti-fade guard because the opacity sits in
a different rule from the `font-size: 11px` it dims. A hole in that
heuristic, not in the seam.
