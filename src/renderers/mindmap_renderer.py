"""Custom pure-Python SVG mind map renderer — premium edition.

Produces a balanced horizontal tree with:
  - Dark navy root with glow
  - Vivid L1 branch nodes with subtle shadows
  - Progressive watercolour fade: deeper nodes get lighter + less saturated
  - Auto text contrast (WCAG): white on dark fills, slate on light fills
  - Organic cubic Bézier connectors with tapered stroke + gradient opacity
  - Generous spacing for a breathable, modern aesthetic
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, field
from xml.sax.saxutils import escape as xml_escape

from src.utils.color_palette import (
    generate_apple_palette,
    depth_color,
    text_color_for_bg,
)

# ── Layout constants ─────────────────────────────────────────────────────────
V_GAP = 14
H_GAP = 52
BRANCH_GAP = 24
NODE_PAD_X = 22
NODE_PAD_Y = 10

FONT_SIZE_ROOT = 18
FONT_SIZE_L1 = 14
FONT_SIZE_L2 = 12.5
FONT_SIZE_LEAF = 11.5
FONT_FAMILY = (
    "'SF Pro Display', 'SF Pro Text', system-ui, -apple-system, "
    "BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
)

# ── Root node theme ──────────────────────────────────────────────────────────
ROOT_FILL_LIGHT = "#1E293B"
ROOT_FILL_DARK = "#E2E8F0"
ROOT_BORDER_LIGHT = "#0F172A"
ROOT_BORDER_DARK = "#CBD5E1"


@dataclass
class MindMapNode:
    text: str
    level: int
    children: list["MindMapNode"] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    branch_index: int = 0


# ── Parsing ──────────────────────────────────────────────────────────────────

def _parse_mindmap(syntax: str) -> MindMapNode | None:
    lines = syntax.strip().split("\n")
    if not lines:
        return None

    start = 0
    if lines[0].strip().lower() == "mindmap":
        start = 1
    if start >= len(lines):
        return None

    root_text = lines[start].strip()
    root_text = re.sub(r"^[\[\(]+|[\]\)]+$", "", root_text).strip()
    if not root_text:
        return None
    root = MindMapNode(text=root_text, level=0)

    stack: list[tuple[int, MindMapNode]] = [(0, root)]

    for line in lines[start + 1:]:
        if not line.strip():
            continue
        raw = line.rstrip()
        indent = len(raw) - len(raw.lstrip())
        if indent == 0 and raw.strip().startswith(("  ", "\t")):
            indent = 2
        text = raw.strip()
        text = re.sub(r"^[\[\(\{]+|[\]\)\}]+$", "", text).strip()
        if not text:
            continue

        level = max(1, indent // 2)
        node = MindMapNode(text=text, level=level)

        while stack and stack[-1][0] >= level:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        else:
            root.children.append(node)
        stack.append((level, node))

    return root


# ── Measurement & Layout ─────────────────────────────────────────────────────

def _font_size(level: int) -> float:
    if level == 0:
        return FONT_SIZE_ROOT
    if level == 1:
        return FONT_SIZE_L1
    if level == 2:
        return FONT_SIZE_L2
    return FONT_SIZE_LEAF


def _estimate_text_width(text: str, font_size: float) -> float:
    return len(text) * font_size * 0.56


def _measure(node: MindMapNode) -> None:
    fs = _font_size(node.level)
    tw = _estimate_text_width(node.text, fs)
    node.width = tw + 2 * NODE_PAD_X
    node.height = fs + 2 * NODE_PAD_Y
    if node.level == 0:
        node.width += 16
        node.height += 8
    for child in node.children:
        _measure(child)


def _subtree_height(node: MindMapNode) -> float:
    if not node.children:
        return node.height
    total = sum(_subtree_height(c) for c in node.children)
    total += (len(node.children) - 1) * V_GAP
    return max(node.height, total)


def _layout_branch(node: MindMapNode, cx: float, top_y: float, direction: int) -> None:
    sh = _subtree_height(node)
    node.x = cx
    node.y = top_y + sh / 2

    if not node.children:
        return

    child_x = cx + direction * (node.width / 2 + H_GAP)
    total_ch = sum(_subtree_height(c) for c in node.children) + (len(node.children) - 1) * V_GAP
    cur_y = node.y - total_ch / 2

    for child in node.children:
        ch = _subtree_height(child)
        child.x = child_x + direction * child.width / 2
        _layout_branch(child, child.x, cur_y, direction)
        cur_y += ch + V_GAP


def _layout(root: MindMapNode) -> tuple[float, float, float, float]:
    _measure(root)
    root.x = 0
    root.y = 0

    left_branches = root.children[::2]
    right_branches = root.children[1::2]

    def _set_branch_idx(node: MindMapNode, idx: int):
        node.branch_index = idx
        for c in node.children:
            _set_branch_idx(c, idx)

    for i, child in enumerate(left_branches):
        _set_branch_idx(child, i * 2)
    for i, child in enumerate(right_branches):
        _set_branch_idx(child, i * 2 + 1)

    base_offset = root.width / 2 + H_GAP

    if left_branches:
        total_left = sum(_subtree_height(c) for c in left_branches) + (len(left_branches) - 1) * BRANCH_GAP
        cur_y = -total_left / 2
        for child in left_branches:
            ch = _subtree_height(child)
            _layout_branch(child, -base_offset - child.width / 2, cur_y, -1)
            cur_y += ch + BRANCH_GAP

    if right_branches:
        total_right = sum(_subtree_height(c) for c in right_branches) + (len(right_branches) - 1) * BRANCH_GAP
        cur_y = -total_right / 2
        for child in right_branches:
            ch = _subtree_height(child)
            _layout_branch(child, base_offset + child.width / 2, cur_y, 1)
            cur_y += ch + BRANCH_GAP

    all_nodes: list[MindMapNode] = []

    def _collect(n: MindMapNode):
        all_nodes.append(n)
        for c in n.children:
            _collect(c)

    _collect(root)
    if not all_nodes:
        return 0, 0, 100, 100

    pad = 60
    min_x = min(n.x - n.width / 2 for n in all_nodes) - pad
    max_x = max(n.x + n.width / 2 for n in all_nodes) + pad
    min_y = min(n.y - n.height / 2 for n in all_nodes) - pad
    max_y = max(n.y + n.height / 2 for n in all_nodes) + pad
    return min_x, min_y, max_x, max_y


# ── SVG Rendering ────────────────────────────────────────────────────────────

def _svg_defs(theme: str, palette: list[dict]) -> str:
    """Build <defs> with filters, gradients, and connector gradient pairs."""
    defs = ['<defs>']

    # Soft drop shadow for root
    defs.append(
        '<filter id="rootShadow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#000" flood-opacity="0.18"/>'
        '</filter>'
    )

    # Subtle shadow for L1
    defs.append(
        '<filter id="l1Shadow" x="-15%" y="-15%" width="130%" height="130%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000" flood-opacity="0.10"/>'
        '</filter>'
    )

    # Per-branch connector gradients — use the vivid stroke color, fading to soft
    for i, entry in enumerate(palette):
        c_vivid = entry["border"]
        c_soft = entry["fill"]
        defs.append(
            f'<linearGradient id="brGrad{i}" x1="0%" y1="0%" x2="100%" y2="0%">'
            f'<stop offset="0%" stop-color="{c_vivid}" stop-opacity="0.55"/>'
            f'<stop offset="100%" stop-color="{c_soft}" stop-opacity="0.25"/>'
            f'</linearGradient>'
        )
        defs.append(
            f'<linearGradient id="brGradR{i}" x1="100%" y1="0%" x2="0%" y2="0%">'
            f'<stop offset="0%" stop-color="{c_vivid}" stop-opacity="0.55"/>'
            f'<stop offset="100%" stop-color="{c_soft}" stop-opacity="0.25"/>'
            f'</linearGradient>'
        )

    defs.append('</defs>')
    return "\n".join(defs)


def _bezier(
    x1: float, y1: float,
    x2: float, y2: float,
    branch_idx: int,
    parent_level: int,
) -> str:
    """Organic cubic Bézier with tapered stroke and gradient fill."""
    dx = abs(x2 - x1)
    cp_offset = dx * 0.55
    if x2 > x1:
        cx1, cx2 = x1 + cp_offset, x2 - cp_offset
        grad_id = f"brGrad{branch_idx}"
    else:
        cx1, cx2 = x1 - cp_offset, x2 + cp_offset
        grad_id = f"brGradR{branch_idx}"

    stroke_w = max(3.0 - parent_level * 0.5, 1.2)

    return (
        f'<path d="M{x1},{y1} C{cx1},{y1} {cx2},{y2} {x2},{y2}" '
        f'fill="none" stroke="url(#{grad_id})" stroke-width="{stroke_w}" '
        f'stroke-linecap="round"/>'
    )


def _render_node(node: MindMapNode, palette: list[dict], theme: str) -> str:
    fs = _font_size(node.level)
    rx = node.height / 2

    if node.level == 0:
        fill = ROOT_FILL_LIGHT if theme == "light" else ROOT_FILL_DARK
        border = ROOT_BORDER_LIGHT if theme == "light" else ROOT_BORDER_DARK
        text_color = "white" if theme == "light" else "#0F172A"
        font_weight = "700"
        shadow_filter = ' filter="url(#rootShadow)"'
    elif node.level == 1:
        idx = node.branch_index % len(palette) if palette else 0
        entry = palette[idx]
        colors = depth_color(entry["hue"], entry.get("fill_saturation", 50), 1, theme)
        fill = colors["fill"]
        border = colors["border"]
        text_color = colors["text"]
        font_weight = "600"
        shadow_filter = ' filter="url(#l1Shadow)"'
    else:
        idx = node.branch_index % len(palette) if palette else 0
        entry = palette[idx]
        colors = depth_color(entry["hue"], entry.get("fill_saturation", 50), node.level, theme)
        fill = colors["fill"]
        border = colors["border"]
        text_color = colors["text"]
        font_weight = "500" if node.level == 2 else "400"
        shadow_filter = ""

    letter_spacing = ""
    if node.level == 0:
        letter_spacing = ' letter-spacing="0.5"'
    elif node.level >= 3:
        letter_spacing = ' letter-spacing="0.2"'

    rect = (
        f'<rect x="{node.x - node.width / 2}" y="{node.y - node.height / 2}" '
        f'width="{node.width}" height="{node.height}" rx="{rx}" '
        f'fill="{fill}" stroke="{border}" stroke-width="1.5"{shadow_filter}/>'
    )
    text = (
        f'<text x="{node.x}" y="{node.y + fs * 0.36}" '
        f'text-anchor="middle" fill="{text_color}" '
        f'font-size="{fs}" font-weight="{font_weight}" '
        f'font-family="{FONT_FAMILY}"{letter_spacing}>'
        f'{xml_escape(node.text)}</text>'
    )
    return rect + text


def _render_connections(parent: MindMapNode, palette: list[dict]) -> str:
    svg = ""
    for child in parent.children:
        idx = child.branch_index % len(palette) if palette else 0
        edge_x_parent = parent.x + (parent.width / 2 if child.x > parent.x else -parent.width / 2)
        edge_x_child = child.x + (-child.width / 2 if child.x > parent.x else child.width / 2)
        svg += _bezier(edge_x_parent, parent.y, edge_x_child, child.y, idx, parent.level)
        svg += _render_connections(child, palette)
    return svg


# ── Main entry point ─────────────────────────────────────────────────────────

def render_mindmap(syntax: str, theme: str = "light") -> str:
    root = _parse_mindmap(syntax)
    if root is None:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60">'
            '<text x="20" y="35" font-size="14" fill="red">'
            'Empty or invalid mindmap syntax</text></svg>'
        )

    n_branches = len(root.children)
    palette = generate_apple_palette(max(n_branches, 1), theme=theme)

    min_x, min_y, max_x, max_y = _layout(root)
    w = max_x - min_x
    h = max_y - min_y

    bg_color = "#FFFFFF" if theme == "light" else "#0F172A"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x} {min_y} {w} {h}" '
        f'width="{w}" height="{h}" style="font-family: {FONT_FAMILY}">',
        _svg_defs(theme, palette),
        f'<rect x="{min_x}" y="{min_y}" width="{w}" height="{h}" fill="{bg_color}"/>',
    ]

    parts.append(_render_connections(root, palette))

    def _render_all(node: MindMapNode):
        parts.append(_render_node(node, palette, theme))
        for child in node.children:
            _render_all(child)

    _render_all(root)
    parts.append("</svg>")
    return "\n".join(parts)
