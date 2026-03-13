"""Icon auto-detection and external SVG loading for architecture diagrams."""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

STATIC_ICONS_DIR = Path(__file__).resolve().parent.parent / "static" / "icons"

KEYWORD_ICON_MAP: list[tuple[list[str], str]] = [
    (["database", "db", "postgres", "mysql", "mongo", "sql", "dynamo", "cockroach", "sqlite"], "database"),
    (["gateway", "api", "nginx", "ingress"], "shield"),
    (["redis", "cache", "memcached"], "redis"),
    (["kafka", "queue", "rabbitmq", "message", "mq"], "kafka"),
    (["docker", "container", "pod"], "docker"),
    (["kubernetes", "k8s"], "kubernetes"),
    (["auth", "login", "sso", "oauth", "iam"], "lock"),
    (["user", "profile", "account", "identity"], "person"),
    (["storage", "s3", "blob", "bucket", "store"], "storage"),
    (["ml", "machine learning", "ai", "model", "training"], "ml-studio"),
    (["monitor", "prometheus", "metric", "logging", "observ"], "event-hubs"),
    (["dashboard", "grafana", "report", "analytics", "power bi", "chart"], "power-bi"),
    (["cdn", "cloudfront", "edge", "akamai"], "network"),
    (["firewall", "waf", "armor", "security", "shield"], "shield"),
    (["ci", "cd", "jenkins", "pipeline", "deploy", "github action"], "docker"),
    (["vault", "secret", "key", "cert", "encrypt"], "lock"),
    (["consul", "registry", "discovery", "eureka", "config"], "gear"),
    (["web", "browser", "frontend", "app", "client", "mobile"], "globe"),
    (["function", "lambda", "serverless", "trigger"], "function-apps"),
    (["server", "compute", "instance", "vm", "ec2"], "server"),
    (["load balancer", "lb", "haproxy", "elb"], "network"),
    (["notification", "email", "sms", "push", "alert"], "gear"),
]


def detect_icon(service_name: str, explicit_tag: str | None = None) -> str | None:
    """4-tier icon resolution: external SVG → explicit tag → keyword auto-detect → None."""
    name_lower = service_name.lower().strip()

    ext_path = STATIC_ICONS_DIR / f"{name_lower.replace(' ', '-')}.svg"
    if ext_path.is_file():
        return f"external:{ext_path}"

    if explicit_tag:
        tag = explicit_tag.strip().lower()
        ext_tag_path = STATIC_ICONS_DIR / f"{tag}.svg"
        if ext_tag_path.is_file():
            return f"external:{ext_tag_path}"
        return tag

    for keywords, icon_name in KEYWORD_ICON_MAP:
        for kw in keywords:
            if kw in name_lower:
                return icon_name

    return None


