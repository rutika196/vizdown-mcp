"""Custom pure-Python SVG architecture / service diagram renderer.

Miro-style output with auto-layout (Sugiyama-inspired), auto icon detection,
step numbering, groups, and right-angle connectors.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from xml.sax.saxutils import escape as xml_escape

from src.utils.icon_registry import detect_icon, render_icon_svg

CELL_W = 210
CELL_H = 190
PAD = 80
ICON_SIZE = 68
LABEL_FONT = 13
LABEL_MAX_CHARS = 18
CONNECTOR_STROKE = 1.6
ARROW_SIZE = 9
STEP_RADIUS = 14
FONT_FAMILY = "'SF Pro Display', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

STEP_COLORS = [
    "#6366F1", "#8B5CF6", "#A855F7", "#7C3AED",
    "#6D28D9", "#5B21B6", "#4F46E5", "#4338CA",
    "#3730A3", "#312E81", "#6366F1", "#8B5CF6",
    "#A855F7", "#7C3AED", "#6D28D9", "#5B21B6",
    "#4F46E5", "#4338CA", "#3730A3", "#312E81",
]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

@dataclass
class ServiceNode:
    name: str
    icon_tag: str | None = None
    icon_key: str | None = None
    col: int = 0
    row: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass
class FlowEdge:
    src: str
    dst: str
    step: int = 0


@dataclass
class Group:
    name: str
    members: list[str] = field(default_factory=list)


def _parse_architecture(syntax: str) -> tuple[str, list[ServiceNode], list[FlowEdge], list[Group]]:
    """Parse custom architecture markdown format."""
    title = ""
    services: list[ServiceNode] = []
    edges: list[FlowEdge] = []
    groups: list[Group] = []

    section = None
    lines = syntax.strip().split("\n")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
            continue
        if line.lower() == "services:":
            section = "services"
            continue
        if line.lower() == "flow:":
            section = "flow"
            continue
        if line.lower() == "groups:":
            section = "groups"
            continue

        if section == "services":
            tag_match = re.match(r"^(.+?)\s*\[(.+?)\]\s*$", line)
            if tag_match:
                name = tag_match.group(1).strip()
                tag = tag_match.group(2).strip()
            else:
                name = line.strip()
                tag = None
            if name:
                services.append(ServiceNode(name=name, icon_tag=tag))

        elif section == "flow":
            parts = re.split(r"\s*->\s*", line)
            for i in range(len(parts) - 1):
                src = parts[i].strip()
                dst = parts[i + 1].strip()
                if src and dst:
                    edges.append(FlowEdge(src=src, dst=dst))

        elif section == "groups":
            if ":" in line:
                gname, members_str = line.split(":", 1)
                members = [m.strip() for m in members_str.split(",") if m.strip()]
                groups.append(Group(name=gname.strip(), members=members))

    for svc in services:
        svc.icon_key = detect_icon(svc.name, svc.icon_tag)

    return title, services, edges, groups


# ---------------------------------------------------------------------------
# Auto-layout (Sugiyama-inspired)
# ---------------------------------------------------------------------------

def _build_adjacency(services: list[ServiceNode], edges: list[FlowEdge]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    name_set = {s.name for s in services}
    fwd: dict[str, list[str]] = defaultdict(list)
    rev: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.src in name_set and e.dst in name_set:
            fwd[e.src].append(e.dst)
            rev[e.dst].append(e.src)
    return fwd, rev


def _topological_layers(services: list[ServiceNode], fwd: dict, rev: dict) -> dict[str, int]:
    """Assign each service to a layer (column) via longest-path layering."""
    name_set = {s.name for s in services}
    in_degree: dict[str, int] = {s.name: 0 for s in services}
    for e_src, dsts in fwd.items():
        for d in dsts:
            if d in in_degree:
                in_degree[d] += 1

    layer: dict[str, int] = {}
    queue = deque([n for n, d in in_degree.items() if d == 0])

    if not queue:
        queue = deque([services[0].name] if services else [])

    while queue:
        node = queue.popleft()
        if node not in layer:
            preds = rev.get(node, [])
            layer[node] = max((layer.get(p, 0) for p in preds), default=-1) + 1
        for nb in fwd.get(node, []):
            in_degree[nb] -= 1
            if in_degree[nb] <= 0 and nb not in layer:
                queue.append(nb)

    for s in services:
        if s.name not in layer:
            layer[s.name] = 0

    return layer


def _minimise_crossings(layers_by_col: dict[int, list[str]], fwd: dict, rev: dict) -> dict[int, list[str]]:
    """Reduce edge crossings using median heuristic (2 sweeps)."""
    cols = sorted(layers_by_col.keys())
    result = dict(layers_by_col)

    for _sweep in range(2):
        for ci in range(1, len(cols)):
            col = cols[ci]
            prev_col_order = {name: idx for idx, name in enumerate(result[cols[ci - 1]])}
            medians: dict[str, float] = {}
            for name in result[col]:
                preds = [p for p in rev.get(name, []) if p in prev_col_order]
                if preds:
                    positions = sorted(prev_col_order[p] for p in preds)
                    medians[name] = positions[len(positions) // 2]
                else:
                    medians[name] = float("inf")
            result[col] = sorted(result[col], key=lambda n: medians.get(n, float("inf")))

    return result


def _assign_positions(
    services: list[ServiceNode],
    edges: list[FlowEdge],
) -> None:
    """Run the full auto-layout pipeline and set x, y on each ServiceNode."""
    fwd, rev = _build_adjacency(services, edges)
    layer_map = _topological_layers(services, fwd, rev)

    layers_by_col: dict[int, list[str]] = defaultdict(list)
    for name, col in layer_map.items():
        layers_by_col[col].append(name)

    layers_by_col = _minimise_crossings(layers_by_col, fwd, rev)

    name_to_svc = {s.name: s for s in services}
    cols = sorted(layers_by_col.keys())

    for col in cols:
        members = layers_by_col[col]
        n = len(members)
        total_h = n * CELL_H
        start_y = -total_h / 2
        for row, name in enumerate(members):
            svc = name_to_svc[name]
            svc.col = col
            svc.row = row
            svc.x = PAD + col * CELL_W + CELL_W / 2
            svc.y = PAD + start_y + total_h / 2 + row * CELL_H + CELL_H / 2


def _assign_steps(edges: list[FlowEdge], services: list[ServiceNode], fwd: dict) -> None:
    """BFS from source nodes to assign step numbers."""
    name_set = {s.name for s in services}
    sources = [s.name for s in services if not any(s.name in dsts for dsts in fwd.values())]
    if not sources:
        sources = [services[0].name] if services else []

    visited_edges: set[tuple[str, str]] = set()
    queue = deque(sources)
    visited_nodes: set[str] = set()
    step = 1

    while queue:
        next_level: list[str] = []
        for node in queue:
            if node in visited_nodes:
                continue
            visited_nodes.add(node)
            for nb in fwd.get(node, []):
                key = (node, nb)
                if key not in visited_edges:
                    visited_edges.add(key)
                    for e in edges:
                        if e.src == node and e.dst == nb and e.step == 0:
                            e.step = step
                            step += 1
                            break
                    if nb not in visited_nodes:
                        next_level.append(nb)
        queue = deque(next_level)


# ---------------------------------------------------------------------------
# SVG Rendering
# ---------------------------------------------------------------------------

def _wrap_label(text: str, max_chars: int = LABEL_MAX_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        if current and len(current) + 1 + len(w) > max_chars:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}" if current else w
    if current:
        lines.append(current)
    return lines[:2]


def _render_text_pill(cx: float, cy: float, text: str, theme: str) -> str:
    """Fallback: clean rounded pill with centred text, no icon."""
    lines = _wrap_label(text)
    line_h = LABEL_FONT + 4
    total_h = line_h * len(lines) + 18
    max_w = max(len(l) * LABEL_FONT * 0.6 for l in lines) + 36
    fill = "#F9FAFB" if theme == "light" else "#374151"
    text_color = "#1F2937" if theme == "light" else "#F3F4F6"
    border = "#E5E7EB" if theme == "light" else "#4B5563"

    svg = (
        f'<rect x="{cx - max_w / 2}" y="{cy - total_h / 2}" width="{max_w}" '
        f'height="{total_h}" rx="{total_h / 2}" fill="{fill}" stroke="{border}" stroke-width="1.2"/>'
    )
    for i, line in enumerate(lines):
        ly = cy - (len(lines) - 1) * line_h / 2 + i * line_h
        svg += (
            f'<text x="{cx}" y="{ly + LABEL_FONT * 0.35}" text-anchor="middle" '
            f'fill="{text_color}" font-size="{LABEL_FONT}" font-weight="600" '
            f'font-family="{FONT_FAMILY}">{xml_escape(line)}</text>'
        )
    return svg


def _render_service(svc: ServiceNode, theme: str) -> str:
    """Render a service: icon + label below (Miro-style)."""
    icon_svg = render_icon_svg(svc.icon_key, svc.x, svc.y - 20, ICON_SIZE)
    if not icon_svg:
        return _render_text_pill(svc.x, svc.y, svc.name, theme)

    text_color = "#1F2937" if theme == "light" else "#F3F4F6"
    lines = _wrap_label(svc.name)
    label_y = svc.y + ICON_SIZE / 2 - 2
    label_svg = ""
    for i, line in enumerate(lines):
        ly = label_y + i * (LABEL_FONT + 4)
        label_svg += (
            f'<text x="{svc.x}" y="{ly}" text-anchor="middle" '
            f'fill="{text_color}" font-size="{LABEL_FONT}" font-weight="600" '
            f'letter-spacing="0.2" '
            f'font-family="{FONT_FAMILY}">{xml_escape(line)}</text>'
        )
    return icon_svg + label_svg


ICON_Y_OFFSET = 20


def _anchor(svc: ServiceNode) -> tuple[float, float]:
    """Return the point where connectors should attach — the icon center."""
    ay = getattr(svc, '_anchor_y', svc.y)
    return svc.x, ay


def _render_connector_line(src: ServiceNode, dst: ServiceNode, theme: str, mid_x_override: float | None = None) -> str:
    """Render ONLY the connector line + arrowhead (no badge)."""
    x1, y1 = _anchor(src)
    x2, y2 = _anchor(dst)

    line_color = "#B8BFC8" if theme == "light" else "#4B5563"
    mid_x = mid_x_override if mid_x_override is not None else (x1 + x2) / 2

    if abs(y1 - y2) < 5:
        path = f"M{x1},{y1} L{x2},{y2}"
        arrow_angle = 0.0 if x2 > x1 else math.pi
    else:
        path = f"M{x1},{y1} L{mid_x},{y1} L{mid_x},{y2} L{x2},{y2}"
        arrow_angle = 0.0 if x2 > mid_x else math.pi

    a_half = 0.4
    ax = x2 - ARROW_SIZE * math.cos(arrow_angle - a_half)
    ay = y2 - ARROW_SIZE * math.sin(arrow_angle - a_half)
    bx = x2 - ARROW_SIZE * math.cos(arrow_angle + a_half)
    by = y2 - ARROW_SIZE * math.sin(arrow_angle + a_half)

    return (
        f'<path d="{path}" fill="none" stroke="{line_color}" '
        f'stroke-width="{CONNECTOR_STROKE}" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<polygon points="{x2},{y2} {ax},{ay} {bx},{by}" fill="{line_color}"/>'
    )


def _render_connector_badge(src: ServiceNode, dst: ServiceNode, step: int, theme: str, mid_x_override: float | None = None) -> str:
    """Render step badge at a unique position per connector.

    Straight lines: badge at midpoint.
    L-shaped paths: badge on the vertical segment — guarantees
    unique y for each destination.
    """
    if step <= 0:
        return ""

    x1, y1 = _anchor(src)
    x2, y2 = _anchor(dst)
    mid_x = mid_x_override if mid_x_override is not None else (x1 + x2) / 2

    if abs(y1 - y2) < 5:
        badge_x = mid_x
        badge_y = y1
    else:
        badge_x = mid_x
        badge_y = y1 + 0.4 * (y2 - y1)

    color_idx = (step - 1) % len(STEP_COLORS)
    badge_fill = STEP_COLORS[color_idx]
    r = STEP_RADIUS

    return (
        f'<g filter="url(#badge-shadow)">'
        f'<circle cx="{badge_x}" cy="{badge_y}" r="{r + 3}" fill="white"/>'
        f'<circle cx="{badge_x}" cy="{badge_y}" r="{r}" fill="{badge_fill}"/>'
        f'<text x="{badge_x}" y="{badge_y + 4}" text-anchor="middle" fill="white" '
        f'font-size="11" font-weight="700" letter-spacing="0.3" '
        f'font-family="{FONT_FAMILY}">{step}</text>'
        f'</g>'
    )


ICON_BRAND_HUE: dict[str | None, float | None] = {
    # Legacy built-in icons
    "event-hubs":    160,
    "function-apps": 44,
    "cognitive":     217,
    "cloud":         217,
    "ml-studio":     217,
    "beaker":        217,
    "power-bi":      38,
    "cpu":           239,
    "gear":          220,
    "person":        270,
    "shield":        160,

    # Iconify-sourced icons (keyed by filename in static/icons/)
    "docker":        210,
    "kubernetes":    220,
    "podman":        220,
    "database":      217,
    "postgres":      217,
    "mysql":         200,
    "mongodb":       130,
    "dynamodb":      217,
    "cockroachdb":   250,
    "sqlite":        210,
    "elasticsearch": 180,
    "elastic":       180,
    "redis":         0,
    "kafka":         0,
    "rabbitmq":      30,
    "nats":          210,
    "mqtt":          270,
    "nginx":         130,
    "envoy":         270,
    "istio":         217,
    "linkerd":       150,
    "consul":        340,
    "etcd":          200,
    "lock":          217,
    "auth":          217,
    "oauth":         217,
    "vault":         0,
    "firewall":      30,
    "server":        270,
    "api":           210,
    "gateway":       30,
    "globe":         174,
    "web":           210,
    "mobile":        210,
    "user":          270,
    "network":       160,
    "dns":           210,
    "vpn":           210,
    "load-balancer": 270,
    "storage":       190,
    "cache":         210,
    "s3":            130,
    "cdn":           174,
    "function":      44,
    "lambda":        44,
    "email":         210,
    "notification":  44,
    "webhook":       270,
    "microservice":  270,
    "analytics":     38,
    "dashboard":     38,
    "react":         195,
    "nextjs":        0,
    "vue":           150,
    "angular":       0,
    "svelte":        15,
    "nodejs":        130,
    "python":        210,
    "go":            195,
    "java":          210,
    "rust":          25,
    "dotnet":        270,
    "graphql":       330,
    "grpc":          160,
    "jenkins":       0,
    "github-actions": 217,
    "gitlab":        25,
    "circleci":      130,
    "terraform":     270,
    "ansible":       0,
    "aws":           35,
    "azure":         210,
    "gcp":           210,
    "cloudflare":    35,
    "vercel":        0,
    "heroku":        270,
    "digitalocean":  210,
    "prometheus":    25,
    "grafana":       30,
    "datadog":       270,
    "sentry":        270,
    "newrelic":      160,
    "ml":            270,
    "ai":            210,
    "tensorflow":    35,
    "pytorch":       0,
    "openai":        0,
    "spark":         25,
    "airflow":       160,
    "snowflake":     200,
    "bigquery":      210,
    "git":           10,
    "github":        0,
    "slack":         330,
    "jira":          217,
    "stripe":        250,
    "twilio":        0,
    "search":        210,
    "cart":           30,
    "order":          270,
    "warehouse":      35,
    "catalog":        25,
    "payment":        210,
    "brain":          270,
    "bell":           38,
    "package":        270,
    "hexagons":       270,
    "cloud-multi":    217,
    None:            220,
}

FALLBACK_HUES = [220, 160, 30, 330, 270, 190, 50, 0, 280, 130]


def _hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    h_str = hex_color.lstrip("#")
    r, g, b = int(h_str[:2], 16) / 255, int(h_str[2:4], 16) / 255, int(h_str[4:6], 16) / 255
    mx, mn = max(r, g, b), min(r, g, b)
    lum = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, lum * 100
    d = mx - mn
    sat = d / (2 - mx - mn) if lum > 0.5 else d / (mx + mn)
    if mx == r:
        hue = ((g - b) / d + (6 if g < b else 0)) * 60
    elif mx == g:
        hue = ((b - r) / d + 2) * 60
    else:
        hue = ((r - g) / d + 4) * 60
    return hue, sat * 100, lum * 100


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    s_f, l_f = s / 100, l / 100
    c = (1 - abs(2 * l_f - 1)) * s_f
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l_f - c / 2
    if h < 60:
        r1, g1, b1 = c, x, 0
    elif h < 120:
        r1, g1, b1 = x, c, 0
    elif h < 180:
        r1, g1, b1 = 0, c, x
    elif h < 240:
        r1, g1, b1 = 0, x, c
    elif h < 300:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x
    r, g, b = int((r1 + m) * 255), int((g1 + m) * 255), int((b1 + m) * 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def _compute_group_hue(members: list[ServiceNode]) -> float:
    """Compute average hue from member icon brand colors using circular mean."""
    icon_hues: list[float] = []
    for m in members:
        h = ICON_BRAND_HUE.get(m.icon_key)
        if h is not None and m.icon_key is not None:
            icon_hues.append(h)

    if not icon_hues:
        return -1.0

    import cmath
    vectors = [cmath.exp(1j * math.radians(h)) for h in icon_hues]
    mean_vec = sum(vectors) / len(vectors)
    return math.degrees(cmath.phase(mean_vec)) % 360


def _resolve_group_hues(groups: list[Group], services: list[ServiceNode]) -> list[float]:
    """Compute hues for all groups, ensuring sufficient visual separation."""
    raw_hues: list[float] = []
    for g in groups:
        members = [s for s in services if s.name in g.members]
        raw_hues.append(_compute_group_hue(members))

    n = len(raw_hues)
    has_real = [h >= 0 for h in raw_hues]

    golden_angle = 137.508
    seed_hues = [(i * golden_angle) % 360 for i in range(n)]

    resolved = list(raw_hues)
    for i in range(n):
        if not has_real[i]:
            resolved[i] = seed_hues[i]

    min_sep = 35.0
    for _pass in range(3):
        for i in range(n):
            for j in range(i + 1, n):
                diff = abs(resolved[i] - resolved[j])
                diff = min(diff, 360 - diff)
                if diff < min_sep:
                    if not has_real[j]:
                        resolved[j] = (resolved[j] + min_sep) % 360
                    elif not has_real[i]:
                        resolved[i] = (resolved[i] + min_sep) % 360
                    else:
                        mid = (resolved[i] + resolved[j]) / 2
                        resolved[i] = (mid - min_sep / 2) % 360
                        resolved[j] = (mid + min_sep / 2) % 360

    return resolved


def _hue_to_group_colors(hue: float, theme: str) -> dict[str, str]:
    if theme == "light":
        bg = _hsl_to_hex(hue, 72, 96)
        border = _hsl_to_hex(hue, 58, 74)
        text = _hsl_to_hex(hue, 65, 30)
    else:
        bg = _hsl_to_hex(hue, 50, 12)
        border = _hsl_to_hex(hue, 55, 52)
        text = _hsl_to_hex(hue, 60, 78)
    return {"bg": bg, "border": border, "text": text}


def _render_group(group: Group, services: list[ServiceNode], theme: str, hue: float = 220) -> str:
    """Render group with colors derived from the resolved hue."""
    members = [s for s in services if s.name in group.members]
    if not members:
        return ""

    colors = _hue_to_group_colors(hue, theme)

    margin_x = 65
    margin_top = 60
    margin_bottom = 45
    min_x = min(s.x for s in members) - margin_x
    max_x = max(s.x for s in members) + margin_x
    min_y = min(s.y for s in members) - margin_top
    max_y = max(s.y for s in members) + margin_bottom

    w = max_x - min_x
    h = max_y - min_y
    label = xml_escape(group.name.upper())
    cx = (min_x + max_x) / 2

    svg = (
        f'<rect x="{min_x}" y="{min_y}" width="{w}" height="{h}" '
        f'rx="14" fill="{colors["bg"]}" fill-opacity="0.45" '
        f'stroke="{colors["border"]}" stroke-width="1.5" stroke-dasharray="8,4"/>'
        f'<text x="{cx}" y="{min_y - 8}" text-anchor="middle" '
        f'fill="{colors["text"]}" font-size="10" font-weight="700" '
        f'letter-spacing="1.0" opacity="0.85" '
        f'font-family="{FONT_FAMILY}">{label}</text>'
    )

    return svg


def _spread_shared_midpoints(edges: list[FlowEdge], name_to_svc: dict[str, ServiceNode]) -> None:
    """When multiple L-shaped connectors share the same vertical mid_x,
    spread them horizontally so they don't overlap into a thick line."""
    from collections import Counter

    buckets: dict[float, list[FlowEdge]] = defaultdict(list)
    for e in edges:
        src = name_to_svc.get(e.src)
        dst = name_to_svc.get(e.dst)
        if not src or not dst:
            continue
        sy = getattr(src, '_anchor_y', src.y)
        dy = getattr(dst, '_anchor_y', dst.y)
        if abs(sy - dy) >= 5:
            mid_x = (src.x + dst.x) / 2
            buckets[mid_x].append(e)

    spread = 6.0
    for mid_x, group in buckets.items():
        if len(group) <= 1:
            continue
        group.sort(key=lambda e: name_to_svc[e.dst].y if e.dst in name_to_svc else 0)
        n = len(group)
        for i, e in enumerate(group):
            offset = (i - (n - 1) / 2) * spread
            e._mid_x_override = mid_x + offset  # type: ignore[attr-defined]


