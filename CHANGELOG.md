# Changelog

What changed between versions, in the words the release was announced in.

**One text, one place.** The entry below a version heading IS the body of
that version's GitHub release — written once, when `VERSION` is bumped,
then pasted into the release form unchanged. Nothing here is a second
telling of what the release notes say, because a second telling drifts
from the first within a few months, and this project has paid for that
more than once.

Why the file exists at all, given the releases are on GitHub: the way
people get this tool is by **downloading one file**. Someone holding
v0.38.0 has no way, from the repository or from `--version`, to learn what
has changed since. The git history is not an answer — a release carries
around thirty commits and most of them are internal. And a release body
that lives only on a hosting service is one outage, one migration or one
renderer away from being gone. The proof is in this file: GitHub's own
copy of the v0.43.0 body has lost the characters that release was about
(see the note under that version).

`Unreleased` is a real state, not a placeholder. `VERSION` names a number
that has not been tagged yet, and the section for it is written as the
work lands rather than assembled on release day. A test asserts that the
number `VERSION` announces has a section here, so the two cannot drift
apart in silence.

Entries for **v0.42.3 and earlier** were published only as GitHub releases
and are not reproduced here: reading them back out of the API means
retyping them, and a hand copy of fifty-one texts is a worse record than a
link to the originals. They are at
<https://github.com/Fade78/lightwebpres/releases>.

---

## Unreleased — 0.47.1

Builds now refuse implicit `sources/`, `templates/` and `language/` symlink
escapes, and optional index fragments and language packs are read through the
same containment guard. The page-script, build-stamp, section and inline-image
scans are bounded so author HTML cannot turn them into quadratic work.

The CLI help now answers consistently for `-h`, `template --help`, and the
options added to `clean`, `template write` and `series slug`. Series metadata
resolution reports the real defaults and supports language-tag and presentation
fields; `audit` reports malformed `series_meta` once and continues as promised.

Presenter sharing and QR dialogs now expose their dialog semantics, keep focus
inside while open, restore focus on close, announce copy completion, and handle
QR generation errors. The inert Scroll action is hidden when its configured
duration is zero, and watch/verify, tag fallback and generated outputs carry
regression coverage.

## v0.47.0

The presenter menu now exposes a Scroll action with a lightning icon. It
toggles between the configured slide glide and an instant `0` ms jump, and
shows the active duration. Configure the default with
`series_meta.scroll_duration` or override it for a build with
`--scroll-duration`; the value is a non-negative integer number of
milliseconds.

Tag selection now rejects a tag with no content on the current page and
falls back to the series default or the first publishable tag, including when
a stale `localStorage['lwp-active-tag']` value is restored.

## v0.46.1

The format glossary and packaged skills now document the effective tag
visibility reports, including article/slide intersections, stable vocabulary,
status counts, default output and read-only inspection commands.

## v0.46.0

`series tags` now inventories the effective tag vocabulary, article status
counts, non-excluded slides and the normal default output. The same resolved
report is exposed by `status` and printed by `audit`; `--tag` narrows the
machine or human inventory without building the series.

## v0.45.10

Overlay transitions now let the presenter-menu, sharing and tag controls
receive their intended clicks, and QR dialogs consume navigation clicks
instead of advancing the deck underneath them.

`audit` now follows build's `excluded` precedence, navigation fingerprints
normalize the default tag, and browser GitLab sync no longer pushes derived
`.lwp-cache` or `.lwp-manifest.json` files. Regression coverage and generated
outputs have been refreshed.

## v0.45.9

The tag filter now keeps incremental builds safe when articles are reordered,
closes its menu without activating navigation underneath it, and accepts
unfinished tag text on slides explicitly excluded from the build. The cache
documentation now describes the runtime tag metadata and article order it
tracks.

## v0.45.8

The incremental build path now applies its draft and output switches
consistently, and `watch` rescans resolved source, template and language paths
so files created after startup remain watched. Presenter-dialog clicks no
longer advance the deck behind them.

The README now distinguishes inline runtime code from copied image assets,
gives portrait reading and landscape presentation equal weight, and documents
the durable slide slugs, explicit series navigation, `--only` side effects,
watch coverage and typography controls. `--inline-images` also refuses quoted
or unquoted relative images left in raw HTML.

The CLI now validates generated manifests before `clean --force`, refuses
symlinked output and tool-owned navigation files that escape their roots, and
does not read a `page_source` symlink before rejecting it. `watch` reports a
failed rebuild and keeps polling, while `init --gitlab-ci` validates the
language value before writing YAML. The guide artefact builder removes stale
files, and the test runner terminates timed-out class processes with their
descendants.

The browser wrapper now rejects ambiguous archive members, releases Pyodide
proxies after each operation, limits its local-server hint to loopback, and
exposes build status and connection errors to assistive technology. The GitLab
tab also provides an explicit way to clear its stored connection data.

## v0.45.7

