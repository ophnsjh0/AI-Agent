#!/usr/bin/env python3
"""DB에 저장된 점검 결과를 터미널에 출력한다."""

import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "a10_monitor.db"

_C = {
    "RESET":  "\033[0m",
    "BOLD":   "\033[1m",
    "CYAN":   "\033[96m",
    "GREEN":  "\033[92m",
    "YELLOW": "\033[93m",
    "RED":    "\033[91m",
    "DIM":    "\033[2m",
}

def _status_color(status: str) -> str:
    if status == "ok":
        return f"{_C['GREEN']}{status}{_C['RESET']}"
    if status == "partial":
        return f"{_C['YELLOW']}{status}{_C['RESET']}"
    return f"{_C['RED']}{status}{_C['RESET']}"

def _mem_mb(mem_json: str | None) -> str:
    if not mem_json:
        return "-"
    try:
        mem = json.loads(mem_json)
        total_kb = mem.get("Total", 0)
        return f"{total_kb // 1024:,} MB"
    except Exception:
        return "-"

def _iface_summary(iface_json: str | None) -> str:
    if not iface_json:
        return "-"
    try:
        ifaces = json.loads(iface_json)
        parts = []
        for i in ifaces:
            s = i.get("stats", {})
            parts.append(f"eth{i['ifnum']}(in:{s.get('packets_input',0)} out:{s.get('packets_output',0)})")
        return "  ".join(parts)
    except Exception:
        return "-"

def _slb_summary(slb_json: str | None) -> str:
    if not slb_json:
        return "-"
    try:
        vs_list = json.loads(slb_json)
        return f"{len(vs_list)}개 / " + ", ".join(v.get("oper", {}).get("state", "?") for v in vs_list)
    except Exception:
        return "-"

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    if not DB_PATH.exists():
        print(f"DB 없음: {DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM inspection_results ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    if not rows:
        print("저장된 점검 결과가 없습니다.")
        return

    width = 90
    print(f"\n{_C['BOLD']}{_C['CYAN']}{'═' * width}{_C['RESET']}")
    print(f"{_C['BOLD']}{_C['CYAN']}  A10 ADC 점검 결과 (최근 {limit}건)  ←  {DB_PATH}{_C['RESET']}")
    print(f"{_C['BOLD']}{_C['CYAN']}{'═' * width}{_C['RESET']}\n")

    for row in rows:
        r = dict(row)
        print(f"{_C['BOLD']}[#{r['id']}]  {r['checked_at']}  {r['host']}  상태: {_status_color(r['status'])}  위험로그: {r['danger_count']}건{_C['RESET']}")
        print(f"  {_C['DIM']}메모리  :{_C['RESET']} {_mem_mb(r['memory_usage'])}")
        print(f"  {_C['DIM']}인터페이스:{_C['RESET']} {_iface_summary(r['interface_stats'])}")
        print(f"  {_C['DIM']}SLB    :{_C['RESET']} {_slb_summary(r['slb_servers'])}")

        log_summary = json.loads(r['log_summary']) if r['log_summary'] else {}
        if log_summary:
            parts = [f"{lvl}:{cnt}" for lvl, cnt in log_summary.items()]
            print(f"  {_C['DIM']}로그요약 :{_C['RESET']} {', '.join(parts)}")
        print()

    print(f"{_C['DIM']}총 {len(rows)}건 표시  (더 보려면: python src/db_status.py <건수>){_C['RESET']}\n")

if __name__ == "__main__":
    main()
