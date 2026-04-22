import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 참조 (backend/ 한 단계 위)
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL: str = os.environ["DATABASE_URL"]
SUPABASE_URL: str = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]
