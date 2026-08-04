# Artistic revision of the 33 themes — B9

Report produced by a dedicated agent, then independently verified. The
machine-readable output is in `themes-revision/`: one `.conf` per theme
(31 files, complete property layers) plus `blocks.txt` (the same content
grouped, with the shared defaults block first).

**Two of the three decisions in §5 are applied** (the dark flips and the
default font split); the third — dropping two `pop` themes — was rejected
after measurement, and the catalogue keeps 33. The per-theme typographic
blocks are **not** applied; they remain in `themes-revision/`.

---

## 0. Verification pass

Re-run independently against the committed engine, not taken on trust.

**Holds.** All **31 blocks resolve through `resolve_theme_properties`
with zero errors** — no unknown key, no type error, no broken reference.
The contrast measurements spot-checked all reproduce: Dracula's `affirm`
at 1.29:1 on the current light ground and 10.38:1 on its own dark one,
Tokyo Night's `call` at 2.05:1 today and 6.46:1 after the flip, Gruvbox's
`faded_red` at 7.60:1.

**Three claims that do not survive checking**, all in the report's
favour except the first:

1. **The nav-dot fix is weaker than claimed.** The report proposes a
   single opaque `#7A7A7A` and states it clears the non-text 3:1 floor on
   31 themes of 33. Measured against every theme's real page and cover
   ground, compositing the translucent cover overlays properly, it
   **fails 3:1 on 12 themes of 33**, worst 1.79:1 on `pop-lagoon`. The
   cause is the same structural fact the report itself establishes for
   accents: a mid-grey cannot clear 3:1 against a *mid-luminance* ground,
   and the whole `pop` family has saturated mid-luminance grounds. The
   conclusion is therefore stronger than the report's, not weaker:
   **B6 has no single-value fix at all** — not for the active dot, which
   the report concedes, and not for the resting dot either. Its own
   limit 6 (give the row a declared background) is the only real
   correction.
2. **The AA-failure table undercounts.** It names four project themes
   that miss the AA floor the spec promises. Measured across all 24
   project themes, there are **five, with nine failing roles**:
   `vaporwave` is missing from the table (`call` 2.94:1, `affirm`
   2.02:1). The report does correct vaporwave's colours in its per-theme
   section, so the omission is in the summary only — but the summary is
   what indicts the spec, and it should indict it accurately.
3. **The hierarchy inversion does not exist.** The report states the key
   figure is smaller than the title above it: `highlight.size` capped at
   `3.4rem` against `title1.size` capped at `52px`. With no root
   font-size override in the sheet, `3.4rem` is **54.4px** — larger than
   52px, and in the fluid range `8vw` dwarfs `4.5vw`. The key figure is
   bigger than the title at every viewport width. Raising it to `5.5rem`
   may still be right on its merits, but the stated justification is
   wrong and should not be repeated in the spec.

---

## 1. Doctrine

### External findings

**Measure.** 45–75 characters per line, 66 as the target, and leading
grows with line length, never the reverse. Screen body text does not go
below 16px. Everything else — serif versus sans, intermediate weights —
is professional convention, which is not a disqualification but is not a
measurement either.

