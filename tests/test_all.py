"""Tests for Vizdown-MCP components."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.color_palette import generate_apple_palette
from src.utils.icon_registry import detect_icon, BUILTIN_ICONS, render_icon_svg
from src.markdown_parser import parse_markdown
from src.renderers.mindmap_renderer import render_mindmap
from src.renderers.architecture_renderer import render_architecture


# ---------------------------------------------------------------------------
# Color palette tests
# ---------------------------------------------------------------------------

def test_palette_count():
    pal = generate_apple_palette(6)
    assert len(pal) == 6
    for entry in pal:
        assert "fill" in entry and "border" in entry
        assert entry["fill"].startswith("#")

def test_palette_empty():
    assert generate_apple_palette(0) == []

def test_palette_dark():
    pal = generate_apple_palette(3, theme="dark")
    assert len(pal) == 3

def test_palette_large():
    pal = generate_apple_palette(50)
    assert len(pal) == 50
    fills = {p["fill"] for p in pal}
    assert len(fills) == 50


# ---------------------------------------------------------------------------
# Icon registry tests
# ---------------------------------------------------------------------------

def test_detect_database():
    assert detect_icon("PostgreSQL Database") == "database"

def test_detect_redis():
    assert detect_icon("Redis Cache") == "redis"

def test_detect_explicit_tag():
    result = detect_icon("My Service", explicit_tag="globe")
    assert result == "globe"

def test_detect_unknown():
    result = detect_icon("Xylophone Zorblatt")
    assert result is None

def test_builtin_icons_render():
    for name, fn in BUILTIN_ICONS.items():
        svg = fn(50, 50, 68)
        assert "<" in svg, f"Icon {name} returned empty SVG"

def test_render_icon_svg_none():
    assert render_icon_svg(None, 0, 0) == ""

def test_render_icon_svg_builtin():
    svg = render_icon_svg("database", 50, 50, 68)
    assert "svg" in svg.lower() or "<" in svg


# ---------------------------------------------------------------------------
# Markdown parser tests
# ---------------------------------------------------------------------------

SAMPLE_MERMAID = """# Test
Some text.

```mermaid
flowchart LR
    A --> B
    B --> C
```

More text.

```mermaid
erDiagram
    USERS ||--o{ ORDERS : places
```
"""

def test_parse_multiple_mermaid():
    blocks = parse_markdown(SAMPLE_MERMAID)
    assert len(blocks) == 2
    assert blocks[0].diagram_type == "flowchart"
    assert blocks[1].diagram_type == "erDiagram"

def test_parse_mindmap_block():
    md = """```mindmap
mindmap
  Root
    Branch A
      Leaf 1
      Leaf 2
    Branch B
```"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "mindmap"

def test_parse_architecture_block():
    md = """```architecture
title: Test System

services:
  API Gateway
  Database

flow:
  API Gateway -> Database
```"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "architecture"

def test_parse_service_diagram_alias():
    md = """```service-diagram
title: Test

services:
  Web App
  Backend

flow:
  Web App -> Backend
```"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "architecture"

def test_auto_mindmap_from_headings():
    md = """# Project Overview
## Backend
- API Gateway
- Auth Service
## Frontend
- Web App
- Mobile App
## Infrastructure
- Kubernetes
- Monitoring
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "mindmap"
    assert "Backend" in blocks[0].syntax

def test_parse_empty():
    assert parse_markdown("") == []
    assert parse_markdown("Just some text without diagrams.") == []


# --- New deep-parser tests ---

def test_parse_unlabeled_fenced_mermaid():
    """Unlabeled ``` with Mermaid content should be auto-detected."""
    md = """Some text

```
flowchart LR
    A --> B --> C
```

More text.
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"
    assert "A --> B" in blocks[0].syntax


def test_parse_mermaid_with_comments():
    """%% comments at the top should not confuse subtype detection."""
    md = """```mermaid
%% This is a sequence diagram for the API
%% Author: John
sequenceDiagram
    Alice->>Bob: Hello
    Bob-->>Alice: Hi
```"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "sequenceDiagram"


def test_yaml_frontmatter_skipped():
    """YAML frontmatter should not confuse the parser."""
    md = """---
title: My Document
date: 2024-01-01
tags: [diagrams, test]
---

# Intro

```mermaid
pie title Favorites
    "Cats" : 40
    "Dogs" : 60
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "pie"


def test_unclosed_fence_does_not_eat_file():
    """An unclosed ``` mermaid should not consume the rest of the file."""
    lines = ["```mermaid", "flowchart LR", "  A --> B"]
    lines += [f"line {i}" for i in range(600)]
    md = "\n".join(lines)
    blocks = parse_markdown(md)
    assert len(blocks) == 0  # unclosed fence is discarded


