"""Master tool registry — flattened view of all MCP tools for LLM prompts."""
from __future__ import annotations

from typing import Any, Dict, List

from .mcp_client import bridge


def master_tool_list() -> List[Dict[str, Any]]:
    """Return tools in a compact form suitable for embedding in LLM prompts."""
    return [
        {
            "qualified_name": t["qualified_name"],
            "server": t["server"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in bridge.list_tools()
    ]


def tool_descriptions_for_prompt() -> str:
    """Compact bulleted text representation of all tools."""
    tools = master_tool_list()
    if not tools:
        return "(no MCP tools connected — generate plausible content from general knowledge)"
    lines = []
    for t in tools:
        # Trim input schema to property names only — keeps prompt small.
        props = ((t.get("input_schema") or {}).get("properties") or {})
        prop_names = ", ".join(props.keys()) or "(no params)"
        desc = (t["description"] or "").strip().replace("\n", " ")
        if len(desc) > 140:
            desc = desc[:137] + "…"
        lines.append(f'- {t["qualified_name"]}({prop_names}): {desc}')
    return "\n".join(lines)
