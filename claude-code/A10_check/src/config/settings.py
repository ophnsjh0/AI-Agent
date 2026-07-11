import os
from pathlib import Path

# ── 기본 경로 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── A10 ADC 연결 정보 ──────────────────────────────────────────────────────────
A10_HOST = os.getenv("A10_HOST", "192.168.74.136")
A10_PORT = int(os.getenv("A10_PORT", "443"))
A10_USERNAME = os.getenv("A10_USERNAME", "admin")
A10_PASSWORD = os.getenv("A10_PASSWORD", "a10")
A10_VERIFY_SSL = os.getenv("A10_VERIFY_SSL", "false").lower() == "true"

# ── API 요청 옵션 ──────────────────────────────────────────────────────────────
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "10"))  # 초
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))  # 초

# ── CLI Fallback (REST API 실패 시 SSH로 직접 명령 실행) ───────────────────────
A10_CLI_PATH = os.getenv("A10_CLI_PATH", "/usr/bin/acos_cli")
A10_SSH_PORT = int(os.getenv("A10_SSH_PORT", "22"))
A10_SSH_KEY_PATH = os.getenv("A10_SSH_KEY_PATH", "")

# ── 스케줄 설정 (매일 1회 정시 실행) ──────────────────────────────────────────
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "8"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Seoul")

# ── 데이터베이스 (SQLite3) ─────────────────────────────────────────────────────
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "a10_monitor.db")))
DB_RETENTION_DAYS = int(os.getenv("DB_RETENTION_DAYS", "90"))  # 보관 기간(일)

# ── 리포트 ────────────────────────────────────────────────────────────────────
REPORT_OUTPUT_DIR = Path(os.getenv("REPORT_OUTPUT_DIR", str(BASE_DIR / "reports")))
REPORT_FORMAT = os.getenv("REPORT_FORMAT", "json")  # json | csv | html

# ── 로깅 ──────────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))
