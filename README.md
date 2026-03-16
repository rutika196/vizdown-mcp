# Clarity-beta

Clarity-beta is an MCP server that converts Markdown files into beautiful diagrams — flowcharts, mind maps, architecture diagrams, ER diagrams, Gantt charts, sequence diagrams, and more. Built with Apple HIG design language.

## Installation

```bash
git clone https://github.com/rutika196/clarity-beta.git
cd clarity-beta
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
pip install -e .
playwright install chromium
```

## IDE Setup

### Cursor

Create or edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "clarity-beta": {
      "command": "/absolute/path/to/clarity-beta/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/clarity-beta"
    }
  }
}
```

> Replace `/absolute/path/to/clarity-beta` with your actual project path.

### VS Code

Create `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "clarity-beta": {
      "command": "/absolute/path/to/clarity-beta/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/clarity-beta"
    }
  }
}
```

> VS Code reads MCP config from `.vscode/mcp.json` — no need to touch `settings.json`.

### IntelliJ IDEA / WebStorm / PyCharm (JetBrains)

JetBrains IDEs (2025.1+) support MCP via the **AI Assistant** plugin.

1. Go to **Settings** → **Tools** → **AI Assistant** → **MCP Servers**.
2. Click **+ Add** and fill in:

| Field | Value |
|-------|-------|
| **Name** | `clarity-beta` |
| **Command** | `/absolute/path/to/clarity-beta/.venv/bin/python` |
| **Arguments** | `-m src.server` |
| **Working Directory** | `/absolute/path/to/clarity-beta` |

Or edit the MCP config file directly at `~/.config/jetbrains/mcp.json`:

```json
{
  "mcpServers": {
    "clarity-beta": {
      "command": "/absolute/path/to/clarity-beta/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/clarity-beta"
    }
  }
}
```

> **Windows users**: replace `.venv/bin/python` with `.venv\\Scripts\\python.exe` and use `\\` in paths.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "clarity-beta": {
      "command": "/absolute/path/to/clarity-beta/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/clarity-beta"
    }
  }
}
```

## Usage

### As a standalone server (stdio transport)

```bash
source .venv/bin/activate
clarity-beta
# or
python -m src.server
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

See the `examples/` folder — 13 ready-to-render Markdown files:

| File | Diagram Type |
|------|-------------|
| `auth_flow.md` | Flowchart (OAuth 2.0 + MFA) |
| `api_sequence.md` | Sequence diagram |
| `order_states.md` | State diagram |
| `database_schema.md` | ER diagram |
| `class_diagram.md` | Class diagram |
| `project_roadmap.md` | Gantt chart |
| `tech_stack_pie.md` | Pie chart |
| `git_workflow.md` | Git graph |
| `company_timeline.md` | Timeline |
| `user_journey.md` | User journey |
| `system_overview.md` | Mind map (custom SVG) |
| `microservices.md` | Architecture (17 services + groups) |
| `ci_cd_pipeline.md` | Architecture (CI/CD pipeline) |

## Running Tests

```bash
python tests/test_all.py
```

## Dependencies

- `mcp[cli]` — MCP Python SDK
- `playwright` — Headless Chromium for Mermaid rendering and PNG/JPEG export
- `cairosvg` — SVG to PDF conversion
- `Pillow` — Image processing (optional, for JPEG)
