"""
Pydantic schemas — the contract between LLM, backend, and frontend.

Two LLM stages produce typed JSON:
- Prompt A → AdjacentIntents  (4 next-room signposts)
- Prompt B → NodeLayout       (full panel UI for the current room)
"""
from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, BeforeValidator, Field


def _trim(n: int):
    """Annotated[str, _trim(N)] — trim oversized strings to N chars rather
    than rejecting them. The LLM still gets a hard cap in the prompt but
    near-miss outputs no longer kill the whole layout."""
    def _do(v):
        if v is None:
            return v
        if isinstance(v, str) and len(v) > n:
            return v[:n].rstrip()
        return v
    return BeforeValidator(_do)


ShortLabel    = Annotated[str, _trim(18)]   # stat label, list value, tag
TinyValue     = Annotated[str, _trim(14)]   # stat value, list value
ListTitle     = Annotated[str, _trim(32)]   # list item title, list block title
SubText       = Annotated[str, _trim(60)]   # list subtitle, intent sublabel
ChartTitle    = Annotated[str, _trim(28)]
ChartSub      = Annotated[str, _trim(44)]
HeroValue     = Annotated[str, _trim(16)]
DeltaText     = Annotated[str, _trim(20)]
EyebrowText   = Annotated[str, _trim(32)]
HeadlineText  = Annotated[str, _trim(64)]
HeadlineSub   = Annotated[str, _trim(56)]
BodyText      = Annotated[str, _trim(180)]   # generous: can hold ~2 short lines
MetricLabel   = Annotated[str, _trim(22)]
MetricSub     = Annotated[str, _trim(34)]
TagText       = Annotated[str, _trim(18)]
IntentLabel   = Annotated[str, _trim(18)]
IntentSub     = Annotated[str, _trim(70)]
IntentPrompt  = Annotated[str, _trim(220)]
IconText      = Annotated[str, _trim(4)]


Direction = Literal["up", "down", "left", "right"]
Trend = Literal["up", "down", "flat"]
Theme = Literal[
    "violet", "emerald", "coral", "cerulean", "amber",
    "indigo", "magenta", "warm", "neutral",
]


# ─── Components ────────────────────────────────────────────────────────────
# All text fields carry hard max_length caps so the LLM cannot bloat the panel
# beyond what fits on a screen. The prompt instructs the model to summarize.

class StatItem(BaseModel):
    label: ShortLabel
    value: TinyValue
    delta: Optional[DeltaText] = None
    trend: Optional[Trend] = None


class StatGrid(BaseModel):
    type: Literal["stat_grid"] = "stat_grid"
    items: List[StatItem] = Field(..., max_length=4)


class ChartBlock(BaseModel):
    type: Literal["chart"] = "chart"
    title: ChartTitle
    subtitle: Optional[ChartSub] = None
    hero_value: Optional[HeroValue] = None
    hero_delta: Optional[DeltaText] = None
    series: List[float] = Field(default_factory=list, max_length=32)


class ListItemModel(BaseModel):
    title: ListTitle
    subtitle: Optional[SubText] = None
    value: Optional[TinyValue] = None
    icon: Optional[IconText] = None


class ListBlock(BaseModel):
    type: Literal["list"] = "list"
    title: Optional[ChartTitle] = None
    items: List[ListItemModel] = Field(..., max_length=5)


class TextBlock(BaseModel):
    type: Literal["text_block"] = "text_block"
    title: Optional[ChartTitle] = None
    body: Annotated[str, _trim(220)]


class MetricBlock(BaseModel):
    type: Literal["metric_block"] = "metric_block"
    label: MetricLabel
    value: HeroValue
    sublabel: Optional[MetricSub] = None


class TagRow(BaseModel):
    type: Literal["tag_row"] = "tag_row"
    tags: List[TagText] = Field(..., max_length=6)


# NOTE: Inline image component dropped — images are now the panel background
# via bg_image_url so they don't add vertical height to the layout.

Component = Annotated[
    Union[StatGrid, ChartBlock, ListBlock, TextBlock, MetricBlock, TagRow],
    Field(discriminator="type"),
]


# ─── Adjacent intents (Prompt A output) ────────────────────────────────────

class IntentSignpost(BaseModel):
    direction: Direction
    label: IntentLabel                            # short, displayed on edge
    sublabel: IntentSub                           # one-line tease
    icon: IconText = "✦"                          # single emoji (unused on tabs)
    intent_prompt: IntentPrompt
    mcp_tool: Optional[str] = None
    target_node_id: Optional[str] = None
    is_back: bool = False
    is_continuation: bool = False


class AdjacentIntents(BaseModel):
    intents: List[IntentSignpost] = Field(..., min_length=1, max_length=4)


# ─── Full node layout (Prompt B output) ────────────────────────────────────

class NodeLayout(BaseModel):
    theme: Theme = "violet"          # legacy fallback when bg_* aren't set
    accent_color: str = "#a78bfa"    # hex; used for headline emphasis
    bg_from: Optional[str] = None
    bg_via: Optional[str] = None
    bg_to: Optional[str] = None
    bg_image_url: Optional[str] = None
    icon: IconText = "✦"
    eyebrow: EyebrowText
    headline: HeadlineText
    headline_accent: Optional[HeadlineSub] = None
    body: Optional[BodyText] = None
    components: List[Component] = Field(default_factory=list, max_length=2)


class FullNodeOutput(BaseModel):
    """Combined Prompt-A + Prompt-B response — both layout and intents in one
    Gemini call. Used by the merged generator; lets us cut a round-trip."""
    layout: NodeLayout
    intents: AdjacentIntents


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

class InitRequest(BaseModel):
    viewport_w: Optional[int] = None
    viewport_h: Optional[int] = None


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
    viewport_w: Optional[int] = None
    viewport_h: Optional[int] = None


class NavigateResponse(BaseModel):
    node: NodeRecord


class ChatRequest(BaseModel):
    session_id: str
    current_node_id: str
    message: str
    viewport_w: Optional[int] = None
    viewport_h: Optional[int] = None


class ChatResponse(BaseModel):
    """Chat can either explain in-place OR teleport to a new node."""
    reply: str
    teleport_node: Optional[NodeRecord] = None
    followups: List[str] = Field(default_factory=list)


class GraphResponse(BaseModel):
    session_id: str
    nodes: List[NodeRecord]
