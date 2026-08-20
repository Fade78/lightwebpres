#!/usr/bin/env python3
"""Regenerate the table of contents of `specifications.md`.

The document is 23 sections and some 160 headings, and until now it had no
index at all: the only way in was to know that the format is §4, the
commands §11, the themes §9, and the `series.json` schema §20. Knowing
that is the reward for having read it, which is the wrong way round.

Derived, never typed, for the reason the register's index is derived: a
list of section numbers maintained by hand is a second place to be wrong.
`test_the_spec_index_matches_the_file` rebuilds this block and fails the
suite if the file disagrees.

**No links.** The index gives numbers and titles, and the numbers are the
addresses — that is how this project cites the document everywhere else,
in the executable, in the tests, in the sibling project. An anchor scheme
would be a second addressing system, invented here, verifiable only in a
renderer this script cannot see.

Fence-aware, and that is not a detail: §4.2 contains a complete example
article whose slide headings are `#` and `##`. Read line by line without
tracking ``` fences, "La température change tout" becomes a section of
the specification.

    python3 tools/spec_index.py            # rewrite the block in place
    python3 tools/spec_index.py --check    # exit 1 if it is stale
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / 'specifications.md'

OPEN = '<!-- SOMMAIRE:'
CLOSE = '<!-- /SOMMAIRE -->'

SECTION = re.compile(r'^## (\d+)\. (.+)$')
SUB = re.compile(r'^### (\d+\.\d+(?:\.\d+)*)\.? (.+)$')


def outline(text):
    """Sections and their subsections, in document order, fences skipped.

    A heading inside a fenced block belongs to an example, not to this
    document. Raises if a top-level heading is unnumbered: the numbering
    is the addressing system, so a section without a number is one no
    other document can cite.
    """
    sections = []
    fenced = False
    for line in text.split('\n'):
        if line.lstrip().startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = SECTION.match(line)
        if m:
            sections.append((m.group(1), m.group(2).strip(), []))
            continue
        if line.startswith('## '):
            raise SystemExit(f'unnumbered section heading: {line!r}')
        m = SUB.match(line)
        if m and sections:
            sections[-1][2].append((m.group(1), m.group(2).strip()))
    if not sections:
        raise SystemExit('no sections found')
    return sections


def render(sections):
    out = [OPEN + ' généré par `python3 tools/spec_index.py`. Ne pas éditer',
           '     à la main : la source est les titres du document. -->',
           '']
    for num, title, subs in sections:
        out.append(f'**§{num}. {title}**')
        if subs:
            out.append('')
            out.append(' · '.join(f'{n} {t}' for n, t in subs))
        out.append('')
    out.append(CLOSE)
    return '\n'.join(out)


def splice(text):
    start = text.index(OPEN)
    end = text.index(CLOSE) + len(CLOSE)
    return text[:start] + render(outline(text)) + text[end:]


def main():
    text = SPEC.read_text(encoding='utf-8')
    fresh = splice(text)
    if '--check' in sys.argv:
        if fresh != text:
            sys.exit(f'{SPEC.name}: le sommaire est périmé — lancer '
                     f'`python3 tools/spec_index.py`')
        return
    SPEC.write_text(fresh, encoding='utf-8')
    sections = outline(text)
    print(f'{SPEC.name}: sommaire régénéré ({len(sections)} sections, '
          f'{sum(len(s[2]) for s in sections)} sous-sections)')


if __name__ == '__main__':
    main()
