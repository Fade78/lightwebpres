
## 14. The literals nobody counted, and the column that finds them

§11 gave a scale to the thirty-five sizes in the property registry. It did
not give one to the sizes written straight into the skeleton, because
nothing in the method distinguished the two: the sweep enumerated
*properties*, and a literal is not a property. So `article.size` grew and
the article's own headings did not. Measured on one built page:

| | 375 | 1920 | 3840 |
|---|---|---|---|
| slide `h2` | 24 | 50.8 | 101.5 |
| `.full-article p` (a property) | 15 | 20.3 | 40.5 |
| `.full-article h2` (a literal) — before | 22 | 22 | **22** |
| `.full-article h2` — after | 22 | 29.7 | 59.4 |

At 3840 a section heading rendered at **0.54× the body text it heads**, and
the inversion had already started at 1920, where the two were 1.75px apart.
Two more of the same: `.slide-body` carried no size at all, so free prose on
a card sat at 16px under a 101.5px title — and the *same prose* rendered at
47.5px if a `fact-label:` happened to precede it, a three-fold difference
decided by a field rather than by the writing. And `.figure` had no size
either, so `caption.size: 0.85em` — the one em-relative size in the reading
surface — resolved against the document's unset 16px and never moved. An em
only scales if something above it does.

Same arithmetic as §11 throughout: coefficient = pixel value ÷ 8, which
reproduces the drawn ratio at 1920×1080 and holds it above. Floors
untouched, so a phone is byte-identical.

**The column, at last.** `tests/test_type_scale.py` renders a real page at
1920 and at 3840 and names every element whose text is the same number of
pixels in both. It walks the DOM rather than a list of selectors —
deliberately, because a list only ever covers the components someone
remembered, and the last three instances of this defect were in components
added after the list was written. The check is an *exact* match against a
`STILL_FLAT` set: a newly flat element fails it, and so does fixing one and
leaving it listed.

It caught something on its own first run, which is the part worth recording.
The initial signature was `tag.class`, so a slide's `h2` and the article's
`h2` collided under the bare key `h2`; first-instance-wins kept the slide's,
which scales, and the instrument reported OK against a deliberately
reintroduced defect. **An instrument that aggregates two things into one key
measures neither.** Signatures are scoped by their nearest classed ancestor
now, and the same mutation fails.

Twelve sizes are still flat and listed: the slide counter, the nav home
glyph, the tag-menu heading, the help overlay, the share popover and its QR
modal. All chrome, all real, all owned by a later lot — and now all named in
a file that fails when the list stops matching the page.

## 15. Three promises, none of them measured

Not a viewport finding, but the same failure of instrument, so it belongs
with the rest: three things a built deck promises that no test had ever
checked, because every test that touched them read the stylesheet instead
of the page.

**The slide-variant dialog could not be operated without a mouse.** It
carries `role="dialog"`, its options are real `<button>`s, and they are
focusable. None of that mattered: five Tab presses left
`document.activeElement` on `BODY`. The global keydown handler
`preventDefault()`s every key whose target is not already inside
`.tag-menu` — and a prevented Tab cancels the focus move, so focus could
never get in to begin with, which meant the target was never inside, which
meant the next Tab was prevented too. Nothing focused the dialog on open,
so the whole feature (shipped in v0.32.0) was mouse-only and its `role`
was never announced. Focus now moves to the active option on open, wraps
on Tab and Shift+Tab, and returns to the button that opened it.

**The speaker counter was invisible on 15 of the 34 themes**, at exactly
1.00:1. `.slide-counter { background: none }` let the cover's gradient
show through, and on a light theme `page.fg` and `cover.bg.from` are both
`color.ink` — the counter's ink *was* its ground, and the 1px border in
`currentColor` disappeared with it. Every neighbouring overlay
(`.presenter-panel`, `.tag-menu`, `.help-overlay`) uses `background:
inherit` and measures AA everywhere; this one element did not. On
`high-contrast` it now measures 21.00:1.

Worth naming: **`theme show`'s contrast report could not have caught
this.** The report walks the property registry, and `.slide-counter` is
skeleton-only with no property for it to read. The report is accurate
where it looks — it prints 4.1626:1 for a pair I measured in the browser
at 4.17:1 — and the gap is its field of view, not its arithmetic.

**One slide per sheet printed one sheet too many, always.**
`.slide:last-child` matched *nothing* on any page ever built: the page
footer and the inline script element follow the last slide, so the last
slide is never the body's last child. The final slide kept
`page-break-after: always` and the footer took a sheet of its own. Six
slides printed seven pages, four printed five, on every page of two
corpora. `:last-of-type` fixes it.

**What the tests had to become.** All three are now measured on the
rendered page — focus walked with real key presses, contrast computed
from resolved colours across five themes, sheets counted in a real PDF. A
string check on the emitted CSS would have called the print rule fine,
because the rule was present and correct and simply selected nothing.

Two things the mutation pass taught while writing them, both about the
fixture rather than the code. The print test did not bite until the probe
carried a `series_meta` footer — with nothing to spill onto the extra
sheet, the defect hides, so **a probe must carry the thing that made the
defect visible or it passes against the bug**. And the sheet count has to
be of *visible* slides: the variant filter hides the cards that do not
carry the active tag, and a hidden card prints nothing.
