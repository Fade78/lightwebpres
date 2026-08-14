# Portrait and landscape: a measurement study

Preparatory work for **B13** (`--content-max`) and **B7** (alignment
axes), now **implemented** — §7 carries the shipped numbers. This file
records what was measured, which hypothesis it killed, and the
configuration the numbers support. Reproduce it with
`tools/viewport_measure.py`.

---

## 1. Why measure rather than reason

The typographic literature agrees on the target: a column carries
**45–75 characters per line**, 66 being the usual optimum, and WCAG
1.4.8 (AAA) sets **80 as a ceiling**. What no amount of reasoning gives
you is the number a given sheet actually produces, because it depends on
the font's average advance, on `clamp()` resolution, on padding, and on
which of several `max-width` declarations wins.

So the sheet was rendered in Chromium at fifteen real viewports, every
phone and tablet in **both rotations**, and the line boxes were counted
directly: one `Range.getClientRects()` rectangle per rendered line, which
makes the browser's own line breaking the authority. Demo copy is far too
short to fill a line, so every component is saturated with filler prose
first; card overflow is read *before* saturation, on the real copy.

## 2. What the baseline does

Three findings, none of which was visible in the CSS.

**The measure is far past the ceiling on every screen above a phone.**
The card summary renders 106 characters per line on a laptop, the fact
body 123, and the article paragraph 127 — against a ceiling of 80. The
article was the worst offender and it is not even governed by
`--content-max`: it carries its own `max-width: 800px`, chosen for a
width and not for a measure, which at 15px text is nearly twice the
right value.

**Rotating a phone doubles the measure.** iPhone 15 goes from 45
characters per line in portrait to 93 in landscape; the article
paragraph from 54 to 117. Portrait is fine — 84vw of a narrow screen
happens to land in the right band by accident. Landscape is not, and
nothing in the sheet notices, because `--content-max: min(84vw, 1100px)`
sees only width.

**Rotating a phone also makes the type bigger while the screen gets
shorter.** Every fluid size is `clamp(…, Nvw, …)`. Turning an iPhone 15
sideways takes the viewport from 852px tall to 393px and simultaneously
takes the cover title from 28px to 38px, because `vw` grew. The result
is measurable: **6 cards out of 8 overflow the viewport in landscape
against 1 in portrait**. Every breakpoint in the sheet keys on
`max-width`; none keys on height. That is the blind spot.

## 3. The hypothesis the measurements killed

The obvious fix for the third finding is `vmin` instead of `vw`: in
portrait `vmin == vw`, so nothing changes, and in landscape the type
follows the constraining dimension. Measured on its own, **it makes the
measure worse** — the summary goes from 93 to 123 characters per line on
a tablet in landscape, from 106 to 135 on a laptop.

Which is obvious in hindsight: a fixed pixel cap divided by a smaller
font is *more* characters, not fewer. `vmin` is only safe once the cap
stops being a pixel count.

## 4. What `ch` does, and the property that makes it work

Expressing the cap as a measure — `page.content-max: 50ch` — has a property
worth stating explicitly, because the whole design rests on it and it was
verified rather than assumed:

> A `ch` length inside a custom property resolves against the font of the
> **consuming element**, not against `:root`. The custom property carries
> a token stream; the substitution happens at the point of use, and only
> then is the length computed.

Measured on a 1080p desktop, one declared value yields a 1613px box for
the cover title (52px type), 721px for the summary (22px), and 474px for
the fact body (18px). One knob, the right measure at every type size —
which is the reason the unit exists.

The consequence for this study is that **characters per line become
viewport-invariant**. The candidate holds 62 for the summary, 55 for the
fact body and 67 for the article paragraph identically from tablet
portrait to ultrawide; the only viewports that fall below are the phones
in portrait, where the proportional gutter binds first and 45–56
characters is the correct answer anyway.

