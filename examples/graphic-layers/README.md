# Anchored graphic compositions

This source-only example combines externally declared image/text assets and a
two-element DRAFT layer with inline Markdown resources, tag matching, native
anchors, screen-only placement and local exceptions. Artwork is original CC0;
the example text may also be reused under CC0-1.0.

Dedicated cards also demonstrate a full-slide `cover` background and a separate
foreground image. Both use theme-linked tint, while resource selection remains
explicit. The native title/summary Markdown uses typed `style.*` pins to render
semantic strong as italic or underlined text, independently from body emphasis.

Build a disposable copy, not this tracked source directory. From the repository
root, choose a fresh destination below `work/tmp/`:

```bash
mkdir -p work/tmp
cp -R examples/graphic-layers work/tmp/graphic-layers-demo
TMPDIR="$PWD/work/tmp" python3 lightwebpres build work/tmp/graphic-layers-demo --lang en
TMPDIR="$PWD/work/tmp" python3 lightwebpres verify work/tmp/graphic-layers-demo --lang en
```

Open `work/tmp/graphic-layers-demo/public/compositions.html`. **C** changes the
theme; **D** changes native text fitting without resizing fixed graphic text.
Print/PDF uses the base slide geometry and omits the screen-only marker.

Open the `#image-background` and `#image-foreground` cards to compare their
planes. The background preserves its aspect ratio and clips to the logical
slide; the foreground does not become a button or reserve native layout space.
Tinted payloads are embedded so these cards also work when opened directly from
disk; ordinary untinted images follow the build's normal asset-copy setting.

```bash
python3 lightwebpres resolve work/tmp/graphic-layers-demo layers --article compositions.md --format json
python3 lightwebpres resolve work/tmp/graphic-layers-demo resources --article compositions.md --format json
```

The same copy builds with `--single-html series.html --inline-images` for a
self-contained document. Neither build mode needs a web server or remote asset.
The exact contract is in `specifications.md` §9.10; `contract` exposes typed
resource shapes and reference names for authoring tools.
