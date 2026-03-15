"""Vizdown-MCP: MCP server that converts Markdown into beautiful diagrams.

Tools:
  render_diagram       — Render an explicit diagram block from Markdown.
  render_auto_diagram  — Analyze any text and auto-generate the best diagram.
  render_all_diagrams  — Render every diagram block in a document.
  list_diagrams        — List detected diagram blocks without rendering.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.markdown_parser import parse_markdown, DiagramBlock
from src.diagram_router import render_block
from src.utils.auto_analyzer import auto_analyze

logger = logging.getLogger("vizdown")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Vizdown-MCP")


def _read_source(file_path: str | None, raw_text: str | None) -> str:
    if raw_text:
        return raw_text
    if file_path:
        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return p.read_text(encoding="utf-8")
    raise ValueError("Provide either file_path or raw content")


@mcp.tool()
async def render_diagram(
    file_path: str | None = None,
    raw_markdown: str | None = None,
    output_format: str = "svg",
    theme: str = "light",
    look: str = "default",
    scale: int = 2,
) -> dict:
    """Render a diagram from Markdown that contains an explicit diagram block.

    The markdown must contain a fenced code block with a diagram type
    (```architecture, ```mindmap, ```mermaid, or any supported Mermaid type).
    The parser will detect and render the first block found.

    Use this tool when you already have or want to write the diagram syntax
    yourself. For automatic diagram generation from plain text, use
    render_auto_diagram instead.

    Args:
        file_path: Path to a .md file containing a diagram block.
        raw_markdown: Raw markdown string with a fenced diagram code block.
        output_format: "svg" (default), "png", "jpeg", or "pdf".
        theme: "light" (default) or "dark".
        look: "default" or "handDrawn" (Mermaid sketch mode).
        scale: Resolution multiplier for PNG/JPEG (default 2).

    Returns:
        Dict with diagram_type, output_format, and base64-encoded output.
    """
    try:
        text = _read_source(file_path, raw_markdown)
        blocks = parse_markdown(text)
        if not blocks:
            return {"error": "No diagram blocks found in the provided markdown."}

        block = blocks[0]
        return await render_block(
            block, theme=theme, look=look,
            output_format=output_format, scale=scale,
        )
    except FileNotFoundError as exc:
        return {"error": str(exc)}
    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception("render_diagram failed")
        return {"error": f"Rendering failed: {exc}"}


@mcp.tool()
async def render_auto_diagram(
    file_path: str | None = None,
    raw_text: str | None = None,
    output_format: str = "svg",
    theme: str = "light",
    look: str = "default",
    scale: int = 2,
) -> dict:
    """Automatically analyze any text and generate the best-fit diagram.

    Feed this tool ANY text — project descriptions, meeting notes, technical
    specs, system overviews, process docs, API docs, data models, timelines —
    and it will:

      1. Deep-scan for entities, relationships, hierarchies, processes,
         interactions, states, and temporal events
      2. Score every diagram type (architecture, mindmap, flowchart, sequence,
         state, ER, timeline) based on what it finds
      3. Pick the highest-scoring type and generate complete diagram syntax
      4. Render the diagram to SVG/PNG/PDF

    Use this when you don't know which diagram type to use, or when you want
    the tool to figure out the best visualization from raw content.

    Supported auto-detected diagram types:
      - architecture  — services, components, flows, groups (custom SVG)
      - mindmap       — hierarchical categories, overviews (custom SVG)
      - flowchart     — sequential steps, decisions, processes (Mermaid)
      - sequenceDiagram — actor interactions, request/response (Mermaid)
      - stateDiagram  — states and transitions (Mermaid)
      - erDiagram     — entities, attributes, relationships (Mermaid)
      - timeline      — dates, milestones, phases (Mermaid)

    Args:
        file_path: Path to any text file (.md, .txt, etc.) to analyze.
        raw_text: Raw text string to analyze and convert to a diagram.
        output_format: "svg" (default), "png", "jpeg", or "pdf".
        theme: "light" (default) or "dark".
        look: "default" or "handDrawn" (Mermaid sketch mode).
        scale: Resolution multiplier for PNG/JPEG (default 2).

    Returns:
        Dict with diagram_type, auto_detected flag, output_format,
        and base64-encoded output.
    """
    try:
        text = _read_source(file_path, raw_text)

        blocks = parse_markdown(text)
        if blocks:
            block = blocks[0]
            result = await render_block(
                block, theme=theme, look=look,
                output_format=output_format, scale=scale,
            )
            result["auto_detected"] = False
            result["note"] = "Found explicit diagram block — rendered directly."
            return result

        diagram_type, syntax = auto_analyze(text)

        if not syntax:
            return {"error": "Could not extract enough structure from the text to generate a diagram."}

        logger.info("Auto-detected diagram type: %s", diagram_type)

        block = DiagramBlock(
            diagram_type=diagram_type,
            syntax=syntax,
            line_start=1,
            line_end=len(text.split("\n")),
            source="auto",
        )

        result = await render_block(
            block, theme=theme, look=look,
            output_format=output_format, scale=scale,
        )
        result["auto_detected"] = True
        result["auto_diagram_type"] = diagram_type
        return result

    except FileNotFoundError as exc:
        return {"error": str(exc)}
    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception("render_auto_diagram failed")
        return {"error": f"Auto-rendering failed: {exc}"}


@mcp.tool()
async def render_all_diagrams(
    file_path: str | None = None,
    raw_markdown: str | None = None,
    output_format: str = "svg",
    theme: str = "light",
    look: str = "default",
    scale: int = 2,
    output_dir: str | None = None,
) -> list[dict]:
    """Render ALL diagram blocks found in a Markdown file.

    Parses the entire document, finds every diagram block, renders each
    separately, and optionally saves output files.

    Args:
        file_path: Path to a .md file.
        raw_markdown: Raw markdown string.
        output_format: "svg", "png", "jpeg", or "pdf".
        theme: "light" or "dark".
        look: "default" or "handDrawn".
        scale: Resolution multiplier for raster output.
        output_dir: Directory to save rendered files. Files are named
                     {stem}_{type}_{index}.{format}.

    Returns:
        List of result dicts, each with diagram_type, index, and base64 output.
    """
    try:
        text = _read_source(file_path, raw_markdown)
        blocks = parse_markdown(text)
        if not blocks:
            return [{"error": "No diagram blocks found."}]

        results = []
        stem = Path(file_path).stem if file_path else "diagram"

        for idx, block in enumerate(blocks):
            try:
                result = await render_block(
                    block, theme=theme, look=look,
                    output_format=output_format, scale=scale,
                )
                result["index"] = idx

                if output_dir:
                    out_path = Path(output_dir)
                    out_path.mkdir(parents=True, exist_ok=True)
                    ext = output_format if output_format != "jpeg" else "jpg"
                    fname = f"{stem}_{block.diagram_type}_{idx}.{ext}"
                    fpath = out_path / fname
                    data = base64.b64decode(result["base64"])
                    fpath.write_bytes(data)
                    result["saved_to"] = str(fpath)

                results.append(result)
            except Exception as exc:
                results.append({
                    "index": idx,
                    "diagram_type": block.diagram_type,
                    "error": f"Failed to render block {idx}: {exc}",
                })

        return results
    except Exception as exc:
        logger.exception("render_all_diagrams failed")
        return [{"error": f"Failed: {exc}"}]


@mcp.tool()
async def list_diagrams(
    file_path: str | None = None,
    raw_markdown: str | None = None,
) -> list[dict]:
    """List all detected diagram blocks without rendering them.

    Args:
        file_path: Path to a .md file.
        raw_markdown: Raw markdown string.

    Returns:
        List of dicts with diagram_type, line_start, and line_end for each block.
    """
    try:
        text = _read_source(file_path, raw_markdown)
        blocks = parse_markdown(text)
        return [
            {
                "diagram_type": b.diagram_type,
                "line_start": b.line_start,
                "line_end": b.line_end,
            }
            for b in blocks
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


def main():
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
