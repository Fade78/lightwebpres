# Operations

Read this for a workflow, not a second command manual. The current executable's
`--help` and contextual help define accepted options; `contract` defines the
versioned slide-draft interface. [Article Format](article-format.md),
[Series and Appearance](series-and-appearance.md) and
[Text and Style](text-and-style.md) retain the exact author-facing mechanics.

## Establish Authority And Ownership

Before any mission, identify its inputs, permitted changes and expected
deliverable. Locate the executable and inspect its `--version` and `--help`.
Confirm the series root, source/output directories, language, environment
overrides and runtime choices. Examples below use `my-series` as a placeholder
for that confirmed directory; invoke a local script as `python3 lightwebpres`
when it is not on PATH. Do not assume an installed skill locates the project.

Read-only inspection does not authorize modification. Source editing does
not imply deleting files, changing shared catalogues, publishing, pushing,
installing software or using credentials. Act only within the user's granted
scope. A permission failure is a blocker, not an invitation to bypass it.

The author owns `sources/`, `series.json`, pinned values in
`templates/settings.conf`, `templates/custom.css` and deliberate overrides.
The engine normally supplies navigation and built-in language packs from
its executable. Generated `public/`, the series README, `.lwp-*` manifests
and `.lwp-cache/nav.json` are derived output/state, not hand-editing targets.
Review existing output ownership before building: regenerating a directory
can overwrite files, and ownership of a source does not establish ownership
of every destination. Use an agreed scratch series for a contained preview.

`--dry-run` journals intended writes and build steps without changing inputs
or output. It is useful for inspecting side effects, **not proof that the
page rendered**. `kit compose --dry-run` also validates disposable files in
the system temporary area; it is not a browser preview.

## Author And Organize

Start from the brief, local editorial conventions and authorized files.
Use `contract --article file.md` for collision-aware draft skeletons, but
complete the fields described in Article Format before building. Preserve
existing slugs when revising or reordering. Only `series slug set` writes
missing slugs into the author's articles; review its dry-run before using
that source-editing command within scope.

For a series change, compare `status`, `series tags` and `series slug` before
and after editing registration, order or metadata. Do not invent
`series article add/remove/set` commands. Changing `active`, `draft` or
`ignored` changes participation, not factual approval. Inspect per-tag
article/slide intersections and the fresh-page default, not only inventory
totals. For a corpus of several series, explicitly inventory each root;
there is no native cross-series corpus store.

The optional externally maintained `sourced-presentation` method can help
with research and editorial verification. LWP does not enforce that method
or generate researched prose. Local audience and citation rules still matter;
neither a successful render nor a status value proves a claim true.

## Select Or Compose Appearance

Inspect `preset list`, `preset show`, `series preset`, `theme show` or
`series theme` before changing a choice. Catalogue reports and series reports
answer different questions: the latter include the series' effective resources
and settings. Use `resolve` for a property whose winning layer is unclear.

Choose the smallest layer that meets the brief. `series theme set` changes
the theme selection while preserving settings pins. `init --preset` may apply
a kit's starter; `series preset set` selects/vendors without applying that
starter. Inspect contextual help for the theme-preservation choice before
changing an existing preset. Do not overwrite a shared theme or kit version
merely because the series needs a local variation.

