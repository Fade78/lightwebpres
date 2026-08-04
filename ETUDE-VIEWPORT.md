# Portrait and landscape: a measurement study

Preparatory work for **B13** (`--content-max`) and **B7** (alignment
axes). Nothing here is implemented yet — this file records what was
measured, which hypothesis it killed, and the configuration the numbers
support. Reproduce it with `tools/viewport_measure.py`.

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

Expressing the cap as a measure — `--content-max: 50ch` — has a property
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
- **the maximum is the measure** — `--content-max: 50ch`.

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

## 7. Retained configuration

| | from | to |
|---|---|---|
| content cap | `min(84vw, 1100px)` | `50ch`, exposed as `page.content-max` |
| article paragraph cap | `800px` | `var(--content-max)` |
| key-figure caption cap | `480px` | `var(--content-max)` |
| article subtitle cap | `700px` | `var(--content-max)` |
| fluid type clamps | `Nvw` | `Nvmin` |
| small-screen `--content-max` override | `calc(100vw - 48px)` | removed |
| height breakpoint | none | `@media (max-height: 520px)` |

Result: characters per line between 45 and 67 on all fifteen viewports,
against 45 to 127 before; landscape phone overflow down from 6 cards in 8
to 3.

**The honest cost.** A narrower column is a taller one. On the cards that
already overflowed on tablet landscape, projector and laptop, the count
is unchanged but the overshoot grows — 71px to 142px on an iPad Pro in
landscape, 5px to 90px on a laptop. Correct measure is paid for in
vertical scroll on cards that were already too tall, and that is the
right side of the trade.

## 8. What this implies for B7

Two constraints on the alignment axes come out of the measurements:

- **`justify` must ship with `hyphens: auto`.** The narrowest measured
  column is 45 characters on a phone in portrait, where unhyphenated
  justification produces rivers. The templates already emit
  `<html lang="{{lang}}">`, so automatic hyphenation has the language tag
  it needs.
- **Alignment is a block property and needs block syntax.** Confirmed by
  nothing here — it is a CSS fact — but the measurements make the case
  concrete: `text-align` on the inline `<span>` the existing instance
  tags produce has no effect at any viewport size.
