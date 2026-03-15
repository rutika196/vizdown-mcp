"""Mermaid diagram renderer using Playwright + headless Chromium."""

from __future__ import annotations

import asyncio
import atexit
import logging
from typing import Optional

from playwright.async_api import Browser, async_playwright, Playwright

logger = logging.getLogger("vizdown.mermaid")

_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_lock = asyncio.Lock()

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"

FONT_STACK = "'SF Pro Display', 'SF Pro Text', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# ---------------------------------------------------------------------------
# Apple HIG themeVariables — full control via Mermaid 'base' theme
# ---------------------------------------------------------------------------

# Mid-tint Apple HIG colors — 40% mixed toward white.
# Same hues as system colors but softer, like Apple Calendar / Health / Stocks.
_M_BLUE    = "#66AEFF"   # from #007AFF
_M_GREEN   = "#7AD98F"   # from #34C759
_M_PURPLE  = "#C88AEB"   # from #AF52DE
_M_ORANGE  = "#FFB866"   # from #FF9500
_M_PINK    = "#FF7D99"   # from #FF2D55
_M_INDIGO  = "#8987E4"   # from #5856D6
_M_TEAL    = "#73CCD9"   # from #30B0C7
_M_YELLOW  = "#FFE066"   # from #FFCC00
_M_MINT    = "#66DBD2"   # from #00C7BE
_M_CYAN    = "#94D9FC"   # from #5AC8FA
_M_RED     = "#FF8580"   # from #FF3B30
_M_BROWN   = "#C2A87E"   # from #A2845E

# Vivid originals kept for borders and small accents
_V_BLUE    = "#007AFF"
_V_GREEN   = "#34C759"
_V_PURPLE  = "#AF52DE"
_V_ORANGE  = "#FF9500"
_V_PINK    = "#FF2D55"
_V_INDIGO  = "#5856D6"
_V_TEAL    = "#30B0C7"
_V_RED     = "#FF3B30"