def test_tilde_fences():
    """~~~ fences should work the same as ```."""
    md = """~~~mermaid
stateDiagram-v2
    [*] --> Active
    Active --> [*]
~~~"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "stateDiagram-v2"


def test_html_wrapped_mermaid():
    """Mermaid blocks inside <pre class='mermaid'> should be detected."""
    md = """<pre class="mermaid">
flowchart LR
    X --> Y --> Z
</pre>
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"
    assert "X --> Y" in blocks[0].syntax


def test_mindmap_alongside_fenced():
    """Mindmap inference should work even when fenced blocks exist."""
    md = """# System Architecture
## Backend
- API Service
- Database
- Cache
## Frontend
- Web App
- Mobile App
## DevOps
- CI/CD
- Monitoring

---

```mermaid
erDiagram
    USERS ||--o{ ORDERS : places
```
"""
    blocks = parse_markdown(md)
    types = [b.diagram_type for b in blocks]
    assert "erDiagram" in types
    assert "mindmap" in types


def test_infer_flowchart_from_steps():
    """Numbered steps with decision language should produce a flowchart."""
    md = """# Deployment Process

1. Pull latest code from repository
2. Run automated tests
3. Check if all tests pass
4. If tests fail, notify the team
5. Build Docker container
6. Deploy to staging environment
7. Validate deployment health
8. If healthy, promote to production
"""
    blocks = parse_markdown(md)
    fc_blocks = [b for b in blocks if b.diagram_type == "flowchart" and b.source == "inferred"]
    assert len(fc_blocks) == 1
    assert "tests" in fc_blocks[0].syntax.lower()


def test_infer_timeline_from_dates():
    """Date patterns in lists should produce a timeline."""
    md = """# Project Milestones

- Q1 2024: Project kickoff and requirements gathering
- Q2 2024: Design phase and architecture review
- Q3 2024: Development sprint 1 and 2
- Q4 2024: Testing and QA
- Q1 2025: Production launch
"""
    blocks = parse_markdown(md)
    tl_blocks = [b for b in blocks if b.diagram_type == "timeline"]
    assert len(tl_blocks) == 1
    assert "Q1 2024" in tl_blocks[0].syntax


def test_infer_er_from_tables():
    """Multiple markdown tables with entity headings should produce an ER diagram."""
    md = """# Data Model

## Users

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| name | varchar | |
| email | varchar | unique |

## Orders

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| user_id | integer | FK references Users |
| total | decimal | |

## Products

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| name | varchar | |
| price | decimal | |
"""
    blocks = parse_markdown(md)
    er_blocks = [b for b in blocks if b.diagram_type == "erDiagram"]
    assert len(er_blocks) == 1
    assert "Users" in er_blocks[0].syntax
    assert "Orders" in er_blocks[0].syntax


def test_multiple_fenced_diagrams_same_file():
    """A file with many different fenced diagram types should find all of them."""
    md = """# Report

```mermaid
flowchart LR
    A --> B
```

Some prose here.

```mermaid
sequenceDiagram
    Alice->>Bob: Hello
```

```architecture
title: Test

services:
  Gateway
  DB

flow:
  Gateway -> DB
```
"""
    blocks = parse_markdown(md)
    types = [b.diagram_type for b in blocks]
    assert "flowchart" in types
    assert "sequenceDiagram" in types
    assert "architecture" in types


def test_explicit_beats_inferred():
    """If a fenced block and inferred block overlap, keep the explicit one."""
    md = """```mermaid
flowchart LR
    A --> B
```

1. First step
2. Second step
3. Third step
"""
    blocks = parse_markdown(md)
    explicit = [b for b in blocks if b.source == "explicit"]
    assert len(explicit) >= 1
    assert explicit[0].diagram_type == "flowchart"


def test_source_field_explicit():
    md = """```mermaid
pie title Test
    "A" : 50
    "B" : 50
```"""
    blocks = parse_markdown(md)
    assert blocks[0].source == "explicit"


def test_source_field_inferred():
    md = """# System
## Part A
- Item 1
- Item 2
## Part B
- Item 3
## Part C
- Item 4
"""
    blocks = parse_markdown(md)
    if blocks:
        inferred = [b for b in blocks if b.source == "inferred"]
        assert len(inferred) >= 1


# --- Bulletproof parser tests (real-world edge cases) ---

