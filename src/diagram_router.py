"""Detect diagram type and route to the correct renderer."""

from __future__ import annotations

import logging

from src.markdown_parser import DiagramBlock

logger = logging.getLogger("vizdown.router")

CUSTOM_SVG_TYPES = {"mindmap", "architecture", "service-diagram"}

MERMAID_TYPES = {
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "erDiagram",
    "stateDiagram", "stateDiagram-v2", "gantt", "gitGraph", "pie",
    "timeline", "quadrantChart", "sankey-beta", "xychart-beta",
    "block-beta", "architecture-beta", "kanban", "packet-beta",
    "journey", "C4Context", "C4Container", "C4Component", "C4Dynamic",
    "requirement",
}


async def render_block(
    block: DiagramBlock,
    theme: str = "light",
    look: str = "default",
    output_format: str = "svg",
    scale: int = 2,
) -> dict:
    """Render a single diagram block and return result dict."""
    dtype = block.diagram_type

    if dtype == "mindmap":
        from src.renderers.mindmap_renderer import render_mindmap
        svg = render_mindmap(block.syntax, theme=theme)
    elif dtype in ("architecture", "service-diagram"):
        from src.renderers.architecture_renderer import render_architecture
        svg = render_architecture(block.syntax, theme=theme)
    else:
        try:
            from src.renderers.mermaid_renderer import render_mermaid
        except ImportError:
            raise RuntimeError(
                f"Diagram type '{dtype}' requires Playwright for Mermaid rendering. "
                "Install with: pip install playwright && playwright install chromium"
            )
        svg = await render_mermaid(block.syntax, theme=theme, look=look)

    if output_format != "svg":
        try:
            from src.utils.export import convert_svg
        except ImportError:
            raise RuntimeError(
                f"Export to '{output_format}' requires additional dependencies. "
                "Install with: pip install playwright cairosvg Pillow"
            )
        encoded = await convert_svg(svg, output_format=output_format, scale=scale)
    else:
        import base64
        encoded = base64.b64encode(svg.encode("utf-8")).decode()

    return {
        "diagram_type": dtype,
        "output_format": output_format,
        "base64": encoded,
    }
