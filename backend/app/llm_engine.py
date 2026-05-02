"""
Gemini-powered LLM engine.

Two prompts:
- Prompt A → AdjacentIntents (suggests 4 next rooms based on the current node)
- Prompt B → NodeLayout      (translates raw MCP output into the panel UI)

Plus a chat router that classifies a user message as:
- explain (just answer in chat)
- teleport (jump to a brand-new node, parented under the current one)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .schemas import (
    AdjacentIntents, Direction, IntentSignpost, NodeLayout,
)
from .tool_registry import tool_descriptions_for_prompt


OPPOSITE: Dict[str, Direction] = {
    "up": "down", "down": "up", "left": "right", "right": "left",
}

logger = logging.getLogger("morph.llm")

try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except Exception:  # pragma: no cover
    HAS_GENAI = False


def _client():
    if not HAS_GENAI:
        raise RuntimeError("google-genai not installed")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    return genai.Client(api_key=GEMINI_API_KEY)


# ─── Low-level call ────────────────────────────────────────────────────────

async def _generate_json(prompt: str, *, schema_hint: str) -> Dict[str, Any]:
    """Call Gemini and parse JSON from the response. Falls back to a stub on error."""
    if not (HAS_GENAI and GEMINI_API_KEY):
        logger.warning("Gemini unavailable — returning stub")
        return {"_stub": True}

    try:
        client = _client()
        resp = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.85,
            ),
        )
        text = (resp.text or "").strip()
        # Some models still wrap output in code fences — strip them.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:  # noqa: BLE001
        logger.exception("Gemini call failed (%s): %s", schema_hint, e)
        return {"_error": str(e)}


# ─── Prompt B: UI layout ──────────────────────────────────────────────────

LAYOUT_SCHEMA_TEXT = """
{
  "theme": "violet | emerald | coral | cerulean | amber | indigo | magenta | warm | neutral",
  "accent_color": "#hex (vibrant, fits theme)",
  "icon": "single emoji",
  "eyebrow": "small uppercase label, ~3-6 words",
  "headline": "bold one-liner (~3-9 words)",
  "headline_accent": "optional emphasized sub-phrase that recolours",
  "body": "optional 1-2 sentence intro (<= 180 chars)",
  "components": [
    /* up to 4 of these. Mix freely. */
    { "type": "stat_grid", "items": [{"label","value","delta?","trend?":"up|down|flat"}] },
    { "type": "chart", "title", "subtitle?", "hero_value?", "hero_delta?", "series":[float,...] },
    { "type": "list", "title?", "items":[{"title","subtitle?","value?","icon?":"emoji"}] },
    { "type": "text_block", "title?", "body" },
    { "type": "metric_block", "label", "value", "sublabel?" },
    { "type": "tag_row", "tags":["..."] }
  ]
}
""".strip()


async def generate_layout(
    *,
    intent_prompt: str,
    mcp_tool: Optional[str],
    mcp_output: Optional[Dict[str, Any]],
    parent_title: Optional[str] = None,
) -> NodeLayout:
    """Prompt B — turn raw MCP output (or pure intent) into a NodeLayout."""
    raw_payload = ""
    if mcp_output is not None:
        raw_payload = json.dumps(mcp_output, default=str)[:6000]

    prompt = f"""You design a single full-bleed panel ("room") in a spatial-canvas app called Morph AI.
The room must feel rich, beautiful, consumer-grade — vibrant gradients, expressive typography,
emojis welcome. Pick a theme + accent that fits the topic.

User intent for this room:
"{intent_prompt}"

{"Parent room: " + parent_title if parent_title else ""}
{"MCP tool executed: " + mcp_tool if mcp_tool else "No MCP tool was run."}

Raw tool output (truncated, may be empty):
{raw_payload or "(none)"}

Translate the data + intent into ONE JSON object with this shape (no extra text, no fences):

{LAYOUT_SCHEMA_TEXT}

