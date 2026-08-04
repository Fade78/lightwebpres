#!/usr/bin/env python3
"""Prototype of the property -> cascade -> CSS interface (ARCHI-TEMPLATES.md).

Not wired into lightwebpres. Its job is to prove the three moving parts fit
together before any of it lands in the executable:

  1. a REGISTRY of typed properties, each naming the component it paints, the
     CSS declaration it feeds, and its default;
  2. one CASCADE, identical for every property, merging layers of plain
     `key: value` dictionaries;
  3. an EMITTER that turns the resolved set into the :root block and the rules
     that read it.

Run it to see the emitted stylesheet for a theme plus an author's settings.
"""

import re
import sys

# ============================================================================
# 1. TYPES — every property has one, and it is checked at generation
# ============================================================================

GENERICS = ('serif', 'sans-serif', 'monospace', 'cursive', 'fantasy')
UNITS = ('px', 'rem', 'em', 'ch', 'vw', 'vh', '%', 'pt')
FUNCS = ('clamp', 'calc', 'min', 'max')


class Invalid(Exception):
    """A property value that does not match its type. Always names the key."""


class Type:
    name = 'value'

    def check(self, key, value):
        return value


class Color(Type):
    name = 'colour'
    HEX = re.compile(r'^#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$')

    def check(self, key, value):
        if value == 'transparent':
            return '#00000000'
        if not self.HEX.match(value):
            raise Invalid(f'{key}: {value!r} is not a colour '
                          f'(expected #RGB, #RRGGBB or #RRGGBBAA)')
        h = value.lstrip('#')
        if len(h) in (3, 4):                       # expand shorthand
            h = ''.join(c * 2 for c in h)
        if len(h) == 6:                            # opaque by default
            h += 'FF'
        return '#' + h.upper()


class Length(Type):
    name = 'length'

    def check(self, key, value):
        if any(value.startswith(f + '(') for f in FUNCS):
            return value                           # a CSS function, passed through
        if value in ('0', 'auto'):
            return value
        m = re.match(r'^-?[\d.]+([a-z%]+)$', value)
        if not m or m.group(1) not in UNITS:
            raise Invalid(f'{key}: {value!r} is not a length '
                          f'(units: {", ".join(UNITS)})')
        return value


class Ratio(Type):
    """Unitless, and deliberately not a Length. A unitless line-height is
    inherited as a factor and re-multiplied by each child's own font-size;
    `1.5rem` is inherited as a fixed length and breaks the moment a child
    changes size. The distinction is invisible until it bites, which is
    exactly the kind of thing typing the surface is for."""
    name = 'ratio'

    def check(self, key, value):
        if not re.match(r'^[\d.]+$', value):
            raise Invalid(f'{key}: {value!r} is not a ratio '
                          f'(a unitless number, e.g. 1.5)')
        return value


class Angle(Type):
    name = 'angle'

    def check(self, key, value):
        m = re.match(r'^-?[\d.]+(deg|rad|turn|grad)$', value)
        if not m:
            raise Invalid(f'{key}: {value!r} is not an angle '
                          f'(deg, rad, turn, grad)')
        return value


class FontStack(Type):
    """G3 — a stack must end on a CSS 2.1 generic. That is the only guarantee
    a browser owes us: everything before it is a chance, the generic is the
    promise."""
    name = 'font stack'

    def check(self, key, value):
        last = [p.strip().strip('"\'') for p in value.split(',')][-1]
        if last not in GENERICS:
            raise Invalid(f'{key}: font stack must end on a generic family '
                          f'({", ".join(GENERICS)}), found {last!r}. '
                          f'No named font is guaranteed to be installed.')
        return value


class Enum(Type):
    def __init__(self, *values, hint=''):
        self.values = values
        self.hint = hint
        self.name = 'one of ' + '|'.join(values)

    def check(self, key, value):
        if value not in self.values:
            msg = f'{key}: {value!r} not allowed (expected {"|".join(self.values)})'
            raise Invalid(msg + (f'. {self.hint}' if self.hint else ''))
        return value


class Text(Type):
    name = 'text'


COLOR, LENGTH, ANGLE, FONT, TEXT = Color(), Length(), Angle(), FontStack(), Text()
RATIO = Ratio()
# G4 — only normal and bold survive a generic family: asked for 600, a
# two-weight font renders 700, and 500 renders 400.
WEIGHT = Enum('normal', 'bold',
              hint='Intermediate weights collapse on a generic family.')
STYLE = Enum('normal', 'italic')
CASE = Enum('none', 'uppercase', 'lowercase', 'small-caps')
NUMERIC = Enum('normal', 'tabular-nums', 'tabular-nums lining-nums')


# ============================================================================
# 2. REGISTRY — one entry per property. `css` is the declaration it feeds.
# ============================================================================