APPLE_THEME_LIGHT = {
    "fontFamily": FONT_STACK,
    "fontSize": "14px",

    "primaryColor": "#DCEEFF",
    "primaryBorderColor": _M_BLUE,
    "primaryTextColor": "#1D1D1F",

    "secondaryColor": "#E6E5FA",
    "secondaryBorderColor": _M_INDIGO,
    "secondaryTextColor": "#1D1D1F",

    "tertiaryColor": "#F0E0FA",
    "tertiaryBorderColor": _M_PURPLE,
    "tertiaryTextColor": "#1D1D1F",

    "lineColor": "#AEAEB2",
    "textColor": "#1D1D1F",

    "noteBkgColor": "#FFF9E0",
    "noteTextColor": "#1D1D1F",
    "noteBorderColor": _M_YELLOW,

    "actorBkg": _M_BLUE,
    "actorBorder": _V_BLUE,
    "actorTextColor": "#FFFFFF",
    "actorLineColor": "#D1D1D6",

    "activationBkgColor": "#DCEEFF",
    "activationBorderColor": _M_BLUE,
    "signalColor": "#48484A",
    "signalTextColor": "#1D1D1F",
    "sequenceNumberColor": "#FFFFFF",
    "labelBoxBkgColor": "#F5F5F7",
    "labelBoxBorderColor": "#D1D1D6",
    "labelTextColor": "#1D1D1F",
    "loopTextColor": "#86868B",

    "nodeBorder": _M_BLUE,
    "mainBkg": "#DCEEFF",
    "nodeTextColor": "#1D1D1F",
    "clusterBkg": "#F5F5F7",
    "clusterBorder": "#D1D1D6",
    "titleColor": "#1D1D1F",
    "edgeLabelBackground": "#FFFFFF",

    "fillType0": "#DCEEFF",
    "fillType1": "#E6E5FA",
    "fillType2": "#F0E0FA",
    "fillType3": "#DCFAE8",
    "fillType4": "#FFF0D9",
    "fillType5": "#FFE4EB",
    "fillType6": "#D9F7F5",
    "fillType7": "#FFF9E0",

    "pie1": _M_BLUE,
    "pie2": _M_GREEN,
    "pie3": _M_PURPLE,
    "pie4": _M_ORANGE,
    "pie5": _M_PINK,
    "pie6": _M_INDIGO,
    "pie7": _M_TEAL,
    "pie8": _M_YELLOW,
    "pie9": _M_MINT,
    "pie10": _M_CYAN,
    "pie11": _M_RED,
    "pie12": _M_BROWN,
    "pieTitleTextSize": "18px",
    "pieTitleTextColor": "#1D1D1F",
    "pieSectionTextSize": "13px",
    "pieSectionTextColor": "#FFFFFF",
    "pieLegendTextSize": "13px",
    "pieLegendTextColor": "#1D1D1F",
    "pieStrokeColor": "#FFFFFF",
    "pieStrokeWidth": "2px",

    "git0": _M_BLUE,
    "git1": _M_GREEN,
    "git2": _M_PURPLE,
    "git3": _M_RED,
    "git4": _M_ORANGE,
    "git5": _M_INDIGO,
    "git6": _M_TEAL,
    "git7": _M_PINK,
    "gitBranchLabel0": "#FFFFFF",
    "gitBranchLabel1": "#FFFFFF",
    "gitBranchLabel2": "#FFFFFF",
    "gitBranchLabel3": "#FFFFFF",
    "gitBranchLabel4": "#FFFFFF",
    "gitBranchLabel5": "#FFFFFF",
    "gitBranchLabel6": "#FFFFFF",
    "gitBranchLabel7": "#FFFFFF",
    "gitInv0": _M_BLUE,

    "cScale0": _M_BLUE,   "cScale1": _M_GREEN,  "cScale2": _M_PURPLE,
    "cScale3": _M_ORANGE,  "cScale4": _M_PINK,   "cScale5": _M_INDIGO,
    "cScale6": _M_TEAL,    "cScale7": _M_YELLOW,  "cScale8": _M_MINT,
    "cScale9": _M_CYAN,    "cScale10": _M_RED,    "cScale11": _M_BROWN,

    "classText": "#1D1D1F",

    "sectionBkgColor": "#DCEEFF",
    "sectionBkgColor2": "#E6E5FA",
    "altSectionBkgColor": "#F5F5F7",
    "gridColor": "#E5E5EA",
    "todayLineColor": _M_RED,
    "taskBkgColor": _M_BLUE,
    "taskBorderColor": _V_BLUE,
    "taskTextColor": "#FFFFFF",
    "taskTextLightColor": "#FFFFFF",
    "activeTaskBkgColor": _M_INDIGO,
    "activeTaskBorderColor": _V_INDIGO,
    "doneTaskBkgColor": _M_GREEN,
    "doneTaskBorderColor": _V_GREEN,
    "critBkgColor": _M_RED,
    "critBorderColor": _V_RED,
    "taskTextDarkColor": "#1D1D1F",
    "taskTextOutsideColor": "#1D1D1F",

    "labelColor": "#1D1D1F",
    "altBackground": "#F5F5F7",

    "relationColor": "#AEAEB2",
    "relationLabelColor": "#1D1D1F",
    "relationLabelBackground": "#FFFFFF",
}

# Dark-mode mid-tints — slightly muted versions of Apple's dark-mode system colors
_MD_BLUE   = "#4DA3FF"   # from #0A84FF
_MD_GREEN  = "#5DD882"   # from #30D158
_MD_PURPLE = "#C97DF0"   # from #BF5AF2
_MD_ORANGE = "#FFB84D"   # from #FF9F0A
_MD_PINK   = "#FF6B88"   # from #FF375F
_MD_INDIGO = "#9897FF"   # from #7D7AFF
_MD_TEAL   = "#5CC9DE"   # from #40C8E0
_MD_YELLOW = "#FFDF4D"   # from #FFD60A
_MD_MINT   = "#7AE8E2"   # from #63E6E2
_MD_CYAN   = "#88D9FF"   # from #70D7FF
_MD_RED    = "#FF6F66"   # from #FF453A
_MD_BROWN  = "#C2A07A"   # from #AC8E68

