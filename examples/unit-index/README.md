# Unit Indexes And Selectors

A source-only example of contents lists inside logical content units. The
first unit has three explicit indexes: everything, selected English evidence,
and an intentionally empty result. It also has a cover, tagged evidence,
series navigation, supporting long-form text and generated page-end notes.
The second unit has no explicit index and receives the automatic one configured
in `series_meta`. No kit or external asset is required.

## Build And Verify

From the repository root, create repository-local scratch if it does not exist,
then publish there, not inside this example. `--no-readme` preserves this manual;
`--nav-cache` keeps derived navigation state outside the example too:

```bash
mkdir -p work/tmp
TMPDIR="$PWD/work/tmp" python3 lightwebpres build examples/unit-index --lang en --output work/tmp/unit-index-example --no-readme --nav-cache work/tmp/unit-index-example-nav.json
TMPDIR="$PWD/work/tmp" python3 lightwebpres verify examples/unit-index --lang en --output work/tmp/unit-index-example --no-readme
TMPDIR="$PWD/work/tmp" python3 lightwebpres build examples/unit-index --lang en --output work/tmp/unit-index-example-single --single-html collection.html --no-readme --nav-cache work/tmp/unit-index-example-single-nav.json
TMPDIR="$PWD/work/tmp" python3 lightwebpres verify examples/unit-index --lang en --output work/tmp/unit-index-example-single --single-html collection.html --no-readme
```

Open `work/tmp/unit-index-example/brief.html` or the combined
`work/tmp/unit-index-example-single/collection.html`. Source files and canonical
`articles[]`, `page_source`, `page_dest` names do not change between modes.

## What To Inspect

- `everything` uses the default `*`: its list includes itself, the other two
  indexes, the cover, long-form text, navigation and generated notes.
- `english-evidence` uses a named compact expression that composes another
  compact query with a JSONPath array-membership query. It selects only the
  English standard evidence slide, not shared `default` slides.
- `empty` names a nonexistent title and displays No matching slides.
- The explicit indexes suppress automatic insertion in the first unit. In the
  second, `next-lwp-index` is inserted after `next-opening`, using its prefix.
- The series selector `-type:unit-index` controls the automatic index only;
  explicit indexes retain their own settings, including the first one's `*`.
- Changing the reader tag does not rebuild or filter the index entry list.
  Following a link uses existing tag-aware reveal; arrows keep normal behavior.
- Resize from desktop to phone width, tab through links, try fullscreen and
  print. Column counts are responsive ceilings and print retains the complete
  source-ordered list, not a fixed number of entries or guaranteed sheet count.

To try an excluded explicit index suppressing automation, add one to a working
copy of the second source with `tags: excluded`. To test collisions, give an
ordinary slide the slug `lwp-index` while automation is enabled: the build must
fail rather than rename either identity. Neither experiment belongs in this
working example's normal source.

## Profile Boundaries

The JSONPath syntax is a documented filter profile, not full RFC 9535 or
I-Regexp. Named expressions are AST references, regexes use a bounded NFA,
and missing operands make all comparisons false, including `!=`. Queries do
not select unpublished units or replace build status flags. See the
[guide tutorial](../../GUIDE.md#add-a-unit-index) and specifications.md
sections 3.3.6, 3.4 and 20.5.5 for syntax, source views, limits and insertion.
