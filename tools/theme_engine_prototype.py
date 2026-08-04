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

Two namespaces, and a reader always knows which side of the line they are on:

    color.ink                shared value   -> type . identity
    summary.fg: ink          component      -> component . axis

References are resolved by the AXIS, which fixes the type, which fixes the
namespace to look in. A bare word is looked up in that namespace; a dotted
word is a qualified reference to another property. Declarations carry their
prefix so they are unambiguous globally; references drop it so the file reads
as configuration rather than as code.

Run it to see the emitted stylesheet for a theme plus an author's settings.
"""

import re
import sys

# ============================================================================
# 1. TYPES — every property has one, checked at generation.
#    `namespace` is where a bare-word reference is looked up; None means the
#    axis takes literals only.
# ============================================================================

GENERICS = ('serif', 'sans-serif', 'monospace', 'cursive', 'fantasy')
UNITS = ('px', 'rem', 'em', 'ch', 'vw', 'vh', '%', 'pt')
FUNCS = ('clamp', 'calc', 'min', 'max')


class Invalid(Exception):
    """A property value that does not match its type. Always names the key."""


class Type:
    name = 'value'
    namespace = None

    def is_literal(self, value):
        return True

    def check(self, key, value):
        return value


class Color(Type):
    name = 'colour'
    namespace = 'color'
    HEX = re.compile(r'^#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$')

    def is_literal(self, value):
        # Unambiguous by construction: a literal colour always starts with #.
        return value.startswith('#') or value == 'transparent'

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
    changes size. Invisible until it bites, which is what typing is for."""
    name = 'ratio'

    def check(self, key, value):
        if not re.match(r'^[\d.]+$', value):
            raise Invalid(f'{key}: {value!r} is not a ratio '
                          f'(a unitless number, e.g. 1.5)')
        return value


class Angle(Type):
    name = 'angle'

    def check(self, key, value):
        if not re.match(r'^-?[\d.]+(deg|rad|turn|grad)$', value):
            raise Invalid(f'{key}: {value!r} is not an angle '
                          f'(deg, rad, turn, grad)')
        return value


class FontStack(Type):
    """A stack must end on a CSS 2.1 generic. That is the only guarantee a
    browser owes us: everything before it is a chance, the generic is the
    promise."""
    name = 'font stack'
    namespace = 'font'

    def is_literal(self, value):
        # A real stack either ends on a generic (so it has a comma) or IS a
        # bare generic. Anything else without a comma is a reference.
        return ',' in value or value in GENERICS

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


COLOR, LENGTH, RATIO, ANGLE, FONT, TEXT = (
    Color(), Length(), Ratio(), Angle(), FontStack(), Text())
# Only normal and bold survive a generic family: asked for 600 a two-weight
# font renders 700, and 500 renders 400 — three declared weights collapse
# into two, and "partial" stops being distinguishable from "yes".
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
        self.default = default    # a literal, or a reference written as a word
        self.css = css            # CSS property name, or None if composite

    @property
    def var(self):
        return '--' + self.key.replace('.', '-')


class Component:
    def __init__(self, key, selector, props, composite=None):
        self.key = key
        self.selector = selector
        self.props = props
        self.composite = composite


def gradient(v_angle, v_from, v_to):
    """A flat fill is a gradient whose two stops are equal — one mechanism,
    no branch, and today's themes stay flat without changing anything."""
    return ('background',
            f'linear-gradient(var({v_angle}), var({v_from}), var({v_to}))')


