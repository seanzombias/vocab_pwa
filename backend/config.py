import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOCAL_DB_PATH = DATA_DIR / "vocab.db"

PORT = int(os.getenv("PORT", "8765"))
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
VOCAB_API_TOKEN = os.getenv("VOCAB_API_TOKEN", "dev-token-change-me")

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()

DEFAULT_ORIGINS = "https://seanzombias.github.io,http://localhost:8080,http://127.0.0.1:8080,http://localhost:8765"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]


def use_turso() -> bool:
    return bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


def normalize_turso_url(url: str) -> str:
    """libsql_client expects https:// host URLs."""
    url = url.strip()
    if url.startswith("libsql://"):
        return "https://" + url[len("libsql://") :]
    return url
