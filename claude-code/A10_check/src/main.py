import json
import logging
import signal
import sqlite3
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

import schedule

from src.config import settings
from src.modules.a10_client import A10Client
from src.modules.report import analyze_logs, print_log_report, save_log_report

# ── 로깅 초기화 ────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    """콘솔 + 파일(로테이션) 핸들러를 설정한다."""
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = settings.LOG_DIR / "a10_monitor.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 파일 핸들러: 10MB 초과 시 롤오버, 최대 5개 보관
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        handlers=[file_handler, console_handler],
    )

logger = logging.getLogger(__name__)

# ── DB 초기화 ──────────────────────────────────────────────────────────────────

def _init_db() -> None:
    """SQLite3 DB와 점검 결과 테이블을 생성한다."""
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inspection_results (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at    TEXT    NOT NULL,
                host          TEXT    NOT NULL,
                system_info   TEXT,
                cpu_usage     TEXT,
                memory_usage  TEXT,
                interface_stats   TEXT,
                slb_servers   TEXT,
                log_summary   TEXT,
                danger_count  INTEGER DEFAULT 0,
                status        TEXT    NOT NULL DEFAULT 'ok'
            )
        """)
        # 보관 기간 초과 레코드 삭제
        conn.execute(
            "DELETE FROM inspection_results WHERE checked_at < datetime('now', ?)",
            (f"-{settings.DB_RETENTION_DAYS} days",),
        )
        conn.commit()
    logger.info("DB 초기화 완료: %s", settings.DB_PATH)


def _save_to_db(record: dict) -> None:
    """점검 결과 한 건을 DB에 저장한다."""
    try:
        with sqlite3.connect(settings.DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO inspection_results
                    (checked_at, host, system_info, cpu_usage, memory_usage,
                     interface_stats, slb_servers, log_summary, danger_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["checked_at"],
                    record["host"],
                    json.dumps(record.get("system_info"), ensure_ascii=False),
                    json.dumps(record.get("cpu_usage"), ensure_ascii=False),
                    json.dumps(record.get("memory_usage"), ensure_ascii=False),
                    json.dumps(record.get("interface_stats"), ensure_ascii=False),
                    json.dumps(record.get("slb_servers"), ensure_ascii=False),
                    json.dumps(record.get("log_summary"), ensure_ascii=False),
                    record.get("danger_count", 0),
                    record.get("status", "ok"),
                ),
            )
            conn.commit()
        logger.info("점검 결과 DB 저장 완료")
    except sqlite3.Error as e:
        logger.error("DB 저장 실패: %s", e)

# ── 점검 실행 ──────────────────────────────────────────────────────────────────

def run_inspection() -> None:
    """A10 ADC 전체 점검을 실행하고 결과를 저장·출력한다."""
    checked_at = datetime.now().isoformat()
    host = settings.A10_HOST
    logger.info("===== 점검 시작 [%s] =====", host)

    client = A10Client()
    record: dict = {"checked_at": checked_at, "host": host, "status": "ok"}

    # ── 로그인 ────────────────────────────────────────────────────────────────
    try:
        ok = client.login()
        if not ok:
            logger.error("ADC 로그인 실패 — 점검 중단")
            record["status"] = "login_failed"
            _save_to_db(record)
            return
    except Exception as e:
        logger.error("로그인 중 예외 발생: %s", e)
        record["status"] = "error"
        _save_to_db(record)
        return

    # ── 상태 수집 ─────────────────────────────────────────────────────────────
    collectors = {
        "system_info":    client.get_system_info,
        "cpu_usage":      client.get_cpu_usage,
        "memory_usage":   client.get_memory_usage,
        "interface_stats": client.get_interface_stats,
        "slb_servers":    client.get_slb_virtual_servers,
    }

    for key, func in collectors.items():
        try:
            record[key] = func()
            logger.info("%s 수집 완료", key)
        except Exception as e:
            logger.error("%s 수집 실패: %s", key, e)
            record[key] = None
            record["status"] = "partial"

    # ── 로그 수집 및 분석 ─────────────────────────────────────────────────────
    try:
        logs = client.get_logs()
        analysis = analyze_logs(logs)
        record["log_summary"] = analysis["summary"]
        record["danger_count"] = len(analysis["danger"])

        # 터미널 컬러 리포트 출력
        print_log_report(analysis)

        # JSON 파일로 저장
        report_path = save_log_report(analysis, host)
        logger.info("로그 리포트 저장: %s", report_path)
    except Exception as e:
        logger.error("로그 수집/분석 실패: %s", e)
        record["log_summary"] = None
        record["danger_count"] = 0

    # ── 로그아웃 ──────────────────────────────────────────────────────────────
    try:
        client.logout()
    except Exception as e:
        logger.warning("로그아웃 중 오류 (무시): %s", e)

    # ── DB 저장 ───────────────────────────────────────────────────────────────
    _save_to_db(record)
    logger.info("===== 점검 완료 [상태: %s] =====", record["status"])

# ── 스케줄러 ──────────────────────────────────────────────────────────────────

def _setup_schedule() -> None:
    """settings에 정의된 시각에 매일 점검을 실행하도록 등록한다."""
    run_time = f"{settings.SCHEDULE_HOUR:02d}:{settings.SCHEDULE_MINUTE:02d}"
    schedule.every().day.at(run_time).do(run_inspection)
    logger.info("점검 스케줄 등록 완료 — 매일 %s 실행", run_time)


def _handle_signal(signum, frame) -> None:
    """SIGINT / SIGTERM 수신 시 안전하게 종료한다."""
    logger.info("종료 신호 수신 (%s) — 프로그램을 종료합니다.", signal.Signals(signum).name)
    sys.exit(0)

# ── 진입점 ────────────────────────────────────────────────────────────────────

def main() -> None:
    _setup_logging()
    logger.info("A10 ADC 점검 자동화 시작")

    _init_db()
    _setup_schedule()

    # 종료 시그널 핸들러 등록
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # 즉시 1회 실행 후 스케줄 루프 대기
    logger.info("초기 점검을 즉시 실행합니다.")
    run_inspection()

    logger.info("스케줄 대기 중 (Ctrl+C로 종료)")
    while True:
        schedule.run_pending()
        time.sleep(30)  # 30초마다 스케줄 체크


if __name__ == "__main__":
    main()
