# Decisions

The **permanent** register of what this project has decided, and of what
it has not decided yet: defects with no urgency, change requests, format
questions still open. Unlike `delete-before-1.0/JOURNAL-1.0.md` (the 1.0
working memory, deleted at release), this file outlives releases —
anything that has to be findable "later" goes here, not in the journal.

Every entry says what has been **verified** and what remains to be
**decided**.

This file was called `BACKLOG.md`, and the name was wrong in a way that
showed: a backlog is a list of work waiting to be done, so an entry that
turned out to need no work had nowhere to go and stayed OPEN. Most of
what is here is not waiting for anything. It is a decision, with the
measurement that made it.

## The six states

An entry is in exactly one of these, named on the field line directly
under its title:

| État | Ce que cela veut dire |
|---|---|
| `à étudier` | La question n'est pas assez mûre pour qu'on agisse. Ce qui manque est dit dans l'entrée. |
| `à faire` | Décidé, pas implémenté. |
| `en cours` | En cours d'implémentation. |
| `terminé` | Fait, avec la mesure qui le montre. |
| `abandonné` | Décidé de ne pas faire. La raison est dans l'entrée, parce que la question reviendra. |
| `sans objet` | L'entrée n'a plus de sujet — soit elle n'en a jamais eu, soit il a cessé d'exister. Ce n'est ni un abandon ni un achèvement. |

The other three fields appear only when they are known: `Depuis` (the
date the state was reached), `Version` (the release that carried it),
`Voir` (where the answer now lives). **A field is never filled from
memory.**

`sans objet` exists because of three entries. Two were written against a
bar the project does not hold and never held (B5, B18), and one described
a defect that stopped being possible when the mechanism under it was
removed (B33). Filed as `terminé` they would claim credit for work nobody
did; filed as `abandonné` they would suggest a live question was dropped.
Neither is what happened.

## How to read this file, and how it decayed

**The field line under a title is the entry's state. Nothing else in the
file is** — not the title, not the prose, not the index below.

**There is now an index, and what changed is not the reasoning.** The old
rule here was that a list of entry numbers with their statuses is a second
place to be wrong, and it was right on the evidence: the revision block
that used to sit at the top listed B15, B16 and B17 among the open entries
long after all three had been fixed. What that argument was missing is
that a second place to be wrong is only dangerous while nothing checks it.
The index below is generated from the field lines by
`tools/decisions_index.py`, and `test_the_decisions_index_matches_the_file`
recomputes it and refuses the suite if the two disagree. It cannot drift
without failing, so it may exist.

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

**And a state is a measurement, not a memory.** `terminé` here means
someone ran something and wrote down what came back. Where an entry claims
a figure, the figure is in it.

**The deliberation stays, behind a dated label.** A settled entry keeps
the reading it was written with — the four cases, the three options, the
measurement that killed a hypothesis — under a line saying whose day it
is and that its present tense is past. Deleting it was considered and is
the wrong trade: what makes this register worth keeping is not the
verdicts, which are also in the code, but why the verdict is that one.
An option ruled out and not written down comes back as a proposal in six
months.

That works only while the label is honest. A settled entry must not carry
a live question inside it: B2 held one for months — a marker syntax
nobody had decided — inside an entry marked settled, where any count by
state would have read it as decided. It is B35 now. **What is still open
gets its own entry and its own state**, however small.

## Index

<!-- INDEX: généré par `python3 tools/decisions_index.py`. Ne pas éditer à
     la main : la source est la ligne de champs de chaque entrée. -->

**à étudier** 7 · **à faire** 0 · **en cours** 0 · **terminé** 50 · **abandonné** 1 · **sans objet** 3

### à étudier

- **B10** — Gamut mapping for lightness-shifted inks
- **B11** — Dichromat separability is not verified
- **B27** — The default sheet fails the navigation floor its own test enforces
- **B30** — Nested emphasis, and a net for whatever the checks do not name
- **B35** — Reaching a verdict class without writing HTML
- **B36** — The engine can halo 32 components; the catalogue haloes three
- **B50** — Soft animation of cover colours

### terminé

- **B1** — Mid-paragraph image with a title
- **B2** — Visual verdict in a table cell
- **B3** — Body-text links are not themed
- **B4** — Key-figure alignment, as an option
- **B6** — The slide-progress dots miss the 3:1 readability floor
- **B7** — Text alignment axes (center, justify, per-component and per-block)
- **B8** — `extends` for external theme files
- **B9** — Typographic revision of the historical catalogue
- **B12** — Box drop-shadow (elevation) axes
- **B13** — `--content-max` is the one themeless variable
- **B14** — Literalize the skeleton; retire TEMPLATE_STYLE
- **B15** — The share popover's mobile overrides never apply
- **B16** — `page_dest: index.html` loses a page in silence
- **B17** — catppuccin's bold-on-highlight is at 3.05:1
- **C1** — Test AST « aucune écriture nue hors helpers »
- **C3** — Filtrage par `tags:`
- **C4** — Audit 2026-08 : décisions actées et dettes restantes
- **B19** — `audit --strict` is blind to every warning the build emits
- **B20** — Only three components can carry a halo, and the worst-served one is a slide heading
- **B21** — Pinning dark colours does not make the furniture dark, and nothing says so
- **B22** — `--version` after a command is a silent no-op
- **B23** — `--inline-images` does not reach an included article's images
- **B24** — `audit` inspects a poorer representation than the one that builds the page
- **B25** — Two rules the project states and does not follow
- **B26** — `audit` prints its warnings on stdout, the render's on stderr
- **B28** — A list item was one line, and its continuation left the list
- **B29** — A structural field ships Markdown to the reader, and nothing said so
- **B31** — `auto` is a length, and on a shadow axis it deletes the shadow
- **B32** — A fix to `nav.js` or a language pack never reaches a series that already exists
- **B34** — A structural field converts an HTML entity; the body does not
- **B37** — `requestFullscreen()` is refused from any non-left mouse event
- **B38** — The two pages share one skeleton and one script
- **B39** — The sources directory is called `sources/`, not `articles/`
- **B40** — The print family: three themes drawn for ink and paper
- **B41** — Print Boss adds a hand-marked newspaper to the print family
- **B42** — Print Ink and Print Grey keep a low-ink table header
- **B43** — Old Press adds a fixed-pitch print pair
- **B44** — Runtime themes stay opt-in and preserve author pins
- **B45** — Series JSON can choose a runtime theme catalogue
- **B46** — Help carries permanent provenance and names the theme shortcut
- **B47** — Essential themes ship by default
- **B48** — Séparer physiquement l’interface et la typographie
- **B49** — La locale du navigateur choisit seulement l’interface
- **B51** — L’inventaire rendu décide quelles images sont publiées
- **B52** — Le défilement instantané a sa propre touche
- **B53** — Les pins de série forment une variante runtime distincte
- **B54** — Un contrat unique pour les brouillons de slides
- **B55** — Les symlinks composent ; le traversal reste refusé
- **B56** — Images dimensionnables et zoom de présentation
- **B57** — Une fiche adjacente partielle doit être alignée avant la suivante

### abandonné

- **C2** — `series article add/remove/set`

### sans objet

- **B5** — Palette roles below AA against their own page
- **B18** — `cover.kicker.fg` is below AA on three themes
- **B33** — A moved anchor is invisible to everyone, including the tool that moved it

<!-- /INDEX -->

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

## B1 — Mid-paragraph image with a title

**État :** terminé · **Version :** v0.12.0

**Type:** implementation bug (the expected behaviour was already
specified).
**Reported against:** v0.11.0, in a long-form article (`_article.md`).
The inline pattern was given the optional title
group it was missing. A decision was made along the way: the title is
not thrown away but becomes a `title` attribute (a tooltip), never a
`<figcaption>` — and it goes through neither inline rendering nor
typography, which have no business inside an attribute value. Covered by
a test that exercises all four cases A/B/C/D **together**, since it was
testing them separately that let the hole through. Spec §6.1 updated.

*Analysis of the report below. It is the reading of that day, kept
because it documents the cause; read its present tense as past.*

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

