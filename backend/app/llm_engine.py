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
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .schemas import (
    AdjacentIntents, Direction, FullNodeOutput, IntentSignpost, LIMITS,
    NodeLayout, Prefs,
)
from .tool_registry import tool_descriptions_for_prompt


def _r(role: str) -> str:
    """Render the (min, max) pair for a role as a compact prompt hint."""
    lo, hi = LIMITS[role]
    if lo == 0:
        return f"<= {hi} chars"
    return f"{lo}-{hi} chars"


_COMPLEXITY = {
    1: "ELI5 — assume zero background. Use everyday words, concrete metaphors.",
    2: "Casual — light explanation, accessible to a curious newcomer.",
    3: "Balanced — informed reader, no heavy jargon.",
    4: "Technical — domain reader, real terminology, no hand-holding.",
    5: "Expert — research-level precision, dense terminology fine.",
}
_DENSITY = {
    1: "Very sparse: prefer 1 component, body 40-70 chars, minimal facts.",
    2: "Sparse: 1 component, body 60-100 chars.",
    3: "Balanced: 1-2 components, body 80-130 chars.",
    4: "Dense: 2 components, longer body, list up to 5 items.",
    5: "Very dense: 2 components packed; max items / longest text allowed.",
}
_CONTRAST = {
    1: "Subtle palette: muted, low saturation; gentle gradient stops.",
    2: "Soft palette: medium saturation, smooth gradient.",
    3: "Balanced palette: vibrant but harmonious.",
    4: "Bold palette: high saturation, dramatic gradient sweep.",
    5: "Sharp palette: extreme contrast between bg_from and bg_to (e.g. deep navy → magenta).",
}


def _prefs_block(prefs: Optional[Prefs]) -> str:
    if prefs is None:
        return ""
    return (
        f"\nUser preferences (apply strictly):\n"
        f"- Complexity {prefs.complexity}/5: {_COMPLEXITY[prefs.complexity]}\n"
        f"- Density    {prefs.density}/5:    {_DENSITY[prefs.density]}\n"
        f"- Contrast   {prefs.contrast}/5:   {_CONTRAST[prefs.contrast]}"
    )


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

def _build_layout_schema_text() -> str:
    return f"""{{
  "theme": "violet | emerald | coral | cerulean | amber | indigo | magenta | warm | neutral",
  "accent_color": "#hex (vibrant, fits theme)",
  "bg_from": "#hex — top-left of the panel gradient",
  "bg_via":  "#hex — optional middle stop",
  "bg_to":   "#hex — bottom-right of the panel gradient",
  "icon": "single emoji ({_r('IconText')})",
  "eyebrow": "{_r('EyebrowText')} uppercase label",
  "headline": "{_r('HeadlineText')} (4-7 words), no period",
  "headline_accent": "OPTIONAL — {_r('HeadlineSub')} distinct sub-tagline; do NOT repeat any words from headline",
  "body": "OPTIONAL — {_r('BodyText')}, ONE sentence",
  "components": [
    /* AT MOST 2. Prefer 1. SUMMARIZE ruthlessly to fit caps. */
    {{ "type": "stat_grid",   "items":[{{"label":"{_r('ShortLabel')}","value":"{_r('TinyValue')}","delta?":"{_r('DeltaText')}","trend?":"up|down|flat"}}] /* 2-3 items */ }},
    {{ "type": "chart",       "title":"{_r('ChartTitle')}","subtitle?":"{_r('ChartSub')}","hero_value?":"{_r('HeroValue')}","hero_delta?":"{_r('DeltaText')}","series":[float,...] /* 8-24 floats */ }},
    {{ "type": "list",        "title?":"{_r('ChartTitle')}","items":[{{"title":"{_r('ListTitle')}","subtitle?":"{_r('SubText')}","value?":"{_r('TinyValue')}","icon?":"emoji"}}] /* 3-5 items */ }},
    {{ "type": "text_block",  "title?":"{_r('ChartTitle')}","body":"{_r('BodyText')}" }},
    {{ "type": "metric_block","label":"{_r('MetricLabel')}","value":"{_r('HeroValue')}","sublabel?":"{_r('MetricSub')}" }},
    {{ "type": "tag_row",     "tags":["{_r('TagText')} each"] /* 3-6 tags */ }},
    {{ "type": "image",       "src":"absolute URL from the provided list","alt?":"{_r('SubText')}","caption?":"{_r('SubText')}" }}
  ]
}}"""


