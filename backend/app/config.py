import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=True)

# OpenRouter configuration
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0"))

# JWT configuration - generate a default secret if not provided
_DEFAULT_JWT_SECRET = secrets.token_hex(32)


def get_jwt_secret() -> str:
    """Get the JWT secret from environment or use a generated default."""
    return os.getenv("JWT_SECRET", _DEFAULT_JWT_SECRET)


def check_jwt_secret() -> None:
    """Warn at startup if the JWT secret is shorter than the recommended 32 bytes."""
    import logging
    secret = get_jwt_secret()
    if len(secret.encode()) < 32:
        logging.warning(
            "JWT_SECRET is shorter than 32 bytes (%d bytes). "
            "Set a longer secret in .env for production use.",
            len(secret.encode()),
        )

# Database configuration
DEFAULT_USER = "user"
DEFAULT_BOARD_TITLE = "My Board"

# Initial seed data for new boards
INITIAL_COLUMNS = [
    ("Backlog", [
        ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
        ("Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    ]),
    ("Discovery", [
        ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    ]),
    ("In Progress", [
        ("Refine status language", "Standardize column labels and tone across the board."),
        ("Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    ]),
    ("Review", [
        ("QA micro-interactions", "Verify hover, focus, and loading states."),
    ]),
    ("Done", [
        ("Ship marketing page", "Final copy approved and asset pack delivered."),
        ("Close onboarding sprint", "Document release notes and share internally."),
    ]),
]


def get_db_path() -> Path:
    env_path = os.getenv("PM_DB_PATH", "").strip()
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[1] / "data" / "pm.db"


def resolve_static_dir() -> Path | None:
    env_dir = os.getenv("PM_STATIC_DIR", "").strip()
    candidates = [
        Path(env_dir) if env_dir else None,
        Path(__file__).resolve().parents[2] / "frontend" / "out",
        Path("/app/frontend/out"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def get_openrouter_api_key() -> str | None:
    return os.getenv("OPENROUTER_API_KEY")