`50ch` and not `66ch`: the `ch` unit measures the advance of the digit
zero, which is narrower than the average lowercase letter. Measured, the
ratio on these font stacks is about 1.3 — 50ch renders 55 to 67 real
characters, centred on the optimum.

## 5. Where the proportional half of the rule lives

The requested shape was *proportional to the screen, with a maximum*.
That is what the retained configuration does, but the two halves live in
different declarations:

- **the proportion is the padding** — `.slide` already carries
  `padding: 60px 8vw`, so the content box is 84vw before any cap applies;
- **the maximum is the measure** — `page.content-max: 50ch`.

Because the padding already imposes 84vw, a `min(92vw, 50ch)` cap would
have an inert first term inside a card. Keeping the gutter in the padding
and the ceiling in the measure puts each half where it belongs and
removes the temptation to encode the same constraint twice.

This also retires the `@media (max-width: 600px)` override of
`--content-max`: it existed to recover characters on small screens, and a
measure that is already bounded by the padding does not need it.

## 6. Height needs its own breakpoint

Neither change fixes landscape overflow, because that is not a typography
problem: a card holding a title, a summary and a fact box does not fit in
375px of height at the minimum readable size, and no cap will make it.
What helps is reclaiming the fixed padding, which on a landscape phone
eats 120px of 375 — a third of the screen:

```css
@media (max-height: 520px) {
  .slide { padding: 24px 6vw; }
  .fact-box { padding: 14px 18px; }
  .highlight { margin: 8px 0 10px; }
}
```

Measured, this takes the landscape phones from 6 overflowing cards out of
8 down to 3, and it is inert everywhere else — portrait and desktop
results are unchanged to the pixel, because the query never matches.

It does not reach zero, and it should not be expected to. `.slide` uses
`min-height: 100vh`, not `height`, so a card that does not fit simply
grows and the page scrolls: the failure mode is graceful and the promise
"one card, one screen" degrades to "one card, one scroll" exactly where
the screen is too small to keep it.

`100svh` would be the matching fix for the mobile URL bar. It is **not**
verified here: headless Chromium has no browser chrome, so `svh`, `lvh`
and `vh` are all equal in this harness. It is recorded as untested.

## 7. Shipped configuration, and what it measured

Implemented, and re-measured on the real build rather than on an injected
override. `tools/viewport_measure.py` reproduces both columns.

| | from | to |
|---|---|---|
| content cap | `min(84vw, 1100px)`, skeleton-only | `50ch`, the `page.content-max` property |
| article paragraph cap | `800px` | `var(--page-content-max)` |
| key-figure caption cap | `480px` | `var(--page-content-max)` |
| article subtitle / intro cap | `700px` | `var(--page-content-max)` |
| fluid type clamps | `Nvw` | `Nvmin` |
| small-screen `--content-max` override | `calc(100vw - 48px)` | removed |
| card height | `min-height: 100vh` | `100vh` then `100svh` |
| height breakpoint | none | `@media (max-height: 520px)`, declared last |