## B2 — Visual verdict in a table cell

**État :** terminé · **Version :** v0.12.0

The question "gap or choice?" got an answer, and it was neither. The default stylesheet **already** shipped `.yes` / `.no` /
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

The one option this entry did not close — an in-cell marker syntax, so
the classes can be reached without writing HTML — is **B35**. It was
living here, in an entry marked settled, which is a good way for a live
question to become invisible.

*Framing of 2026-08-04 below. It is the reading of that day, kept because
it documents the need and the three options; read its present tense as
past.*

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

## B3 — Body-text links are not themed

**État :** terminé · **Version :** v0.12.2

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

## B4 — Key-figure alignment, as an option

**État :** terminé · **Voir :** B7

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

## B5 — Palette roles below AA against their own page

**État :** sans objet · **Voir :** spec §9.5.2

**Closed by the position, not by the numbers.** This entry was written as
a debt: roles under 4.5:1 against their own page, to be paid off theme by
theme until the catalogue was uniformly AA. There is no such bar, and the
entry had no subject. A theme is a stance; the project publishes what each
one measures, and that is the whole of what it owes a reader (§9.5.2).

Anything a project-owned palette needs is the project's own affair as a
theme author and is settled in the theme file, not tracked here as a debt.
Two things do survive this entry, and neither is about a level.

**One is fidelity, and it is a real defect of a different kind.** Seven of
the nine borrowed palettes are colour schemes drawn for a *dark* ground and
were rendered here on a light one. Dracula's green `#50FA7B` is meant to
sit on `#282A36`; on `#F8F8F2` it measured 1.29:1. That is not a palette
that scores low, it is a palette shown on a ground its authors never chose
— the theme notes recorded the compromise ("borrows the text-on-black
here, for want of an official light one") and nobody had measured the
consequence. Four of them — `dracula`, `tokyo-night`, `monokai`,
`everforest` — have since been returned to their own dark grounds, which
appendix A of `delete-before-1.0/REVISION-THEMES.md` establishes as a
**restoration** of fidelity rather than a correction of a score. Whether
the remaining three should follow is the same question, and it is the only
one this entry leaves open.

**The other is D6**, and the recent scoping decision makes it matter more
than it did: nothing in `theme list` or in the gallery distinguishes a
palette this project drew from one it borrowed. The distinction is now
load-bearing — the project holds its own palettes to its own floor as a
theme author and holds borrowed ones to nothing, precisely because they
are someone else's design — and a reader of the catalogue cannot see which
is which.

**What was measured, kept because measurements do not expire.** Three
roles paint real text, and against `--page` on the pre-B9 catalogue of 33:
`ink-quiet` under 4.5:1 on 9, worst 2.48 (`solarized`); `positive` on 11,
worst 1.29 (`dracula`); `accent` on 11, worst 2.05 (`tokyo-night`). After
B9 returned four palettes to their grounds: `ink-quiet` on 7 (worst 2.48,
`solarized`), `affirm` on 7 (worst 1.77, `nord`), `call` on 8 (worst 2.94,
`vaporwave`). Read them as a description of the catalogue, which is what
they always were.

**And one argument worth keeping, because it outlived its occasion.** Each
verdict is its own component since the theme refactor, so retinting one
moves nothing else, and `verdict.yes.fg: ink` is a one-line property
settable per theme, per series or as the shipped default. The reason to
reach for it is not a number:

> If the shape carries the information, the colour no longer has to carry
> it alone.

Every verdict already carries a shape marker (WCAG 1.4.1, and the engine's
weight rule means the marker survives a generic family alone). Once meaning
rests on shape, the colour on that cell is decoration — and decoration is
free to be whatever the theme wants it to be. That is an architectural
fact, and it is the reason a palette can be bold there without anything
being lost.

## B6 — The slide-progress dots miss the 3:1 readability floor

**État :** terminé · **Depuis :** 2026-08-17

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
mechanism). It is theme work, and it belongs with B9's remaining
typographic blocks.

## B7 — Text alignment axes (center, justify, per-component and per-block)

**État :** terminé

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

*Framing of the day the entry was written, below. Read its present tense
as past.*


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

## B8 — `extends` for external theme files

**État :** terminé · **Depuis :** 2026-09-01

The external-theme question is settled by the catalogue format. A theme file
is a complete UTF-8 snapshot of the typed property registry, with its own
metadata; it has no `extends` line and never inherits values from a lower
precedence slug. The one legitimate include remains the cascade itself: a
series' `settings.conf` sits on top of its selected theme.

The catalogue is resolved as **integrated < installed < user < series**.
Collisions replace the whole entry, while `builtin:<slug>` keeps the embedded
entry addressable. `theme create` provides an editable user snapshot, while
`theme migrate` reduces an existing series scaffold; `theme vendor` copies
complete snapshots into a series so its build does not depend on a user's home
directory. The browser digest partitions its session key when an external
snapshot changes.

Measured on the implementation lot: seven regression cases cover collision,
runtime propagation, session invalidation, essential-theme shadowing,
migration, vendor independence and rejection of incomplete files. The
decision is deliberately not to add inheritance later as a convenience: it
would make a collision's actual values depend on an invisible lower file and
would turn a portable vendored series back into a chain of lookups.

## B9 — Typographic revision of the historical catalogue

**État :** terminé · **Depuis :** 2026-08-20

**Applied, and narrower than the report.** `THEME_TYPOGRAPHY` carries 99
values on 31 themes: 58 faces, 19 cover-gradient stops and angles on 7
themes, 16 kicker trackings, and the 6 halo values that are the report's
"two extra halos" — `ember` and `synthwave`, the two palettes drawn
around a glow.

**What was NOT applied, and this is the finding.** The 31 layers declare
541 values, not 99. The rest restates leadings, sizes, palettes and
`nav-dot.*` as they stood in 2026-08, and measured against the current
catalogue they would have changed between 9 and 49 properties per theme
— reverting `color.nav` (§9.5.7), the four palettes returned to their own
grounds, the highlighter decisions, the elevation axes. **A design
document is a snapshot, and this one was read four months after it was
taken.** Applying it whole would have looked like delivering the report
and been a rollback.

The four families this entry says are left were the right list, and
extracting exactly them is what made the pass safe. `tag.tracking` in the
layers is `kicker.tracking` here, from before the editorial rename.

The visible effect on a built page, measured on `pop-lemon` against
v0.42.3: nine lines. Seven of them are one decision — the pop family
moves to sans — reaching six variables that take the text face by
reference. That is the reference working, and it is declared in the
render guard rather than absorbed.

**Report delivered and verified** (`c4156e8`):
`delete-before-1.0/REVISION-THEMES.md`, with 31 validated property layers
in `delete-before-1.0/themes-revision/`. It covered the historical
catalogue of 33 themes; the registry now carries 57.

**Three of its decisions are settled.**

1. **Four borrowed palettes returned to their own ground.** `dracula`,
   `tokyo-night`, `monokai` and `everforest` are `dark_background`. This
   was a fidelity repair, not a score repair: they were drawn for dark
   grounds and were being shown on a light one. Three entry notes that
   were factually false are rewritten.
2. **The serif-text / sans-UI default split adopted.** The `ch` measure is
   font-independent as designed — characters per line unchanged at 62 and
   67 wherever the measure binds, and in band (48, 56) on the narrow phone
   where the padding binds instead.
3. **Dropping `pop-lagoon` and `pop-fuchsia`: rejected, and the report was
   wrong.** Its case was that lagoon is crowded between lime and cobalt.
   Measured on the hue wheel, lagoon's neighbours are *further away than
   average* — 36° and 49° — while the closest pair in the family is
   tangerine→lemon at **15°**, which reads as two plainly different
   colours. The criterion does not survive its own application. `fuchsia`
   and `red` are the closest dark pair at 26°, with different `mark` and
   `affirm`: not a duplicate. Nothing measured supports a removal.

**One of its decisions is void.** It proposed that every built-in theme
meet a readability floor, with a subset meeting a higher standard. There
is no such obligation and there never was one in the program (§9.5.2). Do
not apply it, and do not re-derive it: a "theme that misses the floor" is
not a category this project recognises.

