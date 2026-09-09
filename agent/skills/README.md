# Two Skills, Different Roles

LightWebPres distributes a product skill and an optional editorial method.
They answer different questions and do not have the same status.

| | `lightwebpres` | `sourced-presentation` |
|---|---|---|
| Purpose | Use the tool and write its exact format | Plan and verify sourced editorial work |
| Answers | What does the engine accept, and how do I carry out this task safely? | How do I research, structure and verify this presentation? |
| Status | Part of the product | An optional method offered with it |
| Tracks | The executable and specification | Externally maintained editorial practice |
| If omitted | An agent may guess the syntax or workflow incorrectly | No build requirement is violated |

## The Product Skill

Start at [lightwebpres/SKILL.md](lightwebpres/SKILL.md). Its compact mission
entry covers creating content, organizing a documentary collection, designing
and composing identities, reading/presenting/sharing, publishing/maintaining,
and integration/automation. Diagnosis and validation apply across these
missions. A workflow describes what to do within the user's authority;
it does not grant permission to publish, delete or push.

Load the relevant reference, not the entire package by default:

- [Article Format](lightwebpres/article-format.md): `lwp:meta`, every slide type and field, cascades, slugs, comments and speaker notes.
- [Series and Appearance](lightwebpres/series-and-appearance.md): `series.json`, order, statuses, tag visibility, languages, presets, themes and kits.
- [Text and Style](lightwebpres/text-and-style.md): the limited Markdown converter, images, source notes, typography, instance tags and raw-HTML hooks.
- [Operations](lightwebpres/operations.md): scoped editing, composition, diagnosis, validation, preview, maintenance and automation.

The executable remains the version authority. Use its `--help` and live
`contract` instead of maintaining another CLI or parser schema. The skill's
coverage tests follow Markdown references reachable from the entry, check
parser fields and per-type table rows, reject invented example fields, and
confirm the documented manual styling hooks exist in the composed stylesheet.
An orphan reference does not count as coverage.

For the human walkthrough, use a local `GUIDE.md` when a checkout is available,
or the [canonical guide](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md).
The mission entry links to the guide's six task routes. This skill is for
using the product, not contributing to its engine.

## The Optional Method

`sourced-presentation/SKILL.md` is an editorial method, not the LWP format
contract. It covers short cards that stand on their own, backed by a fully
referenced long-form article, from research through verification at sources.
Use it when that method fits the brief. It can help experienced authors or
those wanting a repeatable process, but LWP does not enforce its rules.

A series' own instructions define audience, scope and editorial conventions.
Neither local rules nor a successful build make a false claim true or justify
misleading omissions. Keep factual verification separate from format checks:
`active` is participation, not approval, and theme measurements are not a
design certification.

The method copy is maintained outside this repository and carries its own
`metadata.version`. Compare that version when checking freshness. Do not
rewrite the method as part of a parser or product-workflow documentation change.

## Install And Update

Copy the **entire `lightwebpres/` directory**, including all four reference
files, into the skill location supported by the agent host. Do not install
only `SKILL.md`. Its internal links are package-relative, and its external
guide/specification links work without a repository checkout. No particular
agent configuration directory is assumed.

Install the optional method separately if wanted; it is not a dependency of
the product skill. The skill does not install the executable or confer access
to a hosted service. The tool and its documentation are available at
<https://github.com/Fade78/lightwebpres>.

Update the product entry and references together when the executable's
contract changes. Keep the method's independently maintained version separate.
