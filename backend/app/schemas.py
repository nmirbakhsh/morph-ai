"""
Pydantic schemas — the contract between LLM, backend, and frontend.

Two LLM stages produce typed JSON:
- Prompt A → AdjacentIntents  (4 next-room signposts)
- Prompt B → NodeLayout       (full panel UI for the current room)

NOTE: we deliberately do NOT use `from __future__ import annotations` here.
Pydantic v2's BeforeValidator closures (e.g. inside `_bounded_str`) need to
resolve at class-definition time — string-deferred annotations break that.
"""
from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class _StrictBase(BaseModel):
    """Reject unknown fields. Used on every request body so a poisoned client
    that sends e.g. `viz_prefs` gets a loud 422 rather than a silent ride-along."""
    model_config = ConfigDict(extra="forbid")


def _bounded_str(min_len: int, max_len: int):
    """A bounded-length str type with proper Pydantic min_length/max_length
    constraints AND a BeforeValidator that gracefully trims oversize input
    rather than rejecting (the LLM frequently overshoots by a few chars and
    the user shouldn't see a stub layout because of it).

    Undersize still hard-fails so we don't ship empty/1-char text — the
    fallback path will retry as two-stage."""
    def _trim(v):
        if v is None:
            return v
        if isinstance(v, str) and len(v) > max_len:
            return v[:max_len].rstrip()
        return v
    return Annotated[
        str,
        BeforeValidator(_trim),
        Field(min_length=min_len, max_length=max_len),
    ]


# (min, max) per role. min = LLM "must be at least this substantial".
# max = hard cap (auto-trimmed). LIMITS dict mirrors them so the prompt
# can show the LLM the same numbers it'll be validated against.
LIMITS: dict[str, tuple[int, int]] = {
    "ShortLabel":   (2, 18),
    "TinyValue":    (1, 14),
    "ListTitle":    (3, 32),
    "SubText":      (0, 60),
    "ChartTitle":   (3, 28),
    "ChartSub":     (0, 44),
    "HeroValue":    (1, 16),
    "DeltaText":    (0, 20),
    "EyebrowText":  (3, 32),
    "HeadlineText": (8, 64),
    "HeadlineSub":  (0, 56),
    "BodyText":     (0, 180),
    "MetricLabel":  (2, 22),
    "MetricSub":    (0, 34),
    "TagText":      (1, 18),
    "IntentLabel":  (2, 18),
    "IntentSub":    (2, 70),
    "IntentPrompt": (8, 220),
    "IconText":     (1, 4),
}

ShortLabel    = _bounded_str(*LIMITS["ShortLabel"])
TinyValue     = _bounded_str(*LIMITS["TinyValue"])
ListTitle     = _bounded_str(*LIMITS["ListTitle"])
SubText       = _bounded_str(*LIMITS["SubText"])
ChartTitle    = _bounded_str(*LIMITS["ChartTitle"])
ChartSub      = _bounded_str(*LIMITS["ChartSub"])
HeroValue     = _bounded_str(*LIMITS["HeroValue"])
DeltaText     = _bounded_str(*LIMITS["DeltaText"])
EyebrowText   = _bounded_str(*LIMITS["EyebrowText"])
HeadlineText  = _bounded_str(*LIMITS["HeadlineText"])
HeadlineSub   = _bounded_str(*LIMITS["HeadlineSub"])
BodyText      = _bounded_str(*LIMITS["BodyText"])
MetricLabel   = _bounded_str(*LIMITS["MetricLabel"])
MetricSub     = _bounded_str(*LIMITS["MetricSub"])
TagText       = _bounded_str(*LIMITS["TagText"])
IntentLabel   = _bounded_str(*LIMITS["IntentLabel"])
IntentSub     = _bounded_str(*LIMITS["IntentSub"])
IntentPrompt  = _bounded_str(*LIMITS["IntentPrompt"])
IconText      = _bounded_str(*LIMITS["IconText"])


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
    body: BodyText


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

class Prefs(_StrictBase):
    """User-tunable generation preferences from the settings popup."""
    complexity: int = Field(default=3, ge=1, le=5)   # 1=ELI5, 5=expert
    density: int    = Field(default=3, ge=1, le=5)   # 1=spartan, 5=info-dense
    contrast: int   = Field(default=3, ge=1, le=5)   # 1=subtle, 5=sharp


class InitRequest(_StrictBase):
    viewport_w: Optional[int] = None
    viewport_h: Optional[int] = None
    prefs: Optional[Prefs] = None


class InitResponse(BaseModel):
    session_id: str
    node: NodeRecord


class NavigateRequest(_StrictBase):
    session_id: str
    parent_node_id: str
    direction: Direction
    intent_prompt: str
    mcp_tool: Optional[str] = None
    prefetch: bool = False  # if true, suppress the SSE log stream
    viewport_w: Optional[int] = None
    viewport_h: Optional[int] = None
    prefs: Optional[Prefs] = None


class NavigateResponse(BaseModel):
    node: NodeRecord


class ChatRequest(_StrictBase):
    session_id: str
    current_node_id: str
    message: str
    viewport_w: Optional[int] = None
    viewport_h: Optional[int] = None
    prefs: Optional[Prefs] = None


class ChatResponse(BaseModel):
    """Chat can either explain in-place OR teleport to a new node."""
    reply: str
    teleport_node: Optional[NodeRecord] = None
    followups: List[str] = Field(default_factory=list)


class GraphResponse(BaseModel):
    session_id: str
    nodes: List[NodeRecord]