Half of that sentence was never about levels and survives on its own:
**visual families such as `pop`, halo and monochrome are editorial
categories**, and `theme show` remains the measured report.

**What is actually left, and it is all typography:** the per-theme blocks
— named display faces, tracking, cover gradients, the two extra halos.
They are in `delete-before-1.0/themes-revision/`, 31 of them, all verified
to resolve. That is the work; it needs no pass structure and no floor.

The one hard floor in the project is elsewhere and has nothing to do with
this entry: navigation furniture clears 3:1 because an invisible progress
dot is a broken control, not a bold palette (§9.5.6). B6 closed it.

*Framing of the day the entry was written, below. Read its present tense
as past.*

The engine gave themes fonts, shadows and per-component axes; only
`terminal` uses them (fixed pitch plus phosphor halo, the owner's
decision). The architecture records that all entries are to be reviewed
under this light — theme-construction work, out of the engine's scope.

## B10 — Gamut mapping for lightness-shifted inks

**État :** à étudier · **Voir :** B9

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

## B11 — Dichromat separability is not verified

**État :** à étudier

The architecture explicitly does not guarantee separability under
dichromat vision; the verdicts' shape marks already serve it (and are now
load-bearing, since weight no longer separates partial from yes), but no
simulation exists and nothing measures the palettes. Assumed gap,
recorded at the owner's level: a check would belong to theme construction
(the catalogue side), never to the renderer.

## B12 — Box drop-shadow (elevation) axes

**État :** terminé

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

## B13 — `--content-max` is the one themeless variable

**État :** terminé

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

*Framing of the day the entry was written, below. Read its present tense
as past.*


The only CSS variable the composed sheet still declares outside the
engine: the skeleton's own layout width (`min(84vw, 1100px)`), the single
`var()` the extraction gap-check tolerates. Pre-rewrite architecture
recorded it as outside the colour apparatus by nature. To settle someday:
expose it as a length property (`page.content-max`) like everything else,
or record the exemption as permanent — today the exemption lives only in
a code comment and the gap-check test.

## B14 — Literalize the skeleton; retire TEMPLATE_STYLE

**État :** terminé

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

*Audit finding of 2026-08-04 below. It is the reading of that day, kept
because it documents the cause; read its present tense as past.*

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

## B15 — The share popover's mobile overrides never apply

**État :** terminé · **Depuis :** 2026-08-18

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

*Reading of the day the entry was written, below. Read its present tense
as past.*


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

## B16 — `page_dest: index.html` loses a page in silence

**État :** terminé · **Depuis :** 2026-08-18

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

*Reading of the day the entry was written, below. Read its present tense
as past.*


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

## B17 — catppuccin's bold-on-highlight is at 3.05:1

**État :** terminé · **Depuis :** 2026-08-18

**Closed, re-measured 2026-08-18 at 4.51:1** — `fact.strong.fg` against
its own `fact.strong.bg`, composited over the fact ground and the page.
The palette's `color.mark` moved and took the shortfall with it.

The entry predicted its own closing: it said the exact-set pin in
`KNOWN_PALETTE_FAILURES` would fail the moment the palette was fixed and
force the exemption out with it. That is what happened, and the set is now
empty — which is that idiom's strongest state, not an absence of coverage.

*Reading of the day the entry was written, below. Read its present tense
as past.*


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

A palette value the project drew, on a surface it pinned as an exact
set: if it is to move, it moves by a measured replacement in the theme
file, not by a mechanism.

## B18 — `cover.kicker.fg` is below AA on three themes

**État :** sans objet · **Voir :** B5

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

## C1 — Test AST « aucune écriture nue hors helpers »

**État :** terminé · **Version :** v0.33.2

**Type:** test d'architecture.
**Signalé dans:** `delete-before-1.0/newargs/PLAN-CLI.md` §6 Phase 3 (ligne 199), comme non
implémenté. Le test `test_no_bare_filesystem_write_outside_helpers`
(`tests/test_lightwebpres.py`) est bien un balayage AST du source : il
interdit `.write_text()` et `.mkdir()`, ainsi que les copies `shutil`, hors
des helpers `_write_file`, `_mkdir`, `_copy` et `_copytree`. Il couvre donc
l'intention de l'entrée ; aucun second test AST n'est nécessaire.

Vérifié le 2026-08-15.

## C2 — `series article add/remove/set`

**État :** abandonné

Hors périmètre de la refonte CLI v0.24 (`delete-before-1.0/newargs/PLAN-CLI.md` §7).
Nécessite son propre cahier des charges ; ce n'est pas une dette mais une
décision de périmètre. Non implémenté et volontairement absent.

---

## C3 — Filtrage par `tags:`

**État :** terminé

Le format partage un espace de noms plat entre les tags de slide et le champ
`tags:` du bloc meta article. `default` est implicite pour une slide sans tag,
`excluded` est retiré au build, et les autres tags sont filtrés dans le
navigateur avec la touche `L`. Un tag d'article est une gate exacte sur les
cartes d'index et de navigation; l'article reste visible seulement si au
moins une slide non exclue accepte aussi le tag sélectionné. Un article sans
tags n'a pas cette gate. Le renommage éditorial `tag:` -> `kicker:` est séparé
de ce mécanisme et ne doit pas être confondu avec les tags d'instance ou le
version tag.

`series_meta.default_tag` choisit le tag initial, avec `default` comme repli;
un choix mémorisé encore présent dans la série reste prioritaire. Un
`default_tag` absent de la sortie sélectionnée est une erreur de build. Le
statut de l'article est appliqué avant ce filtrage et ne peut pas être
réactivé par un tag. La présence lexicale ne suffit pas : `build` et `audit`
avertissent lorsqu'un tag sélectionnable ne trouve aucune slide après la gate
article et l'exclusion des slides, et un article entièrement exclu est lui
aussi signalé comme page vide. Le menu affiche le tag actif, les compteurs et
les titres des fiches/slides effectivement retenues.

`series_meta.lang_tags` associe un tag à un pack typographique ; le premier tag
de langue porté par une slide sélectionne son moteur, avec `--lang`/`LWP_LANG`
comme fallback. `audit` signale les tags invalides et les packs absents sans
bloquer. Le comportement est couvert par les tests black-box, le test
navigateur (`tests/slide_tags_e2e.cjs`, menu, filtrage, persistance,
rechargement) et la documentation permanente.

Les 13 tests e2e navigateur ont été exécutés le 2026-08-15 avec Node +
Playwright.

---

## C4 — Audit 2026-08 : décisions actées et dettes restantes

**État :** terminé · **Version :** v0.33.0

L'audit de cohérence du 14/08/2026 a été dépouillé. Ce qui a été
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

Le statut « e2e navigateur en attente de l'outillage » que portait
l'ancienne section C3 est historique et ne s'applique plus.

## B19 — `audit --strict` is blind to every warning the build emits

**État :** terminé · **Version :** v0.37.0

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

## B20 — Only three components can carry a halo, and the worst-served one is a slide heading

**État :** terminé · **Depuis :** 2026-08-18 · **Voir :** B12, B36

**Delivered, measured 2026-08-20 on the registry: 32 components carry a
halo, each with all four axes** — `fg`, `blur`, `dx`, `dy`, 128 axes in
all, against the three components and nine axes the entry below counted.
`title2`, the slide heading this entry names as the worst-served element
in its own table, is among them, as are the kickers, the sources and the
fact-box body it lists as having no axis at all.

That paragraph is written on 2026-08-20 and it is a repair, not a
record of the day. The entry stated a decision and then a design note
addressed to a future lot, the lot landed, and nothing came back to say
so — which is the decay this register describes in its own header. It
survived the pass that sorted every entry into a state, too: `terminé`
was assigned from the work having been done, not from anything the entry
said. A state is a measurement, so here is the measurement.

