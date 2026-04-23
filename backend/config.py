import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 참조 (backend/ 한 단계 위)
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL: str = os.environ["DATABASE_URL"]
SUPABASE_URL: str = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]


def get_cors_allow_origins() -> list[str]:
    raw_origins = os.environ.get(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://localhost:4173,http://localhost:8082,http://localhost:19006",
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