def _build_intents_schema_text() -> str:
    return f"""{{
  "intents": [
    /* one entry per requested direction. */
    {{
      "direction": "up | down | left | right",
      "label":      "{_r('IntentLabel')} (1-2 words)",
      "sublabel":   "{_r('IntentSub')} one-line tease",
      "icon":       "single emoji (decorative only)",
      "intent_prompt": "{_r('IntentPrompt')} concrete prompt for the next room",
      "mcp_tool":   "qualified MCP tool name OR null",
      "is_continuation": false  /* true ONLY for a 'continue' direction */
    }}
  ]
}}"""


# Lazy globals so other code can still import them by name.
LAYOUT_SCHEMA_TEXT = _build_layout_schema_text()
INTENTS_SCHEMA_TEXT = _build_intents_schema_text()


def _extract_image_urls(mcp_output: Dict[str, Any], max_n: int = 6) -> List[str]:
    """Scan MCP output text for usable image URLs (handles Wikipedia HTML)."""
    if not mcp_output:
        return []
    text = ""
    for item in mcp_output.get("content", []) or []:
        if isinstance(item, dict):
            for k in ("text", "data"):
                v = item.get(k)
                if isinstance(v, str):
                    text += v + "\n"
    if not text:
        return []
    found: List[str] = []
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', text, flags=re.IGNORECASE):
        u = m.group(1)
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            u = "https://en.wikipedia.org" + u
        elif not u.startswith("http"):
            continue
        # Skip Wikipedia chrome/icon assets
        low = u.lower()
        if any(s in low for s in ("/static/images/", "magnify", "ambox", "edit-icon",
                                   "commons-logo", "wiktionary", "wikiquote",
                                   "wikidata", "wikinews", "puzzle", "mediaviewer-icon")):
            continue
        # Prefer larger thumbs (Wikipedia rasters end in /<n>px-…)
        if re.search(r"/\d+px-", low):
            pass  # keep
        if u not in found:
            found.append(u)
        if len(found) >= max_n:
            break
    return found


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
        raw_payload = json.dumps(mcp_output, default=str)[:5000]

    image_urls = _extract_image_urls(mcp_output) if mcp_output else []
    image_block = ""
    if image_urls:
        image_block = (
            "\nAvailable image URLs you may use (pick 0 or 1 for an image component):\n"
            + "\n".join(f"- {u}" for u in image_urls)
        )

    prompt = f"""You design a single full-bleed panel ("room") in Morph AI.
Be DISCIPLINED — show LITTLE content per slide. The user navigates between rooms,
so each room is one focused beat, not a dashboard.

User intent for this room:
"{intent_prompt}"

{"Parent room: " + parent_title if parent_title else ""}
{"MCP tool executed: " + mcp_tool if mcp_tool else "No MCP tool was run."}

Raw tool output (truncated, may be empty):
{raw_payload or "(none)"}{image_block}

Output ONE JSON object, no fences, matching this exact shape:

{LAYOUT_SCHEMA_TEXT}

Hard rules:
- Valid JSON parseable by json.loads.
- AT MOST 2 components. Prefer 1 if a single component conveys the idea.
- headline: 4-7 words, no period.
- headline_accent: leave null OR write a SHORT distinct phrase (3-6 words) that
  does NOT repeat any word from headline. NEVER echo the headline.
- body: <= 130 chars, ONE sentence, optional.
- Pick a vivid theme + accent_color that matches the topic emotionally.

Background gradient (REQUIRED — do not omit bg_from/bg_to):
- Pick bg_from, bg_to (and optionally bg_via) so the panel background reads as
  a unique mood for THIS topic. Subsequent rooms must look visually distinct
  from neighbors so navigating feels like stepping into a new place.
- Use vibrant but readable colors — they must hold white text at high contrast.
  Generally: deep / saturated / not pastel. Lightness ~ 12-32%.
- Different topic = different palette. A history room is NOT the same colour
  as a finance room. Two consecutive rooms should not share dominant hue.
- Examples (illustrative, do NOT copy):
    space    → bg_from "#0a0426" bg_to "#1c0d4d"
    forest   → bg_from "#062a1a" bg_to "#0f4d2c"
    sunset   → bg_from "#3a0a14" bg_to "#7a2410"
    arctic   → bg_from "#08263d" bg_to "#0f4863"
    earth    → bg_from "#241608" bg_to "#5a3210"

Component selection guidance:
- If image URLs are provided AND a relevant photo (not a logo/icon) exists,
  include EXACTLY ONE image component with src set to that URL verbatim.
  The frontend renders it inside a fixed-aspect tile that crops to fit, so
  any image works regardless of dimensions. NEVER invent URLs.
  If you include an image, it counts toward the 2-component limit.
- If you have numeric/quantitative data that varies (over time, across items,
  trends, distributions), use a `chart` — give it 8-24 plausible series values
  drawn from the source. A chart with a hero_value beats three stat cards.
- Use `stat_grid` for 2-3 distinct labeled numbers that DON'T form a series.
- Use `metric_block` for one hero number with a label.
- Use `list` for ranked items, names, dates, or short bullet titles.
- Use `text_block` ONLY when prose really is the best representation.

If no real data, invent plausible illustrative content — never apologize, never say "no data".
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


# ─── MERGED Prompt A+B ────────────────────────────────────────────────────

def _form_factor(w: Optional[int], h: Optional[int]) -> Tuple[str, str]:
    """Return (label, density-guidance text) for a viewport size."""
    if not w or w <= 0:
        return "unknown", "Assume a typical laptop screen."
    if w < 720:
        return "mobile", (
            "MOBILE viewport (~" + str(w) + "x" + str(h or "?") + "). "
            "Use AT MOST 1 component. Keep eyebrow ~3 words, headline 4-5 words, "
            "body 60-100 chars. stat_grid: 2 items max. list: 3 items max. "
            "Each label/title near the LOW end of its char cap. No tag_row unless trivial."
        )
    if w < 1280:
        return "laptop", (
            "LAPTOP viewport (~" + str(w) + "x" + str(h or "?") + "). "
            "1-2 components is fine. Body 80-130 chars. stat_grid up to 3 items, "
            "list up to 4. Aim for a balanced, breathable layout."
        )
    return "large", (
        "LARGE monitor (~" + str(w) + "x" + str(h or "?") + "). "
        "Comfortably fit 2 components. Body up to 130 chars. stat_grid up to 4 "
        "items, list up to 5. Slightly more decorative phrasing is OK."
    )


async def generate_full_node(
    *,
    intent_prompt: str,
    mcp_tool: Optional[str],
    mcp_output: Optional[Dict[str, Any]],
    parent_title: Optional[str] = None,
    history_titles: Optional[List[str]] = None,
    back_direction: Optional[Direction] = None,
    viewport_w: Optional[int] = None,
    viewport_h: Optional[int] = None,
    prefer_continuation_direction: Optional[Direction] = None,
    prefs: Optional[Prefs] = None,
) -> Tuple[NodeLayout, AdjacentIntents]:
    """One Gemini call that returns BOTH the room layout (Prompt B) and the
    next-direction intents (Prompt A). Saves a round-trip per navigate.

    Falls back to two separate calls if the merged response can't be parsed
    into FullNodeOutput (rare with strict response_mime_type=application/json,
    but kept for safety on the long tail)."""
    raw_payload = ""
    if mcp_output is not None:
        raw_payload = json.dumps(mcp_output, default=str)[:5000]

    image_urls = _extract_image_urls(mcp_output) if mcp_output else []
    image_block = ""
    if image_urls:
        image_block = (
            "\nAvailable image URLs (pick at most one for an inline image component):\n"
            + "\n".join(f"- {u}" for u in image_urls)
        )

    needed_dirs: List[Direction] = ["up", "down", "left", "right"]
    if back_direction:
        needed_dirs = [d for d in needed_dirs if d != back_direction]
    needed_str = ", ".join(needed_dirs)

    history_str = " → ".join((history_titles or [])[-6:]) or "(none)"
    form_label, form_guidance = _form_factor(viewport_w, viewport_h)
    prefs_block = _prefs_block(prefs)

    sticky_continue_block = ""
    if prefer_continuation_direction:
        sticky_continue_block = (
            f'\nSTICKY CONTINUE: the user reached this room by sliding '
            f'"{prefer_continuation_direction}" to continue a topic. If THIS '
            f'room would also benefit from a continuation, place is_continuation:true '
            f'on direction "{prefer_continuation_direction}" so the user can keep '
            f'sliding {prefer_continuation_direction} to read more. Do NOT put '
            f'is_continuation on a different direction.'
        )

    prompt = f"""You design ONE room (a full-bleed panel) in Morph AI AND its
