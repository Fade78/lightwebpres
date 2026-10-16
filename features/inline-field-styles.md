# Theme-controlled inline roles in slide fields

Status: integrated for unreleased 0.72.0 (DECISIONS.md B99).
The original uncommitted `feature/layers` worktree announced 0.71.0 and called
this entry B86. Its historical commissioning record authorized a commit, tag
and push, but no such feature commit or local tag existed at integration.
The owner authorized integration on 2026-10-16, after table-only 0.71.0 was
committed/pushed separately. The original worktree stays intact; this request
does not authorize a 0.72.0 tag, push or GitHub release.

## Owner request

The automatic inline Markdown added in 0.70.0 needs the same typed theme
controls as body formatting. The owner also requested a dedicated graphic
documentation section covering free image placement, theme-driven decoration,
foregrounds and full-slide image backgrounds.

Visual inspection exposed a local-file CSS-mask restriction: tinted images
loaded as normal `file:` resources became invisible. Tinted instances now use
embedded data URIs from the validated bounded source snapshot. Untinted assets
keep normal publication semantics; derived assets are deduplicated and do not
leave unused file copies. The browser regression checks actual tinted pixels,
not merely the computed tint colour.

## Contract

- Keep Markdown automatic and unchanged: `**strong**`, `*emphasis*`, inline
  code and HTTP(S) links. These are semantic roles, not hard-coded appearance.
- Add `title1`, `title2`, `summary` and `cover.summary` inline namespaces, each
  with `strong`, `em`, `code` and `link` components. Context-specific cover ink
  must not be replaced by the standard summary ink.
- Each role exposes `fg`, `bg`, `font`, `size`, `weight`, `style`, `decoration`,
  `decoration-color`, `pad-inline`, `pad-block`, `radius` and the established
  four `shadow.*` axes. Use the existing property registry, schema, settings,
  article pins, theme snapshots and runtime theme switcher.
- Defaults keep the field's ink/font/size. Strong is bold; em is italic;
  code uses the shared code font/relative size; links retain field ink and an
  underline. `inherit` is an explicit weight/style value, not a third physical
  font weight. It preserves nested emphasis and the surrounding font treatment.
- Native body headings, fact text, long-form prose, navigation-card labels,
  notes and presentation chrome keep their own component styles. Arbitrary kit
  wrappers do not change which native fields receive the new role styles.
- Relative sizes scale with the owning field and native fitting/zoom. Contrast
  inventory includes each new foreground, mark and decoration, with the
  correct cover/page background and parent font-size/weight. This is measurement,
  not a new aesthetic admission rule.
- Existing complete snapshots may omit the new axes: they use registry defaults.
  No aliases or migration handlers are introduced. Reference depth increases
  from three to five bounded hops so two inline-role references can sit above
  a previously valid three-hop parent chain. Cycles still fail.

## Graphic use cases

Keep the existing `under-content` / `over-content` planes. A background paints
above the theme's base fill and below native content; placing it under an
opaque fill would make it invisible. A full-slide `cover` fit and centred anchor
crop the image without stretching it, changing native layout or catching
gestures. Foreground images use the over-content plane, never reader controls.

Document theme-driven decoration precisely: styles can reference the active
theme while resource registration/application belongs to the documentary
sources. A theme colour snapshot is not an asset package, and changing a
palette does not implicitly select another composition. Do not claim an
unimplemented theme-specific resource catalogue.

## Validation checklist

- [x] Typed field roles, inherited defaults, scoped emission and contrast sites.
- [x] Settings/article pins, snapshots, live contract and resolution reports.
- [x] Chromium/Firefox: palettes, kits, combined HTML, zoom, print and body isolation.
- [x] Background/foreground rendering order, cover geometry and gesture isolation.
- [x] Dedicated usage recipes, real tracked sources and regenerated outputs.
- [x] Compilation, reference guards and complete six-worker regression run
  (qualified results below, not a claim that every recorded run was green).

## Baseline

Before this increment, the complete 1,580-test / 242-class run with six workers
retained the known Pointer Lock failure in `MouseCommands`, as previous runs
did. Log: `work/tmp/layers-theme-baseline-sixworkers.log`. Report the final run
separately rather than attributing that pre-existing test instability to the
new style controls.

## Verification record — 2026-10-15

- The complete post-fix run discovered **1,587 tests / 243 classes** with six
  workers. All **27 graphic-layer tests** and **six inline-field-style tests**
  passed. Its only failing class was `tests.test_mouse_commands.MouseCommands`.
  Log: `work/tmp/layers-theme-final-full-sixworkers.log`.
- That Chromium failure was **not the earlier timeout at line 296**. The MMG
  return-to-index check timed out after five seconds at
  `tests/mouse_commands_e2e.cjs:195`; capture and fullscreen had both been lost.
  The class was already intermittent in the baseline, but this distinct failure
  point is retained rather than described as a proven identical baseline bug.
- The complete mouse-command class then passed alone: **three tests in 21.910s**,
  including Chromium, Firefox and the runtime grammar. Log:
  `work/tmp/layers-theme-final-mouse-isolated.log`. No mouse-navigation fix,
  skipped assertion or relaxed timeout was added for this feature.
- The subsequent full confirmation **passed all 1,587 tests / 243 classes** in
  **355 seconds**, including the complete mouse-command class. Log:
  `work/tmp/layers-theme-confirmation-sixworkers.log`. It used the same runner's
  discovery, worker execution and checks, with only its duration-cache path
  redirected to a fresh directory under `work/tmp/`; browser discovery keeps
  the supplied environment. Although the server restart produced a cancellation
  notification, the saved log contained all class results and the completed
  runner footer, with no failure/error/timeout markers; no matching confirmation
  process remained. This completed result is distinct from the earlier run above.
- The targeted integration runs passed **83 tests** before the final tint fix,
  then **41 tests** after it, including the three integration guards corrected
  after the earlier complete run. Logs:
  `work/tmp/layers-theme-targeted.log` and
  `work/tmp/layers-theme-integration-targeted.log`.
- The two standalone JSON layer recipes were extracted from `GUIDE.md`, built
  with a real SVG asset and verified unchanged. The full tracked example also
  passed `verify --lang en`, matching its preview build options.
- Desktop/mobile captures, both new guide cards and the actual Chromium PDF
  were inspected. The background and tinted foreground now appear when opened
  directly from disk, with no mask/resource/script errors. Captures:
  `work/tmp/layers-theme-final-preview-yhsoquaq/`.
- Product/documentation capture input hashes, dimensions and output hashes,
  both generated indexes, compilation, section references and
  `git diff --check` passed. Guide, gallery, golden demo and capture manifests
  were regenerated through their generators, not edited manually.

These are dated measurements, not a guarantee about later runs. The owner then
authorized the commit, tag and push on the requested branch, without integration
into `main` or publication of a GitHub release.
