<!-- lwp:meta -->
page_title: Graphic layers
page_desc: Reusable compositions, local labels and screen-aware placement.
layers: {"add": ["series/draft"]}
layers_by_type: {"cover": [], "unit-index": []}
style.title2.strong.weight: normal
style.title2.strong.style: italic
style.summary.strong.decoration: underline
---

```lwp-asset
{"schema":"lightwebpres.asset/1","id":"local-label","kind":"html","format":"markdown-inline","style":{"font_size":"14px","color":{"theme":"kicker.fg"},"weight":"bold"}}
---
LOCAL
```

```lwp-layer
{
  "schema": "lightwebpres.layer/1",
  "id": "local-marker",
  "tags": ["evidence"],
  "elements": [{
    "id": "label",
    "asset": "local-label",
    "place": {
      "target": {"ref": "kicker", "bounds": "content", "anchor": "right-center"},
      "self_anchor": "left-center", "offset": ["12px", "0px"]
    }
  }]
}
```

```lwp-layer
{
  "schema": "lightwebpres.layer/1", "id": "screen-marker", "media": ["screen"],
  "elements": [{
    "id": "visible", "asset": "local-label",
    "size": {"height": {"percent": 3, "of": "viewport.height"}},
    "place": {"target": {"ref": "screen", "anchor": "top-right"},
              "self_anchor": "top-right", "offset": ["-20px", "20px"]}
  }]
}
```

<!-- lwp:slide:cover -->
slug: cover
kicker: A composition is not a flattened image
# Graphic layers
summary: Image and text instances share a composition. This cover explicitly opts out.

---

<!-- lwp:slide:unit-index -->
slug: contents
## Try the examples
index-selector: -type:cover -type:unit-index

---

<!-- lwp:slide -->
slug: attached
tags: evidence
kicker: Native anchor
## Content and decoration stay independent
summary: The LOCAL label attaches to the occupied kicker text, not its allocated row.
fact-label: Try a change

Open the appearance menu with **C**. The text colour follows the theme while
the fixed text size stays fixed. The background DRAFT and compass are separate
instances of one external composition.

---

<!-- lwp:slide -->
slug: screen
layers: {"add": ["screen-marker"]}
kicker: Slide, screen and viewport
## Follow the visible fragment
summary: LOCAL follows the top-right of the visible slide portion; the compass stays at the full slide's bottom.

The screen marker is explicitly screen-only. The underlying DRAFT composition
also prints, using the complete logical slide.

---

<!-- lwp:slide -->
slug: image-background
layers: ["theme-background"]
kicker: Behind the content
## A **background** without moving the text
summary: A full-slide SVG follows the **theme ink**, keeps its ratio and crops at the card edges.
fact-label: Try another palette

The landscape is one image instance on the under-content plane. It is tinted
with the active theme's kicker colour rather than borrowing the fitted
kicker's pixels. **C** changes the palette; the composition stays selected.

The formatted word in the title uses an article-owned theme-property pin:
semantic strong is normal-weight italic here, independently of body emphasis.

---

<!-- lwp:slide -->
slug: image-foreground
layers: ["theme-background", "foreground-mark"]
kicker: In front of the card
## A free **foreground** image
summary: The compass sits at a fixed corner offset. It is not a body figure and does not change `size` or fitting.

The foreground uses the same image-asset contract as the background, but paints
above native content. Reader controls remain above both, and decorative images
do not capture click or touch gestures.

---

<!-- lwp:slide -->
slug: no-decoration
layers: []
kicker: A local exception
## No graphics on this card
summary: An explicit empty selection cancels inherited and automatically matched compositions.

---

<!-- lwp:slide:full-article -->
slug: article
article: details.md
layers: [{"use":"series/draft","as":"article-draft","overrides":{"stamp":{"opacity":0.05}}}]
