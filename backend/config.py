import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]
SUPABASE_JWT_SECRET: str = os.environ["SUPABASE_JWT_SECRET"]
