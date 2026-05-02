"""App-wide config from env."""
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/morph.db")
CORS_ORIGINS = [
    o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",") if o.strip()
]
CONFIG_YAML_PATH = os.getenv("CONFIG_YAML_PATH", "/app/config.yaml")
