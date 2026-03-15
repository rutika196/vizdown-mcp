"""Desaturated pastel palette — airy fills, vivid strokes, WCAG-safe text.

Design: 20%-opacity-feel fills achieved via high lightness + low saturation.
Strokes stay vivid at full saturation to carry color identity. Works
beautifully on white backgrounds — the FigJam / Whimsical aesthetic.
"""

import colorsys

# Curated hue bank — hand-tested at high lightness on white backgrounds.
# Ordered for maximum visual separation between adjacent branches.
_CURATED_HUES: list[tuple[float, str]] = [
    (262, "violet"),
    (160, "emerald"),
    (340, "rose"),
    (38,  "amber"),
    (210, "sky"),
    (25,  "orange"),
    (280, "purple"),
    (142, "green"),
    (190, "cyan"),
    (350, "pink"),
    (55,  "yellow"),
    (220, "blue"),
]


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _perceived_luminance(hex_color: str) -> float:
    """WCAG relative luminance — used for text contrast decisions."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16) / 255, int(hex_color[2:4], 16) / 255, int(hex_color[4:6], 16) / 255

    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def text_color_for_bg(bg_hex: str, light_text: str = "#FFFFFF", dark_text: str = "#1E293B") -> str:
    """Return white or dark text depending on background luminance (WCAG contrast)."""
    return light_text if _perceived_luminance(bg_hex) < 0.42 else dark_text


def generate_apple_palette(
    count: int, theme: str = "light",
) -> list[dict[str, str]]:
    """Generate *count* palette entries from the curated hue bank.

    Each entry carries the hue needed by ``depth_color`` downstream.
    Cycles when count > len(_CURATED_HUES).
    """
    if count <= 0:
        return []

    n_hues = len(_CURATED_HUES)
    palette: list[dict] = []
    for i in range(count):
        hue, _ = _CURATED_HUES[i % n_hues]
        fill_s, fill_l = (50.0, 91.0) if theme == "light" else (45.0, 28.0)
        stroke_s, stroke_l = (72.0, 48.0) if theme == "light" else (65.0, 58.0)
        fill = _hsl_to_hex(hue, fill_s, fill_l)
        border = _hsl_to_hex(hue, stroke_s, stroke_l)
        palette.append({
            "fill": fill,
            "border": border,
            "hue": hue,
            "fill_saturation": fill_s,
            "stroke_saturation": stroke_s,
        })
    return palette


def depth_color(
    hue: float,
    saturation: float,       # ignored — kept for API compat
    level: int,
    theme: str = "light",
) -> dict[str, str]:
    """Compute fill + border for a node at a given tree depth.

    Level 1 is a soft tint.  Each deeper level gets marginally lighter
    (the "watercolour fade") while the stroke stays vivid — creating
    the 20%-fill / 100%-stroke visual identity.
    """
    if theme == "light":
        fill_s = 50.0
        fill_base_l = 91.0
        fill_step = 1.8
        fill_max_l = 96.0
        fill_s_decay = 3.0
        fill_min_s = 30.0
        stroke_s = 72.0
        stroke_l = 48.0
    else:
        fill_s = 45.0
        fill_base_l = 22.0
        fill_step = 3.0
        fill_max_l = 38.0
        fill_s_decay = 3.0
        fill_min_s = 25.0
        stroke_s = 65.0
        stroke_l = 58.0

    depth = max(level - 1, 0)
    fl = min(fill_base_l + depth * fill_step, fill_max_l)
    fs = max(fill_s - depth * fill_s_decay, fill_min_s)

    fill = _hsl_to_hex(hue, fs, fl)
    border = _hsl_to_hex(hue, stroke_s, stroke_l)
    text = text_color_for_bg(fill)

    return {"fill": fill, "border": border, "text": text}
