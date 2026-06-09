from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_FX_PATH = BASE_DIR / "data" / "sample_fx.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"

FRANKFURTER_BASE = "https://api.frankfurter.dev"
DEFAULT_FROM = "EUR"
DEFAULT_TO = "USD"

CACHE_TTL_SECONDS = 300
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 0.5