| viewport | summary | fact | article | cards over | worst |
|---|---|---|---|---|---|
| iPhone SE portrait | 45 → **45** | 38 → **38** | 52 → **52** | 3/8 → **3/8** | 225 → **225**px |
| iPhone SE landscape | 74 → **62** | 71 → **57** | 91 → **67** | 6/8 → **3/8** | 555 → **463**px |
| iPhone 15 portrait | 45 → **45** | 41 → **41** | 54 → **54** | 1/8 → **1/8** | 18 → **18**px |
| iPhone 15 landscape | 93 → **62** | 93 → **57** | 117 → **67** | 6/8 → **3/8** | 512 → **445**px |
| Pixel 8 portrait | 48 → **48** | 44 → **44** | 56 → **56** | 0/8 → **0/8** | 0 → **0**px |
| Pixel 8 landscape | 93 → **62** | 99 → **57** | 123 → **67** | 5/8 → **3/8** | 493 → **426**px |
| iPad mini portrait | 87 → **62** | 82 → **55** | 101 → **67** | 0/8 → **0/8** | 0 → **0**px |
| iPad mini landscape | 93 → **62** | 106 → **55** | 127 → **67** | 3/8 → **3/8** | 161 → **186**px |
| iPad Pro 11 portrait | 93 → **62** | 93 → **55** | 108 → **67** | 0/8 → **0/8** | 0 → **0**px |
| iPad Pro 11 landscape | 99 → **62** | 114 → **55** | 127 → **67** | 1/8 → **1/8** | 71 → **96**px |
| Projector 4:3 | 93 → **62** | 106 → **55** | 127 → **67** | 1/8 → **1/8** | 137 → **162**px |
| Laptop 16:10 | 106 → **62** | 123 → **55** | 127 → **67** | 1/8 → **1/8** | 5 → **30**px |
| Desktop 1080p | 106 → **62** | 123 → **48** | 127 → **67** | 0/8 → **0/8** | 0 → **0**px |
| Ultrawide | 106 → **62** | 123 → **48** | 127 → **67** | 0/8 → **0/8** | 0 → **0**px |
| Monitor portrait | 93 → **62** | 106 → **48** | 127 → **67** | 0/8 → **0/8** | 0 → **0**px |

**Characters per line: 45–127 before, 45–67 after, on all fifteen.** The
three phones in landscape go from 6, 6 and 5 overflowing cards out of 8
down to 3 each. Portrait is unchanged to the pixel everywhere, which is
the point: `vmin` is `vw` in portrait and the height query never matches
there, so the fix is paid for only where the problem was.

**The honest cost.** A narrower column is a taller one. On the cards that
already overflowed on tablet landscape, projector and laptop, the count is
unchanged but the overshoot grows — 71px to 96px on an iPad Pro, 5px to
30px on a laptop. Less than the 142px and 90px the injected simulation
predicted, because the height breakpoint gives some of it back. Correct
measure is paid for in vertical scroll on cards that were already too
tall, and that is the right side of the trade.

## 8. What this settled for B7

Two constraints on the alignment axes came out of the measurements, and
both are now in the code:

- **Breaking words at end of line is never automatic.** It shipped once
  tied to `justify` — so choosing an alignment turned it on silently, a
  typographic decision arriving as the side effect of another. It is now
  its own axis, `page.hyphens`, defaulting to CSS's own `manual`. The
  measured 45-character column is why justification is a real risk here;
  it is not a reason to take the decision out of the author's hands.
- **Alignment is a block property and gets block syntax.** `text-align` on
  the inline `<span>` the other instance tags produce has no effect at any
  viewport size, so `{align:center}` is a block tag, its opener and closer
  each alone on their line.

## 9. What was reverted, and what the study got wrong

**`page.content-max` is back to `min(84vw, 1100px)`.** The measurements in
this document stand — the character counts in §7 were real, and the
landscape column genuinely was too long. What the study got wrong is what
it counted as a *gain*.

`50ch` was chosen precisely because a `ch` length in a custom property
resolves against the **consuming** element: §5 called that "one knob, the
right measure at every type size". On a screen it is the opposite of a
feature. One declared value becomes a different pixel width per component
— about 800px on a 32px title, about 450px on 18px body text — so a card's
title runs to one edge and its text stops well short of it. The card loses
its inner edge, and the text stops looking related to the card around it.

That is visible to anyone reading a page, and invisible to this study,
because every column in §7 counts characters per line and none of them
compares two components to each other. **A measurement can only find what
it measures**, and the thing that turned out to matter was an alignment
this instrument had no column for. Reported by the owner, on his own pages,
which is where it shows.

Two things follow for anything like this in future:

- **A ceiling shared by several components has to resolve once**, not per
  element — an absolute or root-relative unit, never `ch`/`em`/`ex`/`lh`.
  There is now a test that fails on any of those, naming the reason.
- **Per-line character counts are not sufficient evidence for a width
  decision.** The next such study needs a column for "do the components on
  one card agree with each other", or it will make this mistake again with
  a different number.