APPLE_THEME_DARK = {
    "fontFamily": FONT_STACK,
    "fontSize": "14px",

    "primaryColor": "#0D2E4D",
    "primaryBorderColor": _MD_BLUE,
    "primaryTextColor": "#F5F5F7",

    "secondaryColor": "#1F1D42",
    "secondaryBorderColor": _MD_INDIGO,
    "secondaryTextColor": "#F5F5F7",

    "tertiaryColor": "#2F1D42",
    "tertiaryBorderColor": _MD_PURPLE,
    "tertiaryTextColor": "#F5F5F7",

    "lineColor": "#636366",
    "textColor": "#F5F5F7",

    "noteBkgColor": "#332D1A",
    "noteTextColor": "#F5F5F7",
    "noteBorderColor": _MD_YELLOW,

    "actorBkg": _MD_BLUE,
    "actorBorder": "#0A84FF",
    "actorTextColor": "#FFFFFF",
    "actorLineColor": "#48484A",

    "activationBkgColor": "#0D2E4D",
    "activationBorderColor": _MD_BLUE,
    "signalColor": "#F5F5F7",
    "signalTextColor": "#F5F5F7",
    "sequenceNumberColor": "#FFFFFF",
    "labelBoxBkgColor": "#1C1C1E",
    "labelBoxBorderColor": "#38383A",
    "labelTextColor": "#F5F5F7",
    "loopTextColor": "#98989D",

    "nodeBorder": _MD_BLUE,
    "mainBkg": "#0D2E4D",
    "nodeTextColor": "#F5F5F7",
    "clusterBkg": "#1C1C1E",
    "clusterBorder": "#38383A",
    "titleColor": "#F5F5F7",
    "edgeLabelBackground": "#1C1C1E",

    "fillType0": "#0D2E4D",
    "fillType1": "#1F1D42",
    "fillType2": "#2F1D42",
    "fillType3": "#0D3320",
    "fillType4": "#3D2800",
    "fillType5": "#3D0D1F",
    "fillType6": "#0D333D",
    "fillType7": "#3D3520",

    "pie1": _MD_BLUE,
    "pie2": _MD_GREEN,
    "pie3": _MD_PURPLE,
    "pie4": _MD_ORANGE,
    "pie5": _MD_PINK,
    "pie6": _MD_INDIGO,
    "pie7": _MD_TEAL,
    "pie8": _MD_YELLOW,
    "pie9": _MD_MINT,
    "pie10": _MD_CYAN,
    "pie11": _MD_RED,
    "pie12": _MD_BROWN,
    "pieTitleTextSize": "18px",
    "pieTitleTextColor": "#F5F5F7",
    "pieSectionTextSize": "13px",
    "pieSectionTextColor": "#FFFFFF",
    "pieLegendTextSize": "13px",
    "pieLegendTextColor": "#F5F5F7",
    "pieStrokeColor": "#1C1C1E",
    "pieStrokeWidth": "2px",

    "git0": _MD_BLUE,
    "git1": _MD_GREEN,
    "git2": _MD_PURPLE,
    "git3": _MD_RED,
    "git4": _MD_ORANGE,
    "git5": _MD_INDIGO,
    "git6": _MD_TEAL,
    "git7": _MD_PINK,
    "gitBranchLabel0": "#FFFFFF",
    "gitBranchLabel1": "#FFFFFF",
    "gitBranchLabel2": "#FFFFFF",
    "gitBranchLabel3": "#FFFFFF",
    "gitBranchLabel4": "#FFFFFF",
    "gitBranchLabel5": "#FFFFFF",
    "gitBranchLabel6": "#FFFFFF",
    "gitBranchLabel7": "#FFFFFF",

    "cScale0": _MD_BLUE,   "cScale1": _MD_GREEN,  "cScale2": _MD_PURPLE,
    "cScale3": _MD_ORANGE,  "cScale4": _MD_PINK,   "cScale5": _MD_INDIGO,
    "cScale6": _MD_TEAL,    "cScale7": _MD_YELLOW,  "cScale8": _MD_MINT,
    "cScale9": _MD_CYAN,    "cScale10": _MD_RED,    "cScale11": _MD_BROWN,

    "classText": "#F5F5F7",

    "sectionBkgColor": "#0D2E4D",
    "sectionBkgColor2": "#1F1D42",
    "altSectionBkgColor": "#1C1C1E",
    "gridColor": "#38383A",
    "todayLineColor": _MD_RED,
    "taskBkgColor": _MD_BLUE,
    "taskBorderColor": "#0A84FF",
    "taskTextColor": "#FFFFFF",
    "taskTextLightColor": "#FFFFFF",
    "activeTaskBkgColor": _MD_INDIGO,
    "activeTaskBorderColor": "#7D7AFF",
    "doneTaskBkgColor": _MD_GREEN,
    "doneTaskBorderColor": "#30D158",
    "critBkgColor": _MD_RED,
    "critBorderColor": "#FF453A",
    "taskTextDarkColor": "#F5F5F7",
    "taskTextOutsideColor": "#F5F5F7",

    "labelColor": "#F5F5F7",
    "altBackground": "#1C1C1E",

    "relationColor": "#636366",
    "relationLabelColor": "#F5F5F7",
    "relationLabelBackground": "#1C1C1E",
}