**What the engine can do, the catalogue does not do.** The 32 components
are a capability; 13 themes declare a halo and all 13 use the same three
anchor points this entry counted, so `title2` — the element named above
as the worst served, and the reason this entry exists — still has no halo
of its own on any theme. That is **B36**, and it is theme work rather
than engine work, which is why this entry is finished and that one is
open.

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

## B21 — Pinning dark colours does not make the furniture dark, and nothing says so

**État :** terminé · **Version :** v0.37.0

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

## B22 — `--version` after a command is a silent no-op

**État :** terminé · **Version :** v0.37.0

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

## B23 — `--inline-images` does not reach an included article's images

**État :** terminé · **Version :** v0.37.0

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

## B24 — `audit` inspects a poorer representation than the one that builds the page

**État :** terminé · **Version :** v0.37.0

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

## B25 — Two rules the project states and does not follow

**État :** terminé · **Depuis :** 2026-08-20 · **Voir :** spec §19.3.1, §23.1

Both halves are closed. The non-breaking space landed in v0.37.0, below.
The shared guard is closed here, and the entry's fork was already
answered by the document it cited.

**The fork did not need deciding.** It offered "either prefix it like the
other two, or keep it shared and add the test that asserts the bodies
match" — and §23.1 already said the sharing is deliberate, naming the two
pairs that WERE prefixed apart and this third name that was not. What was
missing was never a decision; it was the instrument, and that same
sentence said so: *rien ne le vérifie aujourd'hui*.

Prefixing would also have been the weaker answer. It removes the
collision and keeps the duplication, leaving two copies of one security
rule that must agree with nobody watching. Shared plus checked keeps one
rule and makes disagreement fail.

**Compared by AST with docstrings stripped.** The docstrings differ on
purpose — one explains the defence, the other points at it — so text
comparison would fail on prose and on a reflowed line, while passing on a
changed constant. A second test asserts both files still define it: one
of them losing the name leaves the survivor governing both extractions by
accident rather than by the decision §23.1 records.

Proved by mutation both ways: dropping the backslash from one copy's
prefix check fails the equality, and renaming the function in one file
fails the pair.

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

## B26 — `audit` prints its warnings on stdout, the render's on stderr

**État :** terminé · **Depuis :** 2026-08-20 · **Voir :** spec §2.4.1

**Rerouted, all 26 of them.** `audit`'s warnings go through `log('warn',
…)` like every other diagnostic in the program, which puts them on stderr
with the same `[WARNING]` tag. stdout keeps what §2.4.1 puts there and
nothing else: the count line, which is the command's answer.

**Two of this entry's own numbers were wrong, and both understated.** It
said twenty print sites; there were twenty-six. It said "exactly one test
assertion couples `[WARNING]` with stdout, so the change is small";
nineteen tests failed, over roughly thirty assertions, because most of
them read the warning TEXT out of `result.stdout` without the tag being
in the needle. Counting by grepping for a literal missed everything
phrased differently — the same shape of error as the count in B19 that
had gone stale, and the reason the warning collector hooks the funnel
rather than enumerating sites.

Four of the sites needed more than a reroute. They sat inside
`collect_warnings` and were tallied by hand in a `fatal` counter beside
the sink; through `log()` the sink sees them, so the parallel tally is
gone and they are counted once. They were the only warnings in the
program two mechanisms had to agree about.

One test asserted the defect: `plain.stderr.count('[WARNING]') == 0`,
standing in for "the render itself warned about nothing". A true proxy
while audit's warnings were elsewhere, and meaningless once they moved.
It now asserts what it stood for — that no warning on stderr is anything
other than the one saying the series does not build.

The guard reads the SOURCE, not an output: no `print()` of a `[WARNING]`,
`[ERROR]`, `[INFO]` or `[DEBUG]` line anywhere in the executable. A site
added tomorrow on a path no test exercises is caught anyway. Proved by
mutation — printing one warning again fails it by line number.

Exit codes are unchanged, as the entry said: `--strict` gates on audit's
own count and never looked at the stream.

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

## B27 — The default sheet fails the navigation floor its own test enforces

**État :** à étudier

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

**Resolved by the position, 2026-08-20, and the answer is the second
reading.** The entry itself named the fork — either the default is
acceptable, or the 23 overrides are the anomaly, and one of the two
readings is wrong. It is the second. `table.col-snap.rule-fg` edges a
column that already carries its own tinted ground; nothing moves the
reader with it, so it is not navigation and the 3:1 floor is not about
it. There is no carve-out to invoke, because there is no criterion to be
carved out of: a floor on rules-in-general never existed in the program,
and §9.5.2 no longer pretends otherwise.

So the default `mark` is fine and stays. What wants a second look is the
**23 hand-pinned overrides**, added to clear a guard that does not apply
to them — the kind of thing that spreads through a catalogue once one
entry does it. Re-reading them is theme work, small, and it is what is
left of this entry.


## B28 — A list item was one line, and its continuation left the list

**État :** terminé · **Version :** v0.37.0

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

## B29 — A structural field ships Markdown to the reader, and nothing said so

**État :** terminé · **Version :** v0.37.0

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

## B30 — Nested emphasis, and a net for whatever the checks do not name

**État :** à étudier

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

## B31 — `auto` is a length, and on a shadow axis it deletes the shadow

**État :** terminé · **Depuis :** 2026-08-20 · **Voir :** spec §9.2

**Closed by removing the value, and the entry's own plan was wider than
the defect.** It expected a narrower type for the axes where `auto` is
meaningless, and a decision about which length properties legitimately
accept it. Swept over the registry: **none of the 212 do.** Every one
reaches a CSS context that refuses it — shadow offsets, blurs and
spreads, font sizes, border and ring widths, tracking, padding, and the
two max-widths, whose keyword is `none` rather than `auto`. No property
defaults to it and no built-in theme resolves to it.

So there was no type to add. `LengthType` stops accepting `auto`, which
is one line, and refuses it **by name** with the reason: someone who
wrote it did so on purpose and is owed an explanation, not a units list.
What used to happen instead was the failure typing exists to prevent — a
value surviving every check the tool makes and dying in the renderer.

The guard asserts it over the whole registry rather than on a sample,
because this entry's own history is that the hole was found on one axis
and was open on sixty-five. Proved by mutation: putting `auto` back in
the accepted set fails it on `page.shadow.blur`.

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

## B32 — A fix to `nav.js` or a language pack never reaches a series that already exists

**État :** terminé

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
Measured on a demo series: every page built from a series holding the
copies was byte-identical to the page built from one without them.

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

## B33 — A moved anchor is invisible to everyone, including the tool that moved it

**État :** sans objet · **Version :** v0.43.0 · **Voir :** spec §12.1.1

**Closed by removing what made it possible, not by adding a report.**

The entry was written against the derived identity: a card's id was a
hash of its title, so renaming a title moved the anchor, and nothing said
so. The four decisions it listed — where the previous set of identities
lives, whether `build` or `audit` compares them, what the message says,
how a first build stays quiet — were all about detecting a move after the
fact.

There is nothing left to detect. A card's id is the `slug:` its author
declared and nothing derives it (§12.1.1), so no ordinary edit moves it:
not reordering, not inserting, not excluding, and not rewriting the
title. The only thing that changes an anchor now is the author changing
the slug, which is a line they edited on purpose in a file they own —
the same act as renaming a file, and it needs no report.

What remains from the entry, and is delivered: the author has to be able
to SEE the anchors without building the page. `lightwebpres series slug`
lists every card of the series and the name it is published under, in
text or as JSON.

## B34 — A structural field converts an HTML entity; the body does not

**État :** terminé · **Version :** v0.42.3

**Verified, by sweeping all fourteen text fields with four payloads.**
Ordinary punctuation (« », apostrophes, `100 %`, `—`, `3 < 4`) is escaped
correctly everywhere. What is not consistent is the ampersand:

| written | body | structural field |
|---|---|---|
| `Marks & Spencer` | `Marks &amp; Spencer` ✅ | `Marks & Spencer` — bare `&` |
| `&sect;` | `&amp;sect;`, shown literally ✅ | `&sect;`, shown as `§` |
| `<a href="?a=1&amp;b=2">` | `?a=1&amp;amp;b=2` ❌ **broken link** | verbatim ✅ |

The consequence that is not theoretical: `source:
https://x.test/rechercher?q=marks&copy=1&reg=2` reaches the reader as
`…?q=marks©=1®=2`. `&copy` and `&reg` without a semicolon are in HTML5's
legacy character-reference list, so a query string with either is
silently destroyed. Nobody made a mistake typing that.