## 10. And then the ceilings came off entirely

Reported from a 1080p screen in full screen, and confirmed at 4K: the deck
does not use the display. Measured, with the ceilings §7 shipped:

| viewport | column | % of screen | title | body |
|---|---|---|---|---|
| 1440×900 | 1100px | 76% | 31.5px | 18px |
| 1920×1080 | 1100px | **57%** | 37.8px | 21.6px |
| 3840×2160 | 1100px | **29%** | 40px | 22px |

Every clamp is at its ceiling by 4K, so nothing grows any further. A built
page is a deck — every card is `min-height: 100vh` — and a deck shown full
screen has to use the screen.

**Both ceilings came off, and that pairing is the whole point.** The column
is `84vw`; the type keeps its `Nvmin` coefficient, raised by 1.35, with no
upper bound. Uncapping the column alone lengthens every line; raising the
type alone shortens them. Together the characters per line do not move —
measured identical at 1920 and 3840, which is the invariance §5 was after
and did not get.

| viewport | column | % | title | body |
|---|---|---|---|---|
| 375×667 | 315px | 84% | 24px | 16px |
| 768×1024 | 645px | 84% | 36.1px | 20.7px |
| 1440×900 | 1210px | 84% | 42.3px | 24.3px |
| 1920×1080 | 1613px | 84% | 50.8px | 29.2px |
| 3840×2160 | 3226px | 84% | 101.5px | 58.3px |

**The floors are untouched, deliberately.** They are what governs a phone,
where §7 counted the cards that already overflow, and a 35% larger type
would put more of them over. At 375×667 the page is what it was, to the
pixel: the floor binds below roughly a 510px smaller dimension, so nothing
under a small tablet moves at all.

What this adds to §9's lesson: the instrument was not only missing a column
for "do the components agree with each other", it was missing one for "how
much of the screen is this using". Both are questions about the page as a
whole, and every column in §7 is about a line of text.

## 11. Uncapping eight sizes made the other twenty-seven small

§10 gave a scale to the eight sizes the study had ever measured — the two
titles, the summary, the fact body, the table body, the key figure and the
two header lines. There are thirty-five font sizes in the registry. The
other twenty-seven kept the pixel values they were drawn at, so raising the
eight did not leave them alone: it made them small *relative to everything
around them*, and the bigger the screen the smaller they read.

Measured on one card, before and after:

| | 375×667 | 1440 | 1920 | 3840 |
|---|---|---|---|---|
| summary | 16 | 21.9 | 29.2 | 58.3 |
| tag — before | 12 | 12 | 12 | 12 |
| tag — after | 12 | 12.2 | 16.2 | 32.4 |
| key figure's caption — before | 14.4 | 14.4 | 14.4 | 14.4 |
| key figure's caption — after | 14.4 | 14.6 | 19.4 | 38.9 |
| slide number — before | 13 | 13 | 13 | 13 |
| slide number — after | 13 | 13.2 | 17.6 | 35.1 |

The ratio is the thing to read, not the pixels. `tag`/`summary` was 0.556
in the drawing (12px against a 21.6px body at 1080p). After §10 it was
0.412 at 1920 and **0.206 at 3840** — an eyebrow label at a fifth of the
body text on the screen a deck is actually presented on. After: 0.556 at
both, because the coefficient is the pixel value over 8, which is exactly
what reproduces the drawn ratio at 1920×1080 and holds it above.

**The floors do the same work here as in §10.** A floor binds until the
smaller dimension passes about 800px, so every phone and small tablet
renders as it did — 375×667 measured identical, value for value.

`page.block-max` had the same shape of defect from the other side. It was
`min(84vw, 1100px)`: a flat ceiling, while `table.size` had just been given
a scale. At 3840 a table's own text reached 41px inside a box still 1100px
wide — about 26 characters a line. `min(84vw, max(1100px, 102vmin))` makes
the 1100 a floor: 102vmin *is* 1100px at 1920×1080, so nothing at or below
that size moves, and the table holds 68% of the column at 1920 and at 3840
alike.

