import math

def srgb_to_lin(c):
    c = c / 255.0
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055) ** 2.4

def lin_to_srgb(c):
    c = 12.92*c if c <= 0.0031308 else 1.055*(c ** (1/2.4)) - 0.055
    return max(0, min(255, round(c*255)))

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return '#%02X%02X%02X' % (r, g, b)

# --- OKLab (Björn Ottosson) ---
def rgb_to_oklab(r, g, b):
    lr, lg, lb = srgb_to_lin(r), srgb_to_lin(g), srgb_to_lin(b)
    l = 0.4122214708*lr + 0.5363325363*lg + 0.0514459929*lb
    m = 0.2119034982*lr + 0.6806995451*lg + 0.1073969566*lb
    s = 0.0883024619*lr + 0.2817188376*lg + 0.6299787005*lb
    l_, m_, s_ = l ** (1/3), m ** (1/3), s ** (1/3)
    return (0.2104542553*l_ + 0.7936177850*m_ - 0.0040720468*s_,
            1.9779984951*l_ - 2.4285922050*m_ + 0.4505937099*s_,
            0.0259040371*l_ + 0.7827717662*m_ - 0.8086757660*s_)

def oklab_to_rgb(L, a, b):
    l_ = L + 0.3963377774*a + 0.2158037573*b
    m_ = L - 0.1055613458*a - 0.0638541728*b
    s_ = L - 0.0894841775*a - 1.2914855480*b
    l, m, s = l_**3, m_**3, s_**3
    return (lin_to_srgb( 4.0767416621*l - 3.3077115913*m + 0.2309699292*s),
            lin_to_srgb(-1.2684380046*l + 2.6097574011*m - 0.3413193965*s),
            lin_to_srgb(-0.0041960863*l - 0.7034186147*m + 1.7076147010*s))

def to_lch(h):
    L, a, b = rgb_to_oklab(*hex_to_rgb(h))
    return L, math.hypot(a, b), math.atan2(b, a)

def from_lch(L, C, H):
    return rgb_to_hex(*oklab_to_rgb(L, C*math.cos(H), C*math.sin(H)))

# --- WCAG 2 ---
def lum(h):
    r, g, b = hex_to_rgb(h)
    return 0.2126*srgb_to_lin(r) + 0.7152*srgb_to_lin(g) + 0.0722*srgb_to_lin(b)

def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def solve(colour, ground, floor):
    """Lowest-displacement lightness that clears `floor` against `ground`,
    keeping OKLCh chroma and hue. Returns (hex, L, ratio) or None."""
    L0, C, H = to_lch(colour)
    darker = lum(ground) > lum(colour) or ratio(colour, ground) < floor
    best = None
    # scan both directions, prefer the smaller |dL|
    for direction in (-1, 1):
        for i in range(1, 1001):
            L = L0 + direction * i * 0.001
            if not (0.0 <= L <= 1.0):
                break
            cand = from_lch(L, C, H)
            if ratio(cand, ground) >= floor:
                d = abs(L - L0)
                if best is None or d < best[3]:
                    best = (cand, L, ratio(cand, ground), d)
                break
    return best

CASES = [
    ('dracula',     '#50FA7B', '#F8F8F2', 'positive'),
    ('dracula',     '#FF5555', '#F8F8F2', 'accent'),
    ('dracula',     '#6272A4', '#F8F8F2', 'ink-muted'),
    ('tokyo-night', '#9ECE6A', '#D5D6DB', 'positive'),
    ('monokai',     '#A6E22E', '#F8F8F2', 'positive'),
    ('solarized',   '#859900', '#FDF6E3', 'positive'),
    ('nord',        '#A3BE8C', '#ECEFF4', 'positive'),
    ('gruvbox',     '#B8BB26', '#FBF1C7', 'positive'),
]
print(f"{'thème':<12} {'rôle':<10} {'publié':<9} {'r':>5}  ->  {'encre résolue':<14} {'r':>5}  ΔL")
print('-' * 78)
for theme, col, ground, role in CASES:
    r0 = ratio(col, ground)
    s = solve(col, ground, 4.5)
    if s:
        cand, L, r1, d = s
        L0, _, _ = to_lch(col)
        print(f"{theme:<12} {role:<10} {col:<9} {r0:5.2f}  ->  {cand:<14} {r1:5.2f}  {L-L0:+.3f}")
    else:
        print(f"{theme:<12} {role:<10} {col:<9} {r0:5.2f}  ->  IMPOSSIBLE")
