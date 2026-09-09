<p align="center">
  <img src="web/lwp_banner.svg" alt="LightWebPres: Markdown in, publish-ready pages out" width="100%">
</p>

# LightWebPres

**Write in Markdown. Read on a phone, present on a screen, publish as a
static site.**

Keep presentation cards, their sources and supporting long-form text together.
LightWebPres is a single-file Python tool that builds them into scrollable HTML
pages with slide navigation and a series index. Each article carries its CSS
and JavaScript; readers need a browser, not LightWebPres, an account or a
presentation service.

<picture>
  <source media="(max-width: 600px)" srcset="generated/authoring-workflow-mobile.svg">
  <img src="generated/authoring-workflow.svg" alt="Three alternatives converge on the same editable source: a human writes, a human steers an external agent, or an autonomous agent writes from a task. LightWebPres builds those files into an HTML document and assets for reading, presenting and sharing." width="100%">
</picture>

Write the source yourself, direct an agent, or let an autonomous agent carry
out an authoring task. All three paths produce the same files. **LightWebPres
builds the document; it does not supply the agent.**

**Just reading? No installation needed.** Explore the
[presentation overview](generated/guide/guide.html), jump to the
[complete manual](generated/guide/guide.html#guide-complet), or learn the
[reader controls](GUIDE.md#4-read-present-and-share). Open downloaded HTML in
a browser; GitHub's file viewer shows source rather than running the page.

<p align="center">
  <img src="generated/product-responsive.png" alt="The same Nebula content card shown in real landscape and emulated portrait browser viewports" width="100%">
</p>

The same content card in the Nebula theme, captured in actual Chromium
landscape and emulated portrait viewports, not photographs of devices or a
design mockup. Long content scrolls; it is not automatically shortened to fit
a slide. See the [complete first-article example](examples/first-article/README.md).

## Find your route

1. **[Create content](GUIDE.md#1-create-content).** Make a first article,
   add sources and long-form text, preview edits, and review drafts yourself
   or with an agent.
2. **[Organize a documentary collection](GUIDE.md#2-organize-a-documentary-collection).**
   Arrange a corpus into series, reuse canonical articles in different
   contexts, and check language or audience variants.
3. **[Design and compose identities](GUIDE.md#3-design-and-compose-identities).**
   Create a theme, design layouts and chrome, or combine resources into a
   self-contained Identity Kit for other authors.
4. **[Read, present and share](GUIDE.md#4-read-present-and-share).**
   Navigate by keyboard, mouse or touch; use fullscreen, print to PDF, and
   share a series, article or individual slide.
5. **[Publish and maintain](GUIDE.md#5-publish-and-maintain).**
   Check output, deploy a static site, remove stale files, back up inputs and
   restore or upgrade a project.
6. **[Integrate and automate](GUIDE.md#6-integrate-and-automate).**
   Use the browser builder, CI or an agent; consume JSON reports and keep
   editing, building and publishing permissions separate.

Working with an agent? Start with the [mission entry](agent/skills/lightwebpres/SKILL.md)
and [skill index](agent/skills/README.md). Agents use the same
files and engine as people, not a separate content model.

## Quickstart

Download a source archive from the
[GitHub releases](https://github.com/Fade78/lightwebpres/releases) and extract
the `lightwebpres` file. You need **Python 3.8+**, with no extra packages.
The archive also includes the browser builder, documentation and examples;
the single executable is enough for CLI use. It uses only Python's standard
library and can build locally without a network connection. Read the
documentation shipped with your chosen release: this checkout can describe
features not yet published in a release.

From the directory containing `lightwebpres`:

```bash
python3 lightwebpres init my-series
python3 lightwebpres demo my-series --lang en
```

Open **`my-series/public/index.html`** in your browser. `demo` creates three
example articles **and builds them**, so no extra `build` command is needed.
It refuses to overwrite existing work. No web server is required to view
the generated files locally.

On Windows, use `python lightwebpres` or `py lightwebpres` instead of
`python3 lightwebpres`. On Unix, invoking through Python avoids executable
permission issues; `chmod +x lightwebpres` also enables `./lightwebpres`.

**Next: [make your first personal article](GUIDE.md#make-your-first-personal-article).**
The guide supplies the complete Markdown and `series.json` entry, followed by
the build/check loop and `watch --serve --port 8000 --open` preview. Watching
rebuilds saved edits; refresh the browser yourself.

## One article, different identities

<p align="center">
  <img src="generated/appearance-choices.png" alt="The same first article rendered with native LightWebPres, the documentation identity and the composed Field Notes identity" width="100%">
</p>

Three actual Chromium views of the same article with different presentation
choices, not device photographs. A **Theme** supplies typed colors and fonts;
a **Preset** selects a theme, layouts and chrome; an **Identity Kit** bundles
those resources and assets into a reusable, versioned directory.

Use native `builtin/standard` with its Light theme, choose a Commons theme or
preset, or deliver your own kit. Authors select what ships; readers use
**Appearance** to choose among the published **Identity**, **Preset** and
**Theme** options without editing the sources. The default theme alternatives
include Monochrome, Monochrome Night and Print Ink. Contrast reports measure
typed values, not arbitrary custom CSS or overall accessibility.

Browse the [interactive theme gallery](generated/themes-gallery.html) or its
[compact catalogue](generated/themes-gallery.png). For a complete, inspectable
design workflow, the [Field Notes example](examples/kit-composition/README.md)
composes layouts, marks and a theme from three independent source kits.
Distribute themes as files and complete kits as directories or archives,
through your own downloads or repositories. LightWebPres loads those files;
no account is required.

## A workflow for every role

<picture>
  <source media="(max-width: 600px)" srcset="generated/publishing-roles-mobile.svg">
  <img src="generated/publishing-roles.svg" alt="Document architects organize articles and series; theme and kit makers provide appearance resources, including self-contained kits made with kit compose. Integrators and agents orchestrate the build. The resulting HTML serves readers, presenters and publishers; PDF printing happens in the browser and hosting is separate." width="100%">
</picture>

You can organize a documentary collection, design reusable identities, or
integrate LWP into your own publishing tools. These roles can belong to one
person, a team or external agents. Resource selection and build automation
meet at the same engine; publishing the result remains a separate action.
Follow the [six guide routes](GUIDE.md) or explore the
[three-kit composition example](examples/kit-composition/README.md).

## Output you can keep

- **A site, not an application server.** Publish the complete `public/` tree:
  HTML plus referenced `img/` and identity assets. `--inline-images` can embed
  supported images and kit assets, but does not bundle every external dependency.
- **A series in one HTML file.** `build my-series --single-page`
  combines the series contents and articles with deliberate article switching,
  not continuous scrolling through the whole collection. Add `--inline-images`
  to embed supported images; `--output` still names a directory. The filename
  comes from the series title, or pass `--single-page collection.html` to choose
  it explicitly. Fullscreen survives article switches, and printing includes
  only the active filtered
  article, or only the series contents when that view is active. Uniform text
  fitting can cover the current article or the entire series, selected in
  Display settings. See the [single-page guide](GUIDE.md#publish-a-series-in-one-html-file) for extension
  restrictions, links and portability limits.
- **An index when you need one.** `series.json` determines article order and
  navigation. A lone article can claim `index.html`; `--no-index` lets you
  integrate pages into a site whose landing page is managed elsewhere.
- **Stable links.** Explicit slide slugs preserve addresses when titles or
  order change. Sharing and QR generation happen locally, but a receiving
  phone needs a reachable HTTP(S) URL, not a local file or loopback address.
- **Reader controls.** Keyboard, mouse and touch navigation, fullscreen, pause
  screens and browser PDF printing travel with the page. Fullscreen requires
  a deliberate action; rotating a phone does not activate it.
  The menu also provides zoom buttons, local scrolling for wide tables and
  optional text fitting. Content is preserved; native browser pinch remains available.
- **Explicit variants.** Authors supply language or audience variants and tag
  them. French and English typography packs adjust existing spaces; they do
  not translate content or rewrite it to fit the screen.

## Browser or terminal

The CLI works offline with Python's standard library. Every command runs
unattended and returns an exit code. `python3 lightwebpres --help` lists the
commands, options and environment variables; command-specific help narrows
the reference, for example `python3 lightwebpres build --help`.

The browser builder lives in [`web/`](web/). Serve it over HTTP(S); unlike
generated articles, it cannot run from `file://`. It needs its vendored
Pyodide files and a copy of the executable in one of its supported locations.
The [browser chapter](GUIDE.md#build-in-the-browser) gives the local server
command and deployment layout.

Zip builds stay in the tab, using the same executable under Pyodide. GitLab
sync pulls, builds and pushes directly to the configured instance; it needs
CORS and token permissions, never deletes files, and may leave partial commits
after a failed push. The guide explains token storage and recovery.

This lightweight builder is not the separate `lightwebpres-gui` editor project.
For pipelines and agents, `contract`, `status`, `series tags` and `resolve`
provide machine-readable reports. `audit --strict` supplies a warning gate;
`verify` detects output drift. Follow the
[integration route](GUIDE.md#6-integrate-and-automate) for schemas, exit codes
and the difference between a report and successful validation.

## Safety

**LightWebPres is a renderer for trusted sources, not an HTML sanitizer.**
Raw HTML, including scripts, passes through. Sanitize untrusted CMS exports,
third-party translations or generated content upstream before building.
Filename validation and HTML tag-balance checks do not replace that boundary.

**Speaker notes are not private.** The `note:` field is embedded in the HTML,
and its panel opens in the same page that a projector or screen share shows.
Use `comment:` for source-only review notes; those are not published.
Tags are viewing filters, not access control.

Before publishing, inspect the output and use matching build/verify options,
including `--single-page [FILE]` and `--inline-images` when used. Removing an
article or asset from the sources does not itself delete an old published
file. Review `clean` and the host's stale files as described in
[Publish and maintain](GUIDE.md#5-publish-and-maintain). Keep the source project
and its exact engine version: published HTML or a browser `public.zip` is not
an authoring backup.

## Reference

| Document | Purpose |
|---|---|
| [GUIDE.md](GUIDE.md) | Operational manual in task order |
| [Agent operations](agent/skills/lightwebpres/operations.md) | Bounded tasks, inputs and verification for agent-assisted work |
| [LightWebPres skill](agent/skills/lightwebpres/SKILL.md) | Mission entry with focused format and workflow references |
| [GLOSSARY.md](GLOSSARY.md) | Field meanings, defaults and fallback chains |
| [specifications.md](specifications.md) | Normative format and behavior reference, in French |
| [CHANGELOG.md](CHANGELOG.md) | Version changes and release text |

An optional guest [sourced-presentation method](agent/skills/sourced-presentation/SKILL.md)
ships alongside the format skill for people who want an editorial method.
It is independent of LightWebPres and is not required to use the tool.
The [skill index](agent/skills/README.md) distinguishes their roles.

## License

The program is **GNU GPL v3 or later**, with the **LightWebPres Output
Exception**. The legal texts are [COPYING](COPYING) and
[COPYING.EXCEPTION](COPYING.EXCEPTION).

Your generated presentations may be distributed under the terms you choose,
commercially or not. The exception covers the tool's code copied into normal
output; it does not extend to a generator using that output as templates.

The executable remains copyleft. `init` copies it into the series with its
licence files: distributing that repository also distributes GPL software,
not just presentation output. Keep those notices with it.

Third-party code is listed in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
Vendored Pyodide uses MPL 2.0; see [web/vendor/NOTICE.md](web/vendor/NOTICE.md).
The licences cover code, not the LightWebPres name: fork the project, but do
not present a modified version as this project.
