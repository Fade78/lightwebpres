# Backlog

The **permanent** register of things raised but not dealt with: bugs
with no urgency, change requests, format decisions still to be made.
Unlike `delete-before-1.0/JOURNAL-1.0.md` (the 1.0 working memory, deleted at release),
this file outlives releases — anything that has to be findable "later"
goes here, not in the journal.

Every entry says what has been **verified** and what remains to be
**decided**.

## How to read this file, and how it decayed

**The header of an entry is its state. Nothing else in the file is.**
There is no index, on purpose: a list of entry numbers with their statuses
is a second place to be wrong, and this file already learned that lesson
the hard way — the revision block that used to sit here listed B15, B16
and B17 among the open entries long after all three had been fixed.

**How it decayed, because the mechanism matters more than the instance.**
An entry gets written when a defect is found. It gets fixed weeks later,
in a lot named after something else, by someone reading the code rather
than the register. Nothing in that path passes through this file. So the
fix lands, the tests go green, and the entry keeps saying `NOTED` — not
because anyone believed it, because nobody looked.

Probed one by one on 2026-08-18, three of the twenty-five entries
described a state that no longer existed, and one carried a policy the
owner had since reversed. Every other entry was exact. The register is not
careless; it is simply downstream of the work, and nothing carries it
along.

**So: closing an entry is part of the change that closes it.** If a lot
fixes something this file records, the entry moves in the same commit,
with the measurement that shows it. An entry closed later, from memory, is
how the numbers above happened.

**And a status is a measurement, not a memory.** `DONE` here means someone
ran something and wrote down what came back. Where an entry claims a
figure, the figure is in it.

## Who this project has, and what that settles

**One user, who is the owner, and the project is pre-1.0.** Stated here
because several entries were weighing costs that do not exist, and one had
invented a witness.

Read older entries with this in mind. Arguments of the form *an
already-published table would change appearance*, *someone may have a
series relying on this*, or *the input contract's stability* are weighing
a population of one, who is the person deciding. They are not wrong to
have been raised — a format that intends to be stable should think about
breakage before 1.0, not after — but they are not blockers, and an entry
that stalled only on that ground can be decided.

**What this does NOT excuse**, since the temptation runs the other way
too: it is not a licence for silent breakage. Being one's own user makes a
change cheap to accept, not cheap to discover. The reasons an error is
loud, a measurement written down and a guard proved by mutation have
nothing to do with how many people are watching.

One entry did more than hedge: B5 staged an outside witness — "the team
that reported B2", quoted — for an argument the owner had made about
their own series, in the third person. It has been rewritten. If a real user
ever appears, that will be worth recording precisely, and this note is
what will make the difference visible.

**What 1.0 is, decided 2026-08-18.** The project is still in R&D; 1.0 will
be called **when everything has stabilised**, and not on a date or a
checklist. That is a deliberate absence, not an oversight, and it is
written here because the question kept being asked implicitly: several
entries are deferred "until the external theme format exists" or "until a
derivation pass is built" (B8, B10, B11), and without this line it is
impossible to tell whether they are late.

They are not late. Nothing here is on a clock. Two consequences worth
stating so nobody has to rediscover them:

- `delete-before-1.0/` and its 44 files stay where they are. The name
  promises a deletion, not a deadline.
- An entry may be decided whenever the decision is ripe, and implemented
  whenever it is worth implementing. Being pre-1.0 is what makes that
  ordering free — see the note above on what it does *not* excuse.

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
  **Consequence to expect**: an already-published comparison table
  changes appearance on the next build, and that is intended.
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

A neighbouring case, noted at the same time (same family, not the same
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
underline. `--ink` on `--page` is the structural pair used by the renderer
(§9.5.3); its actual ratio remains a measured property of the resolved
palette. WCAG 1.4.1 is satisfied by shape rather than colour.
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

## B5 — Three palette roles fail AA against their own page — DECIDED, and the decision is that this is not a defect

**The premise is what changed, not the numbers (2026-08-17).** This entry
was written as a debt: roles below 4.5:1 against their own page, to be
paid off theme by theme until the catalogue was uniformly AA. The owner's
position is the opposite one, and it settles the entry: **a theme is not
required to reach AA.** What the project owes a reader is not a catalogue
where every entry clears the same bar — it is an honest statement of which
bar each entry clears. That is what `theme info` and the gallery report,
per theme, per WCAG category, measured rather than asserted.

So the roles below AA stay below AA where a palette's own identity puts
them there, and the catalogue says so. What would be a defect is a theme
whose level is *misreported*, or a surface nobody measured at all — and
those are guarded: every colour property is either in `CONTRAST_SITES` or
carries a written exemption in `CONTRAST_UNMEASURED`, and a property in
neither fails the suite.

Two things survive this decision as real work, and neither is this entry:
the per-theme floor on navigation furniture, which is about the tool
functioning rather than about taste (closed by B6), and D6 — nothing yet
distinguishes a borrowed palette from a measured one in the catalogue
listing.

The reading below is kept: it is the measurement that made the decision
possible, and the account of why a borrowed dark scheme on a light ground
cannot be argued into compliance.

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
(§9.5.3); these are palette values themselves. The criteria in §9.5.2 are
a catalogue target, not a renderer guarantee: they were applied to the
twenty-four project-owned palettes and **never retro-applied to the nine
borrowed ones**, which predate them.

**Re-measured after B9, and this entry's own numbers were stale.** The
failure counts above describe the pre-B9 catalogue: `ink-quiet` now fails
on 7 themes of 33 (worst 2.48, `solarized`), `affirm` on 7 (worst 1.77,
`nord`), `call` on 8 (worst 2.94, `vaporwave`). Four of the nine borrowed
palettes were returned to their own dark grounds and clear AA there, so
"eight of the nine failures are borrowed palettes" is now four of seven.
And the criteria were applied to the project palettes but are **met by
nineteen of the twenty-four** — B9 names the five that are not.

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
component now — the theme refactor gave every one of them its own
property — so retinting one moves nothing else. Option 3 — text
takes the body ink, colour stays on the shape mark — is a **one-line
property** (`verdict.yes.fg: ink`), settable per theme, per series
(`settings.conf`) or as the shipped default, instead of a stylesheet
change forced on everyone at once. And the engine's own weight rule (only
`normal`/`bold` survive a generic family) means the shape mark already
carries the yes/partial distinction alone — the user's argument below is
now an architectural fact, not an opinion.

**What remains is editorial, not mechanical**: revise the affected catalogue
entries. Per entry, the coherent outcomes are unchanged — flip
the dark-designed schemes to `dark_background` (which the per-colour
measurements in `delete-before-1.0/REVISION-THEMES.md` appendix A establish as a
*restoration* of fidelity, not a loss), set their
verdict/footnote inks to `ink`, retune the values, or declare-and-mark
them (D6, still undone: nothing in `theme list` or the gallery distinguishes
the nine borrowed palettes from the twenty-four measured ones). Owner's
call, one line per theme once made. The catalogue revision pass (B9) is
the natural vehicle.

