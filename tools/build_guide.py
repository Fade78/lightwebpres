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
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERIES = {
    'series_meta': {
        'title': 'LightWebPres',
        'subtitle': 'The guide, built with the tool it describes',
        'intro': 'Every component named in the guide, rendered by the '
                 'engine the guide documents.',
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

    with tempfile.TemporaryDirectory() as tmp:
        series = pathlib.Path(tmp) / 'guide'
        # `init`, not the `install` alias it used to call: the alias is
        # kept for one MAJOR version and prints a [WARNING] that
        # capture_output swallows, so this would have gone from silent
        # to fatal at the next MAJOR with no signal in between. The
        # deck this very script builds tells its readers `init`.
        cmd = [sys.executable, str(exe), 'init', str(series)]
        if theme:
            cmd += ['--theme', theme]
        subprocess.run(cmd, check=True, capture_output=True)

        sources = series / 'sources'
        shutil.copy(deck, sources / 'guide.md')
        # The long-form piece IS the guide, verbatim. No second copy lives
        # anywhere: it is assembled here and thrown away with the tempdir.
        shutil.copy(guide, sources / 'guide_article.md')
        (series / 'series.json').write_text(
            json.dumps(SERIES, indent=2, ensure_ascii=False), encoding='utf-8')

        subprocess.run([sys.executable, str(exe), 'build', str(series),
                        '--lang', lang, '--output', str(series / 'public')],
                       check=True, capture_output=True)

        output.mkdir(parents=True, exist_ok=True)
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
