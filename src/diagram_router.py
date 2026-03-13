"""Detect diagram type and route to the correct renderer."""

from __future__ import annotations

from src.markdown_parser import DiagramBlock

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
        from src.renderers.mermaid_renderer import render_mermaid
        svg = await render_mermaid(block.syntax, theme=theme, look=look)

    if output_format != "svg":
        from src.utils.export import convert_svg
        encoded = await convert_svg(svg, output_format=output_format, scale=scale)
    else:
        import base64
        encoded = base64.b64encode(svg.encode("utf-8")).decode()

    return {
        "diagram_type": dtype,
        "output_format": output_format,
        "base64": encoded,
    }
