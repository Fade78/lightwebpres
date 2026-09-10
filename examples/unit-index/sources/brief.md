<!-- lwp:meta -->
page_title: Follow the evidence
page_desc: Explicit contents, literal tags and named selectors in one content unit.
notes_placement: page
---

<!-- lwp:slide:cover -->
slug: opening
kicker: A source-only example
# Follow the evidence
summary: A contents list offers stable links without choosing a new reading journey.

---

<!-- lwp:slide:unit-index -->
slug: everything
## Everything published in this unit
summary: The wildcard includes this index, the other indexes and generated notes.
index-max-columns: 3
note: Show that indexes are ordinary published slides too.
comment: The missing index-selector field deliberately demonstrates the default wildcard.

---

<!-- lwp:slide:unit-index -->
slug: english-evidence
## English evidence only
index-max-columns: 2
index-selector: selector:english-evidence

---

<!-- lwp:slide:unit-index -->
slug: empty
## An intentionally empty selection
index-selector: slide:title:"A title that is not in this deck"

---

<!-- lwp:slide -->
slug: evidence-english
tags: expert-en
kicker: Evidence
## Stable identities keep a long and descriptive title independent of the link readers share
summary: Rewriting the heading does not rename the slide.
fact-label: Try it

The authored slug identifies this slide even after reordering. Its note is
collected at the end of the unit.[^identity]

[^identity]: This example demonstrates the engine's slug contract, not an external factual claim.

---

<!-- lwp:slide -->
slug: evidence-french
tags: expert-fr
## A separate tag, not an engine language category
summary: This tag does not translate the slide or automatically select typography.

An index link can reveal a differently tagged target without rebuilding its list.

---

<!-- lwp:slide -->
slug: shared
## Shared reading content is not literal tag membership

This slide is visible with either reading tag because its tags default to
default. It is not selected by the literal expert-en predicate.

---

<!-- lwp:slide:series-nav -->
slug: series-links

---

<!-- lwp:slide:full-article -->
slug: background
article: background.md
