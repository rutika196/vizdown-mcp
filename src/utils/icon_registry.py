"""Icon auto-detection and external SVG loading for architecture diagrams."""

from __future__ import annotations

import os
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

STATIC_ICONS_DIR = Path(__file__).resolve().parent.parent / "static" / "icons"

KEYWORD_ICON_MAP: list[tuple[list[str], str]] = [
    # Specific tech first (matched before generic keywords)
    (["postgres"],           "postgres"),
    (["mysql"],              "mysql"),
    (["mongo"],              "mongodb"),
    (["dynamo"],             "dynamodb"),
    (["cockroach"],          "cockroachdb"),
    (["sqlite"],             "sqlite"),
    (["elasticsearch"],      "elasticsearch"),
    (["redis"],              "redis"),
    (["memcached"],          "cache"),
    (["kafka"],              "kafka"),
    (["rabbitmq"],           "rabbitmq"),
    (["nats"],               "nats"),
    (["mqtt"],               "mqtt"),
    (["docker", "container"],"docker"),
    (["kubernetes", "k8s"],  "kubernetes"),
    (["podman"],             "podman"),
    (["nginx"],              "nginx"),
    (["envoy"],              "envoy"),
    (["istio"],              "istio"),
    (["linkerd"],            "linkerd"),
    (["consul"],             "consul"),
    (["etcd"],               "etcd"),
    (["jenkins"],            "jenkins"),
    (["github action"],      "github-actions"),
    (["gitlab"],             "gitlab"),
    (["circleci"],           "circleci"),
    (["terraform"],          "terraform"),
    (["ansible"],            "ansible"),
    (["prometheus"],         "prometheus"),
    (["grafana"],            "grafana"),
    (["datadog"],            "datadog"),
    (["sentry"],             "sentry"),
    (["newrelic"],           "newrelic"),
    (["elastic"],            "elastic"),
    (["aws"],                "aws"),
    (["azure"],              "azure"),
    (["gcp", "google cloud"],"gcp"),
    (["cloudflare"],         "cloudflare"),
    (["vercel"],             "vercel"),
    (["heroku"],             "heroku"),
    (["digitalocean"],       "digitalocean"),
    (["react"],              "react"),
    (["next.js", "nextjs"],  "nextjs"),
    (["vue"],                "vue"),
    (["angular"],            "angular"),
    (["svelte"],             "svelte"),
    (["node.js", "nodejs"],  "nodejs"),
    (["python"],             "python"),
    (["golang", "go "],      "go"),
    (["java"],               "java"),
    (["rust"],               "rust"),
    (["dotnet", ".net"],     "dotnet"),
    (["graphql"],            "graphql"),
    (["grpc"],               "grpc"),
    (["oauth"],              "oauth"),
    (["vault", "secret"],    "vault"),
    (["lambda"],             "lambda"),
    (["s3"],                 "s3"),
    (["bigquery"],           "bigquery"),
    (["snowflake"],          "snowflake"),
    (["spark"],              "spark"),
    (["airflow"],            "airflow"),
    (["tensorflow"],         "tensorflow"),
    (["pytorch"],            "pytorch"),
    (["openai"],             "openai"),
    (["stripe"],             "stripe"),
    (["twilio"],             "twilio"),
    (["slack"],              "slack"),
    (["jira"],               "jira"),
    (["git"],                "git"),
    (["github"],             "github"),
    (["webhook"],            "webhook"),

    # Generic fallbacks — ALL hand-crafted built-ins. Order matters for substring overlaps.
    (["database", "db", "sql"],                        "database"),
    (["gateway", "ingress"],                           "gateway"),
    (["api"],                                          "api"),
    (["queue", "message", "mq"],                       "kafka"),
    (["email"],                                        "email"),
    (["auth", "login", "sso", "iam"],                  "shield"),
    (["firewall", "waf", "security"],                  "firewall"),
    (["encrypt", "key", "cert"],                       "lock"),
    (["user", "profile", "account", "identity"],       "person"),
    (["storage", "blob", "bucket", "store"],           "storage"),
    (["ml", "machine learning", "model", "training"],  "ml"),
    (["ai", "artificial intelligence"],                "ai"),
    (["monitor", "metric", "logging", "observ"],       "event-hubs"),
    (["dashboard", "report", "power bi"],              "power-bi"),
    (["analytics", "chart"],                           "analytics"),
    (["cdn", "cloudfront", "edge", "akamai"],          "cdn"),
    (["ci", "cd", "pipeline", "deploy"],               "github-actions"),
    (["web", "browser", "frontend", "client"],         "globe"),
    (["mobile", "ios", "android"],                     "mobile"),
    (["function", "serverless", "trigger"],             "function"),
    (["server", "compute", "instance", "vm", "ec2"],   "server"),
    (["load balancer", "lb", "haproxy", "elb"],        "load-balancer"),
    (["notification", "sms", "push", "alert"],         "notification"),
    (["dns"],                                          "dns"),
    (["network", "lan"],                               "network"),
    (["vpn"],                                          "vpn"),
    (["microservice"],                                 "microservice"),
    (["globe", "world"],                               "globe"),
    (["search", "find", "discover"],                   "search"),
    (["cart", "basket", "shopping"],                    "cart"),
    (["order", "checkout", "purchase"],                 "order"),
    (["warehouse", "fulfillment", "inventory"],        "warehouse"),
    (["catalog", "product", "listing"],                "catalog"),
    (["payment", "pay", "billing", "invoice"],         "payment"),
    (["service"],                                      "gear"),
    (["cloud"],                                        "cloud"),
    (["cache", "memcached"],                           "cache"),
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
# Built-in hand-crafted SVG icon renderers (44 icons)
# Each function returns an SVG group string drawn centred at (cx, cy) with
# bounding size *s* (default 68px).
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


# ---------------------------------------------------------------------------
# New hand-crafted icons (22 additional)
# ---------------------------------------------------------------------------

def icon_api(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bw, bh = s * 0.58, s * 0.36
    body = (
        f'<rect x="{mid - bw / 2}" y="{mid - bh / 2}" width="{bw}" height="{bh}" '
        f'rx="6" fill="#6366F1" stroke="#4F46E5" stroke-width="1.5"/>'
        f'<text x="{mid}" y="{mid + 5}" text-anchor="middle" fill="white" '
        f'font-size="14" font-weight="800" font-family="system-ui">API</text>'
        f'<circle cx="{mid - bw / 2 - 5}" cy="{mid - 5}" r="3.5" fill="#A5B4FC"/>'
        f'<circle cx="{mid - bw / 2 - 5}" cy="{mid + 5}" r="3.5" fill="#A5B4FC"/>'
        f'<circle cx="{mid + bw / 2 + 5}" cy="{mid}" r="3.5" fill="#C4B5FD"/>'
        f'<line x1="{mid - bw / 2 - 1}" y1="{mid - 5}" x2="{mid - bw / 2}" y2="{mid - 5}" stroke="#A5B4FC" stroke-width="1.5"/>'
        f'<line x1="{mid - bw / 2 - 1}" y1="{mid + 5}" x2="{mid - bw / 2}" y2="{mid + 5}" stroke="#A5B4FC" stroke-width="1.5"/>'
        f'<line x1="{mid + bw / 2}" y1="{mid}" x2="{mid + bw / 2 + 1}" y2="{mid}" stroke="#C4B5FD" stroke-width="1.5"/>'
    )
    return _g(cx, cy, s, body)


def icon_gateway(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    aw, ah = s * 0.5, s * 0.6
    top = mid - ah / 2
    body = (
        f'<path d="M{mid - aw / 2},{mid + ah / 2} L{mid - aw / 2},{top + ah * 0.25} '
        f'Q{mid - aw / 2},{top} {mid},{top} '
        f'Q{mid + aw / 2},{top} {mid + aw / 2},{top + ah * 0.25} L{mid + aw / 2},{mid + ah / 2}" '
        f'fill="none" stroke="#8B5CF6" stroke-width="3.5" stroke-linecap="round"/>'
        f'<line x1="{mid - aw / 2 - 5}" y1="{mid + ah / 2}" x2="{mid + aw / 2 + 5}" '
        f'y2="{mid + ah / 2}" stroke="#8B5CF6" stroke-width="3" stroke-linecap="round"/>'
        f'<line x1="{mid - 10}" y1="{mid + 4}" x2="{mid + 6}" y2="{mid + 4}" '
        f'stroke="#C4B5FD" stroke-width="2.5"/>'
        f'<polygon points="{mid + 8},{mid + 4} {mid + 3},{mid + 1} {mid + 3},{mid + 7}" fill="#C4B5FD"/>'
    )
    return _g(cx, cy, s, body)


def icon_cart(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    body = (
        f'<path d="M{mid - s * 0.32},{mid - s * 0.18} L{mid - s * 0.22},{mid + s * 0.12} '
        f'L{mid + s * 0.22},{mid + s * 0.12} L{mid + s * 0.28},{mid - s * 0.18}" '
        f'fill="#F59E0B" stroke="#D97706" stroke-width="1.5" stroke-linejoin="round"/>'
        f'<path d="M{mid - s * 0.32},{mid - s * 0.18} L{mid - s * 0.38},{mid - s * 0.28}" '
        f'stroke="#D97706" stroke-width="2.5" stroke-linecap="round"/>'
        f'<circle cx="{mid - s * 0.14}" cy="{mid + s * 0.2}" r="{s * 0.05}" fill="#D97706"/>'
        f'<circle cx="{mid + s * 0.14}" cy="{mid + s * 0.2}" r="{s * 0.05}" fill="#D97706"/>'
        f'<circle cx="{mid - s * 0.14}" cy="{mid + s * 0.2}" r="{s * 0.025}" fill="#FBBF24"/>'
        f'<circle cx="{mid + s * 0.14}" cy="{mid + s * 0.2}" r="{s * 0.025}" fill="#FBBF24"/>'
        f'<circle cx="{mid}" cy="{mid - s * 0.02}" r="{s * 0.06}" fill="white" opacity="0.8"/>'
    )
    return _g(cx, cy, s, body)


def icon_search(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    r = s * 0.22
    lx, ly = mid - 4, mid - 4
    body = (
        f'<circle cx="{lx}" cy="{ly}" r="{r}" fill="#DBEAFE"/>'
        f'<circle cx="{lx}" cy="{ly}" r="{r}" fill="none" stroke="#3B82F6" stroke-width="3"/>'
        f'<line x1="{lx + r * 0.65}" y1="{ly + r * 0.65}" '
        f'x2="{mid + s * 0.28}" y2="{mid + s * 0.28}" '
        f'stroke="#2563EB" stroke-width="4" stroke-linecap="round"/>'
        f'<path d="M{lx - r * 0.35},{ly - r * 0.5} '
        f'Q{lx},{ly - r * 0.75} {lx + r * 0.35},{ly - r * 0.5}" '
        f'fill="none" stroke="white" stroke-width="2" stroke-linecap="round" opacity="0.7"/>'
    )
    return _g(cx, cy, s, body)


def icon_package(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bw, bh = s * 0.55, s * 0.42
    body = (
        f'<rect x="{mid - bw / 2}" y="{mid - bh / 4}" width="{bw}" height="{bh * 0.78}" '
        f'rx="3" fill="#8B5CF6"/>'
        f'<rect x="{mid - bw / 2 - 2}" y="{mid - bh / 4 - bh * 0.2}" '
        f'width="{bw + 4}" height="{bh * 0.25}" rx="3" fill="#A78BFA"/>'
        f'<rect x="{mid - 2.5}" y="{mid - bh / 4}" width="5" height="{bh * 0.78}" '
        f'fill="#C4B5FD" opacity="0.5"/>'
        f'<polyline points="{mid - 6},{mid + 4} {mid - 1},{mid + 9} {mid + 8},{mid - 1}" '
        f'fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return _g(cx, cy, s, body)


def icon_warehouse(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bw, bh = s * 0.65, s * 0.45
    top = mid - bh / 2 + 4
    body = (
        f'<polygon points="{mid},{top - 12} {mid - bw / 2 - 4},{top + 4} '
        f'{mid + bw / 2 + 4},{top + 4}" fill="#92400E"/>'
        f'<rect x="{mid - bw / 2}" y="{top + 4}" width="{bw}" height="{bh}" rx="2" fill="#D97706"/>'
        f'<line x1="{mid - bw / 2 + 4}" y1="{top + bh * 0.35}" '
        f'x2="{mid + bw / 2 - 4}" y2="{top + bh * 0.35}" stroke="#92400E" stroke-width="1.5"/>'
        f'<line x1="{mid - bw / 2 + 4}" y1="{top + bh * 0.65}" '
        f'x2="{mid + bw / 2 - 4}" y2="{top + bh * 0.65}" stroke="#92400E" stroke-width="1.5"/>'
        f'<rect x="{mid - 10}" y="{top + 6}" width="7" height="6" rx="1" fill="#FBBF24"/>'
        f'<rect x="{mid + 2}" y="{top + 6}" width="9" height="6" rx="1" fill="#FCD34D"/>'
        f'<rect x="{mid - 8}" y="{top + bh * 0.37}" width="8" height="6" rx="1" fill="#FCD34D"/>'
        f'<rect x="{mid + 4}" y="{top + bh * 0.37}" width="6" height="6" rx="1" fill="#FBBF24"/>'
        f'<rect x="{mid - 5}" y="{top + bh * 0.67}" width="10" height="{bh * 0.33 - 2}" rx="2" fill="#92400E"/>'
    )
    return _g(cx, cy, s, body)


def icon_catalog(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    cw, ch = s * 0.26, s * 0.22
    gap = s * 0.04
    colors = ["#0EA5E9", "#38BDF8", "#7DD3FC", "#BAE6FD"]
    strokes = ["#0284C7", "#0EA5E9", "#38BDF8", "#7DD3FC"]
    cards = ""
    for i in range(4):
        col, row = i % 2, i // 2
        x = mid - cw - gap / 2 + col * (cw + gap)
        y = mid - ch - gap / 2 + row * (ch + gap)
        cards += (
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="4" '
            f'fill="{colors[i]}" stroke="{strokes[i]}" stroke-width="1"/>'
            f'<line x1="{x + 4}" y1="{y + ch - 6}" x2="{x + cw - 4}" y2="{y + ch - 6}" '
            f'stroke="white" stroke-width="1.5" opacity="0.6"/>'
            f'<circle cx="{x + cw / 2}" cy="{y + ch * 0.35}" r="3" fill="white" opacity="0.5"/>'
        )
    return _g(cx, cy, s, cards)


def icon_payment(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    cw, ch = s * 0.7, s * 0.44
    body = (
        f'<rect x="{mid - cw / 2}" y="{mid - ch / 2}" width="{cw}" height="{ch}" '
        f'rx="6" fill="#10B981" stroke="#059669" stroke-width="1.5"/>'
        f'<rect x="{mid - cw / 2}" y="{mid - ch / 2 + 8}" width="{cw}" height="5" fill="#059669"/>'
        f'<rect x="{mid - cw / 2 + 6}" y="{mid + 1}" width="10" height="8" rx="2" fill="#FBBF24"/>'
        f'<line x1="{mid - cw / 2 + 8}" y1="{mid + 1}" x2="{mid - cw / 2 + 8}" '
        f'y2="{mid + 9}" stroke="#D97706" stroke-width="0.7"/>'
        f'<line x1="{mid - cw / 2 + 6}" y1="{mid + 5}" x2="{mid - cw / 2 + 16}" '
        f'y2="{mid + 5}" stroke="#D97706" stroke-width="0.7"/>'
        f'<circle cx="{mid + 6}" cy="{mid + 5}" r="1.5" fill="white" opacity="0.6"/>'
        f'<circle cx="{mid + 11}" cy="{mid + 5}" r="1.5" fill="white" opacity="0.6"/>'
        f'<circle cx="{mid + 16}" cy="{mid + 5}" r="1.5" fill="white" opacity="0.6"/>'
        f'<circle cx="{mid + 21}" cy="{mid + 5}" r="1.5" fill="white" opacity="0.6"/>'
    )
    return _g(cx, cy, s, body)


def icon_email(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    ew, eh = s * 0.65, s * 0.44
    body = (
        f'<rect x="{mid - ew / 2}" y="{mid - eh / 2}" width="{ew}" height="{eh}" '
        f'rx="4" fill="#0EA5E9"/>'
        f'<path d="M{mid - ew / 2},{mid - eh / 2} L{mid},{mid + 3} L{mid + ew / 2},{mid - eh / 2}" '
        f'fill="#38BDF8" stroke="#0284C7" stroke-width="1.5" stroke-linejoin="round"/>'
        f'<line x1="{mid - ew / 2}" y1="{mid + eh / 2}" x2="{mid - 5}" y2="{mid}" '
        f'stroke="#0284C7" stroke-width="1" opacity="0.3"/>'
        f'<line x1="{mid + ew / 2}" y1="{mid + eh / 2}" x2="{mid + 5}" y2="{mid}" '
        f'stroke="#0284C7" stroke-width="1" opacity="0.3"/>'
    )
    return _g(cx, cy, s, body)


def icon_bell(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bw = s * 0.22
    body = (
        f'<path d="M{mid},{mid - s * 0.28} '
        f'Q{mid - bw - 6},{mid - s * 0.05} {mid - bw},{mid + s * 0.08} '
        f'L{mid - bw - 3},{mid + s * 0.14} L{mid + bw + 3},{mid + s * 0.14} '
        f'L{mid + bw},{mid + s * 0.08} '
        f'Q{mid + bw + 6},{mid - s * 0.05} {mid},{mid - s * 0.28}Z" '
        f'fill="#F59E0B" stroke="#D97706" stroke-width="1.5"/>'
        f'<circle cx="{mid}" cy="{mid + s * 0.2}" r="{s * 0.045}" fill="#D97706"/>'
        f'<circle cx="{mid}" cy="{mid - s * 0.3}" r="{s * 0.035}" fill="#D97706"/>'
        f'<circle cx="{mid + bw + 2}" cy="{mid - s * 0.16}" r="{s * 0.065}" '
        f'fill="#EF4444" stroke="white" stroke-width="1.5"/>'
    )
    return _g(cx, cy, s, body)


def icon_mobile(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    pw, ph = s * 0.38, s * 0.68
    body = (
        f'<rect x="{mid - pw / 2}" y="{mid - ph / 2}" width="{pw}" height="{ph}" '
        f'rx="5" fill="#374151" stroke="#1F2937" stroke-width="1.5"/>'
        f'<rect x="{mid - pw / 2 + 3}" y="{mid - ph / 2 + 8}" '
        f'width="{pw - 6}" height="{ph - 18}" rx="2" fill="#6366F1"/>'
        f'<rect x="{mid - pw / 2 + 5}" y="{mid - ph / 2 + 11}" '
        f'width="{pw - 10}" height="4" rx="1" fill="#818CF8" opacity="0.7"/>'
        f'<rect x="{mid - pw / 2 + 5}" y="{mid - ph / 2 + 17}" '
        f'width="{pw - 14}" height="3" rx="1" fill="#A5B4FC" opacity="0.5"/>'
        f'<rect x="{mid - 5}" y="{mid + ph / 2 - 6}" width="10" height="2.5" rx="1.5" fill="#6B7280"/>'
    )
    return _g(cx, cy, s, body)


def icon_dns(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    r = s * 0.34
    body = (
        f'<circle cx="{mid}" cy="{mid + 2}" r="{r}" fill="#0D9488" stroke="#0F766E" stroke-width="1.5"/>'
        f'<ellipse cx="{mid}" cy="{mid + 2}" rx="{r * 0.4}" ry="{r}" '
        f'fill="none" stroke="white" stroke-width="1" opacity="0.5"/>'
        f'<line x1="{mid - r}" y1="{mid + 2}" x2="{mid + r}" y2="{mid + 2}" '
        f'stroke="white" stroke-width="1" opacity="0.4"/>'
        f'<circle cx="{mid + r * 0.55}" cy="{mid - r * 0.45}" r="7" '
        f'fill="#EF4444" stroke="white" stroke-width="2"/>'
        f'<circle cx="{mid + r * 0.55}" cy="{mid - r * 0.45}" r="2.5" fill="white"/>'
    )
    return _g(cx, cy, s, body)


def icon_vpn(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    sh, sw = s * 0.74, s * 0.54
    top = mid - sh / 2
    body = (
        f'<path d="M{mid},{top} L{mid + sw / 2},{top + sh * 0.18} '
        f'L{mid + sw / 2},{top + sh * 0.5} Q{mid + sw / 2},{top + sh * 0.82} {mid},{top + sh} '
        f'Q{mid - sw / 2},{top + sh * 0.82} {mid - sw / 2},{top + sh * 0.5} '
        f'L{mid - sw / 2},{top + sh * 0.18} Z" fill="#7C3AED" stroke="#6D28D9" stroke-width="1.5"/>'
        f'<circle cx="{mid}" cy="{mid - 3}" r="6" fill="white" opacity="0.9"/>'
        f'<rect x="{mid - 2.5}" y="{mid + 1}" width="5" height="9" rx="2" fill="white" opacity="0.9"/>'
    )
    return _g(cx, cy, s, body)


def icon_webhook(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    body = (
        f'<path d="M{mid + 14},{mid - 16} L{mid + 14},{mid} '
        f'Q{mid + 14},{mid + 14} {mid},{mid + 14} '
        f'Q{mid - 14},{mid + 14} {mid - 14},{mid}" '
        f'fill="none" stroke="#F97316" stroke-width="3.5" stroke-linecap="round"/>'
        f'<circle cx="{mid + 14}" cy="{mid - 18}" r="3" fill="#FBBF24"/>'
        f'<polygon points="{mid - 3},{mid - 14} {mid - 7},{mid - 2} {mid - 1},{mid - 2} '
        f'{mid - 4},{mid + 5} {mid + 5},{mid - 5} {mid},{mid - 5}" fill="#FBBF24"/>'
    )
    return _g(cx, cy, s, body)


def icon_hexagons(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    import math
    hr = s * 0.14
    positions = [(mid, mid - hr * 1.7), (mid - hr * 1.5, mid + hr * 0.85), (mid + hr * 1.5, mid + hr * 0.85)]
    colors = ["#8B5CF6", "#A78BFA", "#7C3AED"]

    def hex_pts(hx, hy):
        return " ".join(
            f"{hx + hr * math.cos((i * 60 - 90) * math.pi / 180)},"
            f"{hy + hr * math.sin((i * 60 - 90) * math.pi / 180)}"
            for i in range(6)
        )

    lines = ""
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            x1, y1 = positions[i]
            x2, y2 = positions[j]
            lines += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#C4B5FD" stroke-width="2.5"/>'

    hexes = ""
    for (hx, hy), color in zip(positions, colors):
        hexes += f'<polygon points="{hex_pts(hx, hy)}" fill="{color}" stroke="{color}" stroke-width="1"/>'
        hexes += f'<circle cx="{hx}" cy="{hy}" r="3" fill="white" opacity="0.8"/>'

    return _g(cx, cy, s, lines + hexes)


def icon_cloud_multi(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    body = (
        f'<ellipse cx="{mid + 5}" cy="{mid + 6}" rx="{s * 0.32}" ry="{s * 0.17}" fill="#93C5FD"/>'
        f'<circle cx="{mid + 10}" cy="{mid - 1}" r="{s * 0.13}" fill="#93C5FD"/>'
        f'<circle cx="{mid - 2}" cy="{mid + 1}" r="{s * 0.1}" fill="#93C5FD"/>'
        f'<ellipse cx="{mid - 3}" cy="{mid + 8}" rx="{s * 0.36}" ry="{s * 0.2}" fill="#3B82F6"/>'
        f'<circle cx="{mid - 14}" cy="{mid}" r="{s * 0.16}" fill="#3B82F6"/>'
        f'<circle cx="{mid + 4}" cy="{mid - 4}" r="{s * 0.18}" fill="#3B82F6"/>'
        f'<circle cx="{mid - 4}" cy="{mid - 8}" r="{s * 0.13}" fill="#3B82F6"/>'
    )
    return _g(cx, cy, s, body)


def icon_firewall(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bw, bh = s * 0.6, s * 0.4
    bx, by = mid - bw / 2, mid - bh / 2 + 6
    bricks = ""
    rows_data = [
        (0, ["#DC2626", "#EF4444", "#DC2626"]),
        (1, ["#EF4444", "#DC2626", "#EF4444"]),
        (2, ["#DC2626", "#EF4444", "#DC2626"]),
    ]
    brick_h = bh / 3
    for row_i, (_, row_colors) in enumerate(rows_data):
        n_cols = 3
        brick_w = bw / n_cols
        off = brick_w * 0.4 if row_i % 2 else 0
        for col in range(n_cols):
            rx = bx + col * brick_w + off
            ry = by + row_i * brick_h
            clamped_w = min(brick_w - 1, bx + bw - rx - 0.5)
            if clamped_w > 0 and rx < bx + bw:
                bricks += (
                    f'<rect x="{max(rx, bx) + 0.5}" y="{ry + 0.5}" '
                    f'width="{clamped_w}" height="{brick_h - 1}" rx="1" fill="{row_colors[col]}"/>'
                )
    flame = (
        f'<path d="M{mid},{by - 14} Q{mid + 8},{by - 4} {mid + 5},{by + 2} '
        f'Q{mid + 10},{by - 2} {mid + 12},{by + 3} Q{mid + 6},{by + 8} {mid},{by + 1} '
        f'Q{mid - 6},{by + 8} {mid - 12},{by + 3} Q{mid - 10},{by - 2} {mid - 5},{by + 2} '
        f'Q{mid - 8},{by - 4} {mid},{by - 14}Z" fill="#F59E0B" opacity="0.85"/>'
        f'<path d="M{mid},{by - 8} Q{mid + 4},{by - 1} {mid + 2},{by + 2} '
        f'Q{mid - 2},{by + 4} {mid - 2},{by + 2} Q{mid - 4},{by - 1} {mid},{by - 8}Z" '
        f'fill="#FBBF24"/>'
    )
    return _g(cx, cy, s, flame + bricks)


def icon_brain(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    body = (
        f'<path d="M{mid},{mid - s * 0.28} '
        f'Q{mid - s * 0.35},{mid - s * 0.3} {mid - s * 0.3},{mid - s * 0.05} '
        f'Q{mid - s * 0.35},{mid + s * 0.12} {mid - s * 0.2},{mid + s * 0.26} '
        f'Q{mid - s * 0.05},{mid + s * 0.32} {mid},{mid + s * 0.26}" '
        f'fill="#8B5CF6" stroke="#7C3AED" stroke-width="1"/>'
        f'<path d="M{mid},{mid - s * 0.28} '
        f'Q{mid + s * 0.35},{mid - s * 0.3} {mid + s * 0.3},{mid - s * 0.05} '
        f'Q{mid + s * 0.35},{mid + s * 0.12} {mid + s * 0.2},{mid + s * 0.26} '
        f'Q{mid + s * 0.05},{mid + s * 0.32} {mid},{mid + s * 0.26}" '
        f'fill="#A78BFA" stroke="#7C3AED" stroke-width="1"/>'
        f'<line x1="{mid}" y1="{mid - s * 0.26}" x2="{mid}" y2="{mid + s * 0.24}" '
        f'stroke="#7C3AED" stroke-width="1.5"/>'
        f'<circle cx="{mid - 8}" cy="{mid - 8}" r="2.5" fill="white"/>'
        f'<circle cx="{mid + 10}" cy="{mid - 4}" r="2.5" fill="white"/>'
        f'<circle cx="{mid - 6}" cy="{mid + 8}" r="2.5" fill="white"/>'
        f'<circle cx="{mid + 7}" cy="{mid + 10}" r="2.5" fill="white"/>'
        f'<line x1="{mid - 8}" y1="{mid - 8}" x2="{mid + 10}" y2="{mid - 4}" '
        f'stroke="white" stroke-width="1" opacity="0.5"/>'
        f'<line x1="{mid - 8}" y1="{mid - 8}" x2="{mid - 6}" y2="{mid + 8}" '
        f'stroke="white" stroke-width="1" opacity="0.5"/>'
        f'<line x1="{mid + 10}" y1="{mid - 4}" x2="{mid + 7}" y2="{mid + 10}" '
        f'stroke="white" stroke-width="1" opacity="0.5"/>'
    )
    return _g(cx, cy, s, body)


def icon_cache(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    bars = ""
    n, pad = 4, 10
    bh = 5
    gap = 3
    colors = ["#0EA5E9", "#38BDF8", "#7DD3FC", "#BAE6FD"]
    widths = [1.0, 0.75, 0.85, 0.6]
    max_w = s - 2 * pad
    total_h = n * bh + (n - 1) * gap
    start_y = mid - total_h / 2
    for i in range(n):
        w = max_w * widths[i]
        y = start_y + i * (bh + gap)
        bars += f'<rect x="{pad}" y="{y}" width="{w}" height="{bh}" rx="2.5" fill="{colors[i]}"/>'
    cr = s * 0.14
    clk_x, clk_y = mid + s * 0.22, mid - s * 0.18
    clock = (
        f'<circle cx="{clk_x}" cy="{clk_y}" r="{cr}" fill="white" stroke="#0EA5E9" stroke-width="2"/>'
        f'<line x1="{clk_x}" y1="{clk_y}" x2="{clk_x}" y2="{clk_y - cr * 0.6}" '
        f'stroke="#0EA5E9" stroke-width="1.5" stroke-linecap="round"/>'
        f'<line x1="{clk_x}" y1="{clk_y}" x2="{clk_x + cr * 0.5}" y2="{clk_y + cr * 0.2}" '
        f'stroke="#0EA5E9" stroke-width="1.5" stroke-linecap="round"/>'
    )
    return _g(cx, cy, s, bars + clock)


def icon_load_balancer(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    body = (
        f'<polygon points="{mid},{mid - s * 0.05} {mid - s * 0.3},{mid + s * 0.05} '
        f'{mid + s * 0.3},{mid + s * 0.05}" fill="#7C3AED" stroke="#6D28D9" stroke-width="1.5"/>'
        f'<rect x="{mid - 1.5}" y="{mid + s * 0.05}" width="3" height="{s * 0.15}" fill="#7C3AED"/>'
        f'<rect x="{mid - s * 0.2}" y="{mid + s * 0.2}" width="{s * 0.4}" height="4" rx="2" fill="#7C3AED"/>'
        f'<circle cx="{mid - s * 0.25}" cy="{mid - s * 0.2}" r="{s * 0.08}" fill="#A78BFA"/>'
        f'<circle cx="{mid + s * 0.25}" cy="{mid - s * 0.2}" r="{s * 0.08}" fill="#C4B5FD"/>'
        f'<line x1="{mid - s * 0.15}" y1="{mid - s * 0.05}" '
        f'x2="{mid - s * 0.22}" y2="{mid - s * 0.14}" stroke="#A78BFA" stroke-width="2"/>'
        f'<line x1="{mid + s * 0.15}" y1="{mid - s * 0.05}" '
        f'x2="{mid + s * 0.22}" y2="{mid - s * 0.14}" stroke="#C4B5FD" stroke-width="2"/>'
    )
    return _g(cx, cy, s, body)


def icon_cdn(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    r = s * 0.32
    body = (
        f'<circle cx="{mid}" cy="{mid}" r="{r}" fill="#0D9488" stroke="#0F766E" stroke-width="1.5"/>'
        f'<ellipse cx="{mid}" cy="{mid}" rx="{r * 0.4}" ry="{r}" '
        f'fill="none" stroke="white" stroke-width="1" opacity="0.5"/>'
        f'<line x1="{mid - r}" y1="{mid}" x2="{mid + r}" y2="{mid}" '
        f'stroke="white" stroke-width="1" opacity="0.4"/>'
        f'<polygon points="{mid + r + 8},{mid - 4} {mid + r + 2},{mid} {mid + r + 8},{mid + 4}" '
        f'fill="#FBBF24"/>'
        f'<polygon points="{mid - r - 8},{mid - 4} {mid - r - 2},{mid} {mid - r - 8},{mid + 4}" '
        f'fill="#FBBF24"/>'
        f'<polygon points="{mid - 4},{mid - r - 8} {mid},{mid - r - 2} {mid + 4},{mid - r - 8}" '
        f'fill="#FBBF24"/>'
    )
    return _g(cx, cy, s, body)


def icon_analytics(cx: float, cy: float, s: float) -> str:
    mid = s / 2
    pad = 10
    body = (
        f'<rect x="{pad}" y="{pad}" width="{s - 2 * pad}" height="{s - 2 * pad}" '
        f'rx="6" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.5"/>'
        f'<polyline points="{pad + 6},{mid + 12} {mid - 8},{mid + 2} {mid + 2},{mid + 8} '
        f'{mid + 10},{mid - 8} {s - pad - 6},{mid - 14}" '
        f'fill="none" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{s - pad - 6}" cy="{mid - 14}" r="3" fill="#10B981"/>'
        f'<line x1="{pad + 6}" y1="{s - pad - 4}" x2="{s - pad - 6}" y2="{s - pad - 4}" '
        f'stroke="#CBD5E1" stroke-width="1" opacity="0.6"/>'
        f'<line x1="{pad + 6}" y1="{pad + 4}" x2="{pad + 6}" y2="{s - pad - 4}" '
        f'stroke="#CBD5E1" stroke-width="1" opacity="0.6"/>'
    )
    return _g(cx, cy, s, body)


BUILTIN_ICONS: dict[str, callable] = {
    "event-hubs": icon_event_hubs,
    "storage": icon_storage,
    "function-apps": icon_function_apps,
    "database": icon_database,
    "cognitive": icon_cognitive,
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
    "api": icon_api,
    "gateway": icon_gateway,
    "cart": icon_cart,
    "search": icon_search,
    "package": icon_package,
    "order": icon_package,
    "warehouse": icon_warehouse,
    "catalog": icon_catalog,
    "payment": icon_payment,
    "email": icon_email,
    "bell": icon_bell,
    "notification": icon_bell,
    "mobile": icon_mobile,
    "dns": icon_dns,
    "vpn": icon_vpn,
    "webhook": icon_webhook,
    "hexagons": icon_hexagons,
    "microservice": icon_hexagons,
    "cloud": icon_cloud_multi,
    "firewall": icon_firewall,
    "brain": icon_brain,
    "ai": icon_brain,
    "ml": icon_brain,
    "cache": icon_cache,
    "load-balancer": icon_load_balancer,
    "cdn": icon_cdn,
    "analytics": icon_analytics,
    "function": icon_function_apps,
}


def _render_external_svg(path: str, cx: float, cy: float, size: float) -> str:
    """Load an external SVG file and render it at (cx, cy) scaled to *size*.

    Strips the outer <svg> wrapper and re-embeds the inner content using a
    nested <svg> with explicit viewBox + pixel width/height so it renders
    correctly when placed inside the parent diagram SVG.
    """
    import re as _re

    raw = load_external_svg(path)

    vb_match = _re.search(r'viewBox="([^"]+)"', raw)
    if vb_match:
        parts = vb_match.group(1).split()
        if len(parts) == 4:
            vb_x, vb_y = float(parts[0]), float(parts[1])
            vb_w, vb_h = float(parts[2]), float(parts[3])
        else:
            vb_x = vb_y = 0.0
            vb_w = vb_h = 64.0
    else:
        vb_x = vb_y = 0.0
        vb_w = vb_h = 64.0

    scale = size / max(vb_w, vb_h)
    rendered_w = vb_w * scale
    rendered_h = vb_h * scale

    defs_match = _re.search(r'(<defs>.*?</defs>)', raw, _re.DOTALL)
    defs = defs_match.group(1) if defs_match else ""

    inner = _re.sub(r'<svg[^>]*>', '', raw, count=1)
    inner = _re.sub(r'</svg>\s*$', '', inner)
    if defs_match:
        inner = inner.replace(defs, '', 1)

    x = cx - rendered_w / 2
    y = cy - rendered_h / 2
    vb = f"{vb_x} {vb_y} {vb_w} {vb_h}"

    return (
        f'{defs}'
        f'<svg x="{x}" y="{y}" width="{rendered_w}" height="{rendered_h}" '
        f'viewBox="{vb}">{inner}</svg>'
    )


def render_icon_svg(icon_key: str | None, cx: float, cy: float, size: float = 68) -> str:
    """Render an icon at (cx, cy). Returns SVG string or empty string for text-only fallback."""
    if icon_key is None:
        return ""

    if icon_key.startswith("external:"):
        path = icon_key[len("external:"):]
        try:
            return _render_external_svg(path, cx, cy, size)
        except Exception:
            return ""

    fn = BUILTIN_ICONS.get(icon_key)
    if fn:
        return fn(cx, cy, size)

    ext_path = STATIC_ICONS_DIR / f"{icon_key}.svg"
    if ext_path.is_file():
        try:
            return _render_external_svg(str(ext_path), cx, cy, size)
        except Exception:
            return ""

    return ""
