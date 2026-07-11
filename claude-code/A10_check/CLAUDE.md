# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 프로젝트: A10 ADC 점검 자동화

매일 정해진 시간에 A10 ADC 상태를 점검하고 결과를 리포팅하는 자동화 시스템.

## 실행 방법

```bash
python src/main.py
```

## 기술 스택

- Python 3.11, requests, sqlite3
- A10 REST API (불가 시 CLI fallback)

## 아키텍처

```
src/
  ├── main.py          # 진입점: 스케줄링 및 전체 흐름 제어
  ├── modules/
  │   ├── a10_client.py  # A10 ADC 인증·REST API·CLI 호출 담당
  │   └── report.py      # 점검 결과 포맷팅 및 리포트 생성
  └── config/
      └── settings.py    # 장비 접속 정보, 스케줄, DB 경로 등 설정
```

**흐름:** `main.py` → `a10_client.py`로 로그인 및 상태 수집 → `report.py`로 결과 포맷 → sqlite3 DB 저장 및 리포트 출력

`a10_client.py`는 REST API를 우선 시도하고, 실패 시 CLI로 fallback한다.

## 코딩 규칙

- 주석은 한글로 작성
- 모든 외부 호출(REST, CLI, DB)에 에러 처리 필수
- DB는 sqlite3 사용 (별도 서버 불필요)
