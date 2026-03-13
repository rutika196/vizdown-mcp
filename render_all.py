"""Render all example diagrams and save SVG outputs to output/ directory."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.markdown_parser import parse_markdown
from src.diagram_router import render_block
import base64


EXAMPLES_DIR = Path(__file__).parent / "examples"
OUTPUT_DIR = Path(__file__).parent / "output"


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    examples = sorted(EXAMPLES_DIR.glob("*.md"))

    print(f"Found {len(examples)} example files\n")

    for md_path in examples:
        text = md_path.read_text(encoding="utf-8")
        blocks = parse_markdown(text)
        stem = md_path.stem

        if not blocks:
            print(f"  SKIP  {md_path.name} — no diagram blocks found")
            continue

        for idx, block in enumerate(blocks):
            suffix = f"_{idx}" if len(blocks) > 1 else ""
            out_name = f"{stem}_{block.diagram_type}{suffix}.svg"
            out_path = OUTPUT_DIR / out_name

            try:
                result = await render_block(block, theme="light", output_format="svg")
                svg_bytes = base64.b64decode(result["base64"])
                out_path.write_bytes(svg_bytes)
                print(f"  OK    {out_name}  ({block.diagram_type}, lines {block.line_start}-{block.line_end})")
            except Exception as e:
                print(f"  FAIL  {out_name}  — {e}")

    print(f"\nDone. Outputs saved to {OUTPUT_DIR}/")

    from src.renderers.mermaid_renderer import close_browser
    await close_browser()


if __name__ == "__main__":
    asyncio.run(main())
