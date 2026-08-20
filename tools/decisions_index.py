#!/usr/bin/env python3
"""Regenerate the index of `DECISIONS.md` from the entries themselves.

The register carried a rule for a long time saying it must have no index,
because a list of entry numbers and their statuses is a second place to be
wrong — and it had been wrong, listing three fixed entries among the open
ones. The rule was right about the danger and wrong about the remedy: a
second place to be wrong is only dangerous while nothing checks it.

So the index is derived, never typed. The source of truth is the field
line under each `## Bn — title`, and
`test_the_decisions_index_matches_the_file` rebuilds this block and fails
the suite if the file disagrees with it. Editing the block by hand does
not survive the next run of either.

    python3 tools/decisions_index.py            # rewrite the block in place
    python3 tools/decisions_index.py --check    # exit 1 if it is stale

`--check` prints nothing on success; the test uses the rendering directly
rather than this exit code, so the two cannot answer differently.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTER = ROOT / 'DECISIONS.md'

OPEN = '<!-- INDEX:'
CLOSE = '<!-- /INDEX -->'

# The order is the reading order: what still needs a decision first, what
# is settled after. `sans objet` is last because it is the only state that
# asks nothing of anyone.
STATES = ['à étudier', 'à faire', 'en cours', 'terminé', 'abandonné',
          'sans objet']

HEADING = re.compile(r'^## ([BC]\d+) — (.+)$')
STATE_FIELD = re.compile(r'^\*\*État :\*\* ([^·\n]+?)(?: ·|$)')


def entries(text):
    """Every entry as (key, title, state), in the file's own order.

    An entry whose field line is missing or names a state outside the six
    raises: the index cannot be derived from a file that does not declare
    itself, and silently skipping such an entry is how a register loses
    one.
    """
    found = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if not m:
            continue
        key, title = m.group(1), m.group(2)
        field = next((ln for ln in lines[i + 1:i + 4] if ln.startswith('**État :**')), None)
        if field is None:
            raise SystemExit(f'{key}: no field line under the title')
        sm = STATE_FIELD.match(field)
        if not sm:
            raise SystemExit(f'{key}: unreadable field line: {field!r}')
        state = sm.group(1).strip()
        if state not in STATES:
            raise SystemExit(f'{key}: unknown state {state!r}')
        found.append((key, title, state))
    if not found:
        raise SystemExit('no entries found')
    return found


def render(found):
    """The index block, between its markers, ready to be spliced in."""
    out = [OPEN + ' généré par `python3 tools/decisions_index.py`. Ne pas éditer à',
           '     la main : la source est la ligne de champs de chaque entrée. -->',
           '']
    counts = {s: sum(1 for _, _, st in found if st == s) for s in STATES}
    out.append(' · '.join(f'**{s}** {counts[s]}' for s in STATES))
    for state in STATES:
        rows = [(k, t) for k, t, st in found if st == state]
        if not rows:
            continue
        out.append('')
        out.append(f'### {state}')
        out.append('')
        for key, title in rows:
            out.append(f'- **{key}** — {title}')
    out.append('')
    out.append(CLOSE)
    return '\n'.join(out)


def splice(text):
    start = text.index(OPEN)
    end = text.index(CLOSE) + len(CLOSE)
    return text[:start] + render(entries(text)) + text[end:]


def main():
    text = REGISTER.read_text(encoding='utf-8')
    fresh = splice(text)
    if '--check' in sys.argv:
        if fresh != text:
            sys.exit(f'{REGISTER.name}: the index is stale — run '
                     f'`python3 tools/decisions_index.py`')
        return
    REGISTER.write_text(fresh, encoding='utf-8')
    print(f'{REGISTER.name}: index regenerated '
          f'({len(entries(text))} entries)')


if __name__ == '__main__':
    main()