next-direction intents in ONE response. Be DISCIPLINED — show LITTLE content
per slide. Each room is one focused beat.

Target viewport: {form_label}
{form_guidance}{prefs_block}

User intent for THIS room:
"{intent_prompt}"

{"Parent room: " + parent_title if parent_title else ""}
{"MCP tool executed: " + mcp_tool if mcp_tool else "No MCP tool was run."}

Raw tool output (truncated, may be empty):
{raw_payload or "(none)"}{image_block}

Recent navigation path: {history_str}{sticky_continue_block}

Available MCP tools (for the next-room intents):
{tool_descriptions_for_prompt()}

Output ONE JSON object with this exact shape, NO fences:

{{
  "layout": {LAYOUT_SCHEMA_TEXT},
  "intents": {INTENTS_SCHEMA_TEXT}
}}

═══════════════════════════════════════════════════════════════════════════
LAYOUT (the current room) rules:
- AT MOST 2 components. Prefer 1.
- ALL text fields have hard char caps (above). SUMMARIZE — do not truncate
  mid-word. Pick the most evocative phrasing within the cap.
- headline: 4-7 words, no period.
- headline_accent: leave null OR a SHORT distinct phrase that does NOT echo
  the headline.
- body: <= 130 chars, ONE sentence, optional.

