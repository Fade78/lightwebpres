<!-- lwp:meta -->
page_title: LightWebPres — the guide
page_desc: Create content, organize a collection, design identities and publish with LightWebPres.
nav_title: Guide
nav_desc: Create, organize, design, read, publish and automate
---

<!-- lwp:slide:cover -->
slug: lightwebpres
kicker: Product manual
slide-layout: hero
# LightWebPres
summary: One source for reading and presenting. Choose a route, or <a href="#guide-complet" style="color: inherit">open the complete manual</a> now.

---

<!-- lwp:slide -->
slug: trois-commandes
kicker: Create content
## Start from a page that already works
highlight: 2
highlight-caption: commands to open a working demo
fact-label: Edit after you have something to inspect
source: <a href="#1-create-content">Guide, route 1: Create content</a>

Run `init my-series`, then `demo my-series --lang en` with the
LightWebPres executable. Demo already builds: open `public/index.html`
inside that series.

Replace an example with your own article, register it in `series.json`,
then build again.[^tutorial]

[^tutorial]: The manual's first-article tutorial includes the complete Markdown source and matching JSON.

---

<!-- lwp:slide -->
slug: tags
kicker: Organize a documentary collection
## Reuse the article, change its context
fact-label: A series selects and orders your material
source: <a href="#2-organize-a-documentary-collection">Guide, route 2: Organize a documentary collection</a>

The same canonical article can serve a briefing and a reading collection.
Each series registers the source and supplies only its context-specific
metadata.

Make the article, long text and images available to both series.
After a shared edit, build both: LightWebPres does not discover the other
series for you.

---

<!-- lwp:slide -->
slug: identity-kits
kicker: Design and compose identities
## Compose a kit, not a dependency chain
fact-label: One autonomous identity to distribute
source: <a href="#3-design-and-compose-identities">Guide, route 3: Design and compose identities</a>

`kit compose` can bring layouts, visual marks and a typed theme from
several kits into one final kit. Authors need the result, not its source kits.

Follow the Field Notes example and its composition diagram in the manual.
Use a theme alone when colors and typography are all you need to change.

---

<!-- lwp:slide -->
slug: themes
kicker: Read, present and share
## Share the point, not directions to it
fact-label: Every slide has a stable address
source: <a href="#4-read-present-and-share">Guide, route 4: Read, present and share</a>

Press **S** to share the current slide by link or QR code. Its `slug:`
keeps that address stable when the deck is reordered.

Readers open the same page in their browser. They can follow the cards
or go straight to the long article for detail, as you can in this guide.

---

<!-- lwp:slide -->
slug: verifications
kicker: Publish and maintain
## Check the output you intend to publish
fact-label: Source warnings and stale files are different failures
source: <a href="#5-publish-and-maintain">Guide, route 5: Publish and maintain</a>

`audit` inspects sources and styles. `verify` compares a fresh render
with the files on disk. Neither replaces inspecting the page in a browser.

Publish `public/`, including its images and kit assets. Keep the authoring
project separately so you can edit and rebuild it later.

---

<!-- lwp:slide -->
slug: pipeline
kicker: Integrate and automate
## Give automation a bounded job
fact-label: State what may change and how to check it
source: <a href="#6-integrate-and-automate">Guide, route 6: Integrate and automate</a>

An agent can edit a named article, theme or kit without owning the whole
project. Specify its allowed files and protect published slugs and destinations.

Require a build and the relevant reports before handoff. The CLI and browser
builder run the same engine; changing the interface does not change the format.

---

<!-- lwp:slide:series-nav -->
slug: la-serie

---

<!-- lwp:slide:full-article -->
slug: guide-complet
article: guide_article.md
