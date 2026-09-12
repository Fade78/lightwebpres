#!/usr/bin/env python3
"""Build the guide with lightwebpres itself.

The guide describes a tool for making card decks backed by a long-form
article. So it is one: `GUIDE.md` becomes the long-form piece, and
`tools/guide-deck.md` is the deck that summarises it. Reading the built
result shows every component the guide names, in situ, styled by the real
engine.

This is not a copy of the guide. The long-form file is assembled from
`GUIDE.md` at build time, so there is no second version to drift — and
the test suite runs this script, so an example that stops working stops
the build.

    python3 tools/build_guide.py [--output generated/guide] [--theme slug]
                                 [--lang fr|en]

`--lang` defaults to `en` here, where the tool's own default is `fr`:
the guide is written in English and the interface strings around it
have to match it.
"""
import argparse
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDENTITY_KIT_CATALOG = ROOT / 'examples' / 'kits'
PRESENTATION_PRESET = 'lightwebpres-docs@0.1.0/docs'
GUIDE_IMAGES = {
    'generated/product-responsive.png': 'img/product-responsive.png',
    'generated/appearance-choices.png': 'img/appearance-choices.png',
    'generated/identity-composition.png': 'img/identity-composition.png',
}
SERIES = {
    'series_meta': {
        'title': 'LightWebPres',
        'subtitle': 'The guide, built with the tool it describes',
        'intro': 'Every component named in the guide, rendered by the '
                 'engine the guide documents.',
        'presentation_preset': PRESENTATION_PRESET,
        'scroll_duration': 0,
    },
    'articles': [{
        'page_source': 'guide.md',
        'page_dest': 'guide.html',
        'nav_title': 'Guide',
        'nav_desc': 'Create, organize, design, read, publish and automate',
    }],
}


def markdown_lines(text):
    """Yield lines with fenced examples (including their delimiters) marked."""
    fence = None
    for line in text.splitlines():
        delimiter = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        protected = fence is not None or delimiter is not None
        if delimiter:
            run, rest = delimiter.groups()
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
                fence = None
        yield line, protected


def heading_slug(title):
    """Keep the guide's existing GitHub-style fragment spelling."""
    return re.sub(r'[^\w -]', '', title.lower()).replace(' ', '-')


def prepare_article(text):
    """Adapt repository links and headings, never the tutorial's code."""
    lines, images = [], set()

    def image(match):
        source = match[2]
        if urlsplit(source).scheme or urlsplit(source).netloc:
            return match[0]
        if source not in GUIDE_IMAGES:
            raise ValueError(f'unknown guide image: {source}; add it to GUIDE_IMAGES')
        images.add(source)
        return match[1] + GUIDE_IMAGES[source]

    def links(line):
        line = re.sub(r'(!\[[^\]]*\]\()([^\s)]+)', image, line)
        line = re.sub(r'(<img\b[^>]*?\bsrc=[\"\'])([^\"\']+)', image, line)
        return re.sub(
            r'(?<!!)\[([^\[\]]+)\]\((?!https?://)([^)]+)\)',
            lambda m: '<a href="' + html.escape(
                m[2] if urlsplit(m[2]).scheme or m[2].startswith('#') else
                'https://github.com/Fade78/lightwebpres/blob/main/' + m[2],
                quote=True) + '">' + html.escape(m[1]) + '</a>', line)

    for line, protected in markdown_lines(text):
        if not protected:
            heading = re.match(r'^(#{1,6}) (.+)$', line)
            if heading:
                level, title = len(heading[1]), heading[2]
                content = re.sub(r'`([^`]+)`', r'<code>\1</code>', html.escape(title))
                line = (f'<h{level} id="{heading_slug(title)}" tabindex="-1">'
                        f'{content}</h{level}>')
            parts, cursor = [], 0
            for code in re.finditer(r'(`+).*?\1(?!`)', line):
                parts.extend((links(line[cursor:code.start()]), code[0]))
                cursor = code.end()
            parts.append(links(line[cursor:]))
            line = ''.join(parts)
        lines.append(line)
    # Guide-only navigation: the engine resolves inner hashes to their slide.
    # Keep heading links inside the manual, including keyboard activation and
    # direct entry. Zero-duration slide navigation avoids a competing glide.
    lines.append('''<script>
(function () {
  var entry = window.location.hash;
  function target(hash) {
    var id;
    try { id = decodeURIComponent(hash.slice(1)); }
    catch (error) { return null; }
    var element = document.getElementById(id);
    return element && (element.id === 'guide-complet' ||
      element.matches('.full-article h1[id], .full-article h2[id], .full-article h3[id], .full-article h4[id], .full-article h5[id], .full-article h6[id]')) ? element : null;
  }
  function visit(element) {
    element.setAttribute('tabindex', '-1');
    element.focus({preventScroll: true});
    element.scrollIntoView({behavior: 'instant', block: 'start'});
  }
  document.addEventListener('click', function (event) {
    var link = event.target.closest('a[href^="#"]');
    if (!link || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    var element = target(link.hash);
    if (!element) return;
    event.preventDefault();
    visit(element);
  });
  window.addEventListener('hashchange', function (event) {
    var element = target(window.location.hash);
    if (!element) return;
    event.stopImmediatePropagation();
    visit(element);
  }, true);
  window.addEventListener('load', function () {
    var element = target(entry);
    if (element) document.fonts.ready.then(function () { visit(element); });
  });
})();
</script>''')
    return '\n'.join(lines) + '\n', images