§6.2 already states the position — every `&` is escaped, a hand-written
entity is neutralised, write the Unicode character, the pipeline is UTF-8
— and it states it for the BODY only. The structural fields fall under
neither that rule nor the raw-HTML-block exception; they are a third
territory nothing describes.

**Proposed.** One rule for both grammars: escape a `&` **outside a tag**,
leave what is inside a tag verbatim. That gives, everywhere: a bare `&`
escaped, `&sect;` literal (the stated position), and a raw `<a
href="…&amp;…">` untouched — which also repairs the body's broken link
above. The engine already knows how to protect tags from a rewrite; that
is what the typography engine does.

**The one cost to state.** A bare `&` inside a raw tag would stop being
corrected to `&amp;`. That is the author's own HTML, and the tool's
declared position is that it does not touch raw HTML (§13.8) — coherent,
but it has to be written down rather than discovered.

**Decided: adopted.** One rule, `escape_amps()`, splitting on the
typography engine's own tag pattern — the same one literally, so the two
cannot disagree about where a tag begins. §6.2 states it for both
grammars now, including what stops being corrected: a bare `&` inside a
raw tag, which is the author's HTML and §13.8's territory.

The guard is a sweep rather than a list: an article and a series carrying
a payload in EVERY field, then the built pages read back for any `&` that
is not a well-formed reference. It earned its shape immediately — it
found two surfaces the hand-written list had missed, the `series-nav`
cards and the article page footer. Three mutations, three killed. No
artefact of this repository moved, as predicted.

## B35 — Reaching a verdict class without writing HTML

**État :** à étudier · **Voir :** B2

Split out of B2 on 2026-08-20, because it was the one question that entry
left open and it was sitting inside an entry marked settled. An index
built from states would have counted it as decided; it is not.

B2 settled the styling side and the documentation: `.yes` / `.no` /
`.partial` / `.col-signal` / `.col-snap` are a documented contract, each
verdict is painted by its own typed properties (`verdict.yes.fg`,
`verdict.yes.mark`, …), and inline HTML is the written route to them. So
a comparison table is expressible today. What it costs is thirty class
attributes written by hand, in a format whose whole argument is that an
author writes prose.

**What is not decided** is whether the format grows a way to say it — an
in-cell marker such as `| +yes |`, `| -no |`, `| ~partial |`. B2 ruled
out the other candidate for good reasons that still hold: deriving the
class from the cell's text would depend on the language, in a format that
ships `fr` and `en` packs, and would retroactively recolour tables
already published, since a cell reading "no" would turn red on the next
build.

**What is left to decide is parsing, not painting.** The components a
marker would bind to already exist, so nothing structural is missing. The
open questions are the marker's shape, how a cell that legitimately
starts with `+` or `~` escapes it, and whether the column case
(`col-signal`) is done in the same pass rather than revisited later —
which is what B2 asked for and the reason to keep them together.

It is an addition to the input contract: a MINOR version, never a fix
(§13.9). Nothing about it is urgent — the need is covered, verbosely.

## B36 — The engine can halo 32 components; the catalogue haloes three

**État :** à étudier · **Voir :** B20, B9

**Narrowed by the B9 pass of 2026-08-20, and half of it answered.** The
revision's halos are applied: 15 themes now carry one, up from 13. Still
three components — `page` (9 themes), `title1` (14), `highlight` (15) —
and that is no longer an accident of which anchor points existed. A
design pass went over all 31 palettes, added halos to two of them, and
gave `title2` one on none. B20's first branch, that a theme may hold its
atmosphere uniform, is what the catalogue's own author chose.

**What stays open is not coverage, it is a number nobody picked.**
`title2` still inherits `page.shadow`, and the measurement below is
unchanged: a blur-to-size ratio of 0.054 where `title1` sits at 0.38. On
a palette that declares no page halo that is nothing at all, which is
fine. On the 9 that declare one it is a faint smear at a seventh of the
proportion the same theme chose for its other heading — not a decision,
an arithmetic leftover of `em` resolving once at the root.

So the question is narrow: on those 9, does `title2` want its own halo,
`page.shadow` want to stop reaching headings, or the ratio to stand as
drawn? Taste, not measurement, which is why it is `à étudier` rather than
`à faire`. `dx` is still declared by no palette and still unasked.

B20 is delivered on the engine side and was never carried into the
catalogue. Counted on the registry and on `THEME_PROPERTY_OVERRIDES`,
2026-08-20:

| | engine | catalogue |
|---|---|---|
| components that can carry a halo | 32 | 3 — `page`, `title1`, `highlight` |
| axes per component | 4 (`fg`, `blur`, `dx`, `dy`) | `fg` 35×, `blur` 35×, `dy` 6×, **`dx` 0×** |
| themes declaring any halo | — | 13 of 57 |

**So the element B20 was written about still has no halo of its own.**
The entry's table names the slide heading as the worst-served element in
the page and says "the slide heading is the worst served, and it is a
heading". Zero themes give `title2` a halo, and the 31 revision layers
waiting in `delete-before-1.0/themes-revision/` (B9) do not add one
either — they add `title1` and `highlight` halos to two themes, which is
what B9 means by "the two extra halos".

What `title2` gets instead is `page.shadow`, inherited. Computed from the
declared values rather than measured in a browser: `body` declares no
`font-size`, so `page.shadow.blur: 0.17em` on `lava` resolves once
against the browser's default size and propagates as that absolute
length. At 1920×1080, `--title2-size` is `max(24px, 4.7vmin)` = 50.8 px
and the inherited blur is 2.7 px — **a blur-to-size ratio of 0.054, where
`title1` sits at 0.38 by declaring its own**, a factor of seven. That is
the same disproportion B20 measured on 2026-08-18, unchanged, because
nothing about the catalogue changed.

**Not a defect in the engine, and not an obligation on every theme.** A
theme may decide all of it, which includes deciding that its atmosphere
is uniform — that was B20's first branch and it is defensible. What is
not defensible is the current state, where the disproportion is an
accident of which three anchor points happened to exist in 2026-08, on
13 palettes whose author never got to choose.

The work is theme-authoring, on the 13 that halo: decide per palette
whether `title2` — and the kickers, the sources, the fact-box body B20
lists — carry their own halo, and at what ratio. It is the same trade as
the rest of B9 and belongs with it in a pass, not before. `dx` needs a
separate look: it exists so a halo can be offset sideways, no palette
uses it, and nobody has asked whether any should.

## B37 — `requestFullscreen()` is refused from any non-left mouse event

**État :** terminé · **Depuis :** 2026-08-22 · **Version :** 0.43.7

**The browsers rule it, and no code can change it.** Firefox refuses
`Element.requestFullscreen()` called inside a mouse handler that was
not triggered by the left button — the error names the rule, verbatim:
"La demande d'accès au plein écran a été refusée, car la fonction
Element.requestFullscreen() a été appelée à l'intérieur d'un
gestionnaire d'évènement de souris qui n'a pas été déclenché par le
bouton gauche de la souris." Chromium enforces the same activation
requirement. The middle button is a real user gesture, but it is not a
LEFT one, so its `requestFullscreen` is silently refused; `exitFullscreen`
needs no gesture at all and always works.

**It explains the double-click.** The double-click was the original
mouse entry into fullscreen for exactly this reason: it is a left-hand
gesture, the only family the browsers accept for entry. Moving the
entry to the middle button (2026-08-22, while redesigning the click
model) worked in a headless harness that does not enforce the rule and
failed on a real Firefox, which does. The redesign then removed the
double-click's entry role entirely — which closed the only mouse entry
left. This entry records the rule so the next redesign does not need a
Firefox console error to rediscover it.

