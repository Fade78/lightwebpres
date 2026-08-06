---
name: sourced-presentation
description: "Produce a sourced presentation for an editorial series: a deck of short cards, each readable on its own, backed by a fully referenced long-form article — either a reversal, confronting a widespread belief with what is established, or an exposition of a subject the reader has never had the pieces for. Covers the whole chain — commissioning research, verifying every fact at its source, writing, re-reading, cross-checking deck against article. Load before writing, revising, verifying or re-reading either one, and before inserting a presentation into an existing series — including for a small touch-up, since it opens on how to locate yourself in work already under way and on what each kind of edit invalidates. Does not cover a given series' settings (audience, lengths, format), which live in its own specification."
metadata:
  version: "0.13"
---

# Sourced presentation — method

A **deck** of short cards, one fact each, backed by a fully referenced **long-form article**.

Two forms. A **reversal** takes a widespread belief and confronts it with what is established. An **exposition** lays out a subject the reader has no belief about, because they have never had the pieces. Everything that follows applies to both; where it does not, the difference is stated.

The deck is what gets read; the article is what makes it defensible. **The article is the source of the cards, never the reverse** — a card with no backing in the article is an assertion with no file behind it.

**The series sets the thresholds; this sets the method.** Audience, register, lengths, field syntax, numbering, the placement of hedging, what counts as one fact: these and their like belong to the series specification. A written series rule overrides one here, and what is written nowhere is decided here.

*What follows is what had to be discovered — not general craft, which you already have. Rules that look deducible from a stated principle mostly are not: they look that way once known. Compressing them out is the standing temptation here.*

**Verification is asymmetric: fifty facts confirmed do not offset one quotation with no source.** A reader who catches one error is right to doubt the rest — they cannot check it, and have just learned they should. *A check reported as done is itself a claim: never report one you skimmed, say what you left unverified.*

## Where you are

**Read the state from disk, never from memory.** The file of facts, the article, the deck and the spec each record what has been decided; a summary of prior work does not. *A session that trusts its own recollection re-decides what was settled and leaves what was pending.*

**Two situations, and they are not the same work.** A page that does not exist yet runs the chain below, once, in order. A page that exists is never on a step — it is in a state that something just changed. Find what changed, then run what that change invalidates.

**The chain is the first pass. Nothing after it is a first pass.**

## The first pass: the chain

1. **The target.** For a reversal, the sentence the reader holds true. For an exposition, the question they cannot answer and why they have never had the pieces.
2. **Adversarial research.** Commission a synthesis demanding both sides and exact statuses.
3. **The actor's own sources**, when there is one.
4. **The file.** Every candidate fact gets a dated verdict.
5. **The article.**
6. **Verification against the sources**, after writing.
7. **The cards**, derived from the article, then **cross-check cards × article**.

Each step writes to disk before the next. **Steps 6 and 7 each catch defects the other misses**: the article alone hides a card promising what it doesn't deliver; the cards alone hide an article claim with no source.

**Where a belief comes from dictates where its sources are.** A claim an actor makes — start from its own documents. A belief a design induces without anyone asserting it — the mechanism is the evidence. A belief kept alive by repetition — the stale source is itself a finding. An ordinary intuition — only research can qualify it.

**For a reversal, the research may confirm the belief.** Then the article says so, and the deck opens on what the belief gets right before what it misses. *Forcing a reversal the evidence does not support is the worst failure available to this method.*

**Where the article makes a new allegation about a named actor, its response is sought**, and that response is itself a fact for the file — a fact about what the actor answered, not about whether the charge holds. *Reporting published material and existing research does not trigger this; formulating a charge does.*

## What a change invalidates

**Every edit invalidates something, and the something is rarely local.** Find the row, run the column.

| What moved | What re-enters |
|---|---|
| A fact in the article | verification against its source; the cross-check on every card carrying it |
| A card | the cross-check on that pair |
| A quotation, anywhere | its status; every other page quoting the same source |
| A correction, anywhere | the same defect across the corpus — a defect found once is a sample |
| A page inserted or removed | every count, cross-reference and ordering claim in the series |
| A section renumbered | every reference to a section number, in both halves |
| A rule added to the spec | every page written before it |
| A tool version | what it now composes, what it stopped reading |

**The last two rows get skipped.** A rule added mid-series governs what comes after it and is never applied backwards; a tool that changes how it builds leaves the old configuration in place, silently. *Both end with a spec describing a minority of its own pages.*

**A correction creates.** Rewriting a card to remove a repetition can install a contradiction with its own proof; shortening a quotation to fit can drop the modality that made it exact. Re-read what you just changed, against the half you did not change.

## The file of facts