def build(output, theme=None, lang='en'):
    exe = ROOT / 'lightwebpres'
    guide = ROOT / 'GUIDE.md'
    deck = ROOT / 'tools' / 'guide-deck.md'
    for f in (exe, guide, deck):
        if not f.exists():
            sys.exit(f'missing: {f}')
    identity_selector, _preset_id = PRESENTATION_PRESET.rsplit('/', 1)
    identity_id, identity_version = identity_selector.split('@', 1)
    identity_manifest = (IDENTITY_KIT_CATALOG / identity_id / identity_version
                         / 'manifest.json')
    if not identity_manifest.exists():
        sys.exit(f'missing: {identity_manifest}')
    article, images = prepare_article(guide.read_text(encoding='utf-8'))
    for source in sorted(images):
        if not (ROOT / source).is_file():
            sys.exit(f'missing guide image: {ROOT / source}')

    temporary_root = ROOT / 'work' / 'tmp'
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temporary_root) as tmp:
        series = pathlib.Path(tmp) / 'guide'
        # `init`, not the `install` alias it used to call: the alias is
        # kept for one MAJOR version and prints a [WARNING] that
        # capture_output swallows, so this would have gone from silent
        # to fatal at the next MAJOR with no signal in between. The
        # deck this very script builds tells its readers `init`.
        cmd = [sys.executable, str(exe), 'init', str(series),
                '--preset', PRESENTATION_PRESET]
        if theme:
            cmd += ['--theme', theme]
        init_env = os.environ.copy()
        init_env['LWP_IDENTITY_KITS_DIR'] = str(IDENTITY_KIT_CATALOG)
        subprocess.run(cmd, check=True, capture_output=True, env=init_env)

        sources = series / 'sources'
        shutil.copy(deck, sources / 'guide.md')
        (sources / 'guide_article.md').write_text(article, encoding='utf-8')
        (sources / 'img').mkdir(exist_ok=True)
        for source in sorted(images):
            shutil.copy(ROOT / source, sources / GUIDE_IMAGES[source])
        (series / 'series.json').write_text(
            json.dumps(SERIES, indent=2, ensure_ascii=False), encoding='utf-8')

        # The build must resolve the copy vendored by init, not the source
        # catalogue. This keeps the generated guide a portable-kit test.
        build_env = os.environ.copy()
        build_env['LWP_IDENTITY_KITS_DIR'] = str(
            pathlib.Path(tmp) / 'no-external-kits')
        subprocess.run([sys.executable, str(exe), 'build', str(series),
                        '--lang', lang, '--output', str(series / 'public')],
                       check=True, capture_output=True, env=build_env)

        output.mkdir(parents=True, exist_ok=True)
        fresh = {item.name for item in (series / 'public').iterdir()}
        # `output` is a generated directory. Remove files from an older
        # build before copying the fresh one, so stale committed artefacts
        # cannot survive while the identity guard compares only current names.
        for item in output.iterdir():
            if item.name in fresh:
                continue
            if item.is_symlink() or item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        for item in (series / 'public').iterdir():
            target = output / item.name
            if item.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(item, target)
            else:
                shutil.copy(item, target)
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=pathlib.Path,
                    default=ROOT / 'generated' / 'guide')
    ap.add_argument('--theme', default=None)
    ap.add_argument('--lang', default='en')
    args = ap.parse_args()
    out = build(args.output, args.theme, args.lang)
    print(f'Guide built with lightwebpres -> {out}')


if __name__ == '__main__':
    main()