# ---------------------------------------------------------------------------
# Apple HIG CSS — surgically targets every Mermaid diagram type
# ---------------------------------------------------------------------------

APPLE_CSS_LIGHT = """
svg { font-family: """ + FONT_STACK + """; background: #FFFFFF !important; }

/* --- Flowchart --- */
.node rect, .node circle, .node ellipse, .node polygon,
.node .label-container { rx: 10; ry: 10; }
.flowchart-link { stroke-width: 1.5 !important; }
.edgeLabel { font-size: 12px !important; }
.cluster rect { rx: 14 !important; ry: 14 !important; fill: #F5F5F7 !important; stroke: #D1D1D6 !important; }
.cluster text { fill: #86868B !important; font-weight: 600 !important; font-size: 12px !important; }

/* --- Sequence --- */
.actor { rx: 8 !important; ry: 8 !important; }
text.actor > tspan { font-weight: 600 !important; }
.messageLine0, .messageLine1 { stroke: #86868B !important; stroke-width: 1.5 !important; }
.messageText { font-size: 13px !important; fill: #1D1D1F !important; }
.note rect { rx: 8 !important; ry: 8 !important; }
.noteText { font-size: 12px !important; }
.activation0, .activation1, .activation2 { rx: 4 !important; ry: 4 !important; }
.loopLine { stroke: #D1D1D6 !important; stroke-dasharray: 6,4 !important; }

/* --- State --- */
.stateGroup rect { rx: 12 !important; ry: 12 !important; }
.stateGroup text { font-size: 13px !important; }
.stateGroup .composit { rx: 14 !important; ry: 14 !important; }
.transition { stroke: #86868B !important; stroke-width: 1.5 !important; }

/* --- ER --- */
.er.entityBox { rx: 10 !important; ry: 10 !important; }
.er.entityLabel { font-weight: 700 !important; font-size: 14px !important; }
.er.attributeBoxOdd { fill: #FFFFFF !important; }
.er.attributeBoxEven { fill: #F5F5F7 !important; }
.er.relationshipLine { stroke: #86868B !important; stroke-width: 1.5 !important; }
.er.relationshipLabel { font-size: 12px !important; fill: #86868B !important; }

/* --- Class --- */
.classGroup rect { rx: 10 !important; ry: 10 !important; }
.classGroup text { font-size: 13px !important; }
.classLabel .box { rx: 10 !important; ry: 10 !important; }
.relation { stroke: #86868B !important; stroke-width: 1.5 !important; }

/* --- Gantt --- */
.grid .tick line { stroke: #E5E5EA !important; }
.section { rx: 0; }
text.taskText { font-size: 12px !important; font-weight: 600 !important; }
text.taskTextOutsideRight, text.taskTextOutsideLeft { font-size: 12px !important; }
.today { stroke: #FF3B30 !important; stroke-width: 2 !important; }

/* --- Pie --- */
.pieCircle { stroke: #FFFFFF !important; stroke-width: 2 !important; }
text.pieTitleText { font-weight: 700 !important; font-size: 18px !important; fill: #1D1D1F !important; }
text.slice { font-size: 13px !important; font-weight: 600 !important; }
.legend text { font-size: 13px !important; }

/* --- Git --- */
.commit-id text { font-size: 11px !important; }
.branch-label text { font-weight: 600 !important; }

/* --- Timeline --- */
.timeline-node path { rx: 10 !important; ry: 10 !important; }
.lineWrapper line { stroke: #AEAEB2 !important; }
.lineWrapper line[marker-end] { stroke: #AEAEB2 !important; }
.lineWrapper line[stroke-dasharray] { stroke: #C7C7CC !important; stroke-width: 1.5 !important; }

/* --- Journey — Apple HIG colors matching Timeline cScale palette --- */
.journey-section.section-type-0, .task.task-type-0 { fill: #66AEFF !important; stroke: #4A94E0 !important; }
.journey-section.section-type-1, .task.task-type-1 { fill: #7AD98F !important; stroke: #5CC275 !important; }
.journey-section.section-type-2, .task.task-type-2 { fill: #C88AEB !important; stroke: #AF6DD4 !important; }
.journey-section.section-type-3, .task.task-type-3 { fill: #FFB866 !important; stroke: #E09B4A !important; }
.journey-section.section-type-4, .task.task-type-4 { fill: #FF7D99 !important; stroke: #E0607A !important; }
.journey-section.section-type-5, .task.task-type-5 { fill: #8987E4 !important; stroke: #6B69C8 !important; }
.journey-section.section-type-6, .task.task-type-6 { fill: #73CCD9 !important; stroke: #56B0BD !important; }
.journey-section.section-type-7, .task.task-type-7 { fill: #FFE066 !important; stroke: #E0C44A !important; }
.journey-section.section-type-8, .task.task-type-8 { fill: #66DBD2 !important; stroke: #4ABFB6 !important; }
.journey-section.section-type-9, .task.task-type-9 { fill: #94D9FC !important; stroke: #70BDE0 !important; }
.journey-section.section-type-10, .task.task-type-10 { fill: #FF8580 !important; stroke: #E06B66 !important; }
.journey-section.section-type-11, .task.task-type-11 { fill: #C2A87E !important; stroke: #A68C62 !important; }
.actor-0 { fill: #66AEFF !important; stroke: #007AFF !important; }
.actor-1 { fill: #7AD98F !important; stroke: #34C759 !important; }
.actor-2 { fill: #C88AEB !important; stroke: #AF52DE !important; }
.actor-3 { fill: #FFB866 !important; stroke: #FF9500 !important; }
.actor-4 { fill: #FF7D99 !important; stroke: #FF2D55 !important; }
.actor-5 { fill: #8987E4 !important; stroke: #5856D6 !important; }
.actor-6 { fill: #73CCD9 !important; stroke: #30B0C7 !important; }
.actor-7 { fill: #FFE066 !important; stroke: #FFCC00 !important; }
.section .sectionTitle { fill: #FFFFFF !important; font-weight: 600 !important; font-size: 13px !important; }
.task { rx: 8 !important; ry: 8 !important; }
text.taskText { fill: #FFFFFF !important; font-weight: 600 !important; font-size: 12px !important; }
text.taskTextOutsideRight { fill: #1D1D1F !important; font-size: 12px !important; }
.legend text { font-size: 12px !important; fill: #1D1D1F !important; }
"""

