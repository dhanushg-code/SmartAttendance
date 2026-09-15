"""Application settings loaded from environment (.env) variables."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "").strip()

# When True the app runs without a scanner / Supabase using in-memory mocks.
DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").strip().lower() in ("1", "true", "yes")

# Reports directory for generated .xlsx files (spec section 9).
REPORTS_DIR: Path = PROJECT_ROOT / "reports"

APP_NAME: str = "SmartAttend"

# SMTP settings for staff email notifications (spec: alerts for upcoming periods)
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM: str = os.getenv("SMTP_FROM", "").strip() or SMTP_USER
SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").strip().lower() in ("1", "true", "yes")


def validate() -> list[str]:
    """Return a list of configuration problems (empty list = OK)."""
    problems: list[str] = []
    if not DEMO_MODE:
        if not SUPABASE_URL:
            problems.append("SUPABASE_URL is not set in .env")
        if not SUPABASE_KEY:
            problems.append("SUPABASE_KEY is not set in .env")
    return problems