Fullscreen entry points now share one state-aware toggle. The mouse gesture,
the `F` key, the presenter menu and the navigation button all enter or exit
according to the browser's current fullscreen element.

## v0.45.6

The README introduction now shows real 16:9 presentation covers in the Lava,
Terminal and Pop Lemon themes, after explaining the mobile-first reading mode
and the mouse-driven public presentation mode.

## v0.45.5

Per-article typography opt-outs now follow the language pack selected by each
slide, including long-form articles and deferred notes. `audit` also renders
ignored entries for render-only faults while normal builds continue excluding
them.

The article skill now describes editorial metadata and ignored audit behavior
accurately. Runtime-theme documentation consistently describes the essential
bundle shipped by default.

The README now opens with a featured visual montage of real rendered article
surfaces before the feature list, while retaining the compact catalogue and
the full interactive theme gallery.

## v0.45.4

The contact sheet now captures each preview row while it is visible, then
composes those painted rows into the full PNG; light themes no longer turn
into blank panels in the README image. Print Ink and Print Grey restore a
very light `#F4F4F4` table header, a small paper-saving wash rather than a
dark fill.

The print family now has two Old Press variants. `print-oldpress` is a
monochrome black-ribbon typewriter on white paper; `print-oldpress-red-ribbon`
loads a restrained red second ribbon for kickers, rules and calls. Both use
the same fixed-pitch face for body text, display text, interface text and the
mono register, including slides and their controls.

`build --themes selectors|all` can now embed a compact, standalone runtime theme
selection. The effective theme from `templates/settings.conf` is always the
first choice, and author pins in settings, page styles and declared custom CSS
variables stay in force. On such pages, **C** opens the searchable picker and
**M** opens the presenter menu with the other deck actions; the selection
survives navigation between pages for the browser session.

Runtime selections can also be stored as the root `themes` list in
`series.json`. Slugs, `all`, `essential`, and `X:Y` facet selectors are
accepted; `essential` embeds Monochrome, Monochrome Night and Print Ink, and
the CLI value takes precedence over the JSON list. The catalogue now includes
Monochrome Night, and the menu text keeps its viewport scale on wide screens.

Every build now embeds the essential theme bundle by default — Monochrome,
Monochrome Night and Print Ink — so the reader always has a high-contrast,
dark-ground and print-friendly alternative. The `C` key opens the picker on
any page. `--no-essential-theme` (build/verify/watch) opts out, and
`--themes`/`series.json["themes"]` still add to the set.

The `H` help overlay now always ends with `Compiled with LightWebPres vX.Y.Z`,
with the product name bolded. When runtime alternatives are embedded, its
shortcut list always names `C` as the way to change theme during the
presentation; the picker opens when alternatives have been embedded. The
overlay is now a real modal: it closes on any key or click (not just H and
Escape), the footer is gone, and the `H` line in the help list says "Opens
the help window" / "Ouvre la fenêtre d'aide".

The interface now follows the browser's language when the build did not
explicitly choose one: `fr-*` locales get French and every other locale gets
English. The page embeds both interface vocabularies and changes only marked
interface surfaces at runtime; typography rules remain build-time output.
Passing `--lang` or setting `LWP_LANG` keeps the chosen interface language
fixed. The presenter menu's navigation badges now say `Page Up` and `Page
Down`, while the full arrow and `Backspace` shortcuts remain available to
keyboard and assistive technology.

Choosing Help from the **M** presenter menu now opens that modal without the
menu's closing click dismissing it again. Pages built with
`--no-essential-theme` no longer advertise a `C` picker they do not carry,
and the flag appears in the command synopsis as well as the full option list.

The presenter menu keeps its action boxes the same size on hover instead of
wrapping when a label becomes bold. It is fully keyboard-navigable: focus
starts on the first action, left/right follow a row and up/down follow the
rendered grid rows, `Tab` and `Home`/`End` move through the controls, and
`Enter`/`Space` activate the focused action.

The presenter menu now calls its help action simply **Help** (`Aide` in the
French interface), while the help window keeps its descriptive title. On
small screens, the help panel gives the shortcut and description columns a
2:3 split so the descriptions no longer collapse into a narrow strip.

The share action is now also available directly on **S**, and the help overlay
names that shortcut in both languages. On touch screens, the double-tap mode
switch now gives a localized status toast, so permanent navigation and
auto-hide are distinguishable without guessing from opacity.

The theme picker now has the same arrow, `Home` and `End` navigation, and each
choice paints a resolved theme preview with its background gradient and
matching foreground ink. Presenter-menu actions carry icons and visible
keyboard shortcuts. The lower-right navigation controls now form one column:
from bottom to top, Menu, down, up and fullscreen; the arrows gray out at
their boundaries. Home, sharing and tags live in the menu.
On touch screens, double tap switches between the default auto-hide mode and
permanent navigation.

## v0.45.3

The gallery's labels, colour swatches and theme descriptions now remain a
reading size beside the measured previews, including on the wide desktop
layout. The previews themselves keep their measured rendering size.

## v0.45.2

The gallery keeps its four real theme surfaces at their measured rendering
size, while its labels, swatches and notes now use a larger desktop reading
scale. The generated gallery, guide and contact sheet are regenerated from
their sources.

The source documentation and embedded help use the current seven-role
catalogue vocabulary, describe the fullscreen gesture precisely, and keep
the language corrections in one place.

The print catalogue now keeps its content and panel surfaces opaque white,
including the cover. `print-ink` uses bold without a coloured wash, while the
new `print-boss` theme uses ordinary-weight text under a yellow highlighter,
like a newspaper marked by hand.

## v0.45.1

The print family: three themes drawn for ink and paper, and nothing else.

A theme's ground is painted, never transparent — `print-color-adjust:
exact` forces the paint onto paper, and the contrast measurements are
computed against declared colours, so "print friendly" could not mean
"transparent background". It means a palette drawn for the printer:
pure white `#FFFFFF` ground, ink colours that survive printing, no
veils that need a screen. That is a usage, not an ambiance, so it is
a new family rather than a handful of members spread across the
existing ones — the closed facet vocabulary gains `print`, and
`theme list --family print` narrows on exactly the three.

