<!-- lwp:meta -->
page_title: Kit-owned graphic layers
notes_placement: page
layers: {"add":["author-marker"]}
---

<!-- lwp:slide:cover -->
slug: cover
kicker: Identity and documentary ownership
# Kit-owned graphic layers
summary: The cover has no kit mark. Its SOURCE marker belongs to this unit.

---

<!-- lwp:slide:unit-index -->
slug: contents
## Try the layer choices
index-selector: -type:cover -type:unit-index

---

<!-- lwp:slide -->
slug: inherited
kicker: Start with this card
## A preset chooses its own compositions
summary: Marked, Review and Clean share one standalone resource catalogue.

Open **C** and switch the preset. Marked shows the corner image. Review rotates
it the other way and adds DRAFT behind the text. Clean removes the preset
graphics. SOURCE remains because the unit adds it after the preset choice.[^owner]

[^owner]: A kit owns its resource definitions; a preset contributes defaults, not a new documentary parent scope.

---

<!-- lwp:slide -->
slug: local
layers: [{"use":"kit/brand","as":"local-brand","overrides":{"image":{"rotate":35,"opacity":1}}}]
kicker: Explicit kit reference
## Replace inherited choices on one card
summary: This array replaces all inherited layers, including the SOURCE marker.

The mark keeps the kit's image binding. Its local instance changes rotation and
opacity. All published presets use the same kit catalogue, so `kit/brand`
exists even in Clean. A native alternative without that resource would be
refused before publication, not left broken at runtime.

---

<!-- lwp:slide -->
slug: disabled
layers: []
kicker: Local opt-out
## No graphics from either owner
summary: A slide-local empty array cancels both kit defaults and unit additions.

---

<!-- lwp:slide:full-article -->
slug: article
article: details.md
