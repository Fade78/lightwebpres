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
the typography rules and their opt-outs, the instance tags.

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

It ships alongside as a **facilitation**, for whoever would like a method
and does not have one. It is an offered interface, not the core of what
LightWebPres does.

**LightWebPres is for people who already know how to write.** It renders
what you give it and has no opinion about how you got there: no rule here
is enforced by the tool, nothing in it is checked at build time, and a
series that follows none of it builds exactly the same. Take it or leave
it.

> The same separation runs through the whole project. The theme system
> renders a theme; it does not teach you to design one. The format
> renders an article; it does not teach you to write one. Each layer does
> its own job and declines the one above it.

---

## Which to load

- **Writing or debugging an article** → `lightwebpres`. Always.
- **Also want a method for sourced editorial work** → add
  `sourced-presentation`. Optional.
- **A series with its own written rules** → those rules win over
  `sourced-presentation`, always. It says so itself: the series sets the
  thresholds, the skill sets the method, and anything written nowhere is
  decided by the skill.

## Keeping them current

Both are plain Markdown with a YAML front matter carrying a `version`.
`lightwebpres/SKILL.md` changes when the format does, and the test suite
will tell you if it lags. `sourced-presentation/SKILL.md` is maintained
outside this repository and synced in; its version number is the one to
compare when you wonder whether a copy is stale.