`print-ink`: pure black on white, a single deep red held in reserve.
`print-grey`: no hue at all — weight, opacity and shape carry the
signal, the same doctrine as monochrome. `print-color`: a blue for the
structure, a green for what is good, a pale yellow highlighter, each
one chosen to survive printing. All three pin their shadows off (the
light family's shadows are shadows of screens, not of paper) and pass
the catalogue's own AA floor on bold fact text.

## v0.45.0

The sources directory is now called `sources/` (it was `articles/` since
the first release). This is a MAJOR break for existing series: the
`lightwebpres init` scaffold creates `sources/`, and an existing series
must rename its directory by hand — the environment variable that points
at it was renamed in lockstep, `LWP_ARTICLES_DIR` → `LWP_SOURCES_DIR`.
What does not change is the `articles` JSON field in `series.json`: the
list of pages keeps its name, as do `page_source` and the `source:`
citation field — only the on-disk directory was renamed.

## v0.44.0

The click is instant, the glide is 200 ms, and a selection is only
ever dismissed.

The left click used to wait 250 ms so the deck could guess at a
double-click — every click felt laggy, and the latency existed to
serve the fullscreen gesture. There is no double-click gesture: a
click lands immediately on the next card and the deck glides to it
over 200 ms, in every mode (reading or fullscreen, the deck moves the
same way). A click that arrives while the deck is still gliding does
not wait — it jumps straight to its target: two clicks in quick
succession land two pages on, a right-click during the glide returns
instantly to the card you left. The glide is the deck's own animation
(requestAnimationFrame, eased), never the browser's `scroll-behavior`,
whose duration varies with the distance and could not be promised.

The middle button is the fullscreen gatekeeper, and the entry is a
two-step gesture. The button alone EXITS fullscreen — entering needs a
LEFT mouse gesture, and the browsers refuse `requestFullscreen()` from
any non-left event (Firefox names the rule in its console; B37), which
is why the button alone can never enter. So: middle button then a LEFT
click within the window enters (the left click carries the gesture the
browser requires), and middle button then a RIGHT click goes Home.
While fullscreen, the middle button exits cleanly and arms nothing —
the click that follows has its ordinary meaning. The wheel itself
keeps scrolling; ⛶ / F stay direct entries. And a two-click jump
leaves no ghost behind: the pair's second click is also the platform's
double-click, which selects the word under the pointer on the card the
deck has just left — a selection the reader never saw, which would
steal the next right-click (copy menu instead of going back). The deck
wipes it with its own motion, at the jump and again on dblclick.

The right button is the
exact mirror of the left, everywhere: it goes back on the index cards
and the series-nav links too (the browser's context menu is gone from
the deck; a selection still owns it).

And a click on an existing selection dismisses it, and only that. The
browser clears the selection on mousedown, before our click event
arrives, so the deck now reads the selection at press time: a click
that pressed down on a highlight is the reader removing it, not a
step forward. Right-click on a selection already belonged to the
reader; the left button now honours the same dismissal.

The index is now a page like any other. The two pages were built by
two skeletons and carried two scripts — the index had its own
navigation, a reduced button set and no share button, so a reader who
moved from an article to the index lost every behaviour they had just
learned. That was an internal split, and the refactor is an internal
one too: the article and the index now share a single page skeleton
and a single `nav.js`, and the index is an ordinary page whose content
happens to be a header, an intro and the article cards instead of
slides (the body carries `class="index-page"`). Because it is the same
script, the index inherits every behaviour the articles have: the same
six buttons (the ↑/↓ pair is gone, replaced by prev/next that move
card by card through the list, exactly as the arrows do), the same
keyboard, the same mouse gestures, the same help overlay, the same
tag menu, the same share popover and QR code — the fiche scope is
disabled there, since there is no current slide, and the slide counter
is hidden, the 0–9 jump has nothing to aim at, and Home means the top
of the page instead of the way back to the index. The QR encoder now
rides on every page. `index_extra` survives untouched: it is still
spliced just before `</body>` on the index only. No existing page
changes structure; what changes is that the index behaves like the
rest of the site.

## v0.43.6

One step, everywhere: the arrows, the buttons and the clicks.

The "step" is one thing on every page now. Arrows, on-screen ↑/↓
buttons, and the left/right clicks all move one step: a whole slide on
an article page (with the incremental scroll inside a slide taller than
the screen and the card-by-card pass on the series-nav slide, §9.3.5),
and one card on the index — where the buttons are the arrows' on-screen
twins, so a click is a card, and the disabled state follows the
journey, not the page. Home clears the card focus and returns to the
top. §8.1, §8.4 and §9.3.5 say so; §8.1's "remonter / haut de page /
descendre" is gone, because the buttons never scrolled the page.

And a selection changes the click, both buttons. A left-click held
into a drag is a selection, not a step — it never advances, and the
click that follows on a selection cancels it (the browser's own
behaviour, which the deck does not touch). A right-click on a
selection opens the browser's menu (copy, search) instead of stepping
back a slide. §8.4 says it in one place now, instead of three
paragraphs that each rediscovered half of it.

## v0.43.5

A right-click on a selection belongs to the reader.

The right button on slide content means "previous slide", and the
native context menu is suppressed to keep that gesture clean. But a
right-click on a HIGHLIGHTED passage asks for the browser's own menu —
copy, copy link, search — and the deck answered with a card backwards,
the same theft the left-button drag guard prevents on the way in. With
a selection present, right-click now opens the browser menu and leaves
the deck where it is; without one, it still goes back a card. Guarded
by the selection, not by the pointer: the long-press on a touch screen
already belongs to the reader (§8.4).

## v0.43.4

The index's arrows walk the cards, and the focus ring is a theme axis.

The index page's keyboard journey was scroll-by-viewport, so a reader
steering it with the arrows never saw what they were pointing at — the
page scrolled, the cards were skipped. The arrows (and the up/down
buttons, which follow the same journey) now step the cards one by one,
exactly as on an article's series-nav slide: the focus scrolls the page
along with it, and Enter opens the focused article. Home clears the
focus and returns to the top.

The focus ring the step uses is a registry axis like the series-nav
one: `card.ring` and `card.ring-width`, measured against the card and
the page (SC 1.4.11), declared on every theme, and painted on the index
cards where the keyboard is pointing.

## v0.43.3

A consistency pass: the documents now say what the tool does.

Three surfaces were reviewed against the executable, and eight findings
came back, all in the prose, none in the code.

README taught a command that fails: `theme show my-series` is refused
by name (a directory is `series theme`, and the same table two pages up
already said so) — the example now uses the form that works. Two
documents called the `--only` flag by a placeholder the help never
uses; both now say `file` like the help and the spec do.

specifications.md §4.4 still listed `full-article` as "0 ou 1" while
its own next paragraph says it is free and §22.8 proves it; the table
now agrees with the prose.

The skill's field table called every slide field optional and then, two
paragraphs down, REQUIRED `slug` on every card — the word "optional"
now carries the exception instead of the reader discovering it. Its
"common mistakes" list still said two `full-article` slides fail the
build, which the body of the skill itself refutes; only `series-nav`
stays. A colour literal is normalized to RGBA with alpha last
(`#RRGGBBAA`), not ARGB, and the index card's title is a `<div>`, not
a `title` attribute — the list of tag-stripping sinks lost the
attribute and gained the reason. And the slide number is engraved on
every slide but the `series-nav`, which is generated furniture, not a
card; measured, not assumed.

The guide's generated HTML is rebuilt from the corrected source, and
the full battery stays green.

## v0.43.2

A click on the ground closes the open window, and only that.

Opening the share popover or the tag menu was a detour that cost the
reader their place: the first click outside it closed the window — and
the same click, on the way out, advanced the deck. The click that
closed the window was the same one that moved the card under the
reader's nose, the moment they asked for nothing. Closing what you
opened is not a navigation, so the click is spent on the close. A
second click, window now closed, navigates as usual. §9.3.4's closing
rule now says so, and §4.3.1 gains the same rule for the tag menu,
which had no outside-click close at all: it now closes on Escape, on L,
on a tag pick, and on a click elsewhere.

The two windows never stack: opening one closes the other, whichever
button opened it.

The test runner learns how long its own tests take, and uses every
core. The battery used to be cut into four fixed batches, so the wall
was as long as the slowest batch and the machine's CPU meter showed the
shape of that: a burst while the fast batches ran, then one worker
draining the long classes alone. Classes are now handed out one by one
to whichever worker finishes first, ordered by the wall-clock each class
measured the previous run — a per-user cache, not a committed list, so
a test that slows down or a new class that is slow are re-learned on
the next run instead of rotting in a table. The run's own log carries
the time of every class and a closing list of the ones that own the
wall, so the battery is its own benchmark.

The wall, measured on this machine: 181 s with fixed batches, 161 s
with the pool and the measured order, and the contrast sweep — one
class, 57 themes, 155 s of wall to itself — is now three shards of
nineteen themes that run in parallel, which brings the wall to 149 s
with the last class at 60 s. The counter class that used to sit idle
under the monolith now absorbs the whole unit battery on the other
workers while the shards finish. On the six-core machine the battery
runs at 121 s, the shards at 60 s each being the floor that decides it.

The runner takes every CPU by default instead of leaving two for the
desktop, and pays for that politeness differently: it nices itself one
step below normal (+5) so the machine stays responsive, with
`--no-nice` to opt out where priority is not wanted.

Documentation and test-suite work; the engine's behaviour is unchanged.

A theme's contrast level stops being written as a standard anywhere in the
project. §9.5.2 stated an admission barème per role, §9.5 said "ce qui est
exigé est double", and the README promised "a documented readability
target" — none of which was ever true of the program, which has never
refused, rewritten, reordered or hidden a theme for what it measures.
Written at that weight, the axis became the frame every reader picked up,
including reviewers who turned it back on the tool and reported, as a
defect, that it "fails the standard it enforces on its output". There is
no such standard. What a theme measures is a design note about that theme.

Delivering a catalogue is a second trade, and the project does hold its
own palettes to its own floor — as their author, in its own test suite,
over the 48 palettes it drew. That guard used to run over all 57 entries,
nine of which it did not draw; measured at the site in question, its own
48 run 5.02:1 to 18.66:1 and the nine borrowed ones 4.51:1 to 14.70:1, so
it sat one hundredth of a point from failing the suite over a decision the
Catppuccin authors made about their own palette. It is scoped to what the
project draws.

Two register entries existed only because of a bar that never existed and
are closed. What survives from them is real and is not about levels: seven
of the nine borrowed palettes are colour schemes drawn for a dark ground
and were shown on a light one, which is a fidelity defect, and four have
been returned to their own grounds.

The repository gets a changelog — this file — on the rule that the entry
under a version heading IS the body of that version's GitHub release,
written once rather than told twice. The reason it exists at all is at the
top of the file, and so is the proof: GitHub's stored copy of the v0.43.0
body has lost the characters that release was about.

Every directory now holds one kind of file. `docs/` held a dated audit, a
build input and a build output at the same time, so the only place you
could learn which was which was a paragraph of prose — and the spec had
been declaring `docs/` to be the audits alone the whole time. The deck the
guide is built from moves to `tools/`, beside the script that reads it,
because it is a build input and corrects like code. The two committed
build outputs, which sat in different rooms, are now peers in
`generated/` — the theme gallery and the guide built with the tool it
describes — along with the gallery's contact sheet. The directory's name
is the instruction, nothing in it is edited by hand, and the root sheds
18.3 MB of generated matter it was carrying unmarked.

Nothing normative moved. `specifications.md`, `GUIDE.md`, `GLOSSARY.md`
and the rest keep their addresses, which are quoted from a sibling
project, from `--help`, and from links already given out.

`BACKLOG.md` becomes `DECISIONS.md`, on six states. The old name was
wrong in a way that showed: a backlog is work waiting to be done, so an
entry that turned out to need no work had nowhere to go and stayed OPEN.
Most of what is in there is not waiting for anything — it is a decision,
with the measurement that made it. Thirty-eight entries carried twelve
status verbs in two languages, spelled twenty different ways — `DONE`,
`FIXED`, `SETTLED`, `CLOSED`, `DECIDED`, `NOTED`, `OPEN`, `EXCLU`, `HALF
FIXED`, `IMPLEMENTÉ ET TESTÉ EN NAVIGATEUR`, `WHAT IS LEFT IS
TYPOGRAPHY`, and one that was just a version number — and between them
they said nothing you could sort by. Each
entry now declares one of six — à étudier, à faire, en cours, terminé,
abandonné, sans objet — on a field line under its title, which is the one
place its state lives. `sans objet` exists for three entries that neither
finished nor were dropped: two were written against a bar this project
does not hold, and one described a defect that stopped being possible.

That register also gets the index its own rules forbade. The rule was
earned — the block that used to sit at its top listed three fixed entries
among the open ones — but it was right about the danger and wrong about
the remedy. A second place to be wrong is only dangerous while nothing
checks it. The index is generated from the field lines by
`tools/decisions_index.py`, and a guard recomputes it and refuses the
suite if the two disagree. Proved by mutation three ways: a state changed
without regenerating, a seventh state invented, an entry left without a
field line.

Sorting the entries by state found a question that had been invisible for
months. B2 was marked settled and carried, near its end, one option it had
not closed — a marker syntax for reaching a verdict class without writing
HTML. Any count by state would have read it as decided. It is B35 now,
`à étudier`, with what B2 ruled out and why. The rule that follows is in
the register's header: what is still open gets its own entry and its own
state, however small.

Re-reading all of it afterwards found one entry closed on evidence that
was not in it. B20 recorded a decision and a design note addressed to a
future lot; the lot landed and nothing came back to say so, so `terminé`
was assigned in this same pass from the work having been done rather than
from anything the entry said — the register's own decay, caught on the
register's own reorganisation. It now carries the measurement: 32 components with a
halo and all four axes each, 128 in all, against the three components and
nine axes it counted.

Asking whether the themes had followed found the other half of the same
entry. They have not: the engine can halo 32 components with four axes
each, and the 13 themes that halo at all use the three anchor points that
existed before the extension, with `dx` used by none. `title2` — the
slide heading B20 exists to name as the worst-served element on the page
— has a halo on no theme, and receives the page's own, resolved once
against the root and propagated as an absolute length. Computed from
`lava`'s declared values at 1920×1080: a blur-to-size ratio of 0.054
where `title1` sits at 0.38. That is B36, `à faire`, and it is theme
work: a theme may decide its atmosphere is uniform, but none of the
thirteen was ever asked.

The deliberation in settled entries was not deleted, which was the other
half of this pass and turned out to be the wrong trade. What makes the
register worth keeping is not the verdicts — those are in the code — but
why the verdict is that one, and an option ruled out and not written down
comes back as a proposal in six months. It stays, under one dated label
instead of the three phrasings it had grown, saying whose day it is and
that its present tense reads as past.

`specifications.md` gets a way in. It is 23 sections and 7 000 lines and
it had no table of contents at all: the only way to find the format, the
commands, the themes or the `series.json` schema was to already know they
are §4, §11, §9 and §20 — knowledge you get by having read the document
you are trying to enter. There is now a generated one, derived from the
headings by `tools/spec_index.py` and guarded like the register's index.
It is fence-aware, which is load-bearing rather than tidy: §4.2 carries a
complete example article whose slide headings are `##`, so read without
tracking fences, "La température change tout" becomes a section of the
specification. The guard was proved on exactly that mutation.

The numbering does not move, and that is measured rather than assumed:
about 1 200 `§N.N` references point at it — 575 inside the document, 308
in the executable and therefore in error messages users read, 219 in the
test suite, 46 in the glossary, 43 in the register, more in the sibling
project. A section number is an address, like a card's slug, and for the
same reason: you do not rename an address you have handed out. So the
reading order is added rather than rearranged. §1.3 is an itinerary — the
steps of writing a series, each pointing at the section that answers it —
and it says why the numbering is frozen so the next reader does not have
to rediscover the arithmetic.

§14, the "parcours utilisateur", was that itinerary's stale ancestor: four
bash snippets at 77% of the way through, written when the tool had a third
of its commands, whose first step was to copy the executable into the PATH
and whose example files came from a series that no longer exists. It now
runs on the current surface — `audit`, `status`, `series slug set`, `theme
show`, `resolve` — and on the same apple-tart example as §4.2 instead of a
second vocabulary. It also stops teaching one thing that does not work:
`verify` builds in memory and compares to the `public/` on disk, so run
just after a build it compares the output to itself and is green by
construction. Its place is CI, or before picking a series back up.

Every section reference in the repository now resolves, and a guard keeps
it that way. There are 1 359 of them — in the documents, in the
executable's error messages, in the test suite — and they are how one
document says "the reason is over there". Nothing breaks when a section
is renumbered, which is why five references to a section 9.2.1 had
survived the rewrite that moved the share matrix to §9.3.4, in three test
files, green the whole time.

The same check found the executable citing, 31 times, the CLI refonte's
design documents — DECISION 1 Phase 2, PROPOSITION 5.10, DECISION-CLI.md
4. Those live in `delete-before-1.0/`, are not distributed, and their
directory name promises they will be deleted. This tool is delivered as
one file people download: someone reading it had no way to resolve any of
those addresses, ever. None was load-bearing — each sat beside a comment
that already gave the reason — so the addresses went and the reasons
stayed. `specifications.md` references are a different matter and stay:
that document ships with the repository.

Writing the guard produced a third rule by failing on itself. Its
docstring cited the two dead references it exists to describe, with the
sign, and the checker counted them as references — correctly, since it
cannot read intent. So: **a dead reference is written without the sign.**
`§` means "go there", and a retired section goes nowhere. The
distinction is worth making in prose anyway, and without it no document
could ever name what it had just fixed.

Two more couplings between the documents and the program are checked
rather than trusted, and both came out clean — the point of measuring
them was not knowing that.

No document tells a reader to type a retired command. Thirteen names have
a canonical replacement kept as an alias for one MAJOR, each printing a
warning `--quiet` swallows, so a document teaching one gives working
output today and a broken command later with nothing in between. Zero
sites here; the sibling project taught retired names for months, which is
why this is a guard and not a note. It matches the invocation, never the
word: `check` and `install` are ordinary English, and one skill says
"check" a dozen times about verifying a fact.

Every field the format accepts is named in `GLOSSARY.md` — 36 of 36 — and
the guard reads the code's own tables rather than a list, because a list
in a test is a third place to be wrong. That file is the vocabulary
contract the GUI binds itself to, so a field it does not name is a field
the GUI has no reason to know exists.

The catalogue gets the typography it was drawn with, four months after
the pass that drew it. 99 values on 31 themes: text and display faces,
the tracking of a kicker, the angle and stops of seven cover gradients,
and a halo on the two palettes built around a glow. `pop` becomes a sans
family, `crimson` an old-style serif, `dread` and `ember` take their
display faces.

**What was left out is the reason this took a measurement first.** The
2026-08 revision delivered 31 property layers holding 541 values, and
they were verified to resolve — then. Resolved against the catalogue as
it stands, they would change between 9 and 49 properties per theme,
because they also restate palettes, leadings, sizes and `nav-dot.*` as
those were before `color.nav` gave the navigation dot a role of its own,
before four borrowed palettes went back to their own grounds, before the
highlighter question was decided. Applied whole, delivering the report
would have been a rollback. A design document is a snapshot; the entry's
own sentence about what was left — faces, tracking, gradients, two halos
— turned out to be exactly the right list, and extracting only that is
what made the pass safe.

On a built page the whole pass shows as nine lines, measured on the theme
the render guard uses. Seven of them are one decision reaching six
variables that take the text face by reference — the reference working,
declared rather than absorbed.

`auto` is no longer a length. It validated, resolved and emitted:
written on a shadow axis, `card.elevation.dx: auto` produced `box-shadow:
auto 1px 8px 0 …`, which no browser parses, so the card lost its shadow
with no build error, no `audit` warning and nothing in `theme show` — a
value surviving every check the tool makes and dying in the renderer,
which is the failure typing exists to prevent.

The fix is smaller than expected because the sweep said so. All 212
length properties reach a CSS context that refuses `auto` — shadow
offsets, blurs and spreads, font sizes, border and ring widths, tracking,
padding, and the two max-widths, whose keyword is `none`. Nothing
defaulted to it, no built-in theme resolved to it. There was no narrower
type missing; there was one value that never belonged. It is refused by
name, with the reason, because someone who wrote it wrote it on purpose.

`audit` puts its warnings on stderr, where §2.4.1 has always said
diagnostics go. All 26 of its own warning sites printed to stdout
instead, which was survivable while audit was the only thing talking and
stopped being so in v0.37.0, when the rendering pass began raising its
warnings through the funnel that obeys the rule. One run then split its
findings across both streams — editorial on stdout, render-borne on
stderr — and nothing said so, so grepping stderr returned half of them.
stdout now carries the count line and nothing else: the command's answer.

Exit codes are untouched; `--strict` gates on audit's own count and never
looked at the stream. What moved is what a person reads.

The guard is on the source rather than on an output — no `print()` of a
`[WARNING]`, `[ERROR]`, `[INFO]` or `[DEBUG]` line anywhere in the
executable — so a site added on a path no test exercises is caught all
the same.

The zip-traversal guard that `web/` defines twice is checked for being
one rule. `_validate_zip_members` sits at module level in both `app.py`
and `git_sync.py`, which `index.html` runs one after the other into a
single Python namespace: the second loaded wins for BOTH call sites,
including the one in the file whose definition was just replaced. Two
copies drifting apart would leave the survivor governing an extraction
the other file believes it is protecting — same name, same signature, no
error, a build that works. §23.1 declared the sharing deliberate and said
nothing verified it; now something does, comparing the two by AST with
docstrings stripped, because what has to match is the rule and not the
prose around it.

`tests/run_tests.py` fetches tags before running. The guard that compares
`VERSION` to the newest tag reads local refs on purpose — a network call
inside a unit test fails where there is no network — and the blind spot
that follows had bitten twice in two days, for six commits and then three.
The runner may make the call the test may not.

The address bar stops naming the first card. Whoever reaches the top of
the page is looking at the page: the URL loses its fragment when the
reader arrives at the first card, by scrolling or by jumping, and keeps
the article's own address — the one worth copying by hand, from the
browser's own URL field. Every other card is unchanged: the bar still
names it, whatever way the reader arrived. §8.4 said the address bar
names the current card, without exceptions; it now says the first card is
the exception, by position and not by type, because a cover sitting mid-
deck is still a card worth a fragment, and a standard card in first
position is not.

The share matrix follows, at the one place it could not. §9.3.4 said a
card's scope is disabled on the cover — "elle se confond avec l'article
lui-même" — which the first-position case had already half-contradicted
("une fiche standard en première position est partageable"): the rule was
about the card's TYPE and the position was doing the real work. A cover
is now shareable like any other card, first position included: the
address bar may hide its fragment, the share matrix does not. The
exclusion that remains is the series-nav slide's, which was always the
real one — its id is not a reading position. The e2e guard that made the
cover the counter-example asserts the opposite now: a cover's copied
link carries the cover's own `#id`.

## v0.43.1 — 2026-08-20

A contrast level is a note about a theme, not a bar it has to clear

The documents had grown a doctrine out of a measurement. A theme's contrast level was written as a standard: §9.5.2 stated an admission barème per role — AAA body text, AA secondary text and accents, 3:1 rules — §9.5 said "ce qui est exigé est double", and the README promised "a documented readability target, checked by measurement". None of that was ever true of the program. Nothing in this executable has ever refused, rewritten, reordered or hidden a theme for what it measures, and the same sections said so two paragraphs later.

Written at that weight, the axis became the frame every reader picked up. It produced two backlog entries about which themes fail a bar nobody enforces, three paragraphs of the spec accounting for which ones fail it, and — the reason this is being corrected now — reviewers who turn it back on the tools themselves and report, as a defect, that a piece of software "fails the standard it enforces on its output". There is no such standard. Deciding what a good theme is was never this software's trade.

So the axis is demoted to what it is. §9.5.2 is no longer "critères d'admission" but how a theme is drawn: there is no bar, the project's own palettes are drawn and then measured, and the measurement is published so an author knows what they are choosing. §9.5's "ce qui est exigé" is gone; a level is not a goal. The README's "readability target" and "higher accessibility standard" are gone; the measurement is a design note about that theme. `--help` says the same in one sentence.

What survives untouched, because it is not about grading: colour is never the only carrier of an information — a comparison table's verdicts each carry a shape marker, and that is a property of the FORMAT no palette can undo. And audit's two colour warnings, which do not speak of levels at all: a navigation control the reader can no longer make out, and text almost exactly the colour of what it sits on. A broken control and words out of reach — things that do not work, never things that could be prettier. Their thresholds sit far below AA on purpose, and they block nothing.

## v0.43.0 — 2026-08-20

A card is called what its author declared, and nothing else.

One rule replaces five. A card's id is the `slug:` line its author wrote. Nothing derives it, nothing falls back to its position, and no ordinary edit moves it — not reordering the deck, not inserting a card, not `tags: excluded`, and not rewriting the heading. That last one is what the derived identity could not hold: it was stable exactly as long as the title was, and a title is what an author retouches. A link you have already given out, or printed as a QR code, now survives everything except you changing the slug on purpose.

`slug:` is required. A card without one stops the build with an error that names the remedy, because someone meeting it for the first time has a series that will not build and no way to guess a command exists to fix it.

Two new commands. `lightwebpres series slug` lists every card of the series and the name it is published under, in text or JSON — `status` answers by article, which is the unit `series.json` describes, and a link points at a card. `lightwebpres series slug set` writes a slug into every card that has none, and only those. It is the one command in this tool that edits your articles, which is why it is a verb you type rather than a flag on the build: a build that rewrote its own inputs would surprise a read-only CI, a version-controlled tree that comes back dirty, and an encrypted series in the browser editor. `--dry-run` says what it would write and writes nothing.

What it writes is random, not derived from your title. Once the value is in the file it IS the identity, and deriving it would make it look as though it still followed the title it came from. Rename it to something readable before you publish: `slug: barrage-de-vajont` is worth more than `slug: 3f7c1a9e`, and the error message says so too.

Two cards on one slug is now an error rather than a silent `-2`. Two values you declared that happen to match are a typing mistake, and a suffix appended in silence would publish an anchor nobody wrote while the card you meant to reach keeps the other.

Gone with the derivation: the Latin-mark folding, the truncated hash, the `sN` and `sN-series` aliases, the collision suffix, and the audit finding about identities that are not durable. The only visible change to a built page is the disappearance of those empty alias spans.

`slug_prefix:` survives, and is now the only thing left that can change what you wrote: it puts a namespace in front of every card id on the page, which is what a series whose pages reuse card names needs.

Also in this release: one rule for the ampersand across both grammars — a `&` outside a tag is escaped, what is inside a tag is left verbatim — so a `source:` line carrying `?q=marks&copy=1&reg=2` no longer reaches the reader as `?q=marks©=1®=2`. A CommonMark autolink is refused by name instead of being blamed on a tag nobody wrote. `--build-stamp` is legible on every theme. And the shell completion offers each command only the options that command accepts, on every typed path.

> **The published body of this release is not this text, in one sentence.**
> The paragraph above ends on the example that gives the release its point:
> a query string carrying `&copy=1&reg=2` used to reach the reader as
> `©=1®=2`. GitHub's stored copy has resolved both entities, so it reads
> `?q=marks©=1` twice and the before and the after are the same string —
> the release announcing the ampersand fix lost its ampersands. The text
> here is the one that was written, with the example intact. It is also
> why a release body that exists only on a hosting service is not a record.