**The argument for option 3, and where it actually comes from.** This
paragraph used to read as third-party testimony — "the team that reported
B2", quoted, "one user, not a mandate". There is no such team. The project
has exactly one user, who is its owner, and the sentence below was the
owner's own reasoning about their own series, written in the third
person. Rewritten
because a register that stages an outside witness is worse than one that
argues in its own name: the appeal to a user who does not exist adds
nothing and can only mislead a later reader — including a later me, who
read it as external validation and nearly left it alone for that reason.

The argument stands on its own, which is why it survives the correction:

> If the shape carries the information, the colour no longer has to carry
> it alone, and it stops having to clear a contrast threshold that a
> borrowed palette cannot guarantee.

That reframes option 3. It is not a loss of colour bolted on to fix a
number: it is the conclusion of the change already shipped when the
verdicts gained their shape markers for WCAG 1.4.1. Once meaning rests on
shape, a palette colour on that cell is decoration, and decoration is not
held to 4.5:1.

The practical note that came with it also holds and costs nothing: the
cells in question are regenerated at every build, so changing their
appearance a second time is free.

## B6 — The slide-progress dots miss the 3:1 readability floor — DONE

**Closed by `color.nav` (2026-08-17), and the entry's own diagnosis is
why.** It concluded there was no single-value fix "for either dot", and
that the alternative was a per-theme patch "that would have to be
re-derived every time a ground changes". Both halves were right, and both
followed from the same cause: the active dot was painted with `color.mark`,
a role that carries an editorial constraint of its own — on most palettes
`mark` is a highlighter, which has to stay pale enough for text to survive
on top of it. Navigation hardware borrowing a highlighter cannot be made
to clear 3:1 by choosing a better value, because the value is not free.

The fix was a seventh palette role rather than a better colour. `color.nav`
paints the navigation furniture and nothing an author writes, so it answers
to the 3:1 floor and to nothing else (§9.5.7). Every theme declares one.
Re-measured across the catalogue against both grounds the dot lands on,
the worst active dot is now **3.17:1** (`pop-lime`), and the forty-one
per-theme pins the old arrangement required are gone.

The resting dots are settled rather than fixed: `nav-dot.bg` is declared a
*ground*, not a foreground — "a slide dot that is not the current one" —
and the current one is marked by `scale(1.3)` as well as by colour, which
is what keeps the row clear of 1.4.1. That is a position, written down in
`CONTRAST_UNMEASURED`, not an unmeasured gap.

The history below is kept because it is the evidence for the diagnosis.

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

> **Proposition non retenue.** Ces trois propriétés n'ont jamais été
> créées : le composant du registre est `nav-dot`, au singulier, et il
> n'a pas de fond déclaré. La question a été tranchée autrement, par
> `color.nav` — un septième rôle de palette plutôt qu'un fond pour la
> rangée. Les chercher dans le registre serait vain.

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

**Alignment sets alignment and nothing else.** It shipped once with
`justify` dragging `hyphens: auto` along, through a `companions` field on
`ThemeProp` — so choosing an alignment silently turned word-breaking on, a
typographic decision arriving as the side effect of another. Owner's call,
and the right one: breaking words at end of line is now its own axis,
`page.hyphens` (`manual | auto`, default `manual` — CSS's own initial
value), inherited, never set for you. The `companions` mechanism had that
single user and went with it; if a second case ever appears it is three
lines. Guarded by a sweep over all 33 themes × five align axes asserting
`hyphens: auto` appears nowhere unasked — a spot check on the defaults
would not have caught the original defect, since only one value of one
axis enabled it.

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

## B9 — Typographic revision of the historical 33-theme catalogue — PARTLY APPLIED

**Report delivered and verified** (`c4156e8`): `delete-before-1.0/REVISION-THEMES.md`, with
31 validated property layers in `delete-before-1.0/themes-revision/`.

**Two of the three decisions applied.** The revision report concerned the
historical catalogue of **33 themes**; the live registry now contains 34.

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

**Policy decided 2026-08-15, and REVERSED since — do not apply it.** It
read: every built-in theme must meet a readability floor (AA for
informative text, 3:1 for informative non-text), while only a subset must
meet the higher project standard.

The owner's later position, recorded at B5, is the opposite on the first
half: **a theme is not obliged to reach AA.** What the project owes a
reader is an honest statement of the level each theme reaches, not a
uniform catalogue. Measured on the current catalogue, a substantial
minority of themes are reported `fail` on body text, deliberately — the
1.9-era floor is not enforced, and enforcing it now would mean retuning
palettes that are doing what their authors intended.

One half of it did survive, and is worth keeping separate: **visual
families such as `pop`, halo and monochrome are editorial categories, not
accessibility levels**, and `theme show` remains the measured report. That
sentence is still the project's position. Only the obligation is gone.

The single hard floor that does exist is elsewhere and has a different
justification: navigation furniture must clear 3:1, because an invisible
progress dot is a broken control rather than a bold palette
(`specifications.md` §9.5.6). It is not an accessibility policy for
themes; it is the boundary between what a test may refuse and what it may
not.

**Still open from the report:** the per-theme typographic blocks (named
display faces, tracking, cover gradients, the two extra halos) and the
themes that miss the new readability floor or the high standard. The blocks
are in `delete-before-1.0/themes-revision/`, all 31 verified to resolve. B5, B6 and B18 now
belong to the readability-floor pass; the remaining catalogue choices belong
to the high-standard and visual-family pass.

Original framing follows.



The engine gave themes fonts, shadows and per-component axes; only
`terminal` uses them (fixed pitch plus phosphor halo, the owner's
decision). The architecture records that all 33 entries are to be
reviewed under this light — theme-construction work, out of the engine's
scope. Natural vehicle for the per-theme value choices of B5 (readable
verdict and secondary inks), B6 (nav-dot values), and B18 (cover kicker
values), plus the visual-family metadata that distinguishes fidelity from
accessibility level. 32 entries remaining.

## B10 — Gamut mapping for lightness-shifted inks — NOTED

The former ink solver was a historical prototype, not used by the executable;
it has been removed from the active tree. The shipped engine deliberately
computes no colour. The experiment shifted OKLCh
lightness at constant chroma and hue, and the shift sometimes leaves the
sRGB gamut, where per-channel clipping distorts chroma — `#008500` is the
recorded case. A real gamut map would reduce chroma instead. Only
relevant if a derivation/measurement pass is ever built for the catalogue
revision (B9); acceptable as clipping until then. Recorded here because
the design document that first recorded it has been absorbed into
`specifications.md` §9 and removed, and this is the only remaining
statement of it.

## B11 — Dichromat separability is not verified — NOTED

The architecture explicitly does not guarantee separability under
dichromat vision; the verdicts' shape marks already serve it (and are now
load-bearing, since weight no longer separates partial from yes), but no
simulation exists and nothing measures the palettes. Assumed gap,
recorded at the owner's level: a check would belong to theme construction
(the catalogue side), never to the renderer.

## B12 — Box drop-shadow (elevation) axes — DONE

Text shadows are properties (`shadow.fg/blur/dy`); the box shadows that
paint depth — cards, nav buttons, the share modal, series links — stay
fixed `rgba` values in the static skeleton, guarded as layout, so a theme
cannot tune its elevation (flatten it, tint it, or push it). By the
completeness rule this is a decision currently confiscated from the
theme; it was left out of the property inventory knowingly, as depth
rather than content. Deciding it means the same three-axis treatment as
text shadows, per elevation-bearing component.

