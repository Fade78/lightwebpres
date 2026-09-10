---
name: lightwebpres
description: >
  Use LightWebPres to create or edit LWP articles, organize series and tags,
  select or compose presentation identities, diagnose builds, and integrate
  or maintain a publishing workflow. Supplies the exact article grammar and
  bounded references for series.json, text conversion and appearance. Use
   when a task mentions LWP, fact-box, highlight, series-nav, full-article, unit-index,
  or a project has series.json and a lightwebpres executable. Not generic
  Markdown, an editorial research method, or permission to publish.
---

# LightWebPres

Turn the user's requested change into valid LWP sources and checked output.
LWP builds scrollable slide-deck articles with optional long-form text from
one deck `.md` per article. It is a single Python 3.8+ standard-library
executable, published and downloadable at
<https://github.com/Fade78/lightwebpres>. If it is absent, ask before assuming
an installation or downloading one. Use the current executable, not remembered
syntax from an older installed skill. A logical content unit groups a deck
and its supporting text, independently of physical HTML output. Persisted
`articles[]`, `page_source`, `page_dest` and related names remain canonical,
not aliases. The live draft schema is `lightwebpres.slide-draft/2` with five types.

## Start With Scope

Identify the series directory, requested result, source files, output path,
language and existing presentation choices. Inspect the relevant files and
read-only reports before changing them. A request to write, diagnose or
preview does not automatically authorize publication, deletion, push,
credential use or overwriting another owner's files. Confirm those actions
when they are not already explicit in the task.

The author owns `sources/`, `series.json`, settings pins, custom CSS and
deliberately installed overrides. The tool owns generated HTML, build
manifests and cache state. Change sources, then regenerate authorized output;
do not patch rendered pages. A local `nav.js` or language-pack override stops
following the embedded version's fixes. See [Operations](operations.md).

Load only the reference needed for the mission. These four files travel
with this entry when the whole `lightwebpres/` directory is copied:

| Reference | Read For |
|---|---|
| [Article Format](article-format.md) | Deck anatomy, metadata cascades, every slide type and field, slugs and speaker notes |
| [Series and Appearance](series-and-appearance.md) | Registration, order, status, tags, scoped/named selectors, languages, presets, kits and runtime choices |
| [Text and Style](text-and-style.md) | The exact converter subset, images, source notes, typography and styling hooks |
| [Operations](operations.md) | Scoped workflows, diagnosis, validation, composition, maintenance and automation |

## 1. Create Content

Inputs: the brief, local editorial rules, authorized source files and assets.
Read [Article Format](article-format.md), then [Text and Style](text-and-style.md)
for the body features you need. Use the engine's `contract` for draft
skeletons and live field rules; fill or remove unfinished placeholders.
Edit only the agreed article scope. Register a new article only when the
task includes adding it to the series. Validate and inspect a local render;
writing an article is not authorization to publish it.

Human walkthrough: [Create content](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#1-create-content).

## 2. Organize A Documentary Collection

Inputs: the selected series or corpus, desired order, statuses, tags and
languages. Read [Series and Appearance](series-and-appearance.md). Inspect
`status`, `series tags` and effective slugs before editing `series.json` or
article metadata. Keep URLs stable and compare visibility intersections after
the change. A corpus spanning series is an editorial organization, not an LWP
database. `status` is participation, **not approval** of facts or publication.

Human walkthrough: [Organize a documentary collection](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#2-organize-a-documentary-collection).

## 3. Design And Compose Identities

Inputs: the intended identity, available resources, target kit/version and
authorized catalogue or series destination. Read [Series and Appearance](series-and-appearance.md)
and [Operations](operations.md). Change the smallest appropriate layer:
instance, article, series settings, theme or structural kit. Composition
needs an explicit recipe and produces an autonomous kit, not inheritance.
Inspect actual content and runtime alternatives; contrast measurements and
compatibility filters are not accessibility or brand approval.

Human walkthrough: [Design and compose identities](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#3-design-and-compose-identities).

## 4. Read, Present And Share

Inputs: the built page, audience, intended viewport and sharing destination.
Use [Operations](operations.md) for local inspection, presentation, print and
stable links. Check tag selection, appearance alternatives, note bodies and
PDF layout on the real output. Local preview or generating a shareable link
does not authorize uploading files, sending the link or exposing a repository.

Human walkthrough: [Read, present and share](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#4-read-present-and-share).

## 5. Publish And Maintain

Inputs: the approved output destination, build options, deployment scope and
any requested upgrade. Follow [Operations](operations.md). Diagnose first;
review overrides before template maintenance and inspect a cleanup plan
before any authorized deletion. Publish only the intended output and assets,
not sources or secrets. Deployment and Git push require their own authority.

Human walkthrough: [Publish and maintain](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#5-publish-and-maintain).

## 6. Integrate And Automate

Inputs: the client or CI environment, supported engine version, paths and
allowed side effects. Follow [Operations](operations.md); discover options
with `--help` and consume the versioned `contract` rather than duplicating
the CLI or parser schema. Use JSON only on reports that support it. LWP does
not provide native AI authoring or an MCP service; an external client owns
those integrations, credentials, approval gates and upstream sanitization.

Human walkthrough: [Integrate and automate](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#6-integrate-and-automate).

## Guardrails Before Editing

- The field-to-prose switch is **one-way** within a slide. Put all fields first; scalar values occupy one physical line. Only slide `comment:` and `note:` support indented continuation.
- Fields are values, not Markdown. Raw HTML is trusted and passed through, including scripts. Sanitize untrusted input upstream; the build is not a security filter.
- Free text uses the documented LWP subset, **not generic CommonMark**. Markdown links require HTTP(S); `---` splits a deck, not a visual rule.
- Every card needs a stable `slug:`. Only standard slides accept a free body; `full-article` references a separate file without LWP markers. `unit-index` generates a list, not prose.
- Index `*` includes every supplied published slide, including itself. Literal tags have no reader shared-default magic; selectors do not replace global publication filters.
- Speaker `note:` content is public in the HTML, even when hidden from normal view. `comment:` stays out of generated pages, but not out of a published source repository.
- Keep research and editorial approval separate from format validation. An optional, externally maintained `sourced-presentation` skill can supply a method; it is not a build requirement.

## Common Mistakes

- `page-title:` is not `page_title:`; unknown meta keys can build silently. Run `audit`.
- `tag:` is not an alias: use `kicker:` for a visible label and `tags:` for filtering.
- `page_source`, `page_dest` and a full-article `article:` target are bare filenames, not paths such as `sources/x.md`.
- Close code fences; write actual characters rather than entities such as `&rarr;` in ordinary text.

## Verify The Result

For diagnosis and validation, read [Operations](operations.md). `--dry-run`
journals planned effects; it is **not proof of rendered output**. Plain
`audit` reports warnings and render failures without failing; `audit --strict`
makes them a CI gate. Read findings, then build and inspect within scope.
`verify` compares existing output with an in-memory rebuild using matching
supported flags, including `--unit-index`, `--unit-index-max-columns`,
`--unit-index-selector`, `--single-html [FILE]` and `--inline-images` when
used. Report commands, options, findings and any unperformed visual or deployment
checks; never call an unbuilt draft verified.

If a checkout is available, use its local `GUIDE.md` for the mission routes
above and `specifications.md` for normative details. Otherwise use the linked
canonical guide and [specification](https://github.com/Fade78/lightwebpres/blob/main/specifications.md).
Do not infer a checkout location from where this skill is installed.