def _group_area(group: Group, services: list[ServiceNode]) -> float:
    members = [s for s in services if s.name in group.members]
    if not members:
        return 0.0
    w = max(s.x for s in members) - min(s.x for s in members) + 130
    h = max(s.y for s in members) - min(s.y for s in members) + 105
    return w * h


def render_architecture(syntax: str, theme: str = "light") -> str:
    """Render architecture diagram syntax into an SVG string."""
    title, services, edges, groups = _parse_architecture(syntax)

    if not services:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="60">'
            '<text x="20" y="35" font-size="14" fill="red">No services found in architecture syntax</text>'
            '</svg>'
        )

    _assign_positions(services, edges)

    fwd, _rev = _build_adjacency(services, edges)
    _assign_steps(edges, services, fwd)

    all_x = [s.x for s in services]
    all_y = [s.y for s in services]
    svg_w = max(all_x) - min(all_x) + 2 * PAD + CELL_W
    svg_h = max(all_y) - min(all_y) + 2 * PAD + CELL_H

    offset_x = -min(all_x) + PAD + CELL_W / 2
    offset_y = -min(all_y) + PAD + CELL_H / 2
    for s in services:
        s.x += offset_x
        s.y += offset_y

    bg_color = "#FFFFFF" if theme == "light" else "#111827"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}" style="font-family: {FONT_FAMILY}">',
        '<defs>'
        '<filter id="badge-shadow" x="-40%" y="-40%" width="180%" height="180%">'
        '<feDropShadow dx="0" dy="1" stdDeviation="2.5" flood-color="#000" flood-opacity="0.12"/>'
        '</filter>'
        '</defs>',
        f'<rect width="{svg_w}" height="{svg_h}" fill="{bg_color}"/>',
    ]

    if title:
        title_color = "#111827" if theme == "light" else "#F9FAFB"
        parts.append(
            f'<text x="{svg_w / 2}" y="40" text-anchor="middle" fill="{title_color}" '
            f'font-size="20" font-weight="700" font-family="{FONT_FAMILY}">'
            f'{xml_escape(title)}</text>'
        )

    group_hues = _resolve_group_hues(groups, services)
    group_indexed = list(enumerate(groups))
    group_indexed.sort(
        key=lambda ig: _group_area(ig[1], services), reverse=True,
    )
    for gi, group in group_indexed:
        parts.append(_render_group(group, services, theme, hue=group_hues[gi]))

    name_to_svc = {s.name: s for s in services}

    for svc in services:
        if render_icon_svg(svc.icon_key, 0, 0, ICON_SIZE):
            svc._anchor_y = svc.y - ICON_Y_OFFSET  # type: ignore[attr-defined]
        else:
            svc._anchor_y = svc.y  # type: ignore[attr-defined]

    _spread_shared_midpoints(edges, name_to_svc)

    # Layer 1: Connector lines (below everything interactive)
    for edge in edges:
        src = name_to_svc.get(edge.src)
        dst = name_to_svc.get(edge.dst)
        if src and dst:
            parts.append(_render_connector_line(src, dst, theme, getattr(edge, '_mid_x_override', None)))

    # Layer 2: Service icons and labels
    for svc in services:
        parts.append(_render_service(svc, theme))

    # Layer 3: Step badges on TOP of everything — never hidden
    for edge in edges:
        src = name_to_svc.get(edge.src)
        dst = name_to_svc.get(edge.dst)
        if src and dst:
            parts.append(_render_connector_badge(src, dst, edge.step, theme, getattr(edge, '_mid_x_override', None)))

    parts.append("</svg>")
    return "\n".join(parts)