SHARED = [
    Prop('color.page',      COLOR, '#F8F8F5'),
    Prop('color.ink',       COLOR, '#1A1A2E'),
    Prop('color.ink-quiet', COLOR, '#6B6B7D'),
    Prop('color.mark',      COLOR, '#FFFC00'),
    Prop('color.call',      COLOR, '#FF4757'),
    Prop('color.affirm',    COLOR, '#3AA55C'),
    Prop('font.text',    FONT, 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'),
    Prop('font.display', FONT, 'text'),
    Prop('font.ui',      FONT, 'text'),
    Prop('font.mono',    FONT, 'ui-monospace, "SF Mono", Menlo, Consolas, monospace'),
]

COMPONENTS = [
    Component('cover', '.slide-cover', [
        Prop('cover.bg.from',  COLOR, 'ink'),
        Prop('cover.bg.to',    COLOR, 'cover.bg.from'),
        Prop('cover.bg.angle', ANGLE, '160deg'),
        Prop('cover.fg',       COLOR, 'page', css='color'),
    ], composite=lambda: gradient('--cover-bg-angle', '--cover-bg-from', '--cover-bg-to')),

    Component('title1', '.slide-cover h1', [
        Prop('title1.fg',      COLOR,  'cover.fg', css='color'),
        Prop('title1.font',    FONT,   'display',  css='font-family'),
        Prop('title1.weight',  WEIGHT, 'bold',     css='font-weight'),
        Prop('title1.size',    LENGTH, 'clamp(2rem, 6vw, 3.5rem)', css='font-size'),
        Prop('title1.leading', RATIO,  '1.1',      css='line-height'),
    ]),

    Component('tag', '.slide-tag', [
        Prop('tag.fg',        COLOR,  'ink-quiet', css='color'),
        Prop('tag.font',      FONT,   'ui',        css='font-family'),
        Prop('tag.weight',    WEIGHT, 'normal',    css='font-weight'),
        Prop('tag.size',      LENGTH, '0.8125rem', css='font-size'),
        Prop('tag.transform', CASE,   'uppercase', css='text-transform'),
        Prop('tag.tracking',  LENGTH, '0.08em',    css='letter-spacing'),
    ]),

    Component('summary', '.summary', [
        Prop('summary.fg',      COLOR,  'ink',  css='color'),
        Prop('summary.font',    FONT,   'text', css='font-family'),
        Prop('summary.size',    LENGTH, 'clamp(1rem, 2vw, 1.375rem)', css='font-size'),
        Prop('summary.leading', RATIO,  '1.5',  css='line-height'),
    ]),

    Component('highlight', '.highlight', [
        Prop('highlight.fg',      COLOR,   'mark',    css='color'),
        Prop('highlight.font',    FONT,    'display', css='font-family'),
        Prop('highlight.size',    LENGTH,  'clamp(2.5rem, 8vw, 5rem)', css='font-size'),
        Prop('highlight.numeric', NUMERIC, 'tabular-nums lining-nums',
             css='font-variant-numeric'),
    ]),

    Component('fact.strong', '.fact-content strong', [
        Prop('fact.strong.bg',     COLOR,  'mark',   css='background'),
        Prop('fact.strong.fg',     COLOR,  'ink',    css='color'),
        Prop('fact.strong.weight', WEIGHT, 'bold',   css='font-weight'),
        Prop('fact.strong.style',  STYLE,  'normal', css='font-style'),
    ]),

    Component('verdict.yes', '.comparison-table .yes', [
        Prop('verdict.yes.fg',     COLOR,  'affirm', css='color'),
        Prop('verdict.yes.weight', WEIGHT, 'bold',   css='font-weight'),
        Prop('verdict.yes.mark',   TEXT,   '"\\25CF"'),
    ]),
    Component('verdict.partial', '.comparison-table .partial', [
        Prop('verdict.partial.fg',     COLOR,  'call', css='color'),
        Prop('verdict.partial.weight', WEIGHT, 'bold', css='font-weight'),
        Prop('verdict.partial.mark',   TEXT,   '"\\25D0"'),
    ]),
    Component('verdict.no', '.comparison-table .no', [
        Prop('verdict.no.fg',     COLOR,  'ink-quiet', css='color'),
        Prop('verdict.no.weight', WEIGHT, 'normal',    css='font-weight'),
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


def reference_target(prop, value):
    """The property `value` points at, or None if it is a literal.

    The AXIS fixes the type, the type fixes the namespace. A bare word is
    looked up there; a dotted word is a qualified reference. That is the whole
    rule, and it removes any need to guess whether a value 'looks like' a key."""
    if prop.type.is_literal(value):
        return None
    if '.' in value:
        return value                      # qualified: title1.font, cover.bg.from
    if prop.type.namespace:
        return f'{prop.type.namespace}.{value}'
    return None


def resolve(*layers):
    """built-in defaults -> theme -> series settings -> article. Later wins.

    Unknown keys are errors, not silence: that is the point of typing the
    surface. References are followed here and never reach the CSS."""
    raw = {k: p.default for k, p in REGISTRY.items()}
    for layer in layers:
        for key, value in layer.items():
            if key not in REGISTRY:
                tail = key.split('.')[-1]
                near = [k for k in REGISTRY if k.split('.')[-1] == tail]
                raise Invalid(f'{key}: unknown property'
                              + (f' (did you mean {near[0]}?)' if near else ''))
            raw[key] = value

    out = {}
    for key, prop in REGISTRY.items():
        value, chain = raw[key], [key]
        while True:
            target = reference_target(prop, value)
            if target is None:
                break
            if target not in REGISTRY:
                raise Invalid(
                    f'{key}: refers to unknown property {target!r}. '
                    f'A bare word is looked up in {prop.type.namespace}.*; '
                    f'a literal {prop.type.name} does not go through the '
                    f'namespace.')
            if target in chain:
                raise Invalid(f'{key}: reference cycle '
                              f'{" -> ".join(chain + [target])}')
            if len(chain) - 1 >= MAX_HOPS:
                raise Invalid(f'{key}: reference chain deeper than {MAX_HOPS} '
                              f'hops ({" -> ".join(chain + [target])})')
            chain.append(target)
            value = raw[target]
        out[key] = prop.type.check(key, value)
    return out


# ============================================================================
# 4. EMISSION — resolved properties become the :root block and the rules
# ============================================================================

def emit(resolved):
    lines = [':root {', '  /* shared */']
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
        decls += [f'  {p.css}: var({p.var});' for p in c.props if p.css]
        if decls:
            lines += [f'{c.selector} {{', *decls, '}']
        mark = next((p for p in c.props if p.key.endswith('.mark')), None)
        if mark:
            lines.append(f'{c.selector}::before {{ content: var({mark.var}); }}')
    return '\n'.join(lines)


# ============================================================================
# DEMO
# ============================================================================

DRACULA = {
    'color.page': '#282A36', 'color.ink': '#F8F8F2', 'color.ink-quiet': '#6272A4',
    'color.mark': '#F1FA8C', 'color.call': '#FF5555', 'color.affirm': '#50FA7B',
}

# A theme may set fonts — "Terminal" in fixed pitch is three lines, and it is
# `font.mono` earning its place: not as a coordination point (it has a single
# consumer) but as the one correct monospace stack, written once.
TERMINAL = dict(DRACULA, **{
    'font.text': 'mono', 'font.display': 'mono', 'font.ui': 'mono',
})

SERIES_SETTINGS = {                      # what the author uncommented
    'font.mono': '"Berkeley Mono", ui-monospace, Menlo, monospace',
    'cover.bg.to': '#44475A',
    'cover.bg.angle': '200deg',
    'tag.transform': 'none',
    'verdict.partial.fg': '#E8A33D',
}

ARTICLE = {'highlight.font': 'mono'}     # one article, one override


def main():
    print(emit(resolve(DRACULA, SERIES_SETTINGS, ARTICLE)))
    print('\n' + '=' * 70)
    print(f'{len(REGISTRY)} properties, {len(COMPONENTS)} components '
          f'(extract — the full inventory is larger)')

    r = resolve(TERMINAL, SERIES_SETTINGS)
    print(f'\nTerminal theme, three lines: font.text/display/ui -> mono')
    print(f'  summary.font  -> {r["summary.font"]}')
    print(f'  title1.font   -> {r["title1.font"]}')
    print('=' * 70 + '\n')

    for label, layer in [
        ('unknown key',          {'tag.color': '#000000'}),
        ('weight off the enum',  {'tag.weight': '600'}),
        ('stack with no generic', {'font.text': '"Helvetica Neue", Helvetica'}),
        ('bare word, no such stack', {'summary.font': 'headline'}),
        ('not a colour',         {'summary.fg': 'dark-grey'}),
        ('bad unit',             {'tag.tracking': '0.08emm'}),
        ('line-height as length', {'summary.leading': '1.5rem'}),
        ('reference cycle',      {'tag.fg': 'summary.fg', 'summary.fg': 'tag.fg'}),
        ('chain too deep',       {'tag.fg': 'summary.fg', 'summary.fg': 'ink-quiet',
                                  'color.ink-quiet': 'ink'}),
    ]:
        try:
            resolve(DRACULA, layer)
            print(f'  {label}: NOT CAUGHT')
        except Invalid as e:
            print(f'  {label}\n      -> {e}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