def test_no_false_positive_python_graph():
    """A ```python block with 'graph' variable must NOT be detected."""
    md = """
```python
graph = build_graph()
nodes = graph.nodes()
for n in nodes:
    print(n)
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 0


def test_no_false_positive_js_graph():
    """A ```js block with 'graph' keyword must NOT be detected."""
    md = """
```js
const graph = new Graph();
graph.addNode('A');
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 0


def test_no_false_positive_unlabeled_graph_equals():
    """An unlabeled block with 'graph = ...' is code, not Mermaid."""
    md = """
```
graph = {}
graph["key"] = "value"
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 0


def test_unlabeled_graph_lr():
    """An unlabeled block with 'graph LR' IS valid Mermaid."""
    md = """
```
graph LR
    A --> B --> C
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "graph"


def test_blockquote_mermaid():
    """Mermaid inside a blockquote (> prefix) must be detected."""
    md = """
> ```mermaid
> flowchart LR
>     A --> B
> ```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"
    assert "A --> B" in blocks[0].syntax


def test_obsidian_callout_mermaid():
    """Mermaid inside Obsidian callouts (> [!note]) must be detected."""
    md = """
> [!note] Architecture
> ```mermaid
> sequenceDiagram
>     Alice->>Bob: Hello
> ```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "sequenceDiagram"


def test_nested_blockquote_mermaid():
    """Mermaid inside nested blockquotes (> >) must be detected."""
    md = """
> > ```mermaid
> > pie title Nested
> >     "A" : 60
> >     "B" : 40
> > ```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "pie"


def test_hugo_shortcode_angle():
    """Hugo {{< mermaid >}} shortcodes must be detected."""
    md = """
{{< mermaid >}}
flowchart LR
    A --> B --> C
{{< /mermaid >}}
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"


def test_hugo_shortcode_percent():
    """Hugo {{% mermaid %}} shortcodes must be detected."""
    md = """
{{% mermaid %}}
sequenceDiagram
    Alice->>Bob: Hello
{{% /mermaid %}}
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "sequenceDiagram"


def test_docusaurus_directive():
    """Docusaurus/MkDocs :::mermaid directives must be detected."""
    md = """
:::mermaid
flowchart LR
    A --> B
:::
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"


def test_html_comment_skips_hidden_block():
    """Mermaid inside <!-- ... --> must NOT be detected."""
    md = """
<!--
```mermaid
flowchart LR
    HIDDEN --> DIAGRAM
```
-->

```mermaid
pie title Real
    "A" : 50
    "B" : 50
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "pie"
    assert "HIDDEN" not in blocks[0].syntax


def test_single_line_html_comment():
    """Single-line <!-- ... --> should be excluded."""
    md = """
<!-- ```mermaid pie title hidden ``` -->

```mermaid
gantt
    title Real
    section A
    Task 1: 2024-01-01, 30d
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "gantt"


def test_mermaid_with_title_attr():
    """```mermaid title='...' (attributes after language tag) must work."""
    md = '''
```mermaid title="System Overview"
flowchart TD
    A[Start] --> B[End]
```
'''
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"


def test_mermaid_with_class_attr():
    """```mermaid {.diagram} (MkDocs/Pandoc class attributes) must work."""
    md = '''
```mermaid {.diagram}
erDiagram
    USERS ||--o{ ORDERS : places
```
'''
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "erDiagram"


def test_toml_frontmatter_skipped():
    """TOML frontmatter (+++) must be skipped without confusion."""
    md = """+++
title = "My Post"
date = "2024-01-01"
+++

```mermaid
pie title Votes
    "Cats" : 70
    "Dogs" : 30
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "pie"


def test_crlf_line_endings():
    """Windows CRLF line endings must be handled transparently."""
    md = "Text\r\n```mermaid\r\nflowchart LR\r\n    A --> B\r\n```\r\n"
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"


def test_mermaid_with_yaml_config():
    """Mermaid blocks with --- config block at the top must detect correctly."""
    md = """
```mermaid
---
config:
  theme: dark
---
flowchart LR
    A --> B
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"


def test_nested_fences_not_detected():
    """Documentation showing mermaid examples in outer fences must not detect inner blocks."""
    md = """
````markdown
```mermaid
flowchart LR
    A --> B
```
````
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 0


def test_empty_mermaid_block_skipped():
    """An empty ```mermaid ... ``` block should be gracefully skipped."""
    md = """
```mermaid
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 0


def test_inline_code_not_detected():
    """Inline `graph LR` should not trigger detection."""
    md = """
Use `graph LR` syntax for left-to-right layouts.

```mermaid
pie title Real
    "X" : 50
    "Y" : 50
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "pie"