**What the middle button is now:** it arms the two-step entry gesture when the
page is not fullscreen and exits fullscreen when it is. Entry is completed with
a left click; the ⛶ button and F remain direct entries. The wheel itself keeps
scrolling.

## B38 — The two pages share one skeleton and one script

**État :** terminé · **Depuis :** 2026-08-22 · **Version :** 0.43.7

**The index was a special case, and special cases drift.** It had its
own script (its own arrow buttons, its own scroll handling), a reduced
button set (no share, no fullscreen next to nothing), and no share
matrix at all. Every behaviour the articles carried — keyboard, mouse,
share, help — had to be reasoned about twice, once per page, and the
two answers were allowed to differ. That is how the index ended up
with a different click model from the articles, and it was reported
from the field: a reader who moved from an article to the index lost
every behaviour they had just learned, and the reduced buttons forced
them to change the way they drove the deck at the moment they were
looking for an article.

**The audit said the behaviours had to be the same everywhere.** The
middle-button fullscreen entry and exit, the 200 ms glide, the
right-click mirror, the double tap — all of it is muscle memory the
reader builds on an article and expects on the index. B37's rule
(requestFullscreen refused from any non-left event) made the click
model more precious, not less: the more the deck's gestures do, the
more it costs when they stop at the index's edge.

**The decision: one `TEMPLATE_PAGE`, one `TEMPLATE_NAV_JS`.** The index
is an ordinary page whose content differs (header, intro, article
cards where an article puts its slides; the body carries
`class="index-page"`). The step on the index is a card — the focus
walks the list, exactly as it walks the series-nav slide of an
article. Share is present with the fiche scope disabled (no current
slide). The ↑/↓ pair is gone; prev/next drive both pages. `index_extra`
is preserved, still spliced before `</body>` on the index only. The
render of existing pages does not change structurally — it is the
behaviour of the index that aligns with the articles.

**What is verified.** The page built by `build_index` uses the same
skeleton as the articles (the same `TEMPLATE_PAGE`, the same
`TEMPLATE_NAV_JS`), the fiche scope of the share matrix is disabled
where there are no slides, and the arrows, buttons and clicks all step
one card. The removed constants and keys are gone from the source; the
`index_nav_up`/`index_nav_down` language keys are left in the packs,
unused, for the owner to decide whether they stay (removing them from
the packs is a separate decision, recorded here by this sentence).

## B39 — The sources directory is called `sources/`, not `articles/`

**État :** terminé · **Depuis :** 2026-08-22 · **Version :** 0.45.0

**The on-disk directory that holds the `.md` files is now `sources/`.**
It was `articles/` since the first release, created by `init`, read by
`build`, named in `LWP_ARTICLES_DIR`. Renamed in lockstep:
`LWP_ARTICLES_DIR` → `LWP_SOURCES_DIR`, the internal `articles_dir` →
`sources_dir`. A MAJOR break: an existing series renames its directory
by hand; nothing else moves, because the build never reads that name
from the series — it is fixed in the executable and the environment
variable.

**What does NOT change, on purpose.** The `articles` JSON field in
`series.json` keeps its name: it is the list of PAGES (each entry is
`page_source`/`page_dest`/`page_title`… — the `page_*` family, frozen
by §20.1), an output-side list, not the sources. `page_source` keeps
its name, and the `source:` citation field keeps its name (the GLOSSARY
already distinguishes it from `page_source`). The `*_article.md` files
keep their name — they are the long-form pieces a `full-article` slide
includes, and they live inside `sources/` like the page files.

**Why not a smaller word.** `sources/` is the material the build reads
(one `.md` per page, plus the `*_article.md` long-forms, plus
`img/`). The docs now write « le répertoire `sources/` » with the name
in code, never « le répertoire source » alone, so the directory is
never confused with « le fichier source » (`page_source`).

## B40 — The print family: three themes drawn for ink and paper

**État :** terminé · **Depuis :** 2026-08-22 · **Version :** 0.45.1

**A theme's ground is painted, never transparent.** `print-color-adjust:
exact` forces the paint onto paper, and every contrast measurement is
computed against declared colours — so "print friendly" cannot be a
transparency mechanism, it has to be a palette drawn for the printer:
pure white ground, inks that survive printing. That makes it a usage, not an
ambiance, and usages are what families are for: the closed facet
vocabulary gains `print`, and `theme list --family print` narrows on
exactly the members.

**Three themes, one per doctrine.** `print-ink` — pure black on white,
one deep red held in reserve, the highest contrast the family holds.
`print-grey` — no hue at all; weight, opacity and shape carry the
signal, the same doctrine as Monochrome. `print-color` — a blue for
the structure, a green for what is good, a pale yellow highlighter,
each chosen to survive printing. All three pin their shadows off
(the light family's shadows are shadows of screens, not of paper) and
pass the catalogue's own AA floor on bold fact text, measured.

## B41 — Print Boss adds a hand-marked newspaper to the print family

**État :** terminé · **Depuis :** 2026-08-23 · **Version :** 0.45.2

The print family keeps its content and panel surfaces opaque `#FFFFFF`,
including the cover, so no print theme spends ink filling a page. The cover's
title, summary, kicker and number are restated in the theme's ink colours;
the ordinary inverted cover defaults would otherwise put pale text on white.

`print-ink` is the printer's economy: its fact-box emphasis is bold and has
no coloured ground. `print-boss` is the deliberate exception: ordinary-weight
text sits on a yellow `fact.strong.bg`, giving the fact box the look of a
newspaper someone marked with a highlighter by hand. The existing `print-grey`
and `print-color` treatments stay unchanged.

## B42 — Print Ink and Print Grey keep a low-ink table header

**État :** terminé · **Depuis :** 2026-08-23 · **Version :** 0.45.4

The print catalogue's white surfaces are not a ban on every change of tone.
`print-ink` and `print-grey` restore a single opaque `#F4F4F4` fill on table
header cells: it separates the column labels from the body while using only
a very light wash of black ink. `print-color` and `print-boss` keep their
headers white; their colour already carries the structure elsewhere.

## B43 — Old Press adds a fixed-pitch print pair

**État :** terminé · **Depuis :** 2026-08-23 · **Version :** 0.45.4

The print family now has two typewriter variants, both on opaque white paper
with shadows disabled. `print-oldpress` uses black ink only and lets bold,
underlines and spacing carry the hierarchy. `print-oldpress-red-ribbon` keeps
the same body ink and adds a restrained red second ribbon for kickers, rules
and calls; red is ink, never a coloured wash behind text.

This is a typography decision as much as a palette one: `font.text`,
`font.display`, `font.ui` and `font.mono` all resolve to the same Courier-like
fixed-pitch stack. A title, a slide number, a navigation control and a code
sample therefore belong to the same old-press voice rather than mixing a
typewriter body with modern interface furniture.

## B44 — Runtime themes stay opt-in and preserve author pins

**État :** terminé · **Depuis :** 2026-08-23 · **Version :** 0.45.4

**Historical record — the opt-in/no-payload behavior below was superseded by
B47, and its global settings-pin behavior by B53.** This entry preserves the
decision and measurements from before those changes.

At the time of this decision, the ordinary build remained a static themed
page. A build that opted into `--themes` carries an inline, indexed delta
payload instead of making the browser reconstruct the property cascade or
fetching a catalogue. The
effective `theme:` in `templates/settings.conf` is always the first entry,
because it is the author's actual starting point even when the requested
list omits it. The browser may replace only unpinned variables; settings,
`style.*` and registry variables redeclared by `custom.css` remain the
author's last word. `sessionStorage` carries the reader's choice between the
pages of a deck without changing its sources.

At that time, the picker was deliberately explicit rather than a cycling
shortcut: **C** opens a searchable dialog, while **M** gathers fullscreen,
theme, help,
presenter, tag, share, navigation and pause actions in one keyboardable
dialog. A build without alternatives keeps C inert and omits the theme
action, so the default page carries no theme-switch data and its static
palette remains the source of truth.