def load_external_svg(path: str) -> str:
    """Read an external SVG file and return its content."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Built-in hand-crafted SVG icon renderers (22 icons)
# Each function returns an SVG group string drawn centred at (cx, cy) with
# bounding size *s*.
# ---------------------------------------------------------------------------

def _g(cx: float, cy: float, s: float, inner: str) -> str:
    """Wrap inner SVG in a translate group centred at (cx, cy)."""
    return f'<g transform="translate({cx - s / 2},{cy - s / 2})">{inner}</g>'


def icon_event_hubs(cx: float, cy: float, s: float) -> str:
    r = s * 0.46
    body = (
        f'<rect x="2" y="2" width="{s - 4}" height="{s - 4}" rx="6" fill="#6B7280" opacity="0.15"/>'
        f'<rect x="6" y="6" width="{s - 12}" height="{s - 12}" rx="4" fill="#374151"/>'
    )
    dots = ""
    grid = 4
    pad = 12
    cell_w = (s - 2 * pad) / (grid - 1)
    for gx in range(grid):
        for gy in range(grid):
            x = pad + gx * cell_w
            y = pad + gy * cell_w
            dots += f'<circle cx="{x}" cy="{y}" r="2.5" fill="#34D399"/>'
    return _g(cx, cy, s, body + dots)


def icon_storage(cx: float, cy: float, s: float) -> str:
    bars = ""
    n, pad, gap = 5, 8, 3
    bh = (s - 2 * pad - (n - 1) * gap) / n
    colors = ["#22D3EE", "#38BDF8", "#60A5FA", "#818CF8", "#A78BFA"]
    for i in range(n):
        y = pad + i * (bh + gap)
        w = s - 2 * pad - i * 4
        x = pad + i * 2
        bars += f'<rect x="{x}" y="{y}" width="{w}" height="{bh}" rx="3" fill="{colors[i]}"/>'
    return _g(cx, cy, s, bars)


def icon_function_apps(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    d = s * 0.35
    diamond = (
        f'<polygon points="{mid},{mid - d} {mid + d},{mid} {mid},{mid + d} {mid - d},{mid}" '
        f'fill="#FBBF24" stroke="#F59E0B" stroke-width="1.5"/>'
    )
    bolt = (
        f'<polygon points="{mid - 4},{mid + 2} {mid + 1},{mid - 1} {mid - 1},{mid - 8} '
        f'{mid + 5},{mid - 2} {mid},{mid + 1} {mid + 2},{mid + 9}" fill="#2563EB"/>'
    )
    return _g(cx, cy, s, diamond + bolt)


def icon_database(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    w, h = s * 0.6, s * 0.7
    ry = h * 0.15
    x = mid - w / 2
    y = mid - h / 2
    body = (
        f'<ellipse cx="{mid}" cy="{y + ry}" rx="{w / 2}" ry="{ry}" fill="#3B82F6"/>'
        f'<rect x="{x}" y="{y + ry}" width="{w}" height="{h - 2 * ry}" fill="#3B82F6"/>'
        f'<ellipse cx="{mid}" cy="{y + h - ry}" rx="{w / 2}" ry="{ry}" fill="#2563EB"/>'
        f'<ellipse cx="{mid}" cy="{y + ry}" rx="{w / 2}" ry="{ry}" fill="#60A5FA"/>'
        f'<text x="{mid}" y="{mid + 4}" text-anchor="middle" fill="white" '
        f'font-size="12" font-weight="700" font-family="system-ui">DB</text>'
    )
    return _g(cx, cy, s, body)


def icon_cognitive(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    cloud = (
        f'<ellipse cx="{mid}" cy="{mid + 4}" rx="{s * 0.4}" ry="{s * 0.25}" fill="#3B82F6"/>'
        f'<circle cx="{mid - 8}" cy="{mid - 4}" r="{s * 0.18}" fill="#3B82F6"/>'
        f'<circle cx="{mid + 8}" cy="{mid - 2}" r="{s * 0.2}" fill="#3B82F6"/>'
        f'<circle cx="{mid}" cy="{mid - 10}" r="{s * 0.16}" fill="#3B82F6"/>'
    )
    nodes = ""
    pts = [(mid - 10, mid - 2), (mid + 10, mid), (mid, mid + 6), (mid - 5, mid + 2), (mid + 6, mid - 5)]
    for i, (px, py) in enumerate(pts):
        nodes += f'<circle cx="{px}" cy="{py}" r="3" fill="white"/>'
        if i < len(pts) - 1:
            nx, ny = pts[i + 1]
            nodes += f'<line x1="{px}" y1="{py}" x2="{nx}" y2="{ny}" stroke="white" stroke-width="1" opacity="0.7"/>'
    return _g(cx, cy, s, cloud + nodes)


def icon_ml_studio(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    flask = (
        f'<path d="M{mid - 6},{mid - 18} L{mid - 6},{mid - 6} L{mid - 18},{mid + 14} '
        f'Q{mid - 18},{mid + 20} {mid - 12},{mid + 20} L{mid + 12},{mid + 20} '
        f'Q{mid + 18},{mid + 20} {mid + 18},{mid + 14} L{mid + 6},{mid - 6} L{mid + 6},{mid - 18}" '
        f'fill="none" stroke="#3B82F6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="M{mid - 14},{mid + 4} Q{mid},{mid + 14} {mid + 14},{mid + 4}" '
        f'fill="#3B82F6" opacity="0.6"/>'
        f'<circle cx="{mid - 4}" cy="{mid + 10}" r="2" fill="white" opacity="0.8"/>'
        f'<circle cx="{mid + 3}" cy="{mid + 7}" r="1.5" fill="white" opacity="0.8"/>'
    )
    return _g(cx, cy, s, flask)


def icon_power_bi(cx: float, cy: float, s: float) -> str:
    bars_svg = ""
    n, pad = 5, 10
    bw = (s - 2 * pad - (n - 1) * 3) / n
    heights = [0.4, 0.7, 1.0, 0.6, 0.85]
    colors = ["#F59E0B", "#FBBF24", "#FCD34D", "#F59E0B", "#D97706"]
    max_h = s - 2 * pad
    for i in range(n):
        h = max_h * heights[i]
        x = pad + i * (bw + 3)
        y = s - pad - h
        bars_svg += f'<rect x="{x}" y="{y}" width="{bw}" height="{h}" rx="2" fill="{colors[i]}"/>'
    return _g(cx, cy, s, bars_svg)


def icon_server(cx: float, cy: float, s: float) -> str:
    body = ""
    pad, gap = 8, 4
    rh = (s - 2 * pad - 2 * gap) / 3
    for i in range(3):
        y = pad + i * (rh + gap)
        body += (
            f'<rect x="{pad}" y="{y}" width="{s - 2 * pad}" height="{rh}" rx="4" fill="#7C3AED"/>'
            f'<circle cx="{s - pad - 8}" cy="{y + rh / 2}" r="2.5" fill="#A78BFA"/>'
            f'<circle cx="{s - pad - 16}" cy="{y + rh / 2}" r="2.5" fill="#C4B5FD"/>'
        )
    return _g(cx, cy, s, body)


def icon_shield(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    sh = s * 0.8
    sw = s * 0.6
    top = mid - sh / 2
    shield_path = (
        f'<path d="M{mid},{top} L{mid + sw / 2},{top + sh * 0.2} '
        f'L{mid + sw / 2},{top + sh * 0.55} Q{mid + sw / 2},{top + sh * 0.85} {mid},{top + sh} '
        f'Q{mid - sw / 2},{top + sh * 0.85} {mid - sw / 2},{top + sh * 0.55} '
        f'L{mid - sw / 2},{top + sh * 0.2} Z" fill="#10B981" stroke="#059669" stroke-width="1.5"/>'
        f'<polyline points="{mid - 7},{mid + 1} {mid - 2},{mid + 7} {mid + 9},{mid - 5}" '
        f'fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return _g(cx, cy, s, shield_path)


def icon_lock(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bw, bh = s * 0.55, s * 0.4
    bx, by = mid - bw / 2, mid - 2
    body = (
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="4" fill="#3B82F6"/>'
        f'<path d="M{mid - bw * 0.3},{by} V{by - bh * 0.5} '
        f'A{bw * 0.3},{bh * 0.5} 0 0 1 {mid + bw * 0.3},{by - bh * 0.5} V{by}" '
        f'fill="none" stroke="#3B82F6" stroke-width="3.5"/>'
        f'<circle cx="{mid}" cy="{by + bh * 0.4}" r="4" fill="white"/>'
        f'<rect x="{mid - 1.5}" y="{by + bh * 0.45}" width="3" height="{bh * 0.25}" rx="1" fill="white"/>'
    )
    return _g(cx, cy, s, body)


def icon_globe(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    r = s * 0.4
    body = (
        f'<circle cx="{mid}" cy="{mid}" r="{r}" fill="#0D9488" stroke="#0F766E" stroke-width="1.5"/>'
        f'<ellipse cx="{mid}" cy="{mid}" rx="{r * 0.4}" ry="{r}" fill="none" stroke="white" stroke-width="1.2" opacity="0.7"/>'
        f'<line x1="{mid - r}" y1="{mid}" x2="{mid + r}" y2="{mid}" stroke="white" stroke-width="1" opacity="0.5"/>'
        f'<ellipse cx="{mid}" cy="{mid}" rx="{r}" ry="{r * 0.35}" fill="none" stroke="white" stroke-width="1" opacity="0.5"/>'
    )
    return _g(cx, cy, s, body)


def icon_network(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    cr = s * 0.32
    body = f'<circle cx="{mid}" cy="{mid}" r="7" fill="#10B981"/>'
    import math
    nodes = ""
    for i in range(5):
        angle = (i * 72 - 90) * math.pi / 180
        nx = mid + cr * math.cos(angle)
        ny = mid + cr * math.sin(angle)
        nodes += (
            f'<line x1="{mid}" y1="{mid}" x2="{nx}" y2="{ny}" stroke="#10B981" stroke-width="1.5"/>'
            f'<circle cx="{nx}" cy="{ny}" r="5" fill="#34D399"/>'
        )
    return _g(cx, cy, s, body + nodes)


def icon_gear(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    import math
    outer_r, inner_r, teeth = s * 0.38, s * 0.28, 8
    path_parts = []
    for i in range(teeth):
        a1 = (i * 360 / teeth - 12) * math.pi / 180
        a2 = (i * 360 / teeth + 12) * math.pi / 180
        a3 = (i * 360 / teeth + 360 / teeth / 2 - 8) * math.pi / 180
        a4 = (i * 360 / teeth + 360 / teeth / 2 + 8) * math.pi / 180
        path_parts.append(f"L{mid + outer_r * math.cos(a1)},{mid + outer_r * math.sin(a1)}")
        path_parts.append(f"L{mid + outer_r * math.cos(a2)},{mid + outer_r * math.sin(a2)}")
        path_parts.append(f"L{mid + inner_r * math.cos(a3)},{mid + inner_r * math.sin(a3)}")
        path_parts.append(f"L{mid + inner_r * math.cos(a4)},{mid + inner_r * math.sin(a4)}")
    d = "M" + path_parts[0][1:] + "".join(path_parts[1:]) + "Z"
    body = (
        f'<path d="{d}" fill="#6B7280"/>'
        f'<circle cx="{mid}" cy="{mid}" r="{s * 0.12}" fill="white"/>'
    )
    return _g(cx, cy, s, body)


def icon_person(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    body = (
        f'<circle cx="{mid}" cy="{mid - s * 0.15}" r="{s * 0.17}" fill="#7C3AED"/>'
        f'<path d="M{mid - s * 0.3},{mid + s * 0.35} '
        f'Q{mid - s * 0.3},{mid + s * 0.05} {mid},{mid + s * 0.05} '
        f'Q{mid + s * 0.3},{mid + s * 0.05} {mid + s * 0.3},{mid + s * 0.35}" '
        f'fill="#7C3AED"/>'
    )
    return _g(cx, cy, s, body)


def icon_kubernetes(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    r = s * 0.4
    import math
    pts = []
    for i in range(6):
        a = (i * 60 - 90) * math.pi / 180
        pts.append((mid + r * math.cos(a), mid + r * math.sin(a)))
    hex_d = "M" + " L".join(f"{x},{y}" for x, y in pts) + "Z"
    spokes = ""
    sr = r * 0.55
    for i in range(6):
        a = (i * 60 - 90) * math.pi / 180
        spokes += (
            f'<line x1="{mid}" y1="{mid}" x2="{mid + sr * math.cos(a)}" '
            f'y2="{mid + sr * math.sin(a)}" stroke="white" stroke-width="2" opacity="0.8"/>'
        )
    body = (
        f'<path d="{hex_d}" fill="#326CE5" stroke="#2457B5" stroke-width="1.5"/>'
        + spokes
        + f'<circle cx="{mid}" cy="{mid}" r="4" fill="white"/>'
    )
    return _g(cx, cy, s, body)


def icon_docker(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bw, bh, gap = 7, 5, 1.5
    hull_x = mid - 2 * (bw + gap)
    hull_y = mid - 2
    hull = f'<path d="M{hull_x},{hull_y + bh + 6} Q{hull_x - 4},{hull_y + bh + 10} {hull_x},{hull_y + bh + 16} Q{mid},{hull_y + bh + 24} {mid + 22},{hull_y + bh + 12} Q{mid + 22},{hull_y + bh + 6} {mid + 18},{hull_y + bh + 4}" fill="#2496ED" opacity="0.3"/>'
    containers = ""
    rows = [(0, 3), (1, 4), (2, 5)]
    for row_i, (start_col, end_col) in enumerate(rows):
        for col in range(start_col, end_col):
            x = hull_x + 4 + col * (bw + gap)
            y = hull_y - row_i * (bh + gap)
            containers += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="1" fill="#2496ED" stroke="#1D7DC4" stroke-width="0.5"/>'
    return _g(cx, cy, s, hull + containers)


def icon_redis(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    dw, dh = s * 0.35, s * 0.15
    body = ""
    offsets = [-1, 0, 1]
    colors = ["#DC2626", "#EF4444", "#F87171"]
    for i, off in enumerate(offsets):
        y = mid + off * (dh + 4)
        body += (
            f'<polygon points="{mid},{y - dh} {mid + dw},{y} {mid},{y + dh} {mid - dw},{y}" '
            f'fill="{colors[i]}" stroke="#B91C1C" stroke-width="1"/>'
        )
    return _g(cx, cy, s, body)


def icon_kafka(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    r = s * 0.38
    body = (
        f'<circle cx="{mid}" cy="{mid}" r="{r}" fill="#231F20"/>'
        f'<text x="{mid}" y="{mid + 8}" text-anchor="middle" fill="white" '
        f'font-size="22" font-weight="900" font-family="system-ui">K</text>'
    )
    return _g(cx, cy, s, body)


def icon_cpu(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    cs = s * 0.5
    body = f'<rect x="{mid - cs / 2}" y="{mid - cs / 2}" width="{cs}" height="{cs}" rx="4" fill="#6366F1" stroke="#4F46E5" stroke-width="1.5"/>'
    pins = ""
    n_pins = 4
    pin_len, pin_w = 6, 3
    for i in range(n_pins):
        offset = mid - cs / 2 + (i + 0.5) * cs / n_pins
        pins += f'<rect x="{offset - pin_w / 2}" y="{mid - cs / 2 - pin_len}" width="{pin_w}" height="{pin_len}" rx="1" fill="#818CF8"/>'
        pins += f'<rect x="{offset - pin_w / 2}" y="{mid + cs / 2}" width="{pin_w}" height="{pin_len}" rx="1" fill="#818CF8"/>'
        pins += f'<rect x="{mid - cs / 2 - pin_len}" y="{offset - pin_w / 2}" width="{pin_len}" height="{pin_w}" rx="1" fill="#818CF8"/>'
        pins += f'<rect x="{mid + cs / 2}" y="{offset - pin_w / 2}" width="{pin_len}" height="{pin_w}" rx="1" fill="#818CF8"/>'
    inner = f'<rect x="{mid - cs * 0.25}" y="{mid - cs * 0.25}" width="{cs * 0.5}" height="{cs * 0.5}" rx="2" fill="#A5B4FC"/>'
    return _g(cx, cy, s, pins + body + inner)


BUILTIN_ICONS: dict[str, callable] = {
    "event-hubs": icon_event_hubs,
    "storage": icon_storage,
    "function-apps": icon_function_apps,
    "database": icon_database,
    "cognitive": icon_cognitive,
    "cloud": icon_cognitive,
    "ml-studio": icon_ml_studio,
    "beaker": icon_ml_studio,
    "power-bi": icon_power_bi,
    "chart": icon_power_bi,
    "server": icon_server,
    "shield": icon_shield,
    "lock": icon_lock,
    "globe": icon_globe,
    "network": icon_network,
    "gear": icon_gear,
    "person": icon_person,
    "kubernetes": icon_kubernetes,
    "docker": icon_docker,
    "redis": icon_redis,
    "kafka": icon_kafka,
    "cpu": icon_cpu,
}


def render_icon_svg(icon_key: str | None, cx: float, cy: float, size: float = 68) -> str:
    """Render an icon at (cx, cy). Returns SVG string or empty string for text-only fallback."""
    if icon_key is None:
        return ""

    if icon_key.startswith("external:"):
        path = icon_key[len("external:"):]
        try:
            svg_content = load_external_svg(path)
            return (
                f'<g transform="translate({cx - size / 2},{cy - size / 2})">'
                f'<g transform="scale({size / 64})">{svg_content}</g></g>'
            )
        except Exception:
            return ""

    fn = BUILTIN_ICONS.get(icon_key)
    if fn:
        return fn(cx, cy, size)
    return ""