APPLE_CSS_DARK = """
svg { font-family: """ + FONT_STACK + """; background: #000000 !important; }

/* --- Flowchart --- */
.node rect, .node circle, .node ellipse, .node polygon,
.node .label-container { rx: 10; ry: 10; }
.flowchart-link { stroke-width: 1.5 !important; }
.edgeLabel { font-size: 12px !important; }
.cluster rect { rx: 14 !important; ry: 14 !important; fill: #1C1C1E !important; stroke: #38383A !important; }
.cluster text { fill: #98989D !important; font-weight: 600 !important; font-size: 12px !important; }

/* --- Sequence --- */
.actor { rx: 8 !important; ry: 8 !important; }
text.actor > tspan { font-weight: 600 !important; }
.messageLine0, .messageLine1 { stroke: #636366 !important; stroke-width: 1.5 !important; }
.messageText { font-size: 13px !important; fill: #F5F5F7 !important; }
.note rect { rx: 8 !important; ry: 8 !important; }
.noteText { font-size: 12px !important; }
.activation0, .activation1, .activation2 { rx: 4 !important; ry: 4 !important; }
.loopLine { stroke: #38383A !important; stroke-dasharray: 6,4 !important; }

/* --- State --- */
.stateGroup rect { rx: 12 !important; ry: 12 !important; }
.stateGroup text { font-size: 13px !important; }
.transition { stroke: #636366 !important; stroke-width: 1.5 !important; }

/* --- ER --- */
.er.entityBox { rx: 10 !important; ry: 10 !important; }
.er.entityLabel { font-weight: 700 !important; font-size: 14px !important; }
.er.attributeBoxOdd { fill: #1C1C1E !important; }
.er.attributeBoxEven { fill: #2C2C2E !important; }
.er.relationshipLine { stroke: #636366 !important; stroke-width: 1.5 !important; }

/* --- Class --- */
.classGroup rect { rx: 10 !important; ry: 10 !important; }
.classGroup text { font-size: 13px !important; }
.relation { stroke: #636366 !important; stroke-width: 1.5 !important; }

/* --- Gantt --- */
.grid .tick line { stroke: #38383A !important; }
text.taskText { font-size: 12px !important; font-weight: 600 !important; }
.today { stroke: #FF453A !important; stroke-width: 2 !important; }

/* --- Pie --- */
.pieCircle { stroke: #1C1C1E !important; stroke-width: 2 !important; }
text.pieTitleText { font-weight: 700 !important; font-size: 18px !important; fill: #F5F5F7 !important; }
text.slice { font-size: 13px !important; font-weight: 600 !important; }

/* --- Git --- */
.commit-id text { font-size: 11px !important; }
.branch-label text { font-weight: 600 !important; }

/* --- Journey — Apple HIG dark-mode colors matching Timeline cScale palette --- */
.journey-section.section-type-0, .task.task-type-0 { fill: #4DA3FF !important; stroke: #3080D9 !important; }
.journey-section.section-type-1, .task.task-type-1 { fill: #5DD882 !important; stroke: #40BD66 !important; }
.journey-section.section-type-2, .task.task-type-2 { fill: #C97DF0 !important; stroke: #A85DD4 !important; }
.journey-section.section-type-3, .task.task-type-3 { fill: #FFB84D !important; stroke: #D99B33 !important; }
.journey-section.section-type-4, .task.task-type-4 { fill: #FF6B88 !important; stroke: #D9506A !important; }
.journey-section.section-type-5, .task.task-type-5 { fill: #9897FF !important; stroke: #7B7AE0 !important; }
.journey-section.section-type-6, .task.task-type-6 { fill: #5CC9DE !important; stroke: #40AEC2 !important; }
.journey-section.section-type-7, .task.task-type-7 { fill: #FFDF4D !important; stroke: #D9C033 !important; }
.journey-section.section-type-8, .task.task-type-8 { fill: #7AE8E2 !important; stroke: #5ECCC6 !important; }
.journey-section.section-type-9, .task.task-type-9 { fill: #88D9FF !important; stroke: #6ABDE0 !important; }
.journey-section.section-type-10, .task.task-type-10 { fill: #FF6F66 !important; stroke: #D9554D !important; }
.journey-section.section-type-11, .task.task-type-11 { fill: #C2A07A !important; stroke: #A6855E !important; }
.actor-0 { fill: #4DA3FF !important; stroke: #0A84FF !important; }
.actor-1 { fill: #5DD882 !important; stroke: #30D158 !important; }
.actor-2 { fill: #C97DF0 !important; stroke: #BF5AF2 !important; }
.actor-3 { fill: #FFB84D !important; stroke: #FF9F0A !important; }
.actor-4 { fill: #FF6B88 !important; stroke: #FF375F !important; }
.actor-5 { fill: #9897FF !important; stroke: #7D7AFF !important; }
.actor-6 { fill: #5CC9DE !important; stroke: #40C8E0 !important; }
.actor-7 { fill: #FFDF4D !important; stroke: #FFD60A !important; }
.section .sectionTitle { fill: #FFFFFF !important; font-weight: 600 !important; font-size: 13px !important; }
.task { rx: 8 !important; ry: 8 !important; }
text.taskText { fill: #FFFFFF !important; font-weight: 600 !important; font-size: 12px !important; }
text.taskTextOutsideRight { fill: #F5F5F7 !important; font-size: 12px !important; }
.legend text { font-size: 12px !important; fill: #F5F5F7 !important; }
"""