Constraints:
- Output must be valid JSON parseable by json.loads.
- 1 to 4 components total. Vary types when sensible.
- Numbers in chart.series must be plain floats, ~6-32 of them.
- Keep eyebrow + headline punchy. Consumer voice (warm, confident, no jargon).
- If no real data, invent plausible illustrative content — never apologize, never say "no data".
"""
    raw = await _generate_json(prompt, schema_hint="layout")
    return _coerce_layout(raw, fallback_intent=intent_prompt)


def _coerce_layout(raw: Dict[str, Any], *, fallback_intent: str) -> NodeLayout:
    if "_stub" in raw or "_error" in raw:
        return _stub_layout(fallback_intent)
    try:
        return NodeLayout.model_validate(raw)
    except ValidationError as e:
        logger.warning("layout validation failed: %s", e)
        return _stub_layout(fallback_intent)


def _stub_layout(intent: str) -> NodeLayout:
    return NodeLayout(
        theme="indigo",
        accent_color="#a78bfa",
        icon="✦",
        eyebrow="Morph AI · Stub",
        headline="The model is offline.",
        headline_accent="Check your Gemini key.",
        body=f"Intent received: “{intent}”. Showing a placeholder until the LLM is reachable.",
        components=[
            {"type": "text_block", "title": "How to fix",
             "body": "Set GEMINI_API_KEY in .env, then restart the backend."},
        ],
    )


# ─── Prompt A: adjacent intents ────────────────────────────────────────────

INTENT_SCHEMA_TEXT = """
{
  "intents": [
    /* one entry per direction the caller asked for. */
    {
      "direction": "up | down | left | right",
      "label": "very short (1-2 words)",
      "sublabel": "one short tease line (< 60 chars)",
      "icon": "single emoji",
      "intent_prompt": "concrete prompt that would generate this room",
      "mcp_tool": "qualified MCP tool name to invoke, or null if none fits",
      "is_continuation": false   /* true ONLY if this direction is a 'continue' to part 2 of the current room */
    }
  ]
}
""".strip()


def _layout_summary(layout: NodeLayout) -> str:
    """Compact textual summary of a node's layout for grounding Prompt A."""
    parts = [f"eyebrow: {layout.eyebrow}", f"headline: {layout.headline}"]
    if layout.body:
        parts.append(f"body: {layout.body[:240]}")
    for c in layout.components[:4]:
        t = c.type
        if t == "stat_grid":
            items = ", ".join(f"{i.label}={i.value}" for i in c.items[:5])
            parts.append(f"stats: {items}")
        elif t == "chart":
            parts.append(f"chart: {c.title}" + (f" hero={c.hero_value}" if c.hero_value else ""))
        elif t == "list":
            items = ", ".join(i.title for i in c.items[:6])
            parts.append(f"list[{c.title or '-'}]: {items}")
        elif t == "text_block":
            parts.append(f"text[{c.title or '-'}]: {c.body[:200]}")
        elif t == "metric_block":
            parts.append(f"metric: {c.label}={c.value}")
        elif t == "tag_row":
            parts.append(f"tags: {', '.join(c.tags[:8])}")
    return " | ".join(parts)[:1400]


async def generate_adjacent_intents(
    *,
    current_layout: NodeLayout,
    current_title: str,
    history_titles: List[str],
    back_direction: Optional[Direction] = None,
    back_target_title: Optional[str] = None,
    mcp_tool_executed: Optional[str] = None,
    mcp_output_summary: Optional[str] = None,
) -> AdjacentIntents:
    """Prompt A — suggest the next rooms grounded in the current room's content.

    If `back_direction` is provided, Prompt A only generates intents for the
    OTHER three directions; the caller injects a synthetic Back intent.
    """
    history_str = " → ".join(history_titles[-6:]) if history_titles else "(none)"
    needed_dirs: List[Direction] = ["up", "down", "left", "right"]
    if back_direction:
        needed_dirs = [d for d in needed_dirs if d != back_direction]
    needed_str = ", ".join(needed_dirs)

    grounding = _layout_summary(current_layout)

    mcp_block = ""
    if mcp_tool_executed:
        mcp_block = f"\nMCP tool that produced this room: {mcp_tool_executed}"
    if mcp_output_summary:
        mcp_block += f"\nKey facts from MCP output: {mcp_output_summary[:600]}"

    prompt = f"""You design the next directional rooms in a spatial-canvas app.
The user just landed on a room. Suggest where each remaining direction should lead,
grounded in the CURRENT room's actual content — not generic ideas.

Current room title: "{current_title}"
Current room content summary:
{grounding}{mcp_block}

Recent path: {history_str}

Available MCP tools:
{tool_descriptions_for_prompt()}

Generate intents for these directions ONLY: {needed_str}

Return ONE JSON object, no fences, matching this exact shape:

{INTENT_SCHEMA_TEXT}

Rules:
- Output exactly {len(needed_dirs)} intents, one per requested direction.
- Each label is 1-2 words. Each sublabel < 60 chars.
- intent_prompt must reference SPECIFIC entities/themes from the current room
  so the next room is a natural follow-up (a deeper dive, a related topic,
  a comparison, etc.).
- If a relevant MCP tool exists, set mcp_tool to its qualified_name.
- If the current room is clearly part 1 of a longer piece (a Wikipedia article
  intro, a paginated list, a topic that needs more pages), make EXACTLY ONE
  direction a "Continue" with `is_continuation: true`, label "Continue",
  intent_prompt that asks for the next part of the topic.
- Avoid backtracking to recent path entries.
"""
    raw = await _generate_json(prompt, schema_hint="intents")
    return _coerce_intents(raw, needed_dirs=needed_dirs)


