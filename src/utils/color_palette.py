"""Dynamic Apple HIG color palette generation with depth-aware tiers."""

import colorsys


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16) / 255, int(hex_color[2:4], 16) / 255, int(hex_color[4:6], 16) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360.0, s * 100.0, l * 100.0


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
    count: int, theme: str = "light"
) -> list[dict[str, str]]:
    """Generate *count* unique colors evenly distributed around the HSL wheel.

    Returns list of ``{"fill": "#hex", "border": "#hex", "hue": float}`` dicts.
    The ``hue`` value enables downstream depth-based lightness computation.
    """
    if count <= 0:
        return []

    base_lightness = 48.0 if theme == "light" else 55.0
    saturation = 82.0
    border_lightness = base_lightness - 10.0

    palette: list[dict] = []
    for i in range(count):
        hue = (i * 360.0 / count + 10) % 360.0
        fill = _hsl_to_hex(hue, saturation, base_lightness)
        border = _hsl_to_hex(hue, saturation, border_lightness)
        palette.append({"fill": fill, "border": border, "hue": hue, "saturation": saturation})
    return palette


def depth_color(
    hue: float,
    saturation: float,
    level: int,
    theme: str = "light",
) -> dict[str, str]:
    """Compute fill + border for a node at a given tree depth.

    Level 1 is vivid.  Each subsequent level gets progressively lighter and
    slightly less saturated — creating a watercolour fade that keeps the
    branch identity while building clear visual hierarchy.

    Returns ``{"fill", "border", "text"}``.
    """
    if theme == "light":
        base_l = 48.0
        l_step = 11.0
        s_decay = 8.0
        max_l = 88.0
        min_s = 35.0
    else:
        base_l = 55.0
        l_step = 8.0
        s_decay = 6.0
        max_l = 78.0
        min_s = 40.0

    depth = max(level - 1, 0)
    lightness = min(base_l + depth * l_step, max_l)
    sat = max(saturation - depth * s_decay, min_s)
    border_l = max(lightness - 10.0, 15.0)

    fill = _hsl_to_hex(hue, sat, lightness)
    border = _hsl_to_hex(hue, sat, border_l)
    text = text_color_for_bg(fill)

    return {"fill": fill, "border": border, "text": text}