def _inject_css_into_svg(svg: str, css: str) -> str:
    """Inject custom CSS into the SVG's existing <style> block."""
    import re as _re
    style_match = _re.search(r"(</style>)", svg)
    if style_match:
        inject_point = style_match.start()
        return svg[:inject_point] + "\n" + css.strip() + "\n" + svg[inject_point:]
    svg_tag_end = svg.find(">")
    if svg_tag_end != -1:
        return svg[:svg_tag_end + 1] + f"<style>{css}</style>" + svg[svg_tag_end + 1:]
    return svg


def _ensure_white_background(svg: str) -> str:
    """Insert a white background rect so the diagram has a solid white background in any viewer."""
    import re as _re
    viewbox_match = _re.search(r'\bviewBox=["\']([^"\']+)["\']', svg)
    if not viewbox_match:
        return svg
    parts = viewbox_match.group(1).strip().split()
    if len(parts) != 4:
        return svg
    x, y, w, h = parts[0], parts[1], parts[2], parts[3]
    rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#FFFFFF"/>'
    insert_after = svg.find(">", svg.find("<svg"))
    if insert_after == -1:
        return svg
    return svg[: insert_after + 1] + rect + svg[insert_after + 1 :]


async def _ensure_chromium() -> None:
    """Auto-install Chromium if not already present."""
    import subprocess
    import sys
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        logger.warning("Could not auto-install Chromium: %s", e.stderr.decode())


