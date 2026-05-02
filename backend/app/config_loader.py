"""Load config.yaml describing MCP servers to bridge."""
from __future__ import annotations

import os
from typing import List, Literal, Optional

import yaml
from pydantic import BaseModel

from .config import CONFIG_YAML_PATH


class MCPServerConfig(BaseModel):
    name: str
    transport: Literal["stdio", "sse", "http"] = "stdio"
    command: Optional[str] = None
    args: List[str] = []
    url: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True


class AppConfig(BaseModel):
    mcp_servers: List[MCPServerConfig] = []


def load_config() -> AppConfig:
    path = CONFIG_YAML_PATH if os.path.exists(CONFIG_YAML_PATH) else "./config.yaml"
    if not os.path.exists(path):
        return AppConfig()
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)