class Prop:
    def __init__(self, key, type_, default, css=None):
        self.key = key            # 'tag.fg'
        self.type = type_
        self.default = default    # literal, or Ref('ink.quiet')
        self.css = css            # CSS property name, or None if composite

    @property
    def var(self):
        return '--' + self.key.replace('.', '-')


class Ref:
    """A default that points at another property. Resolved during the cascade;
    it never survives into the emitted CSS."""
    def __init__(self, key):
        self.key = key


class Component:
    def __init__(self, key, selector, props, composite=None):
        self.key = key
        self.selector = selector
        self.props = props
        self.composite = composite   # extra declarations built from several props


def gradient(prop_from, prop_to, prop_angle):
    """A flat fill is a gradient whose two stops are equal — one mechanism,
    no branch, and today's themes stay flat without changing anything."""
    return ('background',
            f'linear-gradient(var(--{prop_angle}), var(--{prop_from}), var(--{prop_to}))')


SHARED = [
    Prop('page',        COLOR, '#F8F8F5FF'),
    Prop('ink',         COLOR, '#1A1A2EFF'),
    Prop('ink.quiet',   COLOR, '#6B6B7DFF'),
    Prop('tone.mark',   COLOR, '#FFFC00FF'),
    Prop('tone.call',   COLOR, '#FF4757FF'),
    Prop('tone.affirm', COLOR, '#3AA55CFF'),
    Prop('font.text',    FONT, 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'),
    Prop('font.display', FONT, Ref('font.text')),
    Prop('font.ui',      FONT, Ref('font.text')),
    Prop('font.mono',    FONT, 'ui-monospace, "SF Mono", Menlo, Consolas, monospace'),
]

COMPONENTS = [
    Component('cover', '.slide-cover', [
        Prop('cover.bg.from',  COLOR, Ref('ink')),
        Prop('cover.bg.to',    COLOR, Ref('cover.bg.from')),
        Prop('cover.bg.angle', ANGLE, '160deg'),
        Prop('cover.fg',       COLOR, Ref('page'), css='color'),
    ], composite=lambda: gradient('cover-bg-from', 'cover-bg-to', 'cover-bg-angle')),

    Component('tag', '.slide-tag', [
        Prop('tag.fg',        COLOR,  Ref('ink.quiet'), css='color'),
        Prop('tag.font',      FONT,   Ref('font.ui'),   css='font-family'),
        Prop('tag.weight',    WEIGHT, 'normal',         css='font-weight'),
        Prop('tag.size',      LENGTH, '0.8125rem',      css='font-size'),
        Prop('tag.transform', CASE,   'uppercase',      css='text-transform'),
        Prop('tag.tracking',  LENGTH, '0.08em',         css='letter-spacing'),
    ]),

    Component('summary', '.summary', [
        Prop('summary.fg',      COLOR,  Ref('ink'),       css='color'),
        Prop('summary.font',    FONT,   Ref('font.text'), css='font-family'),
        Prop('summary.size',    LENGTH, 'clamp(1rem, 2vw, 1.375rem)', css='font-size'),
        Prop('summary.leading', RATIO,  '1.5',            css='line-height'),
    ]),

    Component('highlight', '.highlight', [
        Prop('highlight.fg',      COLOR,   Ref('tone.mark'),    css='color'),
        Prop('highlight.font',    FONT,    Ref('font.display'), css='font-family'),
        Prop('highlight.size',    LENGTH,  'clamp(2.5rem, 8vw, 5rem)', css='font-size'),
        Prop('highlight.numeric', NUMERIC, 'tabular-nums lining-nums',
             css='font-variant-numeric'),
    ]),

    Component('fact.strong', '.fact-content strong', [
        Prop('fact.strong.bg',     COLOR,  Ref('tone.mark'), css='background'),
        Prop('fact.strong.fg',     COLOR,  Ref('ink'),       css='color'),
        Prop('fact.strong.weight', WEIGHT, 'bold',           css='font-weight'),
        Prop('fact.strong.style',  STYLE,  'normal',         css='font-style'),
    ]),

    Component('verdict.yes', '.comparison-table .yes', [
        Prop('verdict.yes.fg',     COLOR,  Ref('tone.affirm'), css='color'),
        Prop('verdict.yes.weight', WEIGHT, 'bold',             css='font-weight'),
        Prop('verdict.yes.mark',   TEXT,   '"\\25CF"'),
    ]),
    Component('verdict.partial', '.comparison-table .partial', [
        Prop('verdict.partial.fg',     COLOR,  Ref('tone.call'), css='color'),
        Prop('verdict.partial.weight', WEIGHT, 'bold',           css='font-weight'),
        Prop('verdict.partial.mark',   TEXT,   '"\\25D0"'),
    ]),
    Component('verdict.no', '.comparison-table .no', [
        Prop('verdict.no.fg',     COLOR,  Ref('ink.quiet'), css='color'),
        Prop('verdict.no.weight', WEIGHT, 'normal',         css='font-weight'),
        Prop('verdict.no.mark',   TEXT,   '"\\25CB"'),
    ]),
]

REGISTRY = {p.key: p for p in SHARED}
for c in COMPONENTS:
    for p in c.props:
        REGISTRY[p.key] = p


# ============================================================================
# 3. CASCADE — identical for every property. Layers are plain dicts.
# ============================================================================

MAX_HOPS = 2


def resolve(*layers):
    """defaults -> theme -> series settings -> article. Later layers win.

    Unknown keys are errors, not silence: that is the whole point of typing
    the surface. References are followed here and never reach the CSS."""
    raw = {k: p.default for k, p in REGISTRY.items()}
    for layer in layers:
        for key, value in layer.items():
            if key not in REGISTRY:
                near = [k for k in REGISTRY if k.endswith(key.split('.')[-1])]
                raise Invalid(f'{key}: unknown property'
                              + (f' (did you mean {near[0]}?)' if near else ''))
            raw[key] = value

    out = {}
    for key in REGISTRY:
        value, chain = raw[key], [key]
        # One loop for both forms of reference: a Ref() written in a built-in
        # default, and a bare word naming another property — which is how an
        # author writes `cover.fg: ink` in a settings file. Treating them
        # separately is what let a cycle slip past its own guard.
        while True:
            if isinstance(value, Ref):
                target = value.key
            elif isinstance(value, str) and value in REGISTRY:
                target = value
            else:
                break
            if target in chain:
                raise Invalid(f'{key}: reference cycle '
                              f'{" -> ".join(chain + [target])}')
            if len(chain) - 1 >= MAX_HOPS:
                raise Invalid(f'{key}: reference chain deeper than {MAX_HOPS} hops '
                              f'({" -> ".join(chain + [target])})')
            chain.append(target)
            value = raw[target]
        if isinstance(value, Ref):
            raise Invalid(f'{key}: refers to unknown property {value.key!r}')
        out[key] = REGISTRY[key].type.check(key, value)
    return out


# ============================================================================
# 4. EMISSION — resolved properties become the :root block and the rules
# ============================================================================

def emit(resolved):
    lines = [':root {']
    lines.append('  /* shared */')
    for p in SHARED:
        lines.append(f'  {p.var}: {resolved[p.key]};')
    for c in COMPONENTS:
        lines.append(f'  /* {c.key} */')
        for p in c.props:
            lines.append(f'  {p.var}: {resolved[p.key]};')
    lines.append('}')

    for c in COMPONENTS:
        decls = []
        if c.composite:
            prop, value = c.composite()
            decls.append(f'  {prop}: {value};')
        for p in c.props:
            if p.css:
                decls.append(f'  {p.css}: var({p.var});')
        if decls:
            lines.append(f'{c.selector} {{')
            lines.extend(decls)
            lines.append('}')
        # the ::before glyph, driven by the `mark` axis
        mark = next((p for p in c.props if p.key.endswith('.mark')), None)
        if mark:
            lines.append(f'{c.selector}::before {{ content: var({mark.var}); }}')
    return '\n'.join(lines)


# ============================================================================
# DEMO
# ============================================================================

DRACULA = {
    'page': '#282A36', 'ink': '#F8F8F2', 'ink.quiet': '#6272A4',
    'tone.mark': '#F1FA8C', 'tone.call': '#FF5555', 'tone.affirm': '#50FA7B',
}

SERIES_SETTINGS = {                      # what the author uncommented
    'font.mono': '"Berkeley Mono", ui-monospace, Menlo, monospace',
    'cover.bg.to': '#44475A',
    'cover.bg.angle': '200deg',
    'tag.transform': 'none',
    'verdict.partial.fg': '#E8A33D',
}

ARTICLE = {'highlight.font': 'font.mono'}   # one article, one override


def main():
    print(emit(resolve(DRACULA, SERIES_SETTINGS, ARTICLE)))
    print('\n' + '=' * 68)
    print(f'{len(REGISTRY)} properties, {len(COMPONENTS)} components '
          f'(extract — the full inventory is larger)')
    print('=' * 68 + '\n')

    for label, layer in [
        ('unknown key',        {'tag.color': '#000000'}),
        ('weight off the enum', {'tag.weight': '600'}),
        ('stack with no generic', {'font.text': '"Helvetica Neue", Helvetica'}),
        ('not a colour',       {'summary.fg': 'dark-grey'}),
        ('bad unit',           {'tag.tracking': '0.08emm'}),
        ('reference cycle',    {'tag.fg': 'summary.fg', 'summary.fg': 'tag.fg'}),
        ('chain too deep',     {'tag.fg': 'summary.fg', 'summary.fg': 'ink.quiet',
                                'ink.quiet': 'ink'}),
    ]:
        try:
            resolve(DRACULA, layer)
            print(f'  {label}: NOT CAUGHT')
        except Invalid as e:
            print(f'  {label}\n      -> {e}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
