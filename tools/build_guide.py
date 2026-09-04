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
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRESENTATION_PACKAGE_CATALOG = ROOT / 'examples' / 'layouts'
PRESENTATION_PRESET = 'lightwebpres-docs@0.1.0/docs'
SERIES = {
    'series_meta': {
        'title': 'LightWebPres',
        'subtitle': 'The guide, built with the tool it describes',
        'intro': 'Every component named in the guide, rendered by the '
                 'engine the guide documents.',
        'presentation_preset': PRESENTATION_PRESET,
    },
    'articles': [{
        'page_source': 'guide.md',
        'page_dest': 'guide.html',
        'nav_title': 'Guide',
        'nav_desc': 'Setup, anatomy of a page, series, look, shipping',
    }],
}


def build(output, theme=None, lang='en'):
    exe = ROOT / 'lightwebpres'
    guide = ROOT / 'GUIDE.md'
    deck = ROOT / 'tools' / 'guide-deck.md'
    for f in (exe, guide, deck):
        if not f.exists():
            sys.exit(f'missing: {f}')
    package_selector, _preset_id = PRESENTATION_PRESET.rsplit('/', 1)
    package_id, package_version = package_selector.split('@', 1)
    package_manifest = (PRESENTATION_PACKAGE_CATALOG / package_id / package_version
                        / 'manifest.json')
    if not package_manifest.exists():
        sys.exit(f'missing: {package_manifest}')

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
        init_env['LWP_PRESENTATION_PACKAGES_DIR'] = str(PRESENTATION_PACKAGE_CATALOG)
        subprocess.run(cmd, check=True, capture_output=True, env=init_env)

        sources = series / 'sources'
        shutil.copy(deck, sources / 'guide.md')
        # The long-form piece IS the guide, verbatim. No second copy lives
        # anywhere: it is assembled here and thrown away with the tempdir.
        shutil.copy(guide, sources / 'guide_article.md')
        (series / 'series.json').write_text(
            json.dumps(SERIES, indent=2, ensure_ascii=False), encoding='utf-8')

        # The build must resolve the copy vendored by init, not the source
        # catalogue. This keeps the generated guide a portable-package test.
        build_env = os.environ.copy()
        build_env['LWP_PRESENTATION_PACKAGES_DIR'] = str(
            pathlib.Path(tmp) / 'no-external-packages')
        subprocess.run([sys.executable, str(exe), 'build', str(series),
                        '--lang', lang, '--output', str(series / 'public')],
                       check=True, capture_output=True, env=build_env)

        output.mkdir(parents=True, exist_ok=True)
        fresh = {item.name for item in (series / 'public').iterdir()}
        # `output` is a generated directory. Remove files from an older
        # package before copying the fresh build, so stale committed artefacts
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