async def get_browser() -> Browser:
    """Get or create the singleton browser instance."""
    global _playwright, _browser
    async with _lock:
        if _browser and _browser.is_connected():
            return _browser

        try:
            pw = await async_playwright().start()
            _playwright = pw
            _browser = await pw.chromium.launch(headless=True)
        except Exception:
            logger.info("Chromium not found, attempting auto-install...")
            await _ensure_chromium()
            pw = await async_playwright().start()
            _playwright = pw
            _browser = await pw.chromium.launch(headless=True)

        return _browser


async def close_browser() -> None:
    """Clean up the browser on shutdown."""
    global _playwright, _browser
    if _browser:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright:
        try:
            await _playwright.stop()
        except Exception:
            pass
        _playwright = None


async def render_mermaid(
    syntax: str,
    theme: str = "light",
    look: str = "default",
) -> str:
    """Render a Mermaid diagram and return SVG string.

    Args:
        syntax: Raw mermaid diagram syntax (e.g. ``flowchart LR\\n  A-->B``)
        theme: ``"light"`` or ``"dark"``
        look: ``"default"`` or ``"handDrawn"``

    Returns:
        SVG string of the rendered diagram.

    Raises:
        RuntimeError: If mermaid fails to parse the syntax.
    """
    browser = await get_browser()
    page = await browser.new_page(viewport={"width": 1920, "height": 1080})

    errors: list[str] = []

    def _on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", _on_console)

    theme_vars = APPLE_THEME_DARK if theme == "dark" else APPLE_THEME_LIGHT
    custom_css = APPLE_CSS_DARK if theme == "dark" else APPLE_CSS_LIGHT

    import json
    theme_vars_js = json.dumps(theme_vars)

    look_config = ""
    if look == "handDrawn":
        look_config = 'look: "handDrawn",'

    escaped_syntax = (
        syntax
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
    )

    is_gantt = syntax.strip().lower().startswith("gantt")
    container_style = "width: 1800px;" if is_gantt else "width: fit-content;"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <script src="{MERMAID_CDN}"></script>
    <style>
        body {{ margin: 0; padding: 20px; background: transparent; }}
        #diagram {{ {container_style} }}
        {custom_css}
    </style>