**Done: depth belongs to the theme.** Same ruling as B20 and the same lot
— the completeness rule applies, and the box shadows came up into the
registry per elevation-bearing component. Nothing about depth makes it
less a matter of appearance than a colour.

Thirteen declarations moved, on ten components. Five of those components
had no registry existence at all until this — `.tag-menu`,
`.slide-counter`, `.presenter-panel`, `.help-card` and
`.share-qr-modal-content` — and they enter with no properties but the
elevation, because each already resolves its ground and its ink with
`inherit`, deliberately and with the measurement written beside
`.slide-counter`.

Five axes rather than the three the entry proposed. `dx` for the reason
B20 gave it to the halo — the sheet only ever needed the vertical case,
which nobody decided — and `spread`, without which a ring or a soft lift
cannot be expressed. Both default to `0`, so the neutral elevation is the
one the sheet drew. Rest and hover are two groups on the idiom the
registry already uses for a state, `elevation` beside `elevation-hover`,
and the hover selector travels with the group: `.series-link` lifts on
focus as well as on hover.

Unlike the halo, an elevation always emits. `box-shadow` is not
inherited, so a component saying `0 0 0 0 transparent` paints nothing and
blocks nothing — where `text-shadow` at its default would block what the
page set. The alphas are the sheet's carried over as eight-digit hex,
rounding half up as the rest of the registry does; only `.20` was exact,
and the other seven move by less than half a step of alpha.

The catalogue's motivation, stated plainly: every one of those thirteen
shadows was black at an alpha chosen against a white page, and on a dark
ground a black shadow is not a shadow, it is nothing at all.

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
measuring rather than reasoning (`delete-before-1.0/ETUDE-VIEWPORT.md`):

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

## B15 — The share popover's mobile overrides never apply — DONE

**Closed by measurement (2026-08-18), and the entry was right about the
cause.** It described a media query sitting BEFORE the base rule at equal
specificity, so the later rule won on a narrow viewport. Re-measured on
the composed sheet, the order is now the other way round: the base
`.share-popover` rule is at byte 46 223 and the `@media (max-width: 600px)`
block that overrides it at 49 196. The media query wins, and
`bottom: 72px`, `right: 16px` and `max-width: calc(100vw - 32px)` apply.

Fixed at some point in the skeleton work the entry itself anticipated,
and nobody updated the header — which is how it came to be reported as
the project's one live defect three months later.

**The second half stands, and is narrower than it reads.**
`.share-cell-head-disabled { opacity: 0.35 }` does slip past the anti-fade
guard, because the guard looks for an opacity in a rule that ALSO declares
a text property and this one does not. Measured, three rules carry an
opacity below 1 without text properties, and all three are disabled
control states — which WCAG 1.4.3 exempts. The blind spot is real; what it
currently holds is not a defect. Worth stating inside the guard so a
future fade on live text cannot arrive believing itself covered.

The original reading is kept below.


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

## B16 — `page_dest: index.html` loses a page in silence — DONE

**Closed, verified 2026-08-18.** The collision is now a fatal error, exit
1, and the message names the article, explains what would overwrite what,
and states the one-article exception:

```
[ERROR] series.json: article "first.md" resolves to page_dest
"index.html", which collides with the series index — with 3 articles the
index carries the article list, so one of the two pages would overwrite
the other. Give this article another page_dest (in series.json, in its
own meta block, or by renaming the source); only a one-article series may
take the index name.
```

The entry asked for "one comparison and a named error" and worried that
it would turn an accepted configuration into a fatal one. It did, with
the single-article case preserved — which was the whole concern.

The original reading is kept below.


Found while building the guide with the tool (`tools/build_guide.py`): an
article whose `page_dest` is `index.html` collides with the series index
the build always writes, and one of the two silently overwrites the
other. The build prints both names and exits 0:

```
  index.html ← first.md
  index.html
Build complete: 3 articles + index -> …/public
```

The article page is written first and the index lands on top of it, so
what disappears is the article — a page listed in `series.json`, built,
and then destroyed by the next write. Exit code 0, no warning.

This is the defect class §22.8 already forbids for a missing article file
("a corrupted page shipped green"), applied to a name collision instead of
a missing input. The `page_dest` collision check that already exists is
case-insensitive **between articles**; it does not know about the index.

The fix is one comparison and a named error, but it turns a currently
accepted (if broken) configuration into a fatal one, so it wants a look
before it lands: someone may have a single-article series relying on the
index being the only page — which today means their article is the thing
being thrown away, not the index.

## B17 — catppuccin's bold-on-highlight is at 3.05:1 — DONE

**Closed, re-measured 2026-08-18 at 4.51:1** — `fact.strong.fg` against
its own `fact.strong.bg`, composited over the fact ground and the page.
The palette's `color.mark` moved and took the shortfall with it.

The entry predicted its own closing: it said the exact-set pin in
`KNOWN_PALETTE_FAILURES` would fail the moment the palette was fixed and
force the exemption out with it. That is what happened, and the set is now
empty — which is that idiom's strongest state, not an absence of coverage.

The original reading is kept below.


Found while measuring the notes work, and it is **not** a note defect:
catppuccin's `fact.strong.fg` measures **3.05:1** against its own
`fact.strong.bg`, for all bold text in a fact box, with or without a note
in it. Verified on the tree as it stood before any of the notes changes.

It surfaces here because `footnote-call.fg-marked` defaults to
`fact.strong.fg` — the tone the theme already chose for text on that
ground — so the call inherits the palette's own shortfall. That default is
structurally coherent on the other 32; it is not a guarantee of contrast.
catppuccin was the one place where what the theme had chosen was itself
below the floor.

`EveryNoteSurfaceIsMeasuredOnEveryThemeItShipsWith` pins it as an exact
set rather than a floor, so fixing the palette makes that test fail and
forces the exemption out with it.

Same class as B9's five themes: a palette value below AA, needing a
measured replacement rather than a mechanism.

## B18 — `cover.kicker.fg` is below AA on three themes — DECIDED, by the same rule as B5

**The measurement is unchanged and the premise is not.** The three themes
are still the three, still pinned as an exact set, and the tag is still
12px bold, so 4.5:1 is still the right bar to measure against. What
changed is that reaching it is no longer required.

The owner's position, recorded at B5: a theme is not obliged to reach AA.
What the project owes a reader is an honest statement of the level each
theme reaches — which `theme show` and the gallery report, per WCAG
category, measured. A palette below the bar on one surface, reported as
below the bar, is doing exactly what the catalogue promises.

So this entry stops being a debt and becomes what its own last paragraph
already said it was: **a pinned set is a guard, not an intention.** The
guard stays and stays exact — a fourth theme joining the set is a
regression, and a theme that leaves it forces its exemption out — but
nothing is owed on the three that are in it.

The reading below is kept: it is the measurement, and it is still true.


Found while fixing B17, and it is the same pair seen from the other side.
The cover tag is `mark` painted on the cover ground, which on a light
theme *is* `ink` — so catppuccin's tag measured the identical 3.05:1 as
its fact box, and moving `color.mark` fixed both at once. Three other
themes are below the floor for the same reason and were not touched:

| theme | `cover.kicker.fg` on the cover ground |
|---|---|
| pop-tangerine | **2.19:1** |
| pop-lemon | **3.22:1** |
| rose-pine | **4.24:1** |

The tag is 12px bold — not large text — so 4.5:1 is the right bar, not
3:1. Measured from the resolved registry, compositing to 8-bit channels.

Pinned as an exact set, `COVER_TAG_BELOW_AA`, in
`test_the_cover_tag_is_measured_on_the_ground_the_cover_paints`. The set
is the same idiom `KNOWN_PALETTE_FAILURES` used for B17: it cannot grow
in silence, and a fix forces the exemption out with it.

**This entry exists because a pinned set is a guard, not an intention.**
B17 was fixed because it had both — a test that stopped it spreading and
a backlog entry saying someone meant to deal with it. A pinned set alone
would have been a headstone that reads like a decision. Recording it here
is what makes it a debt rather than a shrug.

Deliberately not fixed with B17: a `cover.kicker.fg` literal per theme is
one line each, but the values are an artistic choice on three palettes,
and B17's decided route (move `color.mark`) does not transfer — on
pop-tangerine it would take `mark`-on-page from 3.80:1 to 1.85:1, which
is worse than what it repairs.

Related: `share.rule-fg` on the 15 **light** themes sits at 1.41:1
(pop-tangerine) to 1.46:1 (crimson). The argument that justified raising
it on dark themes applies unchanged — the share button's fill *is* the
popover's fill, so the 1px border is the only thing saying "button" — but
fixing it means moving the registry default `#00000029`, which touches
every light theme at once. Dark and light are asymmetric there until
someone decides that default.

---

## C1 — Test AST « aucune écriture nue hors helpers » — DONE in v0.33.2

**Type:** test d'architecture.
**Signalé dans:** `delete-before-1.0/newargs/PLAN-CLI.md` §6 Phase 3 (ligne 199), comme non
implémenté. Le test `test_no_bare_filesystem_write_outside_helpers`
(`tests/test_lightwebpres.py`) est bien un balayage AST du source : il
interdit `.write_text()` et `.mkdir()`, ainsi que les copies `shutil`, hors
des helpers `_write_file`, `_mkdir`, `_copy` et `_copytree`. Il couvre donc
l'intention de l'entrée ; aucun second test AST n'est nécessaire.

**Status:** résolu ; vérifié le 2026-08-15.

## C2 — `series article add/remove/set` — EXCLU (décision)

Hors périmètre de la refonte CLI v0.24 (`delete-before-1.0/newargs/PLAN-CLI.md` §7).
Nécessite son propre cahier des charges ; ce n'est pas une dette mais une
décision de périmètre. Non implémenté et volontairement absent.

**Status:** exclu.

---

## C3 — Variantes filtrables par `tags:` — IMPLEMENTÉ ET TESTÉ EN NAVIGATEUR

Le format accepte désormais des tags de variante sur les slides : `default`
est implicite, `excluded` est retiré au build, et les autres tags sont filtrés
dans le navigateur avec la touche `L`. Le renommage éditorial `tag:` →
`kicker:` est séparé de cet axe et ne doit pas être confondu avec les tags
d'instance ou le version tag.

`series_meta.lang_tags` associe un tag à un pack typographique ; le premier tag
de langue porté par une slide sélectionne son moteur, avec `--lang`/`LWP_LANG`
comme fallback. `audit` signale les tags invalides et les packs absents sans
bloquer. Le comportement est couvert par les tests black-box, le test
navigateur (`tests/slide_tags_e2e.cjs`, menu, filtrage, persistance,
rechargement) et la documentation permanente.

**Status:** implémenté et vérifié ; les 13 tests e2e navigateur ont été
exécutés le 2026-08-15 avec Node + Playwright.

---

## C4 — Audit 2026-08 : décisions actées et dettes restantes — v0.33.0

L'audit `docs/AUDIT-2026-08.md` (14/08/2026) a été dépouillé. Ce qui a été
corrigé dans la release `v0.33.0` :

- **D-1 (bloquant)** : le filtre de variantes ne masquait pas visuellement
  les slides — `.slide[hidden], .nav-btn[hidden] { display: none }` ajouté
  au squelette (même piège que la galerie avait déjà eu avec
  `.theme-row[hidden]`).
- **S-1** : les chaînes du pack de langue sont désormais échappées selon
  le contexte (entités HTML dans les attributs, JSON dans le nav.js) —
  un pack ne peut plus sortir d'un `title=`/`aria-label=`.
- **S-2** : `--lang`/`LWP_LANG` validé (`[A-Za-z0-9_-]+`) avant d'atteindre
  `<html lang="…">`.
- **A-1** : `watch` accepte `--no-nav`/`--no-index`/`--no-readme`/
  `--drafts-only` (le code était en retrait de la doc).
- **A-6/A-7/A-8/A-9** : `--help` complété (`--slides-page-numbers`,
  `--templates`, `--no-nav` sur verify, forme répertoire de `theme show`)
  et verrouillé par un test contre les tables d'options ; AGENTS.md ne
  prétend plus que l'aide est générée.
- **B-5** : `resolve slide_page_numbers` résout de nouveau.
- **P-1 (décision)** : la frontière de confiance du HTML brut est
  désormais écrite (spec §6.2, README, SKILL) : pas de sanitizer intégré ;
  le markdown tiers doit être assaini en amont.
- **S-3** : la page web divulgue la persistance sessionStorage du jeton ;
  **S-4** : validation explicite des membres de zip (zip-slip) ;
  **S-5** : guillemets du chemin neutralisés dans la commande du garde
  `file://` ; **S-6** : timeout sur `node --check` ; **S-7** :
  `Options -Indexes` ; **S-8** : séquences de contrôle terminal
  neutralisées dans `log()`.
- **F-1** : le test byte-identité est repointé sur `v0.33.0` ; la dette est
  close.

Ce qui reste volontairement ouvert :

- **CSP absent de `web/`** : décision documentée dans `web/.htaccess`
  (inline scripts + wasm + connect-src arbitraire = protection faible pour
  un risque de casse élevé ; pas de sink innerHTML à protéger). À revisiter
  si la page passe à des scripts nonce'd.
- **Déploiement « racine du dépôt »** : copier tout le dépôt tel quel sous
  une racine HTTP expose `.git/`, `delete-before-1.0/` et les tests ; la mise
  en page sûre (servir `web/` seul) est documentée dans le README.
- **E2e navigateur** : exécuté le 2026-08-15 sur un poste avec Node +
  Playwright global — les 13 tests du volet navigateur passent (dont le
  menu de variantes et les axes `note.*` ; le comparateur du test `note`
  a été corrigé pour résoudre les valeurs fluides `max()`/`clamp()` au
  lieu de comparer la chaîne brute).

**Status:** décisions actées ; dettes restantes listées ci-dessus. Le statut
« e2e navigateur en attente de l'outillage » de l'ancienne section C3 est
historique et ne s'applique plus.

## B19 — `audit --strict` is blind to every warning the build emits — FIXED in v0.37.0

