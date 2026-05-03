"""
Pydantic schemas — the contract between LLM, backend, and frontend.

Two LLM stages produce typed JSON:
- Prompt A → AdjacentIntents  (4 next-room signposts)
- Prompt B → NodeLayout       (full panel UI for the current room)
"""
from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, Field


Direction = Literal["up", "down", "left", "right"]
Trend = Literal["up", "down", "flat"]
Theme = Literal[
    "violet", "emerald", "coral", "cerulean", "amber",
    "indigo", "magenta", "warm", "neutral",
]


# ─── Components ────────────────────────────────────────────────────────────

class StatItem(BaseModel):
    label: str
    value: str
    delta: Optional[str] = None
    trend: Optional[Trend] = None


class StatGrid(BaseModel):
    type: Literal["stat_grid"] = "stat_grid"
    items: List[StatItem] = Field(..., max_length=6)


class ChartBlock(BaseModel):
    type: Literal["chart"] = "chart"
    title: str
    subtitle: Optional[str] = None
    hero_value: Optional[str] = None
    hero_delta: Optional[str] = None
    series: List[float] = Field(default_factory=list, max_length=64)


class ListItemModel(BaseModel):
    title: str
    subtitle: Optional[str] = None
    value: Optional[str] = None
    icon: Optional[str] = None


class ListBlock(BaseModel):
    type: Literal["list"] = "list"
    title: Optional[str] = None
    items: List[ListItemModel] = Field(..., max_length=12)


class TextBlock(BaseModel):
    type: Literal["text_block"] = "text_block"
    title: Optional[str] = None
    body: str


class MetricBlock(BaseModel):
    type: Literal["metric_block"] = "metric_block"
    label: str
    value: str
    sublabel: Optional[str] = None


class TagRow(BaseModel):
    type: Literal["tag_row"] = "tag_row"
    tags: List[str] = Field(..., max_length=8)


class ImageBlockComp(BaseModel):
    type: Literal["image"] = "image"
    src: str                         # absolute URL
    alt: Optional[str] = None        # accessibility text
    caption: Optional[str] = None    # short caption shown below


Component = Annotated[
    Union[StatGrid, ChartBlock, ListBlock, TextBlock, MetricBlock, TagRow, ImageBlockComp],
    Field(discriminator="type"),
]


# ─── Adjacent intents (Prompt A output) ────────────────────────────────────

class IntentSignpost(BaseModel):
    direction: Direction
    label: str            # short, displayed on edge ("Health", "Music", "Back")
    sublabel: str         # one-line tease ("Steps, sleep, hydration")
    icon: str             # single emoji
    intent_prompt: str    # full prompt to feed back into Prompt B / MCP call
    mcp_tool: Optional[str] = None  # e.g. "wikipedia:search" — tool to invoke
    # If set, this intent points to an already-existing node — frontend should
    # skip /navigate and just shift coords. Used for the synthetic "Back" intent.
    target_node_id: Optional[str] = None
    is_back: bool = False
    is_continuation: bool = False


class AdjacentIntents(BaseModel):
    intents: List[IntentSignpost] = Field(..., min_length=1, max_length=4)


# ─── Full node layout (Prompt B output) ────────────────────────────────────

class NodeLayout(BaseModel):
    theme: Theme = "violet"
    accent_color: str = "#a78bfa"   # hex; used for headline emphasis
    icon: str = "✦"                  # large emoji for the room
    eyebrow: str
    headline: str
    headline_accent: Optional[str] = None  # short tagline rendered as a sub-headline
    body: Optional[str] = None
    components: List[Component] = Field(default_factory=list, max_length=2)


# ─── Persisted node (DB row → API response) ────────────────────────────────

class NodeRecord(BaseModel):
    node_id: str
    session_id: str
    parent_node_id: Optional[str] = None
    direction_from_parent: Optional[Direction] = None
    coord_x: int = 0
    coord_y: int = 0
    mcp_tool_executed: Optional[str] = None
    title: str
    layout: NodeLayout
    adjacent_intents: AdjacentIntents
    created_at: str


# ─── API request/response shapes ───────────────────────────────────────────

class InitResponse(BaseModel):
    session_id: str
    node: NodeRecord


class NavigateRequest(BaseModel):
    session_id: str
    parent_node_id: str
    direction: Direction
    intent_prompt: str
    mcp_tool: Optional[str] = None
    prefetch: bool = False  # if true, suppress the SSE log stream


class NavigateResponse(BaseModel):
    node: NodeRecord


class ChatRequest(BaseModel):
    session_id: str
    current_node_id: str
    message: str


class ChatResponse(BaseModel):
    """Chat can either explain in-place OR teleport to a new node."""
    reply: str
    teleport_node: Optional[NodeRecord] = None
    followups: List[str] = Field(default_factory=list)


class GraphResponse(BaseModel):
    session_id: str
    nodes: List[NodeRecord]