Background:
- ALWAYS set bg_from + bg_to (and optionally bg_via) to a vibrant deep
  palette (lightness ~12-32%) that fits the topic emotionally. Each slide
  must look distinct from neighbours.
- If image URLs are provided AND a relevant one exists, set bg_image_url
  to that URL — DO NOT include an inline image component. The image will
  render as the panel background with your gradient as a tinted overlay.
- Never invent URLs.

Component selection:
- Numeric series / trend → chart (8-24 floats, hero_value beats stat cards).
- 2-3 distinct labelled numbers → stat_grid.
- One hero number → metric_block.
- Ranked items / names / dates → list (3-5 items).
- Prose only when nothing else fits → text_block.
- Tag_row for short keyword pills.

═══════════════════════════════════════════════════════════════════════════
INTENTS (the next rooms) rules:
- Generate intents for these directions ONLY: {needed_str}.
- Each one must be a meaningfully different next room, GROUNDED in THIS
  room's content (entities, themes, MCP output) — not generic ideas.
- label 1-2 words. sublabel < 64 chars.
- intent_prompt must be specific enough that an LLM can build the next
  room from it.
- If a relevant MCP tool fits, set mcp_tool; else null.
- If THIS room is clearly part 1 of a longer piece, mark EXACTLY ONE
  direction with is_continuation: true labelled "Continue".
