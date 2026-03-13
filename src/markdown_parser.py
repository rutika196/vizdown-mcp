"""Deep Markdown parser — extracts explicit diagram blocks AND infers
diagrams from structured prose (tables, lists, steps, timelines).

Parsing pipeline:
  Phase 0  Normalize CRLF → LF, strip frontmatter (YAML --- / TOML +++)
  Phase 1  Map HTML comment regions → exclusion zones
  Phase 2  Fenced code blocks
           • Labeled: ```mermaid, ```architecture, etc.
           • With attributes: ```mermaid title="x" or ```mermaid {.class}
           • Unlabeled: ``` with strict Mermaid keyword sniffing
           • Blockquote-wrapped: > ```mermaid … > ```
           • Tilde fences: ~~~mermaid … ~~~
           • Unclosed fences capped at 500 lines
  Phase 3  Framework-specific wrappers
           • Hugo shortcodes: {{< mermaid >}} … {{< /mermaid >}}
           • Docusaurus / MkDocs: :::mermaid … :::
  Phase 4  Unfenced architecture syntax (title: / services: / flow:)
  Phase 5  Mermaid inside HTML tags (<pre|div|code class="mermaid">)
  Phase 6  Smart content inference
           • Headings + bullets → Mindmap
           • Markdown tables → ER Diagram
           • Numbered steps → Flowchart
           • Date / milestone lists → Timeline
  Phase 7  Deduplicate (explicit beats inferred on overlap), sort
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DiagramBlock:
    diagram_type: str
    syntax: str
    line_start: int
    line_end: int
    source: str = "explicit"  # "explicit" | "inferred"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FENCED_TYPES = {
    "mermaid",
    "mindmap",
    "architecture",
    "service-diagram",
}

MERMAID_DIAGRAM_KEYWORDS = [
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "erDiagram",
    "stateDiagram", "stateDiagram-v2", "gantt", "gitGraph", "pie",
    "timeline", "quadrantChart", "sankey-beta", "xychart-beta",
    "block-beta", "architecture-beta", "kanban", "packet-beta",
    "journey", "C4Context", "C4Container", "C4Component", "C4Dynamic",
    "mindmap", "requirement",
]

_MERMAID_KW_SORTED = sorted(MERMAID_DIAGRAM_KEYWORDS, key=len, reverse=True)
_MERMAID_KW_SET = set(MERMAID_DIAGRAM_KEYWORDS)

_MAX_UNCLOSED_FENCE = 500

_KW_FOLLOW_CHARS = frozenset(" \t\n;:")
_REJECT_AFTER_KW = frozenset("=(.{[+*/&|^%!@$<>")

_FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})\s*([a-zA-Z][\w.-]*)?")
_BQ_RE = re.compile(r"^\s{0,3}>")
_ARCH_SECTION_RE = re.compile(
    r"^(title|services|flow|groups)\s*:", re.IGNORECASE,
)
_HTML_MERMAID_RE = re.compile(
    r'<(?:pre|code|div)\s+class\s*=\s*["\']mermaid["\']', re.IGNORECASE,
)
_HUGO_OPEN_RE = re.compile(r"\{\{[<%]\s*mermaid\b.*?[%>]\}\}")
_HUGO_CLOSE_RE = re.compile(r"\{\{[<%]\s*/\s*mermaid\s*[%>]\}\}")
_DIRECTIVE_OPEN_RE = re.compile(r"^:{3,}\s*mermaid\b", re.IGNORECASE)
_DIRECTIVE_CLOSE_RE = re.compile(r"^:{3,}\s*$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _keyword_at_start(line: str) -> str | None:
    """Return the Mermaid keyword if *line* starts with one followed by a
    valid boundary (whitespace, semicolon, colon, EOL).

    Rejects lines where the keyword is followed by a programming construct
    like ``=``, ``(``, ``.``, ``{``, etc.  This prevents false positives
    from code blocks containing variable names like ``graph = …``.
    """
    for kw in _MERMAID_KW_SORTED:
        if line.startswith(kw):
            rest = line[len(kw):]
            if not rest:
                return kw
            if rest[0] not in _KW_FOLLOW_CHARS:
                continue
            rest_stripped = rest.lstrip()
            if rest_stripped and rest_stripped[0] in _REJECT_AFTER_KW:
                continue
            return kw
    return None


def _detect_mermaid_subtype(syntax: str) -> str:
    """Detect diagram type, skipping leading %% comments, blank lines,
    and Mermaid YAML config blocks (--- … ---)."""
    in_config = False
    for raw_line in syntax.strip().split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("%%"):
            continue
        if line == "---":
            in_config = not in_config
            continue
        if in_config:
            continue
        kw = _keyword_at_start(line)
        if kw:
            return kw
        break
    return "flowchart"


def _content_looks_like_mermaid(content: str) -> bool:
    """Strict sniff: does an unlabeled block contain Mermaid syntax?
    Skips %% comments and --- config blocks."""
    in_config = False
    for raw_line in content.strip().split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("%%"):
            continue
        if line == "---":
            in_config = not in_config
            continue
        if in_config:
            continue
        return _keyword_at_start(line) is not None
    return False


def _is_architecture_block(text: str) -> bool:
    has_services = bool(re.search(r"^services:\s*$", text, re.MULTILINE))
    has_flow = bool(re.search(r"^flow:\s*$", text, re.MULTILINE))
    return has_services and has_flow


def _strip_frontmatter(lines: list[str]) -> int:
    """Return line index where content starts (after YAML --- or TOML +++
    frontmatter).  Returns 0 if no frontmatter is found."""
    if not lines:
        return 0
    first = lines[0].strip()
    if first == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    elif first == "+++":
        for i in range(1, len(lines)):
            if lines[i].strip() == "+++":
                return i + 1
    return 0


def _ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _in_excluded(idx: int, zones: list[tuple[int, int]]) -> bool:
    return any(s <= idx < e for s, e in zones)


def _dequote_line(line: str) -> str:
    """Strip blockquote prefix(es) (``> ``) preserving content indentation."""
    return re.sub(r"^(\s{0,3}>\s?)+", "", line)


# ---------------------------------------------------------------------------
# Phase 1 — HTML comment exclusion zones
# ---------------------------------------------------------------------------

def _find_comment_zones(lines: list[str], start: int) -> list[tuple[int, int]]:
    """Map ``<!-- … -->`` regions as line-index ranges to exclude.

    For single-line comments (``<!-- … -->`` on one line) the whole line is
    excluded.  For multi-line comments the closing ``-->`` must be the *only*
    content on its line (with optional whitespace).  This avoids false
    matches from Mermaid ``-->`` arrow syntax that can appear inside
    commented-out diagram blocks.
    """
    zones: list[tuple[int, int]] = []
    n = len(lines)
    i = start

    while i < n:
        stripped = lines[i].strip()

        if "<!--" in stripped:
            open_pos = stripped.find("<!--")
            close_pos = stripped.find("-->", open_pos + 4)

            if close_pos >= 0:
                zones.append((i, i + 1))
                i += 1
                continue

            j = i + 1
            while j < n:
                cl = lines[j].strip()
                if cl == "-->" or cl == "-->":
                    zones.append((i, j + 1))
                    i = j + 1
                    break
                j += 1
            else:
                i += 1
            continue

        i += 1

    return zones


# ---------------------------------------------------------------------------
# Phase 2 — Fenced code blocks
# ---------------------------------------------------------------------------

def _phase2_fenced_blocks(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
) -> list[DiagramBlock]:
    """Extract diagram blocks from fenced code.

    Handles labeled, unlabeled-with-sniffing, blockquote-wrapped,
    attribute-suffixed fences, and both backtick and tilde fences.
    """
    blocks: list[DiagramBlock] = []
    i = start
    n = len(lines)

    while i < n:
        if _in_excluded(i, excluded):
            i += 1
            continue

        raw = lines[i]
        is_bq = bool(_BQ_RE.match(raw))
        check_line = _dequote_line(raw).strip() if is_bq else raw.strip()

        fence_match = _FENCE_OPEN_RE.match(check_line)
        if not fence_match:
            i += 1
            continue

        fence_str = fence_match.group(1)
        lang = (fence_match.group(2) or "").lower()
        min_ticks = len(fence_str)
        close_char = fence_str[0]
        close_re = re.compile(
            rf"^{re.escape(close_char)}{{{min_ticks},}}\s*$",
        )

        content_lines: list[str] = []
        j = i + 1
        limit = min(j + _MAX_UNCLOSED_FENCE, n)
        closed = False

        while j < limit:
            if _in_excluded(j, excluded):
                j += 1
                continue

            raw_j = lines[j]
            if is_bq:
                if not _BQ_RE.match(raw_j):
                    break
                dq = _dequote_line(raw_j)
                dq_stripped = dq.strip()
            else:
                dq = raw_j
                dq_stripped = raw_j.strip()

            if close_re.match(dq_stripped):
                closed = True
                break

            content_lines.append(dq if is_bq else raw_j)
            j += 1

        if not closed:
            i += 1
            continue

        syntax = "\n".join(content_lines).strip()
        if not syntax:
            i = j + 1
            continue

        is_known_lang = lang in FENCED_TYPES
        is_unlabeled_mermaid = (not lang) and _content_looks_like_mermaid(syntax)

        if is_known_lang or is_unlabeled_mermaid:
            if lang == "mermaid" or is_unlabeled_mermaid:
                subtype = _detect_mermaid_subtype(syntax)
                dtype = subtype
            elif lang == "service-diagram":
                dtype = "architecture"
            elif lang == "architecture" or _is_architecture_block(syntax):
                dtype = "architecture"
            else:
                dtype = lang

            blocks.append(DiagramBlock(
                diagram_type=dtype,
                syntax=syntax,
                line_start=i + 2,
                line_end=j + 1,
                source="explicit",
            ))

        i = j + 1

    return blocks


# ---------------------------------------------------------------------------
# Phase 3 — Framework-specific wrappers
# ---------------------------------------------------------------------------

def _phase3_framework_wrappers(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> list[DiagramBlock]:
    """Detect Hugo shortcodes and Docusaurus / MkDocs ::: directives."""
    blocks: list[DiagramBlock] = []
    n = len(lines)
    i = start

    while i < n:
        if _in_excluded(i, excluded) or _in_excluded(i, occupied):
            i += 1
            continue

        stripped = lines[i].strip()

        # Hugo shortcodes: {{< mermaid >}} … {{< /mermaid >}}
        if _HUGO_OPEN_RE.search(stripped):
            content_lines: list[str] = []
            j = i + 1
            while j < n:
                if _HUGO_CLOSE_RE.search(lines[j]):
                    break
                content_lines.append(lines[j])
                j += 1
            else:
                i += 1
                continue

            syntax = "\n".join(content_lines).strip()
            if syntax:
                subtype = _detect_mermaid_subtype(syntax) if _content_looks_like_mermaid(syntax) else "flowchart"
                blocks.append(DiagramBlock(
                    diagram_type=subtype,
                    syntax=syntax,
                    line_start=i + 1,
                    line_end=j + 1,
                    source="explicit",
                ))
                occupied.append((i, j + 1))
            i = j + 1
            continue

        # Docusaurus / MkDocs directives: :::mermaid … :::
        if _DIRECTIVE_OPEN_RE.match(stripped):
            content_lines = []
            j = i + 1
            while j < n:
                if _DIRECTIVE_CLOSE_RE.match(lines[j].strip()):
                    break
                content_lines.append(lines[j])
                j += 1
            else:
                i += 1
                continue

            syntax = "\n".join(content_lines).strip()
            if syntax:
                subtype = _detect_mermaid_subtype(syntax) if _content_looks_like_mermaid(syntax) else "flowchart"
                blocks.append(DiagramBlock(
                    diagram_type=subtype,
                    syntax=syntax,
                    line_start=i + 1,
                    line_end=j + 1,
                    source="explicit",
                ))
                occupied.append((i, j + 1))
            i = j + 1
            continue

        i += 1

    return blocks


# ---------------------------------------------------------------------------
# Phase 4 — Unfenced architecture blocks
# ---------------------------------------------------------------------------

def _phase4_unfenced_architecture(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> list[DiagramBlock]:
    """Find architecture-style blocks (title:/services:/flow:) in plain text."""
    blocks: list[DiagramBlock] = []
    n = len(lines)
    i = start

    while i < n:
        if _in_excluded(i, excluded) or _in_excluded(i, occupied):
            i += 1
            continue

        line = lines[i].strip()

        if _ARCH_SECTION_RE.match(line):
            if any(_ranges_overlap(i, i + 1, s, e) for s, e in occupied):
                i += 1
                continue

            block_start = i
            j = i + 1
            while j < n:
                nxt = lines[j].strip()
                if not nxt:
                    lookahead = j + 1
                    while lookahead < n and not lines[lookahead].strip():
                        lookahead += 1
                    if lookahead < n and _ARCH_SECTION_RE.match(lines[lookahead].strip()):
                        j = lookahead
                        continue
                    if lookahead < n and lines[lookahead].strip().startswith(("  ", "\t")):
                        j = lookahead
                        continue
                    break

                if nxt.startswith("#"):
                    break
                if re.match(r"^(`{3,}|~{3,})", nxt):
                    break

                j += 1

            candidate = "\n".join(lines[block_start:j]).strip()
            if _is_architecture_block(candidate):
                blocks.append(DiagramBlock(
                    diagram_type="architecture",
                    syntax=candidate,
                    line_start=block_start + 1,
                    line_end=j,
                    source="explicit",
                ))
                occupied.append((block_start, j))
                i = j
                continue

        i += 1

    return blocks


# ---------------------------------------------------------------------------
# Phase 5 — Mermaid inside HTML wrappers
# ---------------------------------------------------------------------------

def _phase5_html_mermaid(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> list[DiagramBlock]:
    """Detect mermaid blocks inside <pre|div|code class=\"mermaid\">."""
    blocks: list[DiagramBlock] = []
    n = len(lines)
    i = start

    while i < n:
        if _in_excluded(i, excluded) or _in_excluded(i, occupied):
            i += 1
            continue

        if _HTML_MERMAID_RE.search(lines[i]):
            content_lines: list[str] = []
            j = i + 1
            while j < n:
                if re.search(r"</(?:pre|code|div)>", lines[j], re.IGNORECASE):
                    break
                content_lines.append(lines[j])
                j += 1

            syntax = "\n".join(content_lines).strip()
            if syntax and _content_looks_like_mermaid(syntax):
                subtype = _detect_mermaid_subtype(syntax)
                blocks.append(DiagramBlock(
                    diagram_type=subtype,
                    syntax=syntax,
                    line_start=i + 1,
                    line_end=j + 1,
                    source="explicit",
                ))
                occupied.append((i, j + 1))
                i = j + 1
                continue

        i += 1

    return blocks


# ---------------------------------------------------------------------------
# Phase 6 — Smart content inference
# ---------------------------------------------------------------------------

def _phase6_infer_mindmap(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> DiagramBlock | None:
    """Generate a mindmap from heading + bullet structure."""
    heading_lines: list[tuple[int, int, str]] = []
    for i in range(start, len(lines)):
        if _in_excluded(i, excluded) or _in_excluded(i, occupied):
            continue
        stripped = lines[i].strip()
        if stripped.startswith("#") and not stripped.startswith("#!"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped.lstrip("#").strip()
            if text:
                heading_lines.append((i, level, text))

    if len(heading_lines) < 3:
        return None

    bullet_tree: dict[int, list[tuple[int, str]]] = {}
    current_heading_idx = -1
    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            current_heading_idx = i
        elif stripped.startswith(("- ", "* ", "+ ")) and current_heading_idx >= 0:
            if _in_excluded(i, excluded) or _in_excluded(i, occupied):
                continue
            indent = len(lines[i]) - len(lines[i].lstrip())
            text = stripped.lstrip("-*+ ").strip()
            if text:
                bullet_tree.setdefault(current_heading_idx, []).append((indent, text))

    root_text = heading_lines[0][2]
    mm_lines = ["mindmap", f"  {root_text}"]

    for h_line, h_level, h_text in heading_lines[1:]:
        indent = "  " * min(h_level, 4)
        mm_lines.append(f"{indent}{h_text}")
        for bullet_indent, b_text in bullet_tree.get(h_line, []):
            depth = min(h_level + 1 + bullet_indent // 2, 6)
            mm_lines.append(f"{'  ' * depth}{b_text}")

    if len(mm_lines) <= 3:
        return None

    return DiagramBlock(
        diagram_type="mindmap",
        syntax="\n".join(mm_lines),
        line_start=heading_lines[0][0] + 1,
        line_end=heading_lines[-1][0] + 1,
        source="inferred",
    )


_RELATIONSHIP_WORDS = re.compile(
    r"\b(has|belongs?\s+to|contains?|references?|owns?|links?\s+to|"
    r"related\s+to|depends\s+on|parent\s+of|child\s+of|maps?\s+to|"
    r"one[- ]to[- ]many|many[- ]to[- ]many|one[- ]to[- ]one|"
    r"foreign\s+key|primary\s+key|FK|PK)\b",
    re.IGNORECASE,
)


def _phase6_infer_er_from_tables(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> DiagramBlock | None:
    """Detect Markdown tables describing entities with relationships → ER diagram."""
    tables: list[dict] = []
    i = start
    n = len(lines)

    while i < n:
        if _in_excluded(i, excluded) or _in_excluded(i, occupied):
            i += 1
            continue

        stripped = lines[i].strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_start = i
            header_line = stripped
            j = i + 1

            if j < n and re.match(r"^\|[\s:|-]+\|$", lines[j].strip()):
                j += 1
            else:
                i += 1
                continue

            rows: list[str] = []
            while j < n and lines[j].strip().startswith("|"):
                rows.append(lines[j].strip())
                j += 1

            if rows:
                heading_above = ""
                for k in range(table_start - 1, max(start - 1, table_start - 4), -1):
                    hl = lines[k].strip()
                    if hl.startswith("#"):
                        heading_above = hl.lstrip("#").strip()
                        break
                    if hl:
                        break

                tables.append({
                    "heading": heading_above,
                    "header": header_line,
                    "rows": rows,
                    "line_start": table_start,
                    "line_end": j,
                })
            i = j
        else:
            i += 1

    if len(tables) < 2:
        return None

    has_relationship_hints = False
    all_text = " ".join(t["header"] + " ".join(t["rows"]) for t in tables)
    if _RELATIONSHIP_WORDS.search(all_text):
        has_relationship_hints = True

    entity_names = [t["heading"] for t in tables if t["heading"]]
    if not entity_names and not has_relationship_hints:
        return None

    er_lines = ["erDiagram"]
    for table in tables:
        name = table["heading"] or f"Table{tables.index(table) + 1}"
        name = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_") or "Entity"

        er_lines.append(f"    {name} {{")
        for row in table["rows"]:
            cells = [c.strip() for c in row.split("|") if c.strip()]
            if len(cells) >= 2:
                col_name = re.sub(r"[^A-Za-z0-9_]", "_", cells[0]).strip("_")
                col_type = re.sub(r"[^A-Za-z0-9_]", "_", cells[1]).strip("_") or "string"
                pk_marker = " PK" if any(
                    k in cells[0].lower() for k in ("id", "pk", "primary")
                ) else ""
                er_lines.append(f"        {col_type} {col_name}{pk_marker}")
        er_lines.append("    }")

    if len(entity_names) >= 2:
        for idx in range(len(entity_names) - 1):
            a = re.sub(r"[^A-Za-z0-9_]", "_", entity_names[idx]).strip("_")
            b = re.sub(r"[^A-Za-z0-9_]", "_", entity_names[idx + 1]).strip("_")
            er_lines.append(f"    {a} ||--o{{ {b} : references")

    if len(er_lines) <= 2:
        return None

    return DiagramBlock(
        diagram_type="erDiagram",
        syntax="\n".join(er_lines),
        line_start=tables[0]["line_start"] + 1,
        line_end=tables[-1]["line_end"],
        source="inferred",
    )


_STEP_PATTERN = re.compile(r"^\d+[\.\)]\s+.+", re.MULTILINE)
_DECISION_WORDS = re.compile(
    r"\b(if|when|check|decide|validate|verify|whether|condition|branch|else|otherwise|"
    r"approve|reject|accept|deny|pass|fail|success|error)\b",
    re.IGNORECASE,
)
_ARROW_WORDS = re.compile(
    r"(->|→|then|next|leads?\s+to|results?\s+in|triggers?|followed\s+by|sends?\s+to)",
    re.IGNORECASE,
)


def _phase6_infer_flowchart(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> DiagramBlock | None:
    """Detect numbered step sequences with decision language → flowchart."""
    step_groups: list[list[tuple[int, str]]] = []
    current_group: list[tuple[int, str]] = []
    i = start

    while i < len(lines):
        if _in_excluded(i, excluded) or _in_excluded(i, occupied):
            i += 1
            continue

        stripped = lines[i].strip()
        step_match = re.match(r"^(\d+)[\.\)]\s+(.+)", stripped)

        if step_match:
            current_group.append((i, step_match.group(2).strip()))
        else:
            if len(current_group) >= 4:
                step_groups.append(current_group)
            current_group = []
        i += 1

    if len(current_group) >= 4:
        step_groups.append(current_group)

    if not step_groups:
        return None

    best = max(step_groups, key=len)
    texts = [t for _, t in best]
    combined = " ".join(texts)

    has_decisions = bool(_DECISION_WORDS.search(combined))
    has_arrows = bool(_ARROW_WORDS.search(combined))

    if not has_decisions and not has_arrows and len(best) < 5:
        return None

    fc_lines = ["flowchart TD"]
    node_ids: list[str] = []

    for idx, (_, text) in enumerate(best):
        nid = chr(65 + idx) if idx < 26 else f"N{idx}"
        node_ids.append(nid)
        clean = re.sub(r"\*{1,3}|_{1,3}|`|~{2}", "", text).rstrip(".")

        if _DECISION_WORDS.search(clean):
            fc_lines.append(f"    {nid}{{{clean}}}")
        else:
            fc_lines.append(f"    {nid}[{clean}]")

    for idx in range(len(node_ids) - 1):
        fc_lines.append(f"    {node_ids[idx]} --> {node_ids[idx + 1]}")

    return DiagramBlock(
        diagram_type="flowchart",
        syntax="\n".join(fc_lines),
        line_start=best[0][0] + 1,
        line_end=best[-1][0] + 1,
        source="inferred",
    )


_DATE_RE = re.compile(
    r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*[\s,]+\d{4}|"
    r"Q[1-4]\s*\d{4}|"
    r"\d{4}\s*[-–]\s*\d{4}|"
    r"Phase\s+\d|Sprint\s+\d|Week\s+\d|Month\s+\d)",
    re.IGNORECASE,
)


def _phase6_infer_timeline(
    lines: list[str],
    start: int,
    excluded: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> DiagramBlock | None:
    """Detect date/milestone patterns → Mermaid timeline."""
    events: list[tuple[int, str, str]] = []
    i = start

    while i < len(lines):
        if _in_excluded(i, excluded) or _in_excluded(i, occupied):
            i += 1
            continue

        stripped = lines[i].strip()
        date_match = _DATE_RE.search(stripped)
        if date_match and (
            stripped.startswith(("- ", "* ", "+ "))
            or stripped.startswith(tuple("0123456789"))
        ):
            date_str = date_match.group(0)
            rest = stripped.lstrip("-*+ 0123456789.)").strip()
            rest = rest.replace(date_str, "").strip(" :–-—,")
            if rest:
                events.append((i, date_str, rest))
        i += 1

    if len(events) < 3:
        return None

    tl_lines = ["timeline", "    title Project Timeline"]
    for _, date_str, desc in events:
        tl_lines.append(f"    {date_str} : {desc}")

    return DiagramBlock(
        diagram_type="timeline",
        syntax="\n".join(tl_lines),
        line_start=events[0][0] + 1,
        line_end=events[-1][0] + 1,
        source="inferred",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_markdown(text: str) -> list[DiagramBlock]:
    """Deep-parse markdown text and extract all diagram blocks.

    Returns a sorted list of ``DiagramBlock`` instances.
    """
    if not text or not text.strip():
        return []

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # Phase 0 — strip frontmatter
    content_start = _strip_frontmatter(lines)

    # Phase 1 — build HTML comment exclusion zones
    excluded = _find_comment_zones(lines, content_start)

    occupied: list[tuple[int, int]] = []

    # Phase 2 — fenced code blocks
    fenced = _phase2_fenced_blocks(lines, content_start, excluded)
    for b in fenced:
        occupied.append((b.line_start - 1, b.line_end))

    # Phase 3 — framework wrappers (Hugo shortcodes, :::mermaid)
    framework = _phase3_framework_wrappers(lines, content_start, excluded, occupied)
    for b in framework:
        occupied.append((b.line_start - 1, b.line_end))

    # Phase 4 — unfenced architecture
    arch = _phase4_unfenced_architecture(lines, content_start, excluded, occupied)
    for b in arch:
        occupied.append((b.line_start - 1, b.line_end))

    # Phase 5 — HTML-wrapped mermaid
    html_blocks = _phase5_html_mermaid(lines, content_start, excluded, occupied)
    for b in html_blocks:
        occupied.append((b.line_start - 1, b.line_end))

    all_explicit = fenced + framework + arch + html_blocks

    # Phase 6 — smart inference (always runs, respects occupied + excluded)
    inferred: list[DiagramBlock] = []

    mm = _phase6_infer_mindmap(lines, content_start, excluded, occupied)
    if mm:
        inferred.append(mm)

    er = _phase6_infer_er_from_tables(lines, content_start, excluded, occupied)
    if er:
        inferred.append(er)

    fc = _phase6_infer_flowchart(lines, content_start, excluded, occupied)
    if fc:
        inferred.append(fc)

    tl = _phase6_infer_timeline(lines, content_start, excluded, occupied)
    if tl:
        inferred.append(tl)

    # Phase 7 — deduplicate
    #   a) Drop inferred blocks whose ranges overlap an explicit block
    #   b) Drop inferred blocks whose type already exists as an explicit block
    #      (avoids "prose summary" of an explicit diagram becoming a second diagram)
    explicit_types = {e.diagram_type for e in all_explicit}
    inferred_final: list[DiagramBlock] = []
    for b in inferred:
        if b.diagram_type in explicit_types:
            continue
        overlaps = any(
            _ranges_overlap(b.line_start, b.line_end, e.line_start, e.line_end)
            for e in all_explicit
        )
        if not overlaps:
            inferred_final.append(b)

    final = all_explicit + inferred_final
    return sorted(final, key=lambda b: b.line_start)
