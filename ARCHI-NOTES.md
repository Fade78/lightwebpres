# Notes: architecture

What ships today under the name "footnotes" is not one. `[^1]` becomes
`<sup>[^1]</sup>` — the literal marker, brackets and caret included — and
`[^1]: text` becomes a paragraph beginning with the same literal. No
anchor, no link, no numbering, no collection. Three documents promise
"full support for footnotes". For a tool whose central use is the sourced
article, a reference the reader cannot reach is a defect, not a style.

---

## 1. Vocabulary

A note has two parts, and they are always named separately below because
they live in different places:

- the **call** — the marker in the running text, where the claim is made;
- the **body** — the note itself, wherever it ends up.

**Placement** is where the body lands. That is the only structural
decision; everything else is appearance.

## 2. Two placements, and why not three

A page is a sequence of sections. One of them can be the long-form
article. A "separate notes page" is therefore not outside the document —
it is another section of the same page, which is what makes it
implementable at all in a single self-contained file.

Once that is seen, the three candidate placements collapse to two:

**`local` — the body renders at the foot of the unit that called it.**
For a call in a card, that is the foot of that card. For a call in the
long-form article, that is the end of the article. One principle, two
structures: *as close to the call as the structure allows*.

**`page` — every body on the page collects into one notes section at the
end**, a section like the article's, with its own heading and anchor.

A third value — "at the end of the article specifically" — was
considered and dropped: for a call made in the article it is identical to
`local`, and for a call made in a card it is identical to `page`. It
would name no distinct behaviour.

### Why `local` is the default

A card is one screen **and it is directly addressable**: every card has
its own anchor, and the share button hands out links to individual cards.
So a reader can arrive at card 5 without having read cards 1 to 4. If
that reader clicks a call and is thrown to the end of a document they
have not read, the note has cost them their place to gain nothing — the
body could have been six lines below.

The long-form article is the opposite: a continuous scroll, where the
collected block at the end is what every reader already expects, and
where a jump-and-return is the normal gesture.

`local` names both behaviours with one word because it names the same
*principle*, not the same *position*.

### What `page` is for

Cards meant to be projected or read as a clean sequence, where a note
block at the foot of a slide is noise. It is a real want, and it is the
author's to declare.

**A measured consequence to state plainly:** notes at the foot of a card
take room on a screen that is already short — 3 cards in 8 overflow on a
phone in landscape (`ETUDE-VIEWPORT.md`). A card carrying five notes will
scroll. That is an authoring signal more than a rendering problem, but an
author choosing `local` should know it.

## 3. The tooltip is not a placement

It is an **affordance on the call**, and it composes with either
placement: `notes-tooltip: on` puts the body's text on the call as well,
without moving it.

**It is never the only carrier, and cannot be made one.** A tooltip does
not exist on a touch screen, does not exist in print, and is not part of
the reading order. A note that lives only there is lost to a large share
of readers — and losing the reference is the worst place for this tool to
economise. The body is always in the document; the tooltip only saves a
jump.

Its value is therefore highest with `page` (where it saves a real jump)
and lowest with `local` (where the body is already six lines away). It is
off by default.

## 4. Numbering, links, and the cases that need a ruling

**Numbering is continuous, and it restarts with the unit that carries
the bodies.** One rule, and it follows from placement rather than being a
second decision:

| placement | the unit carrying bodies | numbering |
|---|---|---|
| `local`, call in a card | that card | restarts at 1 in each card |
| `local`, call in the article | the article | continuous through the article |
| `page` | the page | continuous across the page |

**The argument is addressability, not symmetry.** A card is shareable on
its own — the share button hands out links to individual cards — so a
reader can arrive at card 5 having seen nothing else. A note numbered 7
there is meaningless to them: they will look for the first six. Numbering
must be scoped the way addressing is. It is also what print does: notes
restart per page, and here the card *is* the page's analogue — one
screen, one unit, its own ground and rules.

**The displayed number is not the anchor id.** HTML requires ids unique
to the document, so the body's id stays scoped (`note-s3-1`: slide 3,
note 1) while the reader sees `1`. Without that, two cards each carrying
one note would emit two `id="note-1"` and every return link would land on
the wrong one.

The author's label (`[^kwh]`, `[^1]`, `[^a]`) stays in the source and can
be anything; what the reader sees is a position. This is not a content
rewrite — the source keeps its labels — so it does not collide with the
rule that the tool never mutates what an author wrote.

**Links go both ways.** The call is a link to the body; the body carries
a return link to the call. The return link is not decoration: without it
a reader who jumped from card 3 has no way back but the scrollbar, and a
screen-reader user has none at all.

**One label called twice yields one body with two return links.** The
alternative — duplicating the body — would give two numbers to one
reference.

**A call with no body** is a claim citing a source that is not there.
`audit` names it, per article. **A body with no call** is a leftover.
`audit` names that too. Neither is fatal: the input contract does not
break over an editorial slip, and `audit` exists precisely for this
class.

**A definition inside a raw HTML block is never converted** — raw HTML is
passed through verbatim by design. Today that silently ships
`[^1]: text` into the page, which is how the combination of `.refs` and
footnotes — both documented, separately — produces broken output at exit
0. `audit` will name it.

## 5. Two cascades, and the reason is mechanical

**Structure and appearance do not cascade through the same layers, and
this is not a matter of taste.** The theme engine composes CSS and
nothing else. CSS cannot move an element from one container to another.
So `placement` *cannot* be a theme property — not because it would be
inelegant, but because a theme physically could not honour it.

| | what it decides | cascade |
|---|---|---|
| **structure** | `notes-placement`, `notes-tooltip` | built-in default → `series_meta` → article meta block |
| **appearance** | type size, rule, colour, marker | the property registry: defaults → theme → `settings.conf` → `style.*` → instance tag |

The structural cascade reuses the shape `author`/`license`/`date`
already have: declared series-wide in `series_meta`, overridden per
article in its own meta block. Nothing new is invented.

The appearance side extends the registry with **three** components,
because the two placements are not one surface. `footnote-call` (`sup`,
with `fg` and `size`) already exists and keeps its name; it styles the
call, which is the same object wherever the body lands.

| Component | The surface | Why it is its own |
|---|---|---|
| `note` | the body itself | shared: type size, colour, leading, the return link |
| `note.local` | the block at the foot of a card | compact furniture *inside* a card — a rule to detach it from the content above, tight spacing, no ground of its own |
| `note.page` | the notes section at the end | a **section**, like the article's: it wants a ground, a heading and a rule, and it is sized for a scroll rather than for the last third of a screen |

Giving them one component would force a theme to style a foot-of-card
block and a full section with the same values, which is the mistake the
§9 rewrite was made to stop: one name carrying two senses, so neither can
move without moving the other.

## 6. The authoring surface

Unchanged from what authors already write, because the syntax is standard
Markdown and there is no reason to invent one:

```markdown
The kettle draws about 3 kW[^kwh] on a domestic ring.

[^kwh]: Measured at 230 V, 13 A. See the appliance's rating plate.
```

And, where a series or an article wants the other placement:

```json
{ "series_meta": { "notes-placement": "page" } }
```

```
<!-- lwp:meta -->
page_title: The kettle
notes-placement: page
notes-tooltip: on
```

## 7. What is load-bearing, and what is an option

If only one thing ships, it is this: **numbering, two-way links and the
ARIA roles**, at `local` placement. That is what turns a literal marker
into a note.

`page` and `notes-tooltip` are options on top. They change no output for
an author who does not ask for them.