**No fact enters the article without a dated verdict** — confirmed, qualified, alleged, rejected. *What counts as one fact rather than two is the series' to fix, and everything downstream depends on it: a card carries one, a deck announces how many.* Record rejections, or they come back next session. Date them, or a fact checked six months ago enters as though it were current.

**A commissioned synthesis is a list of leads, not a file.** It invents specifics — venue, year, sample size — and contradicts itself between body and notes, on central claims. Re-check every figure at the source.

**Then check it against the axes you asked for.** Checking figures cannot reveal a missing axis: the figures are right and the coverage is short. A second brief on the same subject regularly returns what the first left out.

**When the source itself is ambiguous, say so in the note.** A possibly wrong reference is worse than none.

**A report of a source is not that source.** A news piece citing a study, a summary citing a ruling: the chain is followed to its end, and where it cannot be, say which link you stopped at.

**A quotation attributed to a named person is traced to where they said it** — an interview, a talk, a text — one carrying a figure most of all. *Each repetition cites another, and a striking phrase circulates for years without a first utterance. Found none: give what the person is documented as saying, and why the other is dropped.*

**For a study, verification reads the body and the method, not the abstract alone.** An abstract states an association the body restricts to one condition — the figure is right and the claim is not.

**A fact the article leans on is checked for replication.** Has anyone repeated the study, and found what? A single experiment can be sound and still not generalise: failed replications outside its original conditions do not refute it, they **bound** it — and the bound is usually more useful. *Ask it of every load-bearing fact, not the striking ones.*

**Record what funds a source and what ties it has.** Industry funding does not disqualify peer-reviewed work; it changes its weight, and the reader decides only if told.

**A translated quotation is marked as translated and checked against the original.** Translating is interpreting, and the reader cannot see where the interpretation was made.

### Which source wins

**Peer-reviewed work is the default; what follows modifies it, not replaces it.** Review has already applied much of what this section asks — method, effect size, declared limits, competing results — and a study gathers many rulings and incidents into one perspective, which no single one of them can.

**Within that default, rank by what the statement cost the one who made it.** Review and cost answer different questions: a study is better on what is generally true, a ruling or an admission on one case. *A paper does not settle what a company did in one month; an admission establishes no general effect.*

**A statement against its author's interest is the strongest thing a file can hold.** A concession, an admission, a figure that damages the one naming it. Nobody produces these by accident, and nobody produces them to look good.

**Next, what was said to an audience other than your reader**, who was not meant to see it. The audience had to be told something solid enough to act on, and the flattering version was not the one on offer.

**Then what has been adjudicated over what has been alleged**, a body that heard both sides being worth more than a filing that heard one.

**A statement that serves its author sits at the bottom, whoever the author is.** The accused defending itself, the vendor sizing its own market, the campaign group sizing the problem it exists to fight. *The last gets waved through, its conclusion being the one you already hold.*

**Ranking decides which claim leads and which yields in a conflict. It never licenses dropping the weak source in silence** — say what it is, and let the reader weigh it.

**Where cost to the author is equal, the more specific and better dated wins.** A dispatch repeating stale boilerplate loses to one citing a source on a given date.

**When neither can be dated, report the disagreement rather than picking**, and say the change cannot be dated.

### The research prompt

Written before searching. It carries:

- **Named axes**, one per substantive question.
- **Both sides per axis**, naming who holds each position. *An exposition has no camps: ask instead for the strongest finding and the strongest qualification of it, so the brief does not manufacture a controversy.*
- **Each study with its identifiers and its status** — authors, year, venue, design, sample size, finding, and whether it is peer-reviewed, a report, journalism, a company statement or a ruling. *Without the identifiers it cannot be re-checked, which is the point of asking.*
- **What is NOT established, stated explicitly.** Without this, a synthesis fills gaps.
- **Exclusions**, against overlap with what is covered elsewhere.

**Force the counter-case on the axis where it costs most** — a charged subject returns one-sided unless required by name.

**Check what the exclusions cut.** A domain excluded as "covered elsewhere" carries off neighbouring questions covered nowhere.

**Word the axes so an absence of measurement is an acceptable answer**, and reported as one.

## The actor's own sources

*When an identifiable actor is in question. An exposition, or a belief no one asserts, has no such source and this section does not apply.*

**A contradiction between two of the actor's own documents beats any outside accusation** — it cannot be accused of its own words.

**What makes those documents strong is their audience, not their author.** They were addressed to advertisers, investors, recruits — people who had to be told something solid enough to act on, and your reader was never meant to see it. *A statement the actor makes while defending itself is addressed to everyone, and is a different kind of evidence.*

**Look for the pages not addressed to your reader.** An organisation says one thing to its users and another to its customers, both publicly.

