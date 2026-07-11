import json
import logging
import re
from datetime import datetime
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)

# ── ANSI 컬러 코드 ─────────────────────────────────────────────────────────────
_C = {
    "RESET":   "\033[0m",
    "BOLD":    "\033[1m",
    "RED":     "\033[91m",
    "YELLOW":  "\033[93m",
    "CYAN":    "\033[96m",
    "GREEN":   "\033[92m",
    "MAGENTA": "\033[95m",
    "WHITE":   "\033[97m",
    "DIM":     "\033[2m",
    "BG_RED":  "\033[41m",
}

# ── 로그 레벨 분류 기준 ────────────────────────────────────────────────────────
# 심각도 순서: CRITICAL > ERROR > WARNING > INFO > DEBUG > UNKNOWN
_LEVEL_RANK = {
    "EMERGENCY": 0,
    "ALERT":     1,
    "CRITICAL":  2,
    "ERROR":     3,
    "ERR":       3,  # syslog 약어
    "WARNING":   4,
    "WARN":      4,
    "NOTICE":    5,
    "INFO":      6,
    "DEBUG":     7,
    "UNKNOWN":   8,
}

# 메시지 본문에서 추가로 탐지할 위험 키워드
_DANGER_KEYWORDS = re.compile(r"\b(error|fail|failure|failed|critical|down|drop|denied|timeout)\b", re.IGNORECASE)


# ── 공개 함수 ─────────────────────────────────────────────────────────────────

def analyze_logs(logs: list[dict]) -> dict:
    """
    로그 목록을 분류하고 위험 항목을 추출한다.

    반환 구조:
        {
            "total": int,
            "by_level": { "ERROR": [...], "WARNING": [...], ... },
            "danger": [...],   # 레벨이 ERROR 이상이거나 위험 키워드 포함
            "summary": { "ERROR": count, ... }
        }
    """
    by_level: dict[str, list[dict]] = {}
    danger: list[dict] = []

    for entry in logs:
        # 레벨 정규화 (ERR → ERROR, WARN → WARNING 등)
        raw_level = entry.get("level", "UNKNOWN").upper()
        level = _normalize_level(raw_level)
        entry = {**entry, "level": level}  # 정규화된 레벨로 교체

        by_level.setdefault(level, []).append(entry)

        # 위험 항목 판정: 레벨이 ERROR 이상이거나 메시지에 위험 키워드 존재
        rank = _LEVEL_RANK.get(level, 8)
        has_keyword = bool(_DANGER_KEYWORDS.search(entry.get("message", "")))
        if rank <= _LEVEL_RANK["ERROR"] or has_keyword:
            danger.append(entry)

    summary = {lvl: len(items) for lvl, items in sorted(by_level.items(), key=lambda x: _LEVEL_RANK.get(x[0], 9))}

    return {
        "total":    len(logs),
        "by_level": by_level,
        "danger":   danger,
        "summary":  summary,
    }


