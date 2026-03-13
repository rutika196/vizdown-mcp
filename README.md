# Vizdown-MCP

An MCP server that converts Markdown files into beautiful diagrams — flowcharts, mind maps, architecture diagrams, ER diagrams, Gantt charts, sequence diagrams, and more.

## Installation

```bash
cd vizdown-mcp
pip install -e .
playwright install chromium
```

## Usage

### As an MCP server (stdio transport)

```bash
vizdown-mcp
# or
python -m src.server
```

Add to your MCP client config (e.g. Claude Desktop, Cursor):

```json
{
  "mcpServers": {
    "vizdown-mcp": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/vizdown-mcp"
    }
  }
}
```

### MCP Tools

#### `render_diagram`

Render the first diagram found in a Markdown file or raw text.

| Parameter      | Type   | Default   | Description                              |
|----------------|--------|-----------|------------------------------------------|
| `file_path`    | string | —         | Path to a `.md` file                     |
| `raw_markdown` | string | —         | Raw markdown with a diagram block        |
| `output_format`| string | `"svg"`   | `"svg"`, `"png"`, `"jpeg"`, or `"pdf"`   |
| `theme`        | string | `"light"` | `"light"` or `"dark"`                    |
| `look`         | string | `"default"`| `"default"` or `"handDrawn"`            |
| `scale`        | int    | `2`       | Resolution multiplier for PNG/JPEG       |

#### `render_all_diagrams`

Render every diagram block in a file. Same parameters plus `output_dir` to save files.

#### `list_diagrams`

List detected diagram blocks with types and line numbers, without rendering.

## Supported Diagram Types

### Via Mermaid.js (Playwright)
flowchart, sequence, class, ER, state, gantt, gitGraph, pie, timeline, quadrant, sankey, xychart, block-beta, architecture-beta, kanban, journey, C4

### Custom SVG Renderers
- **Mind maps** — balanced horizontal tree with organic Bézier connectors
- **Architecture / service diagrams** — Miro-style auto-layout with icons, step badges, groups

## Examples

See the `examples/` folder:

- `auth_flow.md` — Flowchart showing authentication process
- `microservices.md` — Architecture diagram with 17 services and groups
- `database_schema.md` — ER diagram
- `project_roadmap.md` — Gantt chart
- `system_overview.md` — Mind map

## Running Tests

```bash
python tests/test_all.py
```

## Dependencies

- `mcp[cli]` — MCP Python SDK
- `playwright` — Headless Chromium for Mermaid rendering and PNG/JPEG export
- `cairosvg` — SVG to PDF conversion
- `Pillow` — Image processing (optional, for JPEG)
