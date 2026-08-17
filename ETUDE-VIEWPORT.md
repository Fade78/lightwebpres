
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