</head>
<body>
    <pre class="mermaid" id="diagram">
{escaped_syntax}
    </pre>
    <script>
        mermaid.initialize({{
            startOnLoad: false,
            theme: 'base',
            themeVariables: {theme_vars_js},
            {look_config}
            securityLevel: 'loose',
            flowchart: {{ htmlLabels: true, curve: 'basis' }},
            sequence: {{ mirrorActors: false }},
            gantt: {{ useWidth: 1760 }},
        }});
        mermaid.run({{ querySelector: '#diagram' }});
    </script>
</body>
</html>"""

    try:
        await page.set_content(html, wait_until="networkidle")

        try:
            await page.wait_for_selector("#diagram svg", timeout=10000)
        except Exception:
            parse_errors = [e for e in errors if "Parse error" in e or "Syntax error" in e or "error" in e.lower()]
            if parse_errors:
                raise RuntimeError(
                    f"Mermaid parse error: {parse_errors[0]}\n\nFailing syntax:\n{syntax}"
                )
            raise RuntimeError(
                f"Mermaid render timeout. Errors: {errors}\n\nFailing syntax:\n{syntax}"
            )

        await page.eval_on_selector(
            "#diagram svg",
            """el => {
                const sels = [
                    '.journey-section', '.task[class*=task-type]',
                    '[class*=actor-]'
                ];
                sels.forEach(sel => {
                    el.querySelectorAll(sel).forEach(node => {
                        const cs = getComputedStyle(node);
                        const fill = cs.fill;
                        const stroke = cs.stroke;
                        if (fill && fill !== 'none')
                            node.setAttribute('fill', fill);
                        if (stroke && stroke !== 'none')
                            node.setAttribute('stroke', stroke);
                    });
                });
            }""",
        )

        svg = await page.eval_on_selector(
            "#diagram svg",
            "el => el.outerHTML",
        )

        if 'aria-roledescription="error"' in svg:
            error_text = await page.eval_on_selector(
                "#diagram svg", "el => el.textContent"
            )
            raise RuntimeError(
                f"Mermaid syntax error: {error_text.strip()}\n\nFailing syntax:\n{syntax[:500]}"
            )

        svg = _inject_css_into_svg(svg, custom_css)
        if theme == "light":
            svg = _ensure_white_background(svg)
        return svg

    finally:
        await page.close()