- Avoid backtracking to recent path entries.

Output JSON only.
"""
    raw = await _generate_json(prompt, schema_hint="full_node")

    if not raw or "_stub" in raw or "_error" in raw:
        # Fall back to the two-stage path
        return await _two_stage_fallback(
            intent_prompt=intent_prompt, mcp_tool=mcp_tool, mcp_output=mcp_output,
            parent_title=parent_title, history_titles=history_titles or [],
            back_direction=back_direction, needed_dirs=needed_dirs,
        )

    try:
        full = FullNodeOutput.model_validate(raw)
    except ValidationError as e:
        logger.warning("merged node validation failed, falling back: %s", e)
        return await _two_stage_fallback(
            intent_prompt=intent_prompt, mcp_tool=mcp_tool, mcp_output=mcp_output,
            parent_title=parent_title, history_titles=history_titles or [],
            back_direction=back_direction, needed_dirs=needed_dirs,
        )

    # Defensive: ensure intents only cover the requested directions and
    # backfill any missing ones with stubs.
    seen: set = set()
    out_intents: List[IntentSignpost] = []
    for it in full.intents.intents:
        if it.direction in seen or it.direction not in needed_dirs:
            continue
        seen.add(it.direction)
        out_intents.append(it)
    for d in needed_dirs:
        if d not in seen:
            out_intents.append(_stub_intent_for(d))

    # Sticky-continue post-process: if the user just slid in direction D to
    # continue a topic, any continuation in this node MUST live on D too.
    if prefer_continuation_direction and prefer_continuation_direction in needed_dirs:
        cont_idx = next(
            (i for i, it in enumerate(out_intents) if it.is_continuation), None,
        )
        target_idx = next(
            (i for i, it in enumerate(out_intents)
             if it.direction == prefer_continuation_direction), None,
        )
        if cont_idx is not None and target_idx is not None and cont_idx != target_idx:
            cont_intent = out_intents[cont_idx]
            target_intent = out_intents[target_idx]
            # Move the continuation content onto the preferred direction; demote
            # whatever was there to non-continuation in the other slot.
            cont_intent_swapped = cont_intent.model_copy(
                update={"direction": prefer_continuation_direction},
            )
            target_intent_swapped = target_intent.model_copy(
                update={"direction": cont_intent.direction, "is_continuation": False},
            )
            out_intents[target_idx] = cont_intent_swapped
            out_intents[cont_idx] = target_intent_swapped

    return full.layout, AdjacentIntents(intents=out_intents)


async def _two_stage_fallback(
    *, intent_prompt: str, mcp_tool: Optional[str],
    mcp_output: Optional[Dict[str, Any]],
    parent_title: Optional[str], history_titles: List[str],
    back_direction: Optional[Direction], needed_dirs: List[Direction],
) -> Tuple[NodeLayout, AdjacentIntents]:
    layout = await generate_layout(
        intent_prompt=intent_prompt, mcp_tool=mcp_tool,
        mcp_output=mcp_output, parent_title=parent_title,
    )
    intents = await generate_adjacent_intents(
        current_layout=layout, current_title=layout.headline,
        history_titles=history_titles, back_direction=back_direction,
        back_target_title=parent_title,
        mcp_tool_executed=mcp_tool,
        mcp_output_summary=(json.dumps(mcp_output, default=str)[:1200]
                            if mcp_output else None),
    )
    return layout, intents


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
        elif t == "image":
            parts.append(f"image: {(c.caption or c.alt or 'figure')[:80]}")
        # else: unknown — ignore
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