**System stacks.** [Modern Font Stacks](https://modernfontstacks.com/)
classifies fifteen stacks by typographic family, none requiring a
download. It is the only serious resource for a product that refuses
webfonts, and it names stacks *by intent* — Transitional, Old Style,
Humanist, Antique, Didone, Industrial, Slab — rather than by brand.

**Pairing.** The most reliable couple is a serif with character for the
editorial text and a neutral sans for the apparatus: labels, tags,
sources, buttons. The structural difference does the hierarchy work
unaided, which matters here where only `normal` and `bold` survive.

**Shadows.** A shadow whose colour is nearer the text than the ground —
the definition of a halo — **blurs the edges and degrades legibility**.
A halo never helps reading; it adds atmosphere.

**Dark mode.** Avoid pure black, desaturate accents, replace drop shadows
with layers of lightness.

### The six principles applied

1. **The generic family is the only promise, so a theme's identity never
   rests on a named font.** Verified by rendering: on this Linux, neither
   Didot nor Superclarendon nor Bahnschrift exists, and `gold-leaf`,
   `newsprint` and `dread` all fall back to the same default. What lands
   everywhere is the generic itself, plus size, leading, tracking, case,
   colour and rules. The named stack is a bonus on platforms that have
   it, never the carrier of the identity.
2. **This is a reading product, not a code editor.** The card wants
   impact, the article wants endurance. They do not want the same
   typography but must come from the same family, or the site splits in
   two.
3. **The key figure must be the strongest thing on the card.** (See §0.3
   — the inversion claimed here is not real, but the figure is only
   marginally larger than the title at the cap, which is weak for
   something called a key figure.)
4. **A gradient gives the cover depth, never decoration.** Between two
   close values — at most 12% lightness apart, angle between 150° and
   200° — it turns a flat fill into a volume without the effect being
   nameable. Two widely separated stops produce a 2011 banner: barred.
5. **A halo is legitimate on at most three lines of text, never on body
   copy.** The `page.shadow.*` axes tint the whole site by inheritance:
   **no catalogue theme may touch them.** Tried on `newsprint` (black
   35%, 3px, dy 2px): the fact body turns muddy, every glyph drags a grey
   smear, with nothing gained. Halos are admissible on `title1` and
   `highlight` only, with no offset (`dy: 0`), alpha ≤ 40%, and only
   where the theme *invokes a light* — the phosphor of `terminal`, the
   neon of `synthwave`, the embers of `ember`. Three themes of 33.
6. **Colour paints text only where it has been measured on that ground.**

### Rhythm

One ratio governs everything: leading × size = line height, and leading
follows the measure.

| Surface | Measure | Body | Leading |
|---|---|---|---|
| Card summary | ~84 char. | `clamp(16px, 2vw, 22px)` | 1.5 |
| Card fact box | ~80 char. | `clamp(16px, 1.7vw, 19px)` | 1.6–1.65 |
| Long article | **~105 char. at 15px** | **15px → 18px** | 1.65 |

The long article is the product's measured black spot: `.full-article p`
is capped at 800px and set at 15px, giving a measure above every cited
range, at a size *smaller* than the fact boxes. The longest thing to read
on the site is the worst set. Raising the body to 18px brings the measure
to ~90; reaching 66 needs a property that does not exist (limit 3).

> This converges with `ETUDE-VIEWPORT.md`, which reached the same
> conclusion from the other end — measured in a browser rather than
> computed — and found 127 characters per line rather than 105. Both
> point at the same declaration. The viewport study's fix (`50ch`) is the
> one that closes limit 3.

---

## 2. Product defaults

Today: one characterless system stack for everything — body, titles,
tags, tables — which makes the product look like any generic web page.

**Proposed: a text serif and a UI sans, two genuinely distinct stacks.**
The product sells a long sourced article. A serif says *this is to be
read*; a system sans says *this is an application*. The small textual
apparatus — tags, card numbers, fact labels, sources, footers — moves to
the sans: it is signage, not prose, and at 12px tracked in caps a
neo-grotesque is markedly crisper than a serif.

No third family for `display`: the title/body contrast is already carried
by size and weight, and a third default would be a bet that holds on no
platform without the named fonts. Divergence on `display` is left to the
themes — eleven of them take it.

The shared defaults block is the first section of
`themes-revision/blocks.txt`. Notable choices:

- `font.text` — the Transitional stack, with Georgia inserted before the
  generic to cover the gap Charter/Sitka/Cambria leave on mixed machines.
  Anchored on `serif`, so bare Android and Linux still get a real serif.
- `font.ui` — Neo-Grotesque, deliberately **not** led by `system-ui`,
  which would hand back the OS font, i.e. the absence of choice being
  escaped.
- `font.mono` — Monospace Code, `ui-monospace` first for Safari, never as
  the anchor.

---

## 3. The nine borrowed palettes: a category error

Every borrowed accent was measured against its own light paper,
*including* the official light variants the catalogue does not use:

| Palette | Accents ≥ 4.5:1 on its light paper |
|---|---|
| Nord (Snow Storm) | none of the five Aurora |
| Dracula | none |
| Solarized Light | none of eight (best: orange 4.27) |
| Gruvbox Light (`faded_*`) | one: `faded_red` 7.60 |
| Catppuccin Latte | two: `red` 4.80, `mauve` 4.79 |
| Tokyo Night Day | two: `fg` 4.52, `purple` 4.73 |
| Monokai | none |
| **Everforest Light** | **none** — not one exceeds 3.2 |
| Rosé Pine Dawn | one: `pine` 5.59 |

**This is not a values bug, it is a category error.** A syntax-colouring
palette distributes *hue* at near-constant lightness — exactly its brief,
so no token shouts louder than another. A narrow lightness band beside an
off-white necessarily yields low-contrast text. An editorial palette does
the opposite: it distributes *lightness* and reserves hue. One cannot be
converted into the other by changing three hex values. Solarized says so
explicitly ("selective contrast"); Everforest says so explicitly ("soft
contrast for eye protection"). These are intentions, not accidents.

Two honest exits, one per theme, never a patch:

- **Flip back to `dark_background`** where the palette was designed dark
  and a canonical dark form exists. Measured: on their own dark grounds
  **Dracula, Catppuccin Mocha, Tokyo Night, Rosé Pine Main and Everforest
  Dark all pass**; Monokai passes everything but `call` (3.93); Nord and
  Solarized Dark stay below, which is their assumed character. This is a
  *restoration of fidelity*: the catalogue currently renders Tokyo Night
  with *Night* accents on the *Day* ground, which is neither.
- **Take colour out of the text** — `verdict.yes.fg: ink`,
  `verdict.partial.fg: ink`, `footnote-call.fg: ink` — leaving colour on
  grounds, rules and marks, where the threshold is 3:1 and all these
  palettes clear it.

**Reservation on B5.** The backlog says "colour stays on the shape mark".
**That is not expressible today.** The emitted CSS is
`.comparison-table .yes::before { content: var(--verdict-yes-mark); }` —
the pseudo-element has no colour of its own and inherits the cell's
`color`, i.e. `verdict.yes.fg`. Setting it to `ink` therefore extinguishes
the pill too. Rendered on Dracula, the table goes fully monochrome, "yes"
and "partial" separable only by ● versus ◐. Legible, but not what B5
believes it is buying. It needs `verdict.*.mark-fg` (limit 1).

**Reservation on the flips.** Polarity cannot be reached from a property
layer: `theme_property_layer()` applies `DARK_FURNITURE_PROPS` *before*
`THEME_PROPERTY_OVERRIDES`, gated on the entry's `dark_background` flag.
Setting `color.page` dark in an override yields a dark page with light
furniture — black-on-black veils, silently. The four flips need **the
flag in the `THEMES` entry plus the six roles**, and only then the
property block. This is itself an engine defect (limit 7).

---

## 4. Per-theme decisions

Full property blocks in `themes-revision/<slug>.conf`. Decisions:

**Borrowed.** `nord` stays light — Snow Storm is an official light
category and Aurora is explicitly reserved for error and warning states —
but goes all-humanist-sans, since a serif would contradict the
Scandinavian brief, and the Aurora greens leave the text. `dracula` flips
dark: Alucard now exists and would be the fidelity-perfect answer, but
the agent **refused to publish hex values it could not verify at first
hand** (draculatheme.com returned 403), so the verified dark palette is
used instead. `solarized` keeps its over-contrasted ink deliberately — the
selective-contrast argument assumes a configurable workstation, which an
article reader does not have — but `base1`, the comment tone, is replaced
as secondary text by the canonical `base01` (4.99). `gruvbox` moves from
the `neutral_*` accents (the dark set — the entry's note claiming
otherwise is false) to the `faded_*` set the light mode actually uses.
`catppuccin` is the healthiest of the nine: only `subtext0` → `subtext1`
(5.53) and green out of text. `tokyo-night`, `monokai` and `everforest`
flip dark, all three passing everything on their own grounds.
`rose-pine` is the one theme kept **deliberately below AA** and declared
as such: softness is its proposition, and calling "yes" a blue-green to
gain a contrast point is a contresens.

**Project themes.** Five corrected to meet the AA admission criterion the
spec already promises (§0.2). Beyond that the work is typographic:
`high-contrast` becomes the only theme where every size rises, and moves
to sans because serifs close counters at low acuity; `newsprint` — the
theme whose name *is* a typographic stance and which had none — gets an
antique display face, tight titles, a 3px rubric rule and a red editing
rule; `gold-leaf` gets the one justified didone in the catalogue plus a
warm-to-cool cover gradient (reported as the best result of the whole
revision); `ember` and `synthwave` get the two halos beyond `terminal`;
`terminal` is **left alone** — it already exploited the engine and is
good; the eight `pop` themes get one shared poster/signage block, five
lines each, described as the best return on investment in the catalogue.

---

## 5. Three decisions — outcome

**1 and 3 applied, 2 rejected.** The catalogue keeps 33 themes. See
BACKLOG B9 for what was measured on each. The decisions as they were put:

1. **Flip four borrowed themes to dark** (`dracula`, `tokyo-night`,
   `monokai`, `everforest`). Restores fidelity and fixes the contrast in
   one move, but changes what four named themes look like.
2. **Drop `pop-lagoon` and `pop-fuchsia`**, leaving six pop themes, one
   per sector of the wheel. Lagoon sits between lime and cobalt at the
   same lightness and its own note calls it "the softest of the Pop
   family", which in a family defined by not being soft is an admission;
   fuchsia duplicates `pop-red`, which is the family's declared anchor.
   Catalogue goes from 33 to 31.
3. **Adopt the serif-text / sans-UI default split**, which changes the
   look of every theme that does not override it.

Not decisions, but corrections owed regardless: three entry notes are
factually false (`gruvbox` on borrowed accents, `everforest` on the
"official light+dark pairing", `dracula` on Alucard not existing), and
spec §9.5.2's claim that the project palettes were measured to AA is
untrue for five of them.

---

## 6. Engine limits found, in order of cost

1. **`verdict.*.mark-fg`** — blocking for B5, see §3.
2. **`body-heading.size` / `.font`** — the article's `h2`/`h3` have no
   size and fall back to browser defaults, so at 18px body an `h3` is
   barely larger than the text. The most visible hierarchy gap left.
3. **`page.content-max`** — closed by `ETUDE-VIEWPORT.md`; see B13.
4. **`summary.font` / `.weight` / `.style`** — the second most important
   text on a card exposes only `fg`, `size`, `leading`.
5. **`title1.tracking` / `.transform`, `title2.tracking` / `.fg`** — cost
   `dread` about 30% of its intended register.
6. **`nav-dots.bg` / `.rule-fg` / `.pad`** — the only real fix for B6,
   and §0.1 shows it is needed more than the report claimed.
7. **Polarity is unreachable from a property layer** — see §3. The clean
   fix is to derive polarity from the resolved lightness of `color.page`
   after merge, rather than reading a flag on the entry. That would also
   make the four flips expressible as a pure layer.
8. **`page.bg.from` / `.to` / `.angle`** — only the cover can gradient.
9. **`table.head.transform`** — found by failing; the engine's
   "did you mean `tag.transform`?" worked exactly as promised.
10. **Index typography** — `card.title`, `card.desc`, `series-nav.title`,
    `intro` have no `font`, so the series' front door stays mute while
    the articles have a voice.
11. **`quote.size` / `.font`**.
12. **Alignment** — already B7; `highlight.align` is the acceptance case
    and `cover.align` is added.
13. **`page.tracking`** — no global tracking, so it gets set nowhere.
14. Minor: `caption.font`, `source.weight`, `footer.weight`, `refs.font`,
    `cover.tag.*` beyond `fg`, `fact.font`.

---

**Sources** — [Modern Font Stacks](https://modernfontstacks.com/) ·
[Baymard, line length readability](https://baymard.com/blog/line-length-readability) ·
[Google Fonts Knowledge, measure](https://fonts.google.com/knowledge/using_type/understanding_measure_line_length) ·
[USWDS Typography](https://designsystem.digital.gov/components/typography/) ·
[Learn UI Design, pairing fonts](https://www.learnui.design/blog/guide-pairing-fonts.html) ·
[text-shadow and accessibility](https://mrec.github.io/blog/2025/text-shadow/) ·
[Nord colours and palettes](https://www.nordtheme.com/docs/colors-and-palettes/) ·
[Solarized](https://ethanschoonover.com/solarized/) ·
[Dracula spec](https://draculatheme.com/spec) ·
[dracula/vim](https://github.com/dracula/vim) ·
[morhetz/gruvbox](https://github.com/morhetz/gruvbox) ·
[Catppuccin style guide](https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md) ·
[folke/tokyonight.nvim](https://github.com/folke/tokyonight.nvim) ·
[sainnhe/everforest palette](https://github.com/sainnhe/everforest/blob/master/palette.md) ·
[rose-pine/neovim](https://github.com/rose-pine/neovim)
