# The two skills, and what each one is

Two packaged skills ship with LightWebPres. **They do not have the same
status**, and mistaking one for the other is the easiest way to
misunderstand what this tool is.

| | `lightwebpres` | `sourced-presentation` |
|---|---|---|
| What it is | the **format reference** | a **method**, offered |
| Answers | *what is the exact syntax?* | *how do I go about it?* |
| Status | part of the product | a courtesy, given with it |
| If you ignore it | you will guess the syntax wrong | nothing breaks |
| Tracks | the parser, exactly | editorial practice |

---

## `lightwebpres/SKILL.md` — the format

This one is **the tool's own contract**. It describes what the parser
accepts: the `lwp:meta` block, the four slide types and their fields, the
one-way switch from structured fields to free text, `series.json` wiring,
the read-only `status`/`series tags` visibility reports, the typography rules
and their opt-outs, and the instance tags.

It is written so an agent can emit a correct article without guessing,
and it is kept in step with the executable — the test suite asserts that
it names no field the parser does not know, and that every styling hook
it promises is really in the composed stylesheet. If the format changes
and this file does not, the build goes red.

Read it, or point an agent at it, before writing or debugging an article.

## `sourced-presentation/SKILL.md` — a method, and only that

This one is **not part of the product**. It is a method for one kind of
content — a deck of short cards, each readable on its own, backed by a
fully referenced long-form article — covering the chain from commissioning
research to verifying every fact at its source.

Use it to plan a series, make each card understandable on its own, connect
claims to checked sources, and verify the delivered presentation. It can
help experienced writers as well as people who want a repeatable method.

It remains optional. LightWebPres renders what you give it: these editorial
rules are not enforced at build time, and a series that follows none of
them builds exactly the same.

> The same separation runs through the whole project. The theme system
> renders a theme; it does not teach you to design one. The format
> renders an article; it does not teach you to write one. Each layer does
> its own job and declines the one above it.

---

## Which to load

- **Writing or debugging an article** → `lightwebpres`. Always.
- **Also want a method for sourced editorial work** → add
  `sourced-presentation`. Optional.
- **A series with its own written rules** → use those rules for audience,
  format, scope and editorial conventions; use `sourced-presentation` for
  the method. Local rules cannot make a false claim true, remove necessary
  qualifications or justify a misleading omission. Check claims against
  evidence even when a local convention asks for a simpler story.

## Keeping them current

Both are plain Markdown with YAML front matter. `lightwebpres/SKILL.md`
changes when the executable format does and is checked by the test suite;
the executable and specification are its version authority. The
`sourced-presentation/SKILL.md` copy is maintained outside this repository
and carries its own `metadata.version`, which is the number to compare when
you wonder whether that method copy is stale.
