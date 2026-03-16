"""SVG → PNG, JPEG, PDF conversion using Playwright and cairosvg."""

from __future__ import annotations

import base64
import logging

logger = logging.getLogger("clarity")


async def svg_to_png(svg: str, scale: int = 2) -> str:
    """Render SVG to PNG via Playwright, return base64 string."""
    from src.renderers.mermaid_renderer import get_browser

    browser = await get_browser()
    page = await browser.new_page(device_scale_factor=scale)
    try:
        await page.set_content(
            f'<html><body style="margin:0;padding:0;background:transparent">{svg}</body></html>',
            wait_until="networkidle",
        )
        el = await page.query_selector("svg")
        if not el:
            raise RuntimeError("No SVG element found on page")
        screenshot = await el.screenshot(type="png")
        return base64.b64encode(screenshot).decode()
    finally:
        await page.close()


async def svg_to_jpeg(svg: str, scale: int = 2, quality: int = 90) -> str:
    """Render SVG to JPEG via Playwright, return base64 string."""
    from src.renderers.mermaid_renderer import get_browser

    browser = await get_browser()
    page = await browser.new_page(device_scale_factor=scale)
    try:
        await page.set_content(
            f'<html><body style="margin:0;padding:0;background:white">{svg}</body></html>',
            wait_until="networkidle",
        )
        el = await page.query_selector("svg")
        if not el:
            raise RuntimeError("No SVG element found on page")
        screenshot = await el.screenshot(type="jpeg", quality=quality)
        return base64.b64encode(screenshot).decode()
    finally:
        await page.close()


def svg_to_pdf(svg: str) -> str:
    """Convert SVG to PDF via cairosvg (vector output), return base64 string."""
    import cairosvg

    pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
    return base64.b64encode(pdf_bytes).decode()


async def convert_svg(
    svg: str, output_format: str = "svg", scale: int = 2
) -> str:
    """Convert SVG string to requested format, returning base64 encoded output."""
    if output_format == "svg":
        return base64.b64encode(svg.encode("utf-8")).decode()
    elif output_format == "png":
        return await svg_to_png(svg, scale=scale)
    elif output_format == "jpeg":
        return await svg_to_jpeg(svg, scale=scale)
    elif output_format == "pdf":
        return svg_to_pdf(svg)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