def test_hr_not_confused_with_frontmatter():
    """A --- horizontal rule mid-document must not confuse the parser."""
    md = """---
title: First
---

Some content

---

More content

```mermaid
pie title Data
    "A" : 50
    "B" : 50
```
"""
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "pie"


def test_massive_file_does_not_hang():
    """A 5000-line file with one diagram should parse quickly."""
    lines = [f"This is line {i} of a large document." for i in range(5000)]
    lines[2500] = "```mermaid"
    lines[2501] = "flowchart LR"
    lines[2502] = "    A --> B"
    lines[2503] = "```"
    md = "\n".join(lines)
    blocks = parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0].diagram_type == "flowchart"


def test_multiple_frameworks_in_one_file():
    """A file mixing fenced blocks, Hugo shortcodes, and :::mermaid."""
    md = """
```mermaid
pie title Fenced
    "A" : 50
    "B" : 50
```

{{< mermaid >}}
flowchart LR
    X --> Y
{{< /mermaid >}}

:::mermaid
gantt
    title Directive
    section A
    Task 1: 2024-01-01, 30d
:::
"""
    blocks = parse_markdown(md)
    types = [b.diagram_type for b in blocks]
    assert "pie" in types
    assert "flowchart" in types
    assert "gantt" in types
    assert len(blocks) == 3


# ---------------------------------------------------------------------------
# Mind map renderer tests
# ---------------------------------------------------------------------------

def test_mindmap_render_basic():
    syntax = """mindmap
  Project
    Frontend
      React
      CSS
    Backend
      Python
      Database"""
    svg = render_mindmap(syntax, theme="light")
    assert svg.startswith("<svg")
    assert "Project" in svg
    assert "Frontend" in svg
    assert "Backend" in svg

def test_mindmap_render_dark():
    syntax = """mindmap
  Root
    A
    B"""
    svg = render_mindmap(syntax, theme="dark")
    assert "#0F172A" in svg

def test_mindmap_empty():
    svg = render_mindmap("", theme="light")
    assert "invalid" in svg.lower() or "empty" in svg.lower()


# ---------------------------------------------------------------------------
# Architecture renderer tests
# ---------------------------------------------------------------------------

def test_architecture_basic():
    syntax = """title: Test System

services:
  API Gateway
  Auth Service
  Database

flow:
  API Gateway -> Auth Service
  Auth Service -> Database
"""
    svg = render_architecture(syntax, theme="light")
    assert svg.startswith("<svg")
    assert "Test System" in svg
    assert "API Gateway" in svg

def test_architecture_with_groups():
    syntax = """title: Grouped

services:
  Web App
  API Gateway
  Database
  Redis Cache

flow:
  Web App -> API Gateway
  API Gateway -> Database
  API Gateway -> Redis Cache

groups:
  Backend: API Gateway, Database, Redis Cache
"""
    svg = render_architecture(syntax, theme="light")
    assert "BACKEND" in svg
    assert "stroke-dasharray" in svg

def test_architecture_dark_theme():
    syntax = """title: Dark

services:
  Service A
  Service B

flow:
  Service A -> Service B
"""
    svg = render_architecture(syntax, theme="dark")
    assert "#111827" in svg

def test_architecture_icon_detection():
    syntax = """title: Icons

services:
  PostgreSQL Database
  Redis Cache
  Kafka Queue
  Web Browser

flow:
  Web Browser -> PostgreSQL Database
  PostgreSQL Database -> Redis Cache
  Redis Cache -> Kafka Queue
"""
    svg = render_architecture(syntax, theme="light")
    assert svg.startswith("<svg")

def test_architecture_many_services():
    services = "\n  ".join(f"Service {i}" for i in range(20))
    flows = "\n  ".join(f"Service {i} -> Service {i+1}" for i in range(19))
    syntax = f"""title: Scale Test

services:
  {services}

flow:
  {flows}
"""
    svg = render_architecture(syntax, theme="light")
    assert svg.startswith("<svg")
    assert "Service 0" in svg
    assert "Service 19" in svg

def test_architecture_empty():
    svg = render_architecture("", theme="light")
    assert "No services" in svg


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_tests():
    import inspect
    passed = 0
    failed = 0
    errors = []

    test_functions = [
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]

    for name, fn in sorted(test_functions):
        try:
            result = fn()
            if asyncio.iscoroutine(result):
                asyncio.get_event_loop().run_until_complete(result)
            passed += 1
            print(f"  PASS  {name}")
        except Exception as e:
            failed += 1
            errors.append((name, e))
            print(f"  FAIL  {name}: {e}")

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if errors:
        print("\nFailed tests:")
        for name, e in errors:
            print(f"  - {name}: {e}")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
