#!/usr/bin/env python3
"""Every `§N.N` in this repository resolves to a section of the spec.

A reference is the cheapest thing to write and the first thing to rot:
nothing breaks when a section is renumbered, so nobody notices. This
repository holds about 1 350 of them — in the documents, in the
executable's error messages, in the test suite — and they are the main
way one document says "the reason is over there".

Two rules, and both were earned by a defect this script found the day it
was written.

**An unqualified reference is a reference to `specifications.md`.** That
is how the whole repository already uses it. Five references to a section
9.2.1 survived the §9 rewrite that moved the share matrix to §9.3.4, in
three test files, pointing at a section that had not existed for months.

**A qualified reference must name something a reader can reach.** A
citation is only worth writing if it resolves for whoever reads it, and
who reads it depends on the file. `specifications.md` is in the public
repository; `delete-before-1.0/` is not distributed at all and its name
promises it will be deleted. The executable carried 31 citations of the
CLI design documents — DECISION 1 Phase 2, PROPOSITION 5.10 — in the
one file people download, pointing at documents they have never had
and never will. The reasoning was in the comment beside them; only the
address was unreachable, so the addresses went.

**A dead reference is written without the sign**, and the two paragraphs
above obey it. `§` means "go there"; a section that no longer exists goes
nowhere. The rule was not invented for convenience: this script's own
test failed on its own docstring, which cited with the sign the two dead
references it exists to describe. Marking the difference is right anyway
— `§9.3.4` is an instruction to a reader, `9.2.1` is a fact about the
past — and a checker that could not tell them apart would push every
document into never naming what it fixed.

    python3 tools/check_refs.py            # report, exit 1 if anything dangles
    python3 tools/check_refs.py --quiet    # exit code only
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = ROOT / 'specifications.md'

# Files whose references are not ours to keep: the doomed tree is not
# maintained, and generated artefacts are rebuilt from sources that are
# checked. Local artefacts are not in git's file list at all.
SKIP_PREFIX = ('delete-before-1.0/', 'generated/')

# A reference qualified by a document name belongs to that document, not
# to the specification. Only `lightwebpres-gui` is legitimate here: it is
# a real repository a reader can open. Anything else pointing outside is
# what this script is for.
QUALIFIED = re.compile(r'lightwebpres-gui\s*(?:§\s?\d[\d.]*\s*,?\s*)+'
                       r'|`?lightwebpres-gui`?\s*§')

REF = re.compile(r'§\s?(\d+(?:\.\d+)*)')
HEADING = re.compile(r'^#{2,4} (\d+(?:\.\d+)*)\.? ')


def sections():
    """Every section id of the spec, fences skipped.

    Fence-aware for the reason `tools/spec_index.py` is: §4.2 holds an
    example article whose slide headings are `##`.
    """
    ids, fenced = set(), False
    for line in SPEC.read_text(encoding='utf-8').split('\n'):
        if line.lstrip().startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEADING.match(line)
        if m:
            ids.add(m.group(1))
    if not ids:
        raise SystemExit('no sections found in specifications.md')
    return ids


def tracked():
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files'],
                         capture_output=True, text=True, timeout=30).stdout
    for name in out.split('\n'):
        if not name or name.startswith(SKIP_PREFIX):
            continue
        if name.endswith(('.png', '.html', '.pyc', '.jpg', '.svg', '.zip')):
            continue
        yield name


def dangling():
    """(file, line number, reference, the line) for each broken reference."""
    ids = sections()
    bad = []
    for name in tracked():
        try:
            text = (ROOT / name).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.split('\n'), 1):
            # A line that names the sibling project is citing its spec.
            stripped = QUALIFIED.sub('', line)
            for ref in REF.findall(stripped):
                if ref not in ids:
                    bad.append((name, i, ref, line.strip()))
    return bad


def main():
    bad = dangling()
    if not bad:
        if '--quiet' not in sys.argv:
            print(f'{len(sections())} sections, no dangling reference')
        return
    if '--quiet' not in sys.argv:
        for name, i, ref, line in bad:
            print(f'{name}:{i}: §{ref} does not exist — {line[:90]}')
    sys.exit(1)


if __name__ == '__main__':
    main()
