"""Application configuration - reads environment variables."""
import os

APP_NAME = "Flow"
API_PREFIX = "/api"

# --- Database ---
# DB_MODE: "sqlite" (default, zero-config local dev) or "oracle" (Oracle Cloud / Autonomous DB)
DB_MODE = os.getenv("DB_MODE", "sqlite")

SQLITE_PATH = os.getenv("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "flow.db"))

# Oracle Cloud (Autonomous DB) settings - required when DB_MODE=oracle
ORACLE_USER = os.getenv("ORACLE_DB_USER", "")
ORACLE_PASSWORD = os.getenv("ORACLE_DB_PASSWORD", "")
# Either a full DSN or host/port/service
ORACLE_DSN = os.getenv("ORACLE_DB_DSN", "")  # e.g. "host:1522/servicename_tp"
ORACLE_HOST = os.getenv("ORACLE_DB_HOST", "")
ORACLE_PORT = os.getenv("ORACLE_DB_PORT", "1522")
ORACLE_SERVICE = os.getenv("ORACLE_DB_SERVICE", "")
# Wallet directory for mTLS (Autonomous Database default) - set ORACLE_DB_WALLET_DIR if using wallets
ORACLE_WALLET_DIR = os.getenv("ORACLE_DB_WALLET_DIR", "")
ORACLE_WALLET_PASSWORD = os.getenv("ORACLE_DB_WALLET_PASSWORD", "")

# --- Auth ---
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-please")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(60 * 24 * 30)))  # 30 days