def _coerce_intents(
    raw: Dict[str, Any], *, needed_dirs: List[Direction],
) -> AdjacentIntents:
    if "_stub" in raw or "_error" in raw:
        return _stub_intents(needed_dirs=needed_dirs)
    try:
        intents = AdjacentIntents.model_validate(raw)
        seen: set[str] = set()
        out: List[IntentSignpost] = []
        for it in intents.intents:
            if it.direction in seen or it.direction not in needed_dirs:
                continue
            seen.add(it.direction)
            out.append(it)
        # Backfill any directions the LLM skipped
        for d in needed_dirs:
            if d not in seen:
                out.append(_stub_intent_for(d))
        if not out:
            return _stub_intents(needed_dirs=needed_dirs)
        return AdjacentIntents(intents=out)
    except ValidationError as e:
        logger.warning("intent validation failed: %s", e)
        return _stub_intents(needed_dirs=needed_dirs)


def _stub_intent_for(d: Direction) -> IntentSignpost:
    table: Dict[Direction, IntentSignpost] = {
        "up": IntentSignpost(direction="up", label="Discover",
                             sublabel="A surprise related topic", icon="✨",
                             intent_prompt="Explore something related but unexpected",
                             mcp_tool=None),
        "right": IntentSignpost(direction="right", label="Deeper",
                                sublabel="Go one level deeper", icon="🔬",
                                intent_prompt="Drill deeper into the current topic",
                                mcp_tool=None),
        "down": IntentSignpost(direction="down", label="Examples",
                               sublabel="Concrete examples", icon="📋",
                               intent_prompt="Show concrete examples of the current topic",
                               mcp_tool=None),
        "left": IntentSignpost(direction="left", label="Tangent",
                               sublabel="A sideways topic", icon="↪",
                               intent_prompt="Show a related tangent topic",
                               mcp_tool=None),
    }
    return table[d]


def _stub_intents(needed_dirs: List[Direction]) -> AdjacentIntents:
    return AdjacentIntents(intents=[_stub_intent_for(d) for d in needed_dirs])


def make_back_intent(
    *,
    direction: Direction,
    target_node_id: str,
    parent_title: str,
) -> IntentSignpost:
    """Synthesize a Back signpost pointing to an existing parent node."""
    arrow = {"up": "↑", "down": "↓", "left": "←", "right": "→"}[direction]
    return IntentSignpost(
        direction=direction,
        label="Back",
        sublabel=parent_title[:60] or "Previous room",
        icon=arrow,
        intent_prompt="(back to parent)",
        mcp_tool=None,
        target_node_id=target_node_id,
        is_back=True,
    )


# ─── Chat router (teleport vs explain) ────────────────────────────────────

async def chat_route(
    *, message: str, current_title: str, current_layout_summary: str,
) -> Tuple[str, str, Optional[str], List[str]]:
    """
    Returns (mode, reply, teleport_intent, followups).
    mode is "explain" or "teleport".
    """
    prompt = f"""User is in a spatial-canvas app, currently viewing room "{current_title}".
Room summary: {current_layout_summary}

User says: "{message}"

Decide if the user wants to:
(a) just chat / ask about the current room → mode="explain"
(b) teleport to a different room                  → mode="teleport"

Respond with JSON only, this exact shape:
{{
  "mode": "explain" | "teleport",
  "reply": "<short warm reply, 1-2 sentences>",
  "teleport_intent": "<concrete prompt for the new room, or null>",
  "followups": ["<short suggestion>", "<short suggestion>", "<short suggestion>"]
}}
"""
    raw = await _generate_json(prompt, schema_hint="chat_route")
    if "_stub" in raw or "_error" in raw:
        return ("explain",
                "I'm offline right now — set your Gemini key to chat.", None, [])

    mode = raw.get("mode", "explain")
    reply = raw.get("reply") or "Got it."
    teleport_intent = raw.get("teleport_intent") if mode == "teleport" else None
    followups = raw.get("followups") or []
    if not isinstance(followups, list):
        followups = []
    return mode, reply, teleport_intent, [str(f)[:80] for f in followups[:4]]


# ─── MCP arg synthesis ────────────────────────────────────────────────────

async def synthesize_mcp_args(
    *, tool_qualified_name: str, intent_prompt: str, tool_schema: Dict[str, Any],
) -> Dict[str, Any]:
    """Ask Gemini to fill in args for the chosen MCP tool from intent text."""
    prompt = f"""Given this MCP tool and a user intent, synthesize the arguments JSON.

Tool: {tool_qualified_name}
Tool input schema (JSON Schema):
{json.dumps(tool_schema)[:2000]}

User intent: "{intent_prompt}"

Return ONLY a JSON object whose keys match the tool's properties.
If no arguments are needed or you can't infer them, return {{}}.
"""
    raw = await _generate_json(prompt, schema_hint="mcp_args")
    if not isinstance(raw, dict) or "_error" in raw or "_stub" in raw:
        return {}
    raw.pop("_stub", None)
    raw.pop("_error", None)
    return raw