**What is verified.** The primary-first ordering, `all`, unknown slugs,
modified settings, pinned variables, absent-option behaviour and compact
payload have unit coverage. The real-browser probe switches to an alternate
theme, keeps a pinned color, carries the choice to an article page, restores
the primary theme, and opens both dialogs. `python3 tests/run_tests.py` passes
with 995 tests in 184 classes and 6 workers; the guide, specification index
and decision index regenerate cleanly.

## B45 — Series JSON can choose a runtime theme catalogue

**État :** terminé · **Depuis :** 2026-08-23 · **Version :** 0.45.4

**Historical runtime-theme note — B53 superseded the old primary ordering when
`settings.conf` contains property pins: the dynamic custom variant now comes
before the raw base snapshot.**

The runtime selection is also a property of a series, not only of one build
invocation. The object form of `series.json` may carry a root `themes` list;
it is validated whenever present, and a direct-array series remains the
backward-compatible form without JSON theme configuration. The command-line
`--themes` value wins over a valid JSON selection, while the effective theme
from `settings.conf` remains first in the payload.

The list accepts slugs, `all`, `essential`, and the closed `X:Y` facet
vocabulary. The `essential` label is intentionally stable and currently
means `monochrome`, `monochrome-night` and `print-ink`. Facet aliases are
`background`/`bg`, `family`/`fam` and `background hue`/`bgh`; multiple
selectors form a catalogue-order union with duplicates removed. Watch polls
`series.json` with the other build inputs, so changing the list rebuilds the
pages with the new payload.

**What is verified.** Unit and black-box coverage measures primary ordering,
the special labels, all facet aliases, invalid list shapes, invalid selectors,
CLI precedence, watch reloads and verify reuse. The new Monochrome Night
palette passes the existing rendered contrast and catalogue property checks.

## B46 — Help carries permanent provenance and names the theme shortcut

**État :** terminé · **Depuis :** 2026-08-23 · **Version :** 0.45.4

**Historical runtime-theme note — the opt-in/no-payload behavior described
below was superseded by B47.**

The `H` overlay always carries a small final provenance line, independent of
the opt-in `--build-stamp` marker: `Compiled with LightWebPres vX.Y.Z`, with
the product name bolded. This makes every generated page identify the tool
that supplied its presenter runtime without making the page non-reproducible
or exposing a build time.

The help list always says that `C` changes the theme during the presentation,
whether or not the current page carries alternatives. The picker opens only
when alternatives have been embedded; at the time of this decision, on an
ordinary page the line documented the capability without making the static
page carry a runtime catalogue.

**What is verified.** Black-box and browser tests check the permanent stamp,
the bold product name, the version shape and the visible `C` instruction.

## B47 — Essential themes ship by default

**État :** terminé · **Depuis :** 2026-08-23 · **Version :** 0.45.4

**Historical runtime-theme note — B53 superseded the statement below that the
effective settings theme is always the first payload entry when it carries
property pins.**

Every build now embeds the essential bundle — Monochrome, Monochrome Night
and Print Ink — as runtime alternatives, so **C** is functional on any page
without the author opting in. The effective theme from `settings.conf`
remains primary and first in the payload; the essential three are added
after it, deduplicated in catalogue order, so a series whose primary is
already one of the three does not see it twice.

`--no-essential-theme` opts out for authors who want a static page or a
custom selection via `--themes`/`series.json["themes"]`. The flag is
accepted on `build`, `verify` and `watch`; without it, the essential set
ships on every build, including the ones that do not pass `--themes`.

**Why those three, and why by default.** Accessibility: a high-contrast
theme (Monochrome) and a dark-ground one (Monochrome Night) are always
within reach, on any page, regardless of what the author chose — the reader
who cannot read the page as drawn has an alternative that does not depend
on the author having planned for them. Print: Print Ink is drawn for paper,
so the reader who wants a printable view of any series has one without the
author having marked the series as printable. Sobriety: none of the three
carries a hue, so the essential set does not clash with the editorial intent
of a page whose palette is built around one.

The help overlay was also made a real modal in the same lot: it carries
`role="dialog"` and `aria-modal`, manages focus, and closes on any key or
click rather than only on H and Escape. The footer is gone, the version
stamp is always present, and the `H` line in the help list says "Opens the
help window" / "Ouvre la fenêtre d'aide" — the overlay is a window the
reader opens, not a state the deck enters.

## B48 — Séparer physiquement l’interface et la typographie

**État :** terminé · **Depuis :** 2026-08-30

The executable still keeps one compatibility object internally: `rules` are
the build-time typography engine and `strings` are the interface vocabulary.
Series files now separate those lifecycles physically, so a series can
distribute or replace only its interface without carrying typography rules.

The chosen direction is physical separation, not a second conceptual layer in
the same JSON file: `interface/{lang}.json` for UI strings and
`typography/{lang}.json` for rules. The built-in French and English packs stay
available, and the loader remains the single compatibility boundary.
Resolution is independent per domain: `--language-file` is the explicit
unified override, then domain environment/directories, legacy unified files,
FHS resources for a real installed `bin/lightwebpres`, and finally the
embedded pack. `series_meta.lang_tags` selects typography only; browser
runtime data carries interface strings only.

`init`, `template show/write/update`, `watch`, incremental fingerprints and
the audit path all follow the split layout. Legacy `language/{lang}.json` and
the embedded compatibility shape remain supported, while split files reject
the opposite domain so a partial override cannot silently alter typography or
interface behavior.

The guards cover split precedence and validation, FHS discovery and its
standalone boundary, runtime payloads, watch paths and `build --only`
invalidations. The full suite passes with 1105 tests in 197 classes.

## B49 — La locale du navigateur choisit seulement l’interface

**État :** terminé · **Depuis :** 2026-08-24

When a build has not explicitly fixed its language, the first browser locale
selects the interface at page load: a locale beginning with `fr` selects the
French pack; every other locale selects English. This is deliberately a
two-way rule, so `fr-FR` and `fr_CA` are French while an unsupported locale
does not create a half-translated page. An explicit `--lang` or `LWP_LANG`
keeps the build language and disables that automatic choice.

Only interface strings cross the runtime boundary. Typography rules have
already been applied to authored content and are not re-run when the reader's
locale changes. The page embeds the French and English string dictionaries,
marks translated HTML surfaces and updates visible text, labels, titles and
the help/navigation runtime after the DOM is ready.

**What is verified.** The browser probe opens the same build with `fr-FR` and
`en-US` contexts and checks the HTML language, help title, share label and
article CTA. Unit coverage keeps the two built-in vocabularies in parity,
checks the runtime payload and preserves the explicit build-language path;
`python3 tests/run_tests.py` passes with 1013 tests in 185 classes.

## B50 — Soft animation of cover colours

**État :** à étudier

A reference cover was observed with a fixed dark-blue background gradient:
`135deg`, `#1A1A2E` at `0%`, `#16213E` at `50%`, and `#0F3460` at `100%`.
Its centred bold title carries a slow, symmetric warm gradient:
`#FF5030`, `#FF8040`, `#FFB050`, `#FF8040`, `#FF5030`, with a `300%` background
size and a `16s ease-in-out infinite` position animation. The two observed
frames are phases of that animation, not two palettes.

**Ce qui est vérifié.** `custom.css` can already express the browser effect,
but the built-in theme registry currently exposes only two cover stops and a
solid `title1.fg`. A first-class version would need typed title-gradient and
animation properties, a static print/reduced-motion fallback, and deterministic
gallery and rendered-test handling.

**Ce qui reste à décider.** Decide whether this belongs in the theme contract
as an optional effect, and if so which animation controls are safe to expose;
existing themes should remain static by default.

## B51 — L’inventaire rendu décide quelles images sont publiées

**État :** terminé · **Depuis :** 2026-08-30

Le build ne publie plus automatiquement chaque fichier de `sources/img/`.
Après avoir composé les pages qu’il écrit ou qu’il conserve dans une
reconstruction incrémentale, il relève leurs `src` locaux et ne copie que les
fichiers référencés qui existent réellement. Cette même représentation rendue
couvre les images Markdown, les figures, le contenu `full-article`, le HTML
brut et les pages qui restent en place pour `--only` ou `--drafts-only`.