**Its own words cut both ways.** A claim that presents it well is carried like any other — verified where it can be, and given its status where it cannot: a statement nobody has audited. *Quoting a document only where it incriminates builds a prosecution out of primary sources, and the reader cannot see the selection.*

**A defensive response is evidence of what the actor chose to defend, not of what is true.** An organisation under accusation is obliged to answer: weighing that answer against the charge as though both were testimony dilutes a sound finding. Read it for what it does not contest, and for what it selects. *Defending eleven points of twelve concedes the twelfth, and that concession is the fact.*

**The exchange does not end at the response.** What the accusers said back is part of the file, and finding it is a separate search. *Stopping at the reply leaves the last word with the party under threat — an artefact of your search order, not of the evidence.*

**Read a guarantee to its exact scope.** "We do not sell" is not "we do not hold": what is held is exploited otherwise, can leak, and falls under a jurisdiction.

**Archive the dated text, not just the address** — these pages change.

## The article

**Two placements for hedging, and the series chooses.** *Distributed*: every claim carries its degree of certainty where it stands, and a limits section consolidates only what cuts across the file. *Concentrated*: the body states plainly and one section holds every reservation — which suits a series whose cards must not moderate one another, since a card carrying its own hedge moderates the deck.

**Under either placement, a limits section never walks back what the body overstated.** And the status of a claim — alleged, measured, declared — is not hedging: it travels with the claim, always. *A card says « a complaint alleges », never « though this rests on one study »: the first is what the fact is, the second what the article thinks of it.*

**Hedging every sentence asserts nothing; hedging only at the end asserts too much**, and takes it back where fewer readers go.

**The article's scope clearly exceeds the deck's**, and it develops every fact a card will carry. An article that merely expands its cards gives them nothing to stand on.

**Sourcing is checked after writing** — a claim added mid-draft escapes the attention that wrote it.

### What makes an article false without making it inaccurate

**A wording that alarms wrongly is as false as one that reassures wrongly.** Denying a specific protection makes the reader conclude none exists. Find the axis that describes the situation rather than the one that negates it: rarely "protected or not", usually "protected against what, and by whom".

**An absence is reported, and never upgraded.** A control that doesn't exist, a figure an actor publishes on everything but one point: these are findings. But "we did not find" is not "it does not exist" — saying so changes the claim's status.

**A decimal is information from a count or a declaration, decoration from a model, a median or a projection.** A modelled figure given to two decimals while its range spans an order of magnitude measures nothing: it reassures. Give the order of magnitude and say it is one.

**Check that a result applies to the case at hand.** A rate obtained under given conditions does not transfer elsewhere unsaid. Extrapolation is the hardest defect to see from the position that writes it, because the figure is exact and the source real.

**Source the counter-case at the level of the accusation**, by what its claims cost their authors and not merely by document type. An article whose second side rests on journalism while the first rests on peer-reviewed work is a prosecution dressed as balance — and one whose second side rests only on the accused's own defence is the same fault mirrored.

**A claim's status belongs in the text, not only the note** — complaint or decision, allegation or judgment, statement or audit.

### What the article never does

**Self-certify.** "An honest article keeps findings that trouble it — this one does" states a norm then claims to meet it; any manipulative text can write it. A rule one imposes on oneself can be checked; a quality one claims cannot. *This defect recurs despite the rule, disguised as modesty. Look for it explicitly.*

**Tell the reader what to feel.** The article describes the object and the state of knowledge; the reader judges. *The series says whether its subject and audience require further care.*

**Talk about itself in a factual section.** *Exception: a section whose subject is the article, such as the one presenting its sources.*

## The cards

A card carries **one fact**. Its title asserts it, its stake says what it changes for the reader, its proof establishes it impersonally and without restating the stake.

**A hedge in a title is a card that hasn't found its fact.**

**A title promises nothing the proof fails to deliver**, and a figure does not restate the title in another form — a count spelled out then given in digits is the same fact twice.

### Every unit reads alone

The reader **enters anywhere**: skims, skips, returns. **A card assumes nothing it has not itself supplied.** Four cases, none of them obvious from the principle:

**An acronym is expanded once per article, not once per series** — nobody reads in order.

**Function before brand**: what a technology does, then its name. Naming it first and glossing after leaves the reader holding a label.

**A venue name validates nothing** for a reader who cannot place it, and it reads as though it did. The text carries what makes the study solid — its size, its method, who ran it; the venue belongs in the source line.

**A bare notation says nothing.** What the intended reader has been taught is explained rather than deleted — the number with its magnitude; what they haven't is translated. *A figure kept "for precision" that means nothing to its reader is decoration.*