Recorded here on 2026-08-18 because it was the one open point left in
`delete-before-1.0/docs/PLAN-CORRECTIONS-2026-08-17.md`, a design document whose lots are
all delivered and which is therefore leaving the active tree. The point
itself was never settled, so it moves rather than goes.

`--strict` inverts the exit code on the slightest warning, and is
documented as a CI gate. But `audit` never compiles anything, so warnings
raised **during a build** are invisible to it. Counted on the current
tree: **ten** `log('warn', …)` sites live in the build path — an image
escaping the article directory, a symlink skipped, a missing language
pack, a pinned property that no longer exists, an inherited
`templates/style.css`, an article that could not be read, among others.

A pipeline gated on `audit --strict` can therefore be green while a build
of the same series prints a real warning. That is a hole in the gate, not
in the warnings.

**Two coherent outcomes, and the ambiguity is the actual defect.** Either
`--strict` becomes the complete gate — which means `audit` learns to
raise what the build would raise, without building — or the documentation
stops presenting it as one and names what it covers. Leaving it half-way
is what makes it a trap: it looks like a gate.

**DECIDED 2026-08-18: the complete gate.** The owner's reasoning is worth
keeping because it settles the cost objection that had blocked this:
*a build is very fast on a human scale, while a missed audit can have
graver consequences — so the cost of auditing is not a problem.* This is
the same decision as B24 seen from the exit code, and the two close
together.

Also recorded, since this entry's own number had drifted: it claims ten
`log('warn', …)` sites "in the build path". Measured 2026-08-18 by AST,
there are **ten in the executable altogether**, spread over nine
functions, and several are nowhere near a build — `_warn_legacy`,
`cmd_resolve`, `cmd_series_info`, `cmd_refresh_templates` (twice).
Establishing the real partition is the first step of the lot, not a
prerequisite to the decision.

Sharpened by the v0.36.0 work, which added a warning class to `audit`
without asking what `audit` does not see.

**FIXED in v0.37.0.** `audit` renders the series in memory and collects
what the render says through a hook in `log()` rather than through an
enumeration of sites — so a warning added later is collected later, which
is precisely what drifted here. The partition was measured first, as the
entry asked: four of the ten sites are what a series can raise without
`audit` seeing it, and each has a test. A render that turns out **fatal**
now counts too: `audit` used to print an `[ERROR]` and then conclude "No
warnings", exiting 0, on a series no build could produce.

One thing the fix made worse and did not close: `audit`'s own warnings go
to stdout while the render's go to stderr, so a single run splits them
across both streams. Filed as **B26** rather than folded in.

## B20 — Only three components can carry a halo, and the worst-served one is a slide heading — DECIDED 2026-08-18: the halo belongs to the theme

From `delete-before-1.0/docs/THEMES-A-ECRIRE-2026-08-17.md`, absorbed here for the same
reason as B19: the document is delivered, this decision is not.

`page.shadow` is inherited, so its `em` resolves once at the root and
propagates as an absolute length. A halo is therefore proportional to the
glyph only where a component declares its own. There are **three** such
anchor points — `page`, `title1`, `highlight` — and neither `title2`, nor
`summary`, nor `fact`. Measured, blur over rendered size:

| element | size | blur ÷ size |
|---|---|---|
| kicker, `fact-label`, source | 13.5 px | 0.15 |
| summary | 24.3 px | 0.09 |
| **slide `h2`** | **42.3 px** | **0.05** |
| `h1` | 54.9 / 31.5 px | 0.26 |
| key figure | 97.2 px | 0.13 |

The slide heading is the worst served, and it is a heading.

**The decision**: accept that the atmosphere is uniform and only the
title and the key figure get a proportional halo — which is defensible —
or add anchor points to the registry. The second is a change to the
**engine**, not a theme setting, which is why it is a decision rather
than a task.

Recorded alongside it, so it is a choice and not a discovery: `page.shadow`
being inherited, it also reaches the chrome — progress dots, counter and
presenter panel carry the theme's shadow at 2.1 px / 16 %.

**DECIDED 2026-08-18: the halo belongs to the theme, which may decide all
of it.** Anchor points go into the registry, and the three axes extend to
every textual component rather than the three that have them.

What already works, and is worth knowing before designing the extension:
`shadow.fg` is **independent of the character's own colour**, so the two
effects the owner named are already expressible on the three components
that carry axes — a coloured glyph under a white halo (a neon tube behind
a coloured mask), or a halo tinted toward the ground to simulate bleed.
Measured 2026-08-18: nine axes exist, `fg`/`blur`/`dy` on `page`,
`title1` and `highlight`, all defaulting to `transparent`/`0`/`0`.

So the gap is not expressiveness, it is **coverage**: `title2` — the slide
heading, the worst-served element in the table above — the kickers, the
sources and the fact-box body have no axis at all.

**`dx` is added, decided the same day.** There was `dy` and no `dx`, so a
halo could only be offset vertically — a constraint nobody chose, arrived
at by only ever needing the vertical case. Every component that gets the
axes gets four of them: `fg`, `blur`, `dx`, `dy`. Note for the lot: `dx`
is the one axis of the four with no reasonable one-sided default, since a
shadow offset only to the right is as arbitrary as one offset only down —
its default is `0`, like `dy`, and the neutral halo stays the centred one.

## B21 — Pinning dark colours does not make the furniture dark, and nothing says so — FIXED in v0.37.0

Same origin as B20, and the most consequential of the three.
`DARK_FURNITURE_PROPS` keys off the theme definition's `dark_background`
flag. That flag is **not a registry property**, so no amount of pinning in
`settings.conf` can reach it. An author who darkens `color.page` and
lightens `color.ink` gets a dark palette wearing light furniture: the
veils stay white and opaque over a near-black page.

Re-measured on the current tree, pinning a dark palette onto a light
theme: **38 body-text pairs below AA, worst 1.027:1** — text on its own
ground. The original relevé recorded 21 below AA at 1.08:1, so the trap
has got worse as the surface has grown, not better.

Nothing warns. The build is silent, `audit` is silent, and the author
discovers it by looking — or does not.

**This is the same class as the meta-key silence closed in v0.36.0**: a
configuration that cannot work, accepted without a word. The difference
is that here the cause is structural — the author is asking for something
the cascade cannot express.

**DECIDED 2026-08-18: it warns** — and the ruling is wider than this
entry, because the question turned out to be wider.

**The boundary, measured 2026-08-18** on a real series, six settings
pinned one at a time. What the tool refuses, fatally, is *malformed*
input: a property that does not exist, a reference cycle, an invalid
colour, an unknown unit. What it accepts in silence — exit 0 from `build`,
from `audit`, **and from `audit --strict`** — is *well-formed and
meaningless*:

| pinned in `settings.conf` | build | audit | audit --strict |
|---|---|---|---|
| `page.fg` equal to `page.bg` — contrast **1.00:1** | 0 | 0 | 0 |
| `nav-dot.bg-active: page.bg` — the dot disappears | 0 | 0 | 0 |
| `fact.strong.fg` equal to `fact.strong.bg` | 0 | 0 | 0 |
| `note.size: 3px`, under the 12 px floor | 0 | 0 | 0 |
| a dark palette pinned onto a light theme (this entry) | 0 | 0 | 0 |