La copie reste additive : elle fusionne dans `public/img/` et ne supprime pas
un fichier déjà présent. Le manifeste, lui, ne déclare que les fichiers que
ce build a effectivement publiés, afin que `clean` puisse suivre une image
devenue orpheline sans re-bénir tout ce qui traîne dans la sortie.

`audit` utilise le même inventaire après son rendu en mémoire. Il distingue
les occurrences inline et figure, avertit les fichiers source inutilisés et
les références locales manquantes. Si un rendu échoue, il n’invente pas une
absence de référence pour une page qu’il n’a pas pu observer : l’usage est
indiqué comme indéterminé et l’échec du rendu est compté séparément. Les
références externes, `data:`, absolues ou hors de `img/` restent hors de cet
inventaire.

**Ce qui est vérifié.** Les tests couvrent les images inline, figures et
inclusions, les fichiers inutilisés, les sorties additives, les builds
`--only` et `--drafts-only`, le manifeste et les symlinks d’images. L’audit
conserve son comportement non bloquant, tandis que `--strict` compte ses
nouveaux avertissements.

## B52 — Le défilement instantané a sa propre touche

**État :** terminé · **Depuis :** 2026-08-30

L’action **Scroll** du menu présentateur est accessible par **I**, en plus de
son bouton. La touche alterne entre la durée configurée et `0` sans toucher
aux sources; elle reste active lorsque le menu est ouvert, comme les autres
actions. Le raccourci est exposé dans l’aide et dans
`aria-keyshortcuts`/`kbd`, afin que le geste, le clavier et l’interface
assistive donnent la même réponse.

**Ce qui est vérifié.** Les tests unitaires et le probe navigateur vérifient
la présence de la ligne d’aide, la sémantique du bouton et les deux états de
l’action, avec le menu ouvert ou fermé.

## B53 — Les pins de série forment une variante runtime distincte

**État :** terminé · **Depuis :** 2026-09-02 · **Version :** 0.51.0
**Voir :** specifications.md §9.3.7 ; `lightwebpres` ;
`tests/test_lightwebpres.py`, `tests/test_runtime_themes.py` et
`tests/runtime_themes_e2e.cjs`

`templates/settings.conf` names two different things for the runtime picker:
the base catalogue theme and the properties the series deliberately pins over
it. When at least one property is pinned, the first runtime entry is therefore
the dynamic `custom(<theme>)` variant, while the unmodified base snapshot keeps
its own `<theme>` entry immediately after it. The settings pins belong only to
the custom variant; choosing the raw base or another runtime theme is allowed
to replace them. Page `style.*` properties and registry variables declared by
`custom.css` remain protected on every runtime choice, because they are
page-owned rather than the series' optional base variant.

The static sheet is composed from the same custom variant. Returning to it
removes only inline runtime differences, and the browser session key continues
to distinguish the resulting ordered catalogue. A series with no property pin
keeps the existing base theme id; a series without `theme:` uses
`custom(default)` when it has pins.

**Ce qui est vérifié.** Unit, build/verify and real-browser coverage prove the
custom/raw ordering, replacement of a settings pin by a raw theme, restoration
of the custom sheet, and persistence across article pages.

## B54 — Un contrat unique pour les brouillons de slides

**État :** terminé · **Depuis :** 2026-09-01 · **Version :** 0.51.0
**Voir :** specifications.md §4.7, §11.17 ; `lightwebpres` et
`tests/test_lightwebpres.py`

La grammaire des quatre types de slides reste écrite une seule fois dans
`SLIDE_TYPES`. Elle est exposée aux éditeurs par le contrat versionné
`lightwebpres.slide-draft/1`, plutôt que par une seconde table maintenue dans
le GUI ou dans un agent : champs acceptés et obligatoires, ordre canonique,
cardinalités, texte libre, règles de valeurs vides, IDs réservés et
squelettes de source sont produits depuis le registre.

Les squelettes reçoivent des slugs aléatoires non vides, distincts entre eux
et protégés contre les slugs de l'article lu par `--article` ainsi que les IDs
du moteur. Le contrat et `allocate_slide_slug()` ne modifient aucune source.
Les valeurs scalaires vides sont absentes, `tags:` vide devient `default`, un
`#`/`##` vide reste un titre valide, et `article:` vide distingue un
`full-article` en cours de rédaction d'une directive absente : avertissement
et omission dans le premier cas, erreur fatale dans le second.

**Ce qui est vérifié.** Les tests de round-trip des quatre squelettes, de
l'allocation et des collisions, de la commande JSON/texte, des champs vides,
des titres vides, de la préservation des espaces insécables et du rendu sans
placeholder sont verts. La batterie complète passe avec **1143 tests dans 202
classes**, `python3 tests/run_tests.py --workers 4`.

## B55 — Les symlinks composent ; le traversal reste refusé

**État :** terminé · **Depuis :** 2026-09-03

Un dépôt de série peut partager ses sources, ses images, ses templates, sa
sortie et son cache par symlink. Le système de fichiers suit déjà ces liens
nativement ; les refuser dans les commandes ordinaires rendait la composition
partagée impossible et confondait une cible externe avec un traversal écrit
dans la valeur elle-même.

La règle retenue est donc lexicale : les chemins absolus et les segments `..`
restent refusés, tandis qu'un symlink est suivi, y compris hors de la racine
logique. `audit` avertit des liens sortants dans les racines, les sources
référencées, les fichiers de présentation et les packs de langue ; l'audit
simple reste non bloquant et `--strict` transforme ses avertissements en
échec. Les tests de composition et de suivi des liens sont verts, la
documentation est alignée et la batterie complète confirme le contrat.

## B56 — Images dimensionnables et zoom de présentation

**État :** terminé · **Depuis :** 2026-09-03

Le Markdown reste lisible sans extension : une image peut porter le raccourci
`{50%}`, qui applique un zoom général à l'image. Quand il faut plus, le suffixe étendu
utilise des paires contrôlées comme `{width=50% height=auto align=right}` ; la
validation n'autorise que `width`, `height`, `zoom` et `align`, et refuse le CSS
arbitraire. `align` ne s'applique qu'aux figures autonomes, afin qu'une image
au fil du texte ne change pas le flux du paragraphe.

Le zoom de la page est une aide de présentation distincte du zoom navigateur :
`+` agrandit, `-` réduit et `=` réinitialise, dans une plage bornée. Il n'est
pas persisté et les raccourcis `Ctrl/Cmd +/-` restent au navigateur. Les
raccourcis de bord (`End`, `Ctrl/Cmd+Home`, `Ctrl/Cmd+End`) complètent le
parcours sans modifier les sources.

**Ce qui est vérifié.** Les tests unitaires couvrent les deux formes d'image,
les valeurs étendues valides et le refus d'une clé inconnue. Le probe
Playwright couvre les trois touches de zoom et les bords de l'index et d'un
article ; les artefacts ont été régénérés et la batterie complète est verte.

## B57 — Une fiche adjacente partielle doit être alignée avant la suivante

**État :** terminé · **Depuis :** 2026-09-03 · **Version :** 0.52.0

Une fiche plus haute que l'écran se parcourt par incréments, mais un incrément
ne doit pas empiéter sur la fiche voisine. Vers le bas, il s'arrête au bas de
la fiche courante ; vers le haut, il s'arrête à son haut. La fiche adjacente
n'est atteinte qu'au mouvement suivant, alignée au haut de la fenêtre.

Un défilement manuel peut néanmoins laisser une fiche adjacente partiellement
visible. Elle n'est alors pas consommée : le prochain mouvement dans sa
direction l'aligne d'abord et ne saute pas la fiche. Cette règle s'applique
aux flèches, aux boutons, aux clics et aux balayages tactiles ; les nav-dots
et la détection de fiche suivent le même état logique.

**Ce qui est vérifié.** Le probe Playwright couvre le saut observé vers le bas,
les limites d'un incrément vers le haut et les trois entrées de progression
vers une fiche partiellement visible. La batterie complète est verte : 1159
tests dans 204 classes.