def print_log_report(analysis: dict) -> None:
    """분석 결과를 터미널에 컬러로 출력한다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    width = 70

    # ── 헤더 ─────────────────────────────────────────────────────────────────
    print(f"\n{_C['BOLD']}{_C['CYAN']}{'═' * width}{_C['RESET']}")
    print(f"{_C['BOLD']}{_C['CYAN']}  A10 ADC 로그 분석 리포트   {now}{_C['RESET']}")
    print(f"{_C['BOLD']}{_C['CYAN']}{'═' * width}{_C['RESET']}\n")

    # ── 요약 통계 ─────────────────────────────────────────────────────────────
    print(f"{_C['BOLD']}[ 레벨별 요약 ]  총 {analysis['total']}건{_C['RESET']}")
    for level, count in analysis["summary"].items():
        bar = _level_bar(level, count, analysis["total"])
        label = f"{_level_colored(level):<30}"
        print(f"  {label} {bar}  {count}건")
    print()

    # ── 위험 항목 강조 출력 ───────────────────────────────────────────────────
    danger = analysis["danger"]
    if danger:
        print(f"{_C['BOLD']}{_C['BG_RED']}{_C['WHITE']}  ⚠  주의 필요 항목  ({len(danger)}건)  {_C['RESET']}")
        print(f"{_C['DIM']}{'─' * width}{_C['RESET']}")
        for entry in danger:
            _print_danger_entry(entry)
        print()
    else:
        print(f"{_C['GREEN']}{_C['BOLD']}  ✓ 위험 로그 없음{_C['RESET']}\n")

    # ── 전체 로그 (레벨별 그룹) ───────────────────────────────────────────────
    print(f"{_C['BOLD']}[ 전체 로그 ]{_C['RESET']}")
    print(f"{_C['DIM']}{'─' * width}{_C['RESET']}")
    for level, entries in sorted(analysis["by_level"].items(), key=lambda x: _LEVEL_RANK.get(x[0], 9)):
        print(f"\n  {_level_colored(level)}  ({len(entries)}건)")
        for e in entries:
            ts  = f"{_C['DIM']}{e.get('timestamp', ''):<18}{_C['RESET']}"
            src = f"{_C['DIM']}[{e.get('source', '')}]{_C['RESET']}"
            msg = _highlight_keywords(e.get("message", ""))
            print(f"    {ts} {src} {msg}")

    print(f"\n{_C['DIM']}{'═' * width}{_C['RESET']}\n")


def save_log_report(analysis: dict, host: str) -> Path:
    """분석 결과를 JSON 파일로 저장하고 경로를 반환한다."""
    settings.REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = settings.REPORT_OUTPUT_DIR / f"log_report_{host}_{ts}.json"

    payload = {
        "generated_at": datetime.now().isoformat(),
        "host":         host,
        "total":        analysis["total"],
        "summary":      analysis["summary"],
        "danger_count": len(analysis["danger"]),
        "danger":       analysis["danger"],
        "by_level":     {lvl: items for lvl, items in analysis["by_level"].items()},
    }

    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("로그 리포트 저장 완료: %s", path)
    except OSError as e:
        logger.error("로그 리포트 저장 실패: %s", e)
        raise

    return path


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _normalize_level(level: str) -> str:
    """syslog 약어를 통일된 레벨명으로 변환한다."""
    mapping = {"ERR": "ERROR", "WARN": "WARNING", "EMERG": "EMERGENCY", "CRIT": "CRITICAL"}
    return mapping.get(level, level)


def _level_colored(level: str) -> str:
    """레벨명에 심각도에 맞는 컬러를 적용한다."""
    rank = _LEVEL_RANK.get(level, 8)
    if rank <= 2:   # EMERGENCY ~ CRITICAL
        return f"{_C['BOLD']}{_C['BG_RED']}{_C['WHITE']} {level} {_C['RESET']}"
    if rank == 3:   # ERROR
        return f"{_C['BOLD']}{_C['RED']} {level} {_C['RESET']}"
    if rank == 4:   # WARNING
        return f"{_C['BOLD']}{_C['YELLOW']} {level} {_C['RESET']}"
    if rank == 5:   # NOTICE
        return f"{_C['MAGENTA']} {level} {_C['RESET']}"
    if rank == 6:   # INFO
        return f"{_C['CYAN']} {level} {_C['RESET']}"
    return f"{_C['DIM']} {level} {_C['RESET']}"


def _highlight_keywords(message: str) -> str:
    """메시지 내 위험 키워드를 빨간색으로 강조한다."""
    return _DANGER_KEYWORDS.sub(
        lambda m: f"{_C['BOLD']}{_C['RED']}{m.group()}{_C['RESET']}",
        message,
    )


def _level_bar(level: str, count: int, total: int) -> str:
    """레벨 비율을 나타내는 ASCII 막대를 반환한다."""
    bar_width = 20
    filled = round(bar_width * count / total) if total else 0
    rank = _LEVEL_RANK.get(level, 8)
    color = _C["RED"] if rank <= 3 else (_C["YELLOW"] if rank == 4 else _C["DIM"])
    return f"{color}{'█' * filled}{'░' * (bar_width - filled)}{_C['RESET']}"


def _print_danger_entry(entry: dict) -> None:
    """위험 항목 1건을 강조 형식으로 출력한다."""
    level = entry.get("level", "")
    ts    = entry.get("timestamp", "")
    src   = entry.get("source", "")
    msg   = _highlight_keywords(entry.get("message", ""))
    rank  = _LEVEL_RANK.get(level, 8)

    prefix = f"{_C['BOLD']}{_C['RED']}▶{_C['RESET']}" if rank <= 3 else f"{_C['BOLD']}{_C['YELLOW']}▷{_C['RESET']}"
    print(f"  {prefix} {_level_colored(level)} {_C['DIM']}{ts}  [{src}]{_C['RESET']}")
    print(f"      {msg}")
