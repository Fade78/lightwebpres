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

## Unreleased — 0.43.2

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

`tests/run_tests.py` fetches tags before running. The guard that compares
`VERSION` to the newest tag reads local refs on purpose — a network call
inside a unit test fails where there is no network — and the blind spot
that follows had bitten twice in two days, for six commits and then three.
The runner may make the call the test may not.

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