So the engine **validates form and never meaning**. That is the general
statement, and `dark_background` is one instance of it.

On this entry's own case, measured the same day: **27 furniture properties**
key off the flag, and pinning does not move one of them. On `ledger` with
a dark palette pinned, against `dracula`:

```
slide.rule-fg   ledger=#0000001A   ledger+dark=#0000001A   dracula=#FFFFFF24
quote.rule-fg   ledger=#00000029   ledger+dark=#00000029   dracula=#FFFFFF3D
```

Black rules at 10% opacity over a near-black page — identical to the light
theme, byte for byte.

**What "it warns" means in practice.** Judging this requires the resolved
values, which is exactly what B24 decided `audit` will hold. So this is not
a separate mechanism: it is the first thing the raised `audit` says.
`--strict` then turns it into a failure for anyone who wants the gate
(B19), which reconciles it with `specifications.md` §9.5.6 — that section
calls an invisible progress dot a broken control rather than a bold
palette, and warning-plus-`--strict` gives it a refusal without making the
default refuse a deliberate choice.

Promoting `dark_background` to a registry property stays possible and is
**not** decided here; warning removes the silence, which was the defect.

**FIXED in v0.37.0.** `audit` judges the **resolved** sheet — not what the
author typed, which is the only way to see a fault nobody wrote:
`footnote-call.fg-marked` defaults to `fact.strong.fg`, so killing the
latter takes the former into invisibility with it, and the judgement
reports both. Three findings — text below the illegibility floor, a
navigation control below 3:1, an absolute size below the readability floor
— and the four silent rows of the table above now warn and fail
`--strict`. The fifth, the dark palette pinned onto a light theme, warns
by consequence rather than by name: the furniture stays light, the pairs
it makes are measured, and the ones that collapse are reported one by one.
Naming the cause instead of its effects still wants `dark_background` in
the registry, which stays open.

The thresholds are **derived from the delivered catalogue, not chosen**,
because B5 and B18 decided a theme is not required to reach AA and a
threshold that made a shipped theme warn would be a wrong threshold. A
test sweeps every theme plus the default sheet to keep it that way.

## B22 — `--version` after a command is a silent no-op — FIXED in v0.37.0

`--version` is declared a global option: §2.4.1 promised all eight are
accepted "before or after" the command, and that no command can refuse
them. Seven of the eight hold. `--version` does not.

Measured on the current tree:

| Invocation | What happens |
|---|---|
| `lightwebpres --version build s` | prints `LightWebPres v0.36.0`, exits 0 |
| `lightwebpres build s --version` | **builds the series**, prints no version |
| `lightwebpres theme gallery --version` | **writes a 13 MB gallery file** |
| `lightwebpres status s --version` | prints the status report |

The cause is structural, not a typo. `_parse_global_options` short-circuits
on `--version` only while scanning the head of the line, before a command
has been chosen. The post-command parser accepts the flag — `allowed =
_COMMAND_OPTIONS[command] | _GLOBAL_OPTIONS` — and then never reads it.

**Why it is worth an entry rather than a shrug**: §2.4.2 states that an
option the parser does not recognise is a fatal error, "never a silent
no-op". This is the one option that is recognised and silently does
nothing — the exact failure the rule exists to forbid, sitting inside the
rule's own section. `--help` has the same shape, but `-h` after a command
does print the command's help, so only `--version` is affected.

**Resolved by refusing it.** The table conflated two natures: six
modifiers, for which "before or after" is a real convenience, and two
actions that replace the command rather than modify it. `--help` earns its
post-command position because there it means the help OF that command;
`--version` has no contextual meaning, so honouring it after a command
would silently discard the command typed. It is now refused by name, with
a message pointing at `lightwebpres --version`. Reference practice is split
the same way — `git commit --version` refuses, `curl` and `tar`
short-circuit — and only `git log`'s accept-and-ignore matched what this
did. `_GLOBAL_MODIFIERS` and `_GLOBAL_ACTIONS` now carry the distinction in
the code. The `--` terminator, which the `--help` check had been ignoring,
covers both actions.

## B23 — `--inline-images` does not reach an included article's images — FIXED in v0.37.0

`--inline-images` promises "a single self-contained HTML file" (§8.4).
For an image written in a slide, it delivers: measured, a 309-byte SVG
becomes 419 bytes of data URI, ×1.36, and `public/img/` is not copied.

For an image inside a file pulled in by a `full-article` slide, it does
not. `build_article` calls `convert_markdown(article_md, ...)` without
`inline_images=` or `articles_dir=` — every other call site passes both.
Measured on the series `lightwebpres demo` ships, built clean with
`--inline-images`: `first.html` contains **0** `data:image` URIs, **1**
relative `src="img/demo-figure.svg"`, and `public/img/` **does not
exist**. The page is broken, and the build says nothing.

That is worse than the missing feature: the option's whole point is that
the file travels alone, and the one configuration where it silently
fails to is the one an author reaches for when the article is long.

**Resolved, and guarded.** The call site now passes `inline_images=` and
`articles_dir=` like every other. The invariant got the build-time guard it
deserved: `validate_self_contained` fails the build when a page built with
`--inline-images` still carries a relative `src`, naming the file and the
paths. Two cases reach it — raw `<img>` HTML, which the converter never
touches by design, and an image the containment guard refused, whose `src`
survives its warning. Both would ship a dangling reference.

Worth recording: the full suite passed with the one-line fix reverted. The
defect had no guard at all, which is why two were written.

## B24 — `audit` inspects a poorer representation than the one that builds the page — FIXED in v0.37.0

Filed first as a small defect: a footnote label outside `\w+` reaches the
reader as literal text, and `audit` reports nothing. Measured: `[^a-b]` in
a slide publishes the literal string `note[^a-b]`, its body renders as an
ordinary paragraph, `audit` emits **0** warnings, exit 0 twice.

It is not a small defect. It is the visible end of a structural one, and
the right entry is the structure.

**Where each command stops.** Measured by reading the call graph:

| command | goes as far as | writes |
|---|---|---|
| `audit` | `parse_markdown_extended` — the syntax tree | nothing |
| `verify` | **the full render** (`build_article`, `build_index`) | nothing |
| `build` | the full render | everything |

`audit` never calls `convert_markdown`. The footnote pattern
(`\[\^(\w+)\]`) lives inside it. So the label defect is not a check
somebody forgot to write — it is **unreachable** from where `audit`
stands, along with every other fault produced at render time.

**The shape that would fix it already exists in the repo.** `verify` is
literally "build without writing": it calls the same `build_article` and
`build_index`, holds the HTML in memory, and compares it to what is on
disk. What separates it from what `audit` needs is not the mechanism but
the purpose — it compares where `audit` would report.

**The decision.** Raise `audit` to the level `verify` already occupies:
one render pipeline, warnings collected during the render instead of by a
separate pass over a poorer tree. Against it, honestly:

- `audit` becomes as slow as a build. Today it is the cheap command an
  author runs constantly.
- The render functions return HTML and report nothing. Collecting
  warnings through them needs a channel — a scope object threaded down,
  or a module-level collector, both of which touch a lot of code.