**What §10 did not have a column for, again.** The instrument measured the
eight sizes it knew about. Nothing in it asked *how many sizes are there*,
so twenty-seven properties sat outside every table in this document while
being changed, relative to their neighbours, by the change §10 made. A
count of the population is the cheapest column there is and it was the one
missing.

## 12. A centred box is the only one whose width is also its centre

Reported, not measured first: on a card, the big number was not centred on
the same thing as the text around it.

`.highlight` read `--page-block-max` like every other box. Every *other*
box is left-aligned, so a narrower one still starts at the column's left
edge and reads as deliberate. The key figure is centred, and a centred box
that is narrower than the column has a different **centre**, not just a
different width. Measured, on one card:

| viewport | column centre | key figure centre | off by |
|---|---|---|---|
| 1440×810 | 720 | 665 | 55px |
| 1920×1080 | 960 | 704 | 256px |
| 3840×2160 | 1920 | 857 | **1063px** |

After, all three agree exactly: 720/720, 960/960, 1920/1920, with the h2,
the summary, the caption and the fact box on the same centre.

The second defect was in the same four lines and was found only because
they were being rewritten. `.highlight` was `display: flex` with
`align-items: center`, which is what centred the figure and its caption —
and `highlight.align`, a registry property since the theme refactor, emits
`text-align` onto that element. `text-align` does nothing to flex items.
Setting `highlight.align: left` and rebuilding moved the figure by **zero
pixels**: a documented, themeable, tested property that had never once had
an effect. Its tests checked that the custom property appeared in the
sheet, which it did.

**The lesson, and it is the same one as §9 in a different costume:** a test
that a value is *emitted* is not a test that it is *obeyed*. The cheap
version of the missing check is to set the property to its least likely
value, rebuild, and measure that something moved.

## 13. Everything drawn against a glyph, and the one list that was not

Two more instances of §11's defect, both reported rather than found by
the instrument.

**A halo is sized by the glyph it surrounds.** Three things are drawn
against the text rather than beside it: the coloured box a marked run
sits in (with its corner radius), the underline under it (with its
thickness and its clearance from the baseline), and the glow a theme may
put around a title. All were flat pixels. 4px of side padding reads as a
marker at 24px type and as a printing error at 47px; `terminal`'s 10px
glow surrounded a 51px title at 1080p and an identical 10px surrounded a
132px one at 3840, which is the theme's one visual idea disappearing on
the screen a deck is presented on. Measured after, on the marked run:

| viewport | side padding | radius | underline |
|---|---|---|---|
| 375×667 | 4px | 2px | 2px |
| 1440×810 | 4.05px | 2.03px | 2.03px |
| 1920×1080 | 5.4px | 2.7px | 2.7px |
| 3840×2160 | 10.8px | 5.4px | 5.4px |

The floors are what keep the two collisions this rule was measured to
avoid — the descenders, and the mark's lower edge — as they were measured.

**`.series-list` was 680px flat**, so the cross-article navigation sat at
42% of the column at 1920 and 21% at 3840, against the left edge of a card
whose heading ran the full width. A series-nav card holds exactly two
things, that heading and this list, so any width narrower than the column
is §12's problem again: a second centre on the card that can least afford
one. It reads `--page-content-max` now — wider *and* centred, because it
is the column. Measured: heading centre and list centre agree at 720, 960
and 1920.

**What the instrument still does not have.** §11 noted it had no column
for how many sizes exist. It has no column for how many *lengths* exist
either: about 150 literal pixel values remain in the skeleton, and most
of them should stay — a 1px border is 1px, a media-query breakpoint is a
breakpoint, and fixed chrome is positioned against the viewport, not
against the type. The distinction that matters is not px versus vmin; it
is whether the length is drawn against the text. Every defect in §11
through §13 sat on the wrong side of that line, and nothing in this
document asks the question directly.
