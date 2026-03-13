"""Vizdown-MCP: MCP server that converts Markdown into beautiful diagrams."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.markdown_parser import parse_markdown, DiagramBlock
from src.diagram_router import render_block

logger = logging.getLogger("vizdown")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Vizdown-MCP")


def _read_source(file_path: str | None, raw_markdown: str | None) -> str:
    if raw_markdown:
        return raw_markdown
    if file_path:
        p = Path(file_path).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        return p.read_text(encoding="utf-8")
    raise ValueError("Provide either file_path or raw_markdown")


@mcp.tool()
async def render_diagram(
    file_path: str | None = None,
    raw_markdown: str | None = None,
    output_format: str = "svg",
    theme: str = "light",
    look: str = "default",
    scale: int = 2,
) -> dict:
    """Render the first diagram found in a Markdown file or raw text.

    Args:
        file_path: Path to a .md file containing a diagram block.
        raw_markdown: Raw markdown string with a diagram code block.
        output_format: "svg" (default), "png", "jpeg", or "pdf".
        theme: "light" (default) or "dark".
        look: "default" or "handDrawn" (Mermaid sketch mode).
        scale: Resolution multiplier for PNG/JPEG (default 2).

    Returns:
        Dict with diagram_type, output_format, and base64-encoded output.
    """
    text = _read_source(file_path, raw_markdown)
    blocks = parse_markdown(text)
    if not blocks:
        return {"error": "No diagram blocks found in the provided markdown."}

    block = blocks[0]
    result = await render_block(block, theme=theme, look=look, output_format=output_format, scale=scale)
    return result


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
    text = _read_source(file_path, raw_markdown)
    blocks = parse_markdown(text)
    if not blocks:
        return [{"error": "No diagram blocks found."}]

    results = []
    stem = Path(file_path).stem if file_path else "diagram"

    for idx, block in enumerate(blocks):
        result = await render_block(block, theme=theme, look=look, output_format=output_format, scale=scale)
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

    return results


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


def main():
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