- Three commands would share one path, so a bug in it is a bug in all
  three. That is the point, and also the risk.

For it: every fault produced at render time becomes auditable at once,
and the failure mode this entry documents — *the guard looks at a
representation poorer than the one that makes the page* — stops being
available. It is the same class as B21: not a missing check, a place
where a check cannot see.

**DECIDED 2026-08-18: `audit` renders, and goes one level deeper than
`verify`.** The cost objection is answered above (B19): a build is fast on
a human scale, a missed audit is not cheap. The owner added the part that
makes this more than a plumbing change — *see whether the depth should be
increased.* It should.

`verify` renders and **compares**. The level above is to render and
**judge**: measure the contrast of the pairs actually resolved from the
author's `settings.conf`, check the size floors, check the 3:1 navigation
floor of `specifications.md` §9.5.6. None of the three exists on the
author's side today, and `measure_contrast` — which already does exactly
this work for `theme show` on built-in themes — has simply never been
pointed at a series. See B21 for what that judging must say.

The narrow footnote-label fix folds into the lot rather than preceding it:
a call or a body matching `\[\^` but not `\[\^\w+\]` is a warning naming
the article and the label.

**FIXED in v0.37.0**, in three parts, and the row of the table above that
said `audit` stops at the syntax tree is no longer true.

`audit` renders. It goes one level past `verify`, which renders and
compares: it renders and **judges** — see B21 for what the judging says.
`--templates` is the one scope that does not render, since restricting
`audit` to the presentation layer and then dragging per-article faults in
would contradict the option.

The footnote-label guard did **not** fold in where the entry expected. It
lives in the syntax pass, not the rendering one, and for a reason worth
keeping: a broken label is a shape, settled before anything renders — and
the converter never sees these labels, so rendering has nothing to report
about them. What the converter would not read as a note either is skipped,
so that acting on a warning is always the right move: code spans, fenced
blocks, raw HTML, and `[^a-b](url)`, which the link rule claims before the
note rule ever sees it.

## B25 — Two rules the project states and does not follow — HALF FIXED in v0.37.0

Two invariants written down as requirements, neither applied nor guarded.
Filed together because they share a shape: a rule that reads as settled
and is not.

**The non-breaking space in a language pack.** §19.3.1 rule 2 said to
write it as ` `, "never as a literal character", and claimed both
built-in packs do so "for this reason, learned by losing it". Measured:
`grep -c 'u00a0' lightwebpres` → **0**. Both `LANG_FR` and `LANG_EN` carry
literal U+00A0, and `init` writes 9 literal ones into `language/fr.json`.
The rule is sound — an invisible character does get lost in a copy, an
editor, a diff — but stating it while doing the opposite is worse than
either. §19.3.1 now records it as a known, untreated risk. Converting the
two packs is mechanical; the guard is a test asserting no literal U+00A0
in the pack literals.

**Done in v0.37.0.** Both packs converted (18 occurrences), `init`
propagates the escape into the file it writes, and two guards hold the two
halves: one refuses a literal U+00A0 anywhere in the executable, the other
asserts every `nbsp_*` rule still emits a non-breaking space on a control
string. The first protects the writing, the second the effect — a rule can
no longer become a no-op unnoticed. The engine's output on thirteen
control strings is byte-identical before and after.

**`_validate_zip_members` is shared without being declared shared.**
§23.1 claimed the only module-level names that could collide between
`web/app.py` and `web/git_sync.py` were prefixed apart. A third is not:
`_validate_zip_members`, the zip path-traversal guard, is defined at
module level in both. `index.html` executes `app.py` then `git_sync.py`
in one namespace, so the second definition wins. Compared by AST with
docstrings stripped, the two bodies are **identical** today — so it is
inert, and inert by coincidence. It is a security guard; the two copies
diverging would be silent. Either prefix it like the other two, or keep it
shared and add the test that asserts the bodies match. **Still open**: it
lives in `web/`, not in the executable, and it wants its own lot.

## B26 — `audit` prints its warnings on stdout, the render's on stderr — OPEN

`specifications.md` §2.4.1 is unambiguous: error, warning, info and debug
go to **stderr**; progress and a command's answer go to stdout. Twenty
`print('[WARNING] ...')` sites in the executable ignore it, and they are
all in `audit`.

That was survivable while audit was the only thing talking. It stopped
being survivable in v0.37.0, because the rendering pass raises its
warnings through `log()` — which obeys the rule. So one `audit` run now
splits its warnings across both streams: the editorial ones on stdout, the
render-borne ones on stderr. Someone grepping stderr for `[WARNING]` gets
half of them and has no way to know.

Measured: 20 offending sites in the executable, and exactly **one** test
assertion couples `[WARNING]` with stdout, so the change is small. What is
not small is the decision — piping `audit | grep` breaks for anyone who
built on the current behaviour.

**The exit code is not affected**: `--strict` counts every warning
whichever stream carried it, so the gate B19 asked for is complete either
way. This is about a human reading the output, not about CI.

Filed rather than folded into the v0.37.0 lot. That lot was "audit renders
and judges"; rerouting twenty print sites is a different change, and doing
it quietly under cover of another is how a diff becomes unreviewable.

## B27 — The default sheet fails the navigation floor its own test enforces — OPEN

Found while deriving the thresholds for the judgement pass, and it is a
defect in the delivered defaults, not in the new guard.

`table.col-snap.rule-fg` defaults to `mark`, which on the **registry
defaults** — the sheet a bare `init` writes, with no `theme:` line — is
pure yellow `#FFFC00` on white: **1.02:1**.

What makes it an entry rather than a curiosity: **23 of the 57 themes
carry a hand-pinned override for exactly this property** (21 of them to
`call`), put there to clear the existing hard test. The default sheet
never got one, because that test iterates `THEMES` and the defaults are
not a theme. The guard was written, the catalogue was brought up to it,
and the one sheet every new series starts from was never in scope.

Measured alternatives on the default palette: `call` gives 2.98:1 and
would **not** clear the floor either; `ink-quiet` gives 4.66:1; `nav`
gives 8.02:1.

Not fixed here. Changing a registry default repaints the 34 themes that do
not override it, which is a catalogue decision and wants its own lot.

Note that §9.5.2 states a carve-out for `mark` as a rule colour, so this
may be judged acceptable — but then the 23 overrides are the anomaly, and
one of the two readings is wrong.


## B28 — A list item was one line, and its continuation left the list — FIXED in v0.37.0

Reported 2026-08 from a real 28-article corpus (29 pages, 5.4 MB), where
`build`, `verify` and `audit` were all green and **73 Markdown markers
were visible on screen**. Ten files carried this one — mostly lists of
limits and caveats, where every item is long and therefore wrapped.

The item ended at the end of its first line. The continuation did not
merely lose its wrapping: it became a paragraph of its own, emitted
**after** the list closed. Measured on three items, two of them wrapped:

```
<ul><li>Item un, coupé</li></ul>
<p>  sur deux lignes.</p>
<ul><li>Item deux…</li></ul>
<p>non indentée du tout.</p>
<ul><li>Item trois simple.</li></ul>
```