### Composing the deck

**The opening comes first, and nothing precedes it** — not method, not context, not sources. A reversal opens by attacking the belief; an exposition opens on the most surprising fact rather than the most important — or, when nothing surprises, on the one that makes the rest legible. The opening decides whether the reader continues.

**It sometimes takes two cards.** A claim and the evidence establishing it are one move: anything inserted between them breaks the argument in half.

**The sources card comes after the opening, never inside it** — the reader doesn't ask where facts come from until one has surprised them.

**That card answers differently for each subject**, because each domain imposes its own investigative method — what was obtained, tested, ruled on or published, and by whom. An interchangeable sources card is filler: the reader learns to skip it.

**It is also the one place to state the file's limits** — a preprint, an editorial expression of concern, a conflicted vendor, a single source — without breaking the argument's thread.

**Between the opening and the close, the cards escalate by default**: what the reader lives, then the mechanism behind it, then what has been measured, then what is structural. Order carries the argument — a deck sorted by how strong each fact is reads as a list. **When the subject imposes another order** — a legal threshold before the mechanism it governs — that order prevails.

**The last card that carries a fact is one of agency, never a threat.** *Apparatus may follow it — a series index, the long-form article itself — and that is fine: the reader who scans stops at the last card that says something.* It carries a fact: a real right, a setting that exists, a check within the reader's reach — never an exhortation, which cannot be verified, and which the reader can only obey or refuse. *When no lever exists, saying so beats inventing one.*

**A deck written after the article inherits its facts and loses its hedges.** Announced becomes did; we found no study becomes none exists — a short form drops the hedge first. *Check the pair at each derivation: the card was true when written, and the article moved.*

**An announced count is exact, and the series fixes what it counts.** A tool may count a different set, and the two will never coincide. *Two defensible conventions differ by one on every deck at once: check that the spec and the tool agree.* Recount at every addition.

## The re-readings

Five passes, none replacing another. **On a first pass, all five. On a return, whatever the invalidation table sends you to — plus the corpus pass whenever a property was touched on more than one page.**

**A check that needs judgement runs from a list, not from a pattern.** Enumerate what must be examined — every load-bearing fact, every named quotation, every single-study claim — then walk it. *Pattern checks finish; judgement checks stop at the salient cases and feel finished. What is greppable gets done in full, what matters in part.*

**The article alone**, read continuously, after any series of edits including purely lexical ones. Pattern checks skim usefully; **what the reading catches is not locally detectable** — a duplicate, a broken sequence, a reference gone stale after a title changed elsewhere. Editing by successive replacement produces duplicates mechanically, each insertion ignoring its neighbour.

**The cards, one by one**, against the card rules and the deck composition — and the article against the list of what it never does, self-certification first, since that one reforms despite its rule.

**At least one pass runs without the draft in view, from the sources alone.** Re-reading one's own text recognises what it meant to say; reading from the sources finds what it failed to say. *This is not step 6 of the chain: that one asks whether each written claim matches its source, this one asks what the sources hold that the article never used. Verifying and finding an omission are different operations, and doing one does not do the other.*

**The cross-check.** Three questions. Is every figure in a card found in the article? Does any card assert more than the article does, limits included — shortening a fact hardens it? Is every claim a card repeats actually sourced in the article? Unsourced claims surface here; in the article alone they blend into referenced text.

**One pass runs across the corpus, on one property at a time.** Some defects have no local form: a sentence on every page reads as apparatus from any one of them. *A reader given one page cannot know the sentence is not that page's.* Take one property, walk every page on it alone.

## What breaks silently

**A bulk operation reports its successes, never its misses, and a check narrower than what it checks passes silently.** Renumbering after an insertion is the type case: the pattern matches one written form, leaves the other, and two items share a number.

**Verify the result — the whole sequence, the whole set — not the operation's report**, and prefer a broad pattern you read to a narrow one that skims.

**Read what the operation produced, not merely that its target is gone**: a substitution can remove every occurrence you searched for and leave malformed text where it struck.

**A defect found once is a sample, not the defect.** Before recording it fixed, search the class it belongs to, across every page and both halves of each. *Search the class, not the string: a vendor removed by name survives as three other vendors. And the article is the larger half and the less examined — a term fixed in the cards survives there for months.*

**An insertion stales the pages describing the series**: lists, counts, numbered references, reading paths, recommendations citing comparable cases. They don't announce themselves.

**Working notes are written in the reader's language** — an internal term written a hundred times ends up once too often in an article.

**A correction made after publication is visible and dated.** Correcting silently leaves a reader who checked yesterday holding a claim the file no longer makes, and destroys the verifiability everything else here builds.
