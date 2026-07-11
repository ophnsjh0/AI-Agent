import logging
import subprocess
import time

import requests
import urllib3

from src.config import settings

# SSL 경고 억제 (verify=False 사용 시)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class A10Client:
    """A10 ADC REST API 클라이언트 (실패 시 CLI fallback)"""

    def __init__(self):
        self.base_url = f"https://{settings.A10_HOST}:{settings.A10_PORT}/axapi/v3"
        self.session = requests.Session()
        self.session.verify = settings.A10_VERIFY_SSL
        self._auth_token: str | None = None

    # ── 공개 인터페이스 ────────────────────────────────────────────────────────

    def login(self) -> bool:
        """ADC에 로그인하고 인증 토큰을 획득한다."""
        try:
            return self._rest_login()
        except Exception as e:
            logger.warning("REST 로그인 실패, CLI로 연결 확인: %s", e)
            return self._cli_check_reachable()

    def get_system_info(self) -> dict:
        """시스템 기본 정보(모델, 펌웨어 버전 등)를 반환한다."""
        return self._call_with_fallback(
            rest_func=self._rest_get_system_info,
            cli_func=self._cli_get_system_info,
            name="시스템 정보",
        )

    def get_cpu_usage(self) -> dict:
        """CPU 사용률 정보를 반환한다."""
        return self._call_with_fallback(
            rest_func=self._rest_get_cpu_usage,
            cli_func=self._cli_get_cpu_usage,
            name="CPU 사용률",
        )

    def get_memory_usage(self) -> dict:
        """메모리 사용률 정보를 반환한다."""
        return self._call_with_fallback(
            rest_func=self._rest_get_memory_usage,
            cli_func=self._cli_get_memory_usage,
            name="메모리 사용률",
        )

    def get_interface_stats(self) -> list[dict]:
        """전체 인터페이스 통계를 반환한다."""
        return self._call_with_fallback(
            rest_func=self._rest_get_interface_stats,
            cli_func=self._cli_get_interface_stats,
            name="인터페이스 통계",
        )

    def get_slb_virtual_servers(self) -> list[dict]:
        """SLB 가상 서버 목록과 상태를 반환한다."""
        return self._call_with_fallback(
            rest_func=self._rest_get_slb_virtual_servers,
            cli_func=self._cli_get_slb_virtual_servers,
            name="SLB 가상 서버",
        )

    def get_logs(self, limit: int = 200) -> list[dict]:
        """시스템 로그를 조회한다. REST 실패 시 CLI의 'show log'로 fallback."""
        return self._call_with_fallback(
            rest_func=lambda: self._rest_get_logs(limit),
            cli_func=lambda: self._cli_get_logs(limit),
            name="시스템 로그",
        )

    def logout(self) -> None:
        """인증 세션을 종료한다."""
        if not self._auth_token:
            return
        try:
            self.session.post(f"{self.base_url}/logoff", timeout=settings.CONNECTION_TIMEOUT)
            logger.info("REST 로그아웃 완료")
        except Exception as e:
            logger.warning("로그아웃 중 오류 (무시): %s", e)
        finally:
            self._auth_token = None

    # ── REST API 구현 ──────────────────────────────────────────────────────────

    def _rest_login(self) -> bool:
        """REST API로 로그인하고 Authorization 헤더를 설정한다."""
        payload = {
            "credentials": {
                "username": settings.A10_USERNAME,
                "password": settings.A10_PASSWORD,
            }
        }
        resp = self._rest_request("POST", "/auth", json=payload, auth_required=False)
        token = resp.get("authresponse", {}).get("signature")
        if not token:
            raise ValueError("인증 토큰을 받지 못했습니다.")
        self._auth_token = token
        self.session.headers.update({"Authorization": f"A10 {token}"})
        logger.info("REST 로그인 성공 (host=%s)", settings.A10_HOST)
        return True

    def _rest_get_system_info(self) -> dict:
        resp = self._rest_request("GET", "/version/oper")
        return resp.get("version", {}).get("oper", {})

    def _rest_get_cpu_usage(self) -> dict:
        # vThunder는 data-cpu/control-cpu oper 모두 204(빈 응답) 반환
        data = self._rest_request("GET", "/system/data-cpu/oper")
        ctrl = self._rest_request("GET", "/system/control-cpu/oper")
        result = {}
        if data:
            result["data-cpu"] = data.get("data-cpu", {}).get("oper", data)
        if ctrl:
            result["control-cpu"] = ctrl.get("control-cpu", {}).get("oper", ctrl)
        if not result:
            raise RuntimeError("CPU 데이터 없음 (vThunder REST 미지원)")
        return result

    def _rest_get_memory_usage(self) -> dict:
        resp = self._rest_request("GET", "/system/memory/oper")
        return resp.get("memory", {}).get("oper", {})

    def _rest_get_interface_stats(self) -> list[dict]:
        # 인터페이스 목록 조회 후 각 포트 stats 개별 수집
        iface_resp = self._rest_request("GET", "/interface/ethernet")
        ifaces = iface_resp.get("ethernet-list", [])
        result = []
        for iface in ifaces:
            ifnum = iface.get("ifnum")
            try:
                stats_resp = self._rest_request("GET", f"/interface/ethernet/{ifnum}/stats")
                stats = stats_resp.get("ethernet", {}).get("stats", {})
                result.append({"ifnum": ifnum, "stats": stats})
            except Exception as e:
                logger.warning("인터페이스 %s stats 조회 실패: %s", ifnum, e)
                result.append({"ifnum": ifnum, "stats": {}})
        return result

    def _rest_get_slb_virtual_servers(self) -> list[dict]:
        resp = self._rest_request("GET", "/slb/virtual-server/oper")
        return resp.get("virtual-server-list", [])

    def _rest_get_logs(self, limit: int) -> list[dict]:
        """REST API로 syslog 항목을 조회한다."""
        import re
        resp = self._rest_request("GET", "/syslog/oper")
        raw_entries = resp.get("syslog", {}).get("oper", {}).get("system-log", [])
        # 형식: "May 13 2026 16:03:47 Notice      [FACILITY]:메시지"
        pattern = re.compile(
            r"(?P<timestamp>\w+\s+\d+\s+\d{4}\s+[\d:]+)\s+"
            r"(?P<level>\w+)\s+"
            r"(?:\[(?P<facility>[^\]]+)\]:)?"
            r"(?P<message>.+)"
        )
        result = []
        for e in raw_entries[-limit:]:
            line = e.get("log-data", "").strip()
            m = pattern.match(line)
            if m:
                result.append({
                    "timestamp": m.group("timestamp"),
                    "level":     m.group("level").upper(),
                    "facility":  m.group("facility") or "",
                    "message":   m.group("message").strip(),
                    "source":    "rest",
                })
            elif line:
                result.append({"timestamp": "", "level": "UNKNOWN", "facility": "", "message": line, "source": "rest"})
        return result

    def _rest_request(self, method: str, path: str, *, auth_required: bool = True, **kwargs) -> dict:
        """재시도 로직을 포함한 REST 요청 공통 처리."""
        if auth_required and not self._auth_token:
            raise RuntimeError("로그인 후 호출해야 합니다.")

        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                resp = self.session.request(
                    method, url, timeout=settings.CONNECTION_TIMEOUT, **kwargs
                )
                resp.raise_for_status()
                if resp.status_code == 204 or not resp.content:
                    return {}
                return resp.json()
            except requests.exceptions.RequestException as e:
                last_exc = e
                logger.debug("REST 요청 실패 (%d/%d): %s", attempt, settings.MAX_RETRIES, e)
                if attempt < settings.MAX_RETRIES:
                    time.sleep(settings.RETRY_DELAY)

        raise ConnectionError(f"REST 요청 최종 실패 [{method} {path}]: {last_exc}") from last_exc

    # ── CLI Fallback 구현 ──────────────────────────────────────────────────────

    def _cli_check_reachable(self) -> bool:
        """CLI로 장비 접근 가능 여부만 확인한다 (ping 수준)."""
        try:
            result = self._cli_run("show version")
            reachable = len(result) > 0
            if reachable:
                logger.info("CLI 연결 성공 (host=%s)", settings.A10_HOST)
            return reachable
        except Exception as e:
            logger.error("CLI 연결 실패: %s", e)
            return False

    def _cli_get_system_info(self) -> dict:
        output = self._cli_run("show version")
        return {"raw": output, "source": "cli"}

    def _cli_get_cpu_usage(self) -> dict:
        output = self._cli_run("show cpu")
        return {"raw": output, "source": "cli"}

    def _cli_get_memory_usage(self) -> dict:
        output = self._cli_run("show memory")
        return {"raw": output, "source": "cli"}

    def _cli_get_interface_stats(self) -> list[dict]:
        output = self._cli_run("show interface brief")
        return [{"raw": output, "source": "cli"}]

    def _cli_get_slb_virtual_servers(self) -> list[dict]:
        output = self._cli_run("show slb virtual-server")
        return [{"raw": output, "source": "cli"}]

    def _cli_get_logs(self, limit: int) -> list[dict]:
        """CLI 'show log' 출력을 파싱해 구조화된 리스트로 반환한다."""
        # A10 syslog 형식: <Month> <Day> <HH:MM:SS> <host> <facility>.<level>: <message>
        import re
        output = self._cli_run(f"show log | tail -n {limit}")
        pattern = re.compile(
            r"(?P<timestamp>\w{3}\s+\d+\s+[\d:]+)\s+"
            r"\S+\s+"                          # 호스트명 (무시)
            r"(?P<facility>\S+?)\.(?P<level>\w+):\s+"
            r"(?P<message>.+)"
        )
        entries = []
        for line in output.splitlines():
            m = pattern.match(line.strip())
            if m:
                entries.append({
                    "timestamp": m.group("timestamp"),
                    "level":     m.group("level").upper(),
                    "facility":  m.group("facility"),
                    "message":   m.group("message"),
                    "source":    "cli",
                })
            elif line.strip():
                # 파싱 불가 라인도 raw 메시지로 보존
                entries.append({
                    "timestamp": "",
                    "level":     "UNKNOWN",
                    "facility":  "",
                    "message":   line.strip(),
                    "source":    "cli",
                })
        return entries

    def _cli_run(self, command: str) -> str:
        """SSH를 통해 A10 CLI 명령을 실행하고 출력을 반환한다."""
        ssh_cmd = ["ssh"]

        # SSH 키 인증 설정
        if settings.A10_SSH_KEY_PATH:
            ssh_cmd += ["-i", settings.A10_SSH_KEY_PATH]

        ssh_cmd += [
            "-p", str(settings.A10_SSH_PORT),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-o", "PubkeyAuthentication=no",
            "-o", "PreferredAuthentications=password",
            f"{settings.A10_USERNAME}@{settings.A10_HOST}",
            command,
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                input=settings.A10_PASSWORD,
                capture_output=True,
                text=True,
                timeout=settings.CONNECTION_TIMEOUT,
            )
            if result.returncode != 0:
                raise RuntimeError(f"CLI 명령 오류: {result.stderr.strip()}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"CLI 명령 타임아웃: {command}") from e

    # ── 공통 유틸 ──────────────────────────────────────────────────────────────

    def _call_with_fallback(self, *, rest_func, cli_func, name: str):
        """REST를 우선 시도하고 실패 시 CLI로 fallback한다."""
        try:
            result = rest_func()
            logger.debug("%s 조회 완료 (REST)", name)
            return result
        except Exception as e:
            logger.warning("%s REST 실패, CLI로 재시도: %s", name, e)
            try:
                result = cli_func()
                logger.debug("%s 조회 완료 (CLI fallback)", name)
                return result
            except Exception as cli_e:
                logger.error("%s CLI도 실패: %s", name, cli_e)
                raise RuntimeError(f"{name} 조회 실패 (REST·CLI 모두 불가)") from cli_e