One list of three became **three lists of one**. So the loss is threefold
and only the third is visible: the reading order, the structure a screen
reader announces, and any emphasis spanning the two lines, which ships as
literal `**`. CommonMark takes both the indented continuation and the
unindented *lazy* one; neither worked, while a paragraph outside a list
handled the same case correctly.

**FIXED.** An item runs until a blank line or the start of another block —
the same `_is_paragraph_continuation` a paragraph uses, shared rather than
restated, because an item's text IS a paragraph and two copies of that
judgement would drift.

Worth keeping from the report: correcting the CORPUS instead of the tool
produced two collateral casualties — a note body glued to the previous one
(which `audit` caught) and five unbalanced paragraphs. That is the
argument for fixing the parser rather than teaching authors to avoid it.

## B29 — A structural field ships Markdown to the reader, and nothing said so — FIXED in v0.37.0

Same report, 32 fields across 16 pages, `source:` lines among them — the
exact place a reader checking a claim looks. A field is a VALUE, one
physical line taken verbatim; the free text beside it is Markdown; nothing
in the file marks the border.

The border is also not where an author would guess. A field passes **raw
HTML** straight through — `page_title: A<br>B` is in our own README — so
someone who finds that markup "works" in a field generalises, and
`**gras**` reaches the reader as five literal characters.

**FIXED**, as a warning: the behaviour is right and the silence was the
defect. Only PAIRED markers count — `2 ** 8` is arithmetic and `**kwargs`
is Python, and warning on those is the noise that gets a check switched
off. It reads the parsed slide rather than the source, because only the
parse says which side of the border a given `**` fell on.

## B30 — Nested emphasis, and a net for whatever the checks do not name — OPEN

Two proposals from the same report, neither delivered, both for the same
reason: measured, they carry false positives that a release meant for
writing must not.

**Nested emphasis.** `Un gras **imbriqué **dans un autre** ici**` renders
the emphasis *exactly inverted* — the passage meant to be bold is not, and
what surrounds it is — and `****quatre****` leaves two asterisks visible.
This is **conformant**: CommonMark does not nest `**` in `**`. So it is
not a rendering bug but an editing trap with no net, and it appears
naturally when adding emphasis inside an already-emphasised passage —
typically during a revision. The report's nine occurrences were all
introduced in a single day of corrections. The asterisk count stays even,
so no balance check sees it.

**A scan of the rendered text.** The report's own transversal suggestion,
and it is the right idea: `verify` compares the render to a reference, and
nothing checks that the render does not contain *unrendered source*. With
`audit` now rendering, it costs nothing to run.

Both want the same care, and the report's claim that neither can produce a
false positive is wrong. Measured on an article documenting Python, the
proposed regex fires **4 times** on `a ** b`, `**kwargs` and a fenced
block containing `def f(**kwargs): return 2 ** 8`. Excluding `code` and
`pre` before stripping tags brings it to **0**. The machinery that already
skips code spans, fenced blocks and raw HTML exists here, in
`unrecognized_note_labels`.

One residue has no clean answer on the rendered side: `\*\*` legitimately
renders as `**`, and the backslash is gone by then. A source-side check
sees the escape; a rendered-side net does not. That is the argument for
doing it on the source, and the argument against is that a net exists
precisely to catch what nobody enumerated.

Not in the release the owner is about to write 28 articles with. A noisy
`audit` in that release is worse than a silent one.

## B31 — `auto` is a length, and on a shadow axis it deletes the shadow — OPEN

`LengthType` accepts `auto` alongside `0` and the units, which is right
for the axes that can take it and wrong for the ones that cannot. Written
into a shadow axis it validates, resolves, and emits: `card.elevation.dx:
auto` becomes `box-shadow: auto 1px 8px 0 #0000000F`, which no browser
can parse, so the card loses its shadow entirely — no build error, no
`audit` warning, nothing in `theme show`. Measured: the value survives
every check the tool makes and dies silently in the renderer.

The same hole is open on the four halo axes and on every other length
whose CSS context has no `auto` — a blur, a spread, a border width. It
predates the elevation work; that work widened it by sixty-five
properties and thirteen declarations.

What it is really about is that `length` is one type doing two jobs. The
fix is a narrower type for the axes where `auto` is meaningless
(`PROP_OFFSET`, or a flag on `LengthType`), not a special case at the
emission site — the engine's whole shape is that a value is checked once,
where its type is named. Deciding which of the existing length properties
legitimately accept `auto` is the work, and it is a sweep of the
registry, not a patch.

## B32 — A fix to `nav.js` or a language pack never reaches a series that already exists — FIXED, cause and symptom both

Two files the tool owns live inside the series and are read from disk at
every build: `templates/nav.js` and `language/*.json`. `init` copies them
in whole, and from then on the build uses the copy. So a behaviour the
tool fixes reaches nobody who already has a series — and the only thing
between an author and that is what the build says about it.

It said the wrong amount. `nav.js` got an `[INFO]`, which `--quiet`
silences, and `--quiet` is what a pipeline runs. The language packs got
nothing whatsoever, on any command, though a pack carries the typography
rules *and* the interface strings, so a stale one keeps an old spacing
and an old vocabulary at once.

The bill was three fixes shipped in v0.39.0 — the cursor, the mouse
selection, the F key on the index — none of which reached an existing
series, reported three times as "it still does not work" by the person
who asked for them. The line that would have explained it was the one
nobody saw.

**FIXED** at warning level, for both files, with a case each way: a
current series stays silent, a stale one warns under `--quiet`, and a
pack the tool does not ship (`de.json`) is left alone, because that is
somebody's work rather than a stale copy. The remedy differs by file and
the message says which: `template update` for `nav.js`, the author's
judgement for a pack, since `rules` replaces the base set wholesale and
overwriting the file would erase what they added.

**And then the cause**, in the same release. Warning about a copy repairs
the symptom; not handing out the copy repairs the cause, and the measured
fact settles which was needed: on a fresh `init`, all three files were
byte for byte identical to what the executable already held. Not one was
a customisation. What they were was a snapshot, and the snapshot is the
freezing mechanism.

Autonomy did not depend on them either — `init` copies the executable
into the series (§11.1) and the executable contains all three, so the
archive was always the executable and the copies added nothing to it.
Measured on a demo series: four pages built from a series holding the
copies are byte-identical to four built from one without them.

So `init` writes none of them, and two commands hand them over to whoever
wants one. `template show <file>` prints one on stdout — no series
needed, which serves the commoner need (what does the B key do) without
leaving anyone owning a frozen copy for having asked. `template write
<file> [dir]` installs one where the build reads it, through the build's
own path resolution, because the LAYOUT is the tool's knowledge and not
the author's: a redirect to the wrong directory leaves a file that does
nothing, with no error. It refuses to overwrite without `--force`, and it
says what the copy costs at the moment the cost is taken on — which is
the whole lesson above, that the trap was never the copy but the not
knowing.

`template update` became the repair path for a series scaffolded before
this: a copy identical to the built-in one is removed (lossless by
construction), a differing `nav.js` is saved as `.bak` and removed, a
differing language pack is reported and kept, since its `rules` replace
the base set wholesale and overwriting it would erase the author's own.