For composition, obtain source kit roots, the final identity/version, target
manifest, desired files and authorized output catalogue. Read
`kit compose --help` and the
[identity walkthrough](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#3-design-and-compose-identities)
for the recipe and manifest examples; specifications.md §9.9 is normative.
The recipe explicitly names the final resources: composition is not an
implicit merge, inheritance or dependency resolver. The output is an
autonomous kit, and an existing target is refused. Inspect the dry-run,
compose only in the authorized destination, then test the result in a scratch
series before selecting it in an existing publication.

Validate required layouts, chrome, assets and selected alternatives against
real cards and the index. The engine measures theme contrast per category;
it does not design an accessible identity or certify brand approval. Browser
inspection remains necessary for wrapping, contrast, clipping and asset paths.

## Diagnose And Validate

Choose the check that answers the failure, rather than rebuilding blindly:

- Unexpected title, colour or field value: `resolve` shows the deciding and losing layers; slide-field reports list their occurrences rather than a cascade.
- Missing articles/cards: inspect `status`, `series tags`, exclusions, draft flags and the effective default tag.
- Source/render warnings: `audit` renders in memory, writes no output and examines all listed articles, including drafts and ignored entries.
- Presentation-only investigation: `audit --templates` omits article checks and does not render. It is not a substitute for a full audit.
- Stale existing output: `verify` compares with a rebuild in memory, including pages, index, series README and selected presentation assets. Missing or different checked files cause failure.

Plain `audit` exits zero even for reported render failures. Read the findings;
`--strict` turns warnings and render failures into non-zero CI results.
Reports include unused/missing rendered images, malformed metadata or notes,
symlinks leaving logical roots and unreadable resolved styles. If rendering
fails, image usage can be unavailable rather than known to be unused.
Do not infer success from plain audit's exit status.

Wide Markdown-table warnings are **ESTIMATE** findings before reader scaling
at `1024x768`, `768x1024`, `1280x720` and `1680x720`. They include resolved
size/font-size settings, longest tokens and padding, not exact browser layout
or font metrics. Custom CSS can differ; no warning is not a fit guarantee.
Try the reader's local table scroll before proposing an editorial rewrite.

For an authorized normal English-language output build:

```bash
lightwebpres audit my-series --lang en --strict
lightwebpres build my-series --lang en
lightwebpres verify my-series --lang en
```

Adapt to the actual language and options. A clean build confirms parsing and
rendering, not editorial approval or visual fit. Inspect the generated page
on desktop and mobile, including tags, links, source notes and appearance
alternatives. Read warnings even when build exits zero.

`verify` needs the same supported rendering flags and environment as the
build, including language, themes, presentation alternatives, typography,
draft inclusion, navigation and scroll duration where applicable. Consult
`verify --help`: not every build option is accepted. In particular,
`verify` cannot reproduce `--inline-images`; keep a separate non-inline
output for that CI check. Build-stamp differences and surrounding whitespace
are ignored, not arbitrary body differences. Audit has its own smaller option
set; do not pass build-only switches to it.

Use `verify` **before** rebuilding when the question is whether an existing
publication has drifted; rebuilding first destroys that comparison. After
an intended source change, build then verify to check the regenerated output.
If no engine or browser is available, report the missing check explicitly.

## Read, Present And Share

Inspect a local build before any authorized distribution. `watch --serve`
can rebuild and serve on `127.0.0.1`; launching it is an explicit local preview,
not public hosting. The page's presenter menu and built-in help document
controls. **C** selects appearance, **L** selects tags when available,
**N** toggles the speaker panel and **I** toggles scrolling duration.
Check the active tag and browser-persisted choices when reproducing a view.

**Menu** also offers presentation zoom **-**, **+**, **Reset**, wide-table
handling, text fitting and independent table/image shrink switches. **O** cycles
`clip`, `overflow`, `scroll`; **A** cycles `fixed`, `uniform`, `per-slide`.
Use local table scrolling to reach clipped columns without navigating the
deck. `fixed` keeps responsive theme sizes without content fitting; uniform
reduction measures all currently visible slides, including long-form content,
while per-slide reduction measures each independently. Author limits live in
`series_meta.reading`; use [Series and Appearance](series-and-appearance.md)
for exact keys, defaults and validation. Content that still does not fit at
the floor stays available to scroll rather than being removed.

Record these reading choices separately: unlike Appearance choices, they and
presentation zoom remain only in the loaded page, including after Menu closes
and reopens. Zoom is independent magnification and can cause overflow; pinch
remains native browser zoom. Check resize, tags, theme/preset changes and late
font/image loading. Browser touch emulation is not a physical-device check;
report the actual test environment without claiming device verification.

Speaker notes are in the public HTML and their same-page panel is visible
on a projected/shared screen. Ctrl/Cmd+P starts slides on separate sheets;
long slides can span several. Print clears runtime fitting scales and zoom,
and expands table viewports without screen clipping. Inspect the PDF for
paper-width overflow and notes. Use effective `series slug` names
for stable article/card links and QR destinations, not ordinal slide numbers.
Confirm the intended public base URL before distributing those links.

Normal output includes separate images and kit assets: distribute the whole
intended output tree, not a lone HTML file assumed to contain every asset.
`--inline-images` is a distinct build mode with validation of supported local
image references, not a reason to skip checks. See the
[sharing walkthrough](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#4-read-present-and-share).

## Publish And Maintain

Confirm the deployment destination and approval separately from local build
authority. Publish output and referenced assets, not source notes, credentials
or the entire project by accident. The browser tool's GitLab workflow can
write to a remote repository; it is not authorized merely by a preview request.
No community hosting service or native AI publishing service is promised.

For an upgrade, record the current version, inspect overrides and compare
with `template show` before maintenance. `template write` installs an override
that stops following the embedded resource. `template update` removes an
identical local `nav.js`; a differing one is saved as `nav.js.bak` and removed
from the active path. Inspect any existing backup too. Identical built-in
language-pack copies are removed; differing packs are kept and reported.
`--scaffold` refreshes settings comments while retaining valid pins; retired
keys are preserved in a commented trailing section for review. These actions
need maintenance authority, not just a diagnosis request.

`clean` proposes manifest-based orphan removal by default; `--force` actually
removes files. Inspect the plan and confirm deletion authority first, using
the same output directory as the build. Dry-run is not permission to execute
the plan. After authorized maintenance, audit, rebuild and inspect. See
[Publish and maintain](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#5-publish-and-maintain).

## Integrate And Automate

Use `--help`/contextual help for the running version's commands and option
placement. Do not copy a static CLI schema from this skill. A client should
consume `contract` and its schema/version rather than infer fields from
rendered HTML. JSON is available on relevant read-only reports: `contract`,
`status`, `series tags`, `series slug`, `resolve`, `theme show`, `series theme`,
`preset list`, `preset show` and `series preset`. It is not a universal
`--format json` switch for build, audit, verify or mutations.

Pass explicit paths and capture UTF-8 output, diagnostics and exit codes.
Record the version, flags and relevant `LWP_*` environment variables so a
second run can reproduce the same resource selection. A relative `--output`
is resolved against the working directory, not the series argument. Keep
credentials out of source and logs. CI should distinguish strict audit,
output-drift verification, authorized regeneration and deployment approval.

The lightweight browser tool and separate GUI reuse the engine through
Pyodide; they are not a native LWP AI-authoring API or MCP server. An external
agent/client owns its tool bridge and upstream sanitization. Consult
[Integrate and automate](https://github.com/Fade78/lightwebpres/blob/main/GUIDE.md#6-integrate-and-automate)
for deployment and browser details rather than inventing integrations.

At handoff, state changed sources/resources, outputs, exact checks and flags,
warnings, visual checks performed, and anything not published or not verified.
Return to the [mission entry](SKILL.md) to choose another bounded reference.
