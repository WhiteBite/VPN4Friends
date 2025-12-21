"""
Комплексный тест VPN подключения.

Проверяет:
1. TCP подключение к серверу
2. VLESS/REALITY handshake
3. HTTP/HTTPS через прокси
4. DNS резолвинг
5. Скорость соединения
6. Различные сайты (Google, YouTube, Telegram и т.д.)

Использование:
    python tools/vpn_test.py
    python tools/vpn_test.py --verbose
    python tools/vpn_test.py --sites google.com,youtube.com
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: float = 0.0


class VPNTester:
    def __init__(
        self,
        env_path: Path,
        singbox_path: str | None = None,
        socks_host: str = "127.0.0.1",
        socks_port: int = 1080,
        verbose: bool = False,
    ):
        self.env = self._parse_env_file(env_path)
        self.singbox = self._find_singbox(singbox_path)
        self.curl = self._find_curl()
        self.socks_host = socks_host
        self.socks_port = socks_port
        self.verbose = verbose
        self.results: list[TestResult] = []
        self._proc: subprocess.Popen | None = None
        self._tmp_dir: str | None = None

    def _parse_env_file(self, path: Path) -> dict[str, str]:
        if not path.exists():
            raise FileNotFoundError(f"env file not found: {path}")
        env: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            env[k.strip()] = v
        return env

    def _find_singbox(self, explicit: str | None) -> str:
        if explicit and Path(explicit).exists():
            return explicit
        local = Path(__file__).resolve().parent / "sing-box.exe"
        if local.exists():
            return str(local)
        which = shutil.which("sing-box") or shutil.which("sing-box.exe")
        if which:
            return which
        raise FileNotFoundError("sing-box not found")

    def _find_curl(self) -> str:
        curl = shutil.which("curl") or shutil.which("curl.exe")
        if not curl:
            raise FileNotFoundError("curl not found")
        return curl

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [debug] {msg}")

    def _run_test(self, name: str, func: callable) -> TestResult:
        start = time.time()
        try:
            passed, message = func()
            duration = (time.time() - start) * 1000
            result = TestResult(name, passed, message, duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = TestResult(name, False, str(e), duration)
        self.results.append(result)
        status = "✓" if result.passed else "✗"
        print(f"  {status} {name}: {result.message} ({result.duration_ms:.0f}ms)")
        return result

    def _curl(
        self, url: str, proxy: bool = True, timeout: float = 15.0, extra_args: list[str] | None = None
    ) -> tuple[int, str, str]:
        cmd = [self.curl, "-4", "-s", "--max-time", str(int(timeout))]
        if proxy:
            cmd.extend(["--proxy", f"socks5h://{self.socks_host}:{self.socks_port}"])
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(url)
        self._log(f"curl: {' '.join(cmd)}")
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    def _build_config(self) -> dict[str, Any]:
        return {
            "log": {"level": "debug" if self.verbose else "info", "timestamp": True},
            "dns": {
                "strategy": "prefer_ipv4",
                "servers": [
                    {"tag": "bootstrap", "address": "1.1.1.1"},
                    {"tag": "doh", "address": "https://cloudflare-dns.com/dns-query", "address_resolver": "bootstrap"},
                ],
                "final": "doh",
            },
            "inbounds": [
                {"type": "socks", "tag": "socks-in", "listen": self.socks_host, "listen_port": self.socks_port, "sniff": True}
            ],
            "outbounds": [
                {
                    "type": "vless",
                    "tag": "proxy",
                    "server": self.env["VLESS_SERVER"],
                    "server_port": int(self.env["VLESS_PORT"]),
                    "uuid": self.env["VLESS_UUID"],
                    "flow": self.env["VLESS_FLOW"],
                    "packet_encoding": "xudp",
                    "tls": {
                        "enabled": True,
                        "server_name": self.env["REALITY_SNI"],
                        "utls": {"enabled": True, "fingerprint": self.env["REALITY_FINGERPRINT"]},
                        "reality": {
                            "enabled": True,
                            "public_key": self.env["REALITY_PUBLIC_KEY"],
                            "short_id": self.env["REALITY_SHORT_ID"],
                        },
                    },
                },
                {"type": "direct", "tag": "direct"},
            ],
            "route": {"rules": [{"protocol": "dns", "outbound": "direct"}], "final": "proxy"},
        }

    def start_proxy(self) -> bool:
        """Запуск sing-box прокси."""
        self._tmp_dir = tempfile.mkdtemp(prefix="vpn_test_")
        cfg_path = Path(self._tmp_dir) / "config.json"
        log_path = Path(self._tmp_dir) / "sing-box.log"
        cfg_path.write_text(json.dumps(self._build_config(), indent=2), encoding="utf-8")

        with log_path.open("w", encoding="utf-8") as log_f:
            self._proc = subprocess.Popen(
                [self.singbox, "run", "-c", str(cfg_path)],
                stdout=log_f,
                stderr=subprocess.STDOUT,
            )

        # Ждём открытия порта
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with socket.create_connection((self.socks_host, self.socks_port), timeout=1):
                    time.sleep(0.5)  # Даём стабилизироваться
                    return True
            except OSError:
                time.sleep(0.2)
        return False

    def stop_proxy(self) -> None:
        """Остановка sing-box."""
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        if self._tmp_dir:
            import shutil as sh
            sh.rmtree(self._tmp_dir, ignore_errors=True)

    # === Тесты ===

    def test_tcp_connection(self) -> tuple[bool, str]:
        """Проверка TCP подключения к серверу."""
        server = self.env["VLESS_SERVER"]
        port = int(self.env["VLESS_PORT"])
        try:
            with socket.create_connection((server, port), timeout=5):
                return True, f"{server}:{port} reachable"
        except OSError as e:
            return False, f"{server}:{port} - {e}"

    def test_proxy_startup(self) -> tuple[bool, str]:
        """Проверка запуска прокси."""
        if self.start_proxy():
            return True, f"SOCKS5 listening on {self.socks_host}:{self.socks_port}"
        return False, "Failed to start sing-box"

    def test_get_ip(self) -> tuple[bool, str]:
        """Получение IP через прокси."""
        rc, ip, _ = self._curl("http://api.ipify.org")
        if rc == 0 and ip:
            server_ip = self.env["VLESS_SERVER"]
            if ip == server_ip:
                return True, f"IP: {ip} (matches server)"
            return True, f"IP: {ip} (server: {server_ip})"
        return False, "Failed to get IP"

    def test_https(self) -> tuple[bool, str]:
        """Проверка HTTPS через прокси."""
        # Получаем только HTTP код без вывода body
        rc, out, err = self._curl("https://www.google.com", extra_args=["-w", "%{http_code}", "-o", "NUL"])
        code = out[-3:] if len(out) >= 3 else out  # HTTP код в конце
        if rc == 0 and code in ("200", "301", "302"):
            return True, f"HTTPS works (HTTP {code})"
        # Попробуем другой сайт
        rc2, out2, err2 = self._curl("https://httpbin.org/get")
        if rc2 == 0 and "origin" in out2:
            return True, "HTTPS works (httpbin)"
        return False, f"HTTPS failed: rc={rc}, code={code}, err={err}"

    def test_dns(self) -> tuple[bool, str]:
        """Проверка DNS резолвинга."""
        rc, out, _ = self._curl("http://www.cloudflare.com/cdn-cgi/trace")
        if rc == 0 and "ip=" in out:
            return True, "DNS resolution works"
        return False, "DNS resolution failed"

    def test_site(self, domain: str) -> tuple[bool, str]:
        """Проверка доступности сайта."""
        url = f"https://{domain}" if not domain.startswith("http") else domain
        rc, out, err = self._curl(url, extra_args=["-w", "%{http_code}", "-o", "NUL", "-L"])
        code = out[-3:] if len(out) >= 3 else out
        if rc == 0 and code in ("200", "301", "302", "303", "307", "308"):
            return True, f"{domain} - HTTP {code}"
        # Попробуем HTTP если HTTPS не работает
        http_url = f"http://{domain}"
        rc2, out2, _ = self._curl(http_url, extra_args=["-w", "%{http_code}", "-o", "NUL", "-L"])
        code2 = out2[-3:] if len(out2) >= 3 else out2
        if rc2 == 0 and code2 in ("200", "301", "302", "303", "307", "308"):
            return True, f"{domain} - HTTP {code2} (http only)"
        return False, f"{domain} - rc={rc}, code={code}"

    def test_speed(self) -> tuple[bool, str]:
        """Простой тест скорости (скачивание 100KB через HTTP)."""
        # Используем HTTP endpoint для теста
        start = time.time()
        rc, out, err = self._curl(
            "http://httpbin.org/bytes/102400",  # 100KB
            extra_args=["-o", "NUL"],
            timeout=30,
        )
        duration = time.time() - start
        if rc == 0 and duration > 0:
            speed_kbps = (100 * 8) / duration  # 100KB в Kbps
            return True, f"~{speed_kbps:.0f} Kbps (100KB in {duration:.1f}s)"
        return False, f"Speed test failed: rc={rc}, err={err}"

    def run_all_tests(self, sites: list[str] | None = None) -> bool:
        """Запуск всех тестов."""
        print("\n=== VPN Connection Test ===\n")
        print(f"Server: {self.env['VLESS_SERVER']}:{self.env['VLESS_PORT']}")
        print(f"SNI: {self.env['REALITY_SNI']}")
        print()

        # Базовые тесты
        print("[1/5] TCP Connection")
        if not self._run_test("TCP to server", self.test_tcp_connection).passed:
            return False

        print("\n[2/5] Proxy Startup")
        if not self._run_test("Start sing-box", self.test_proxy_startup).passed:
            return False

        print("\n[3/5] Basic Connectivity")
        self._run_test("Get external IP", self.test_get_ip)
        self._run_test("HTTPS connection", self.test_https)
        self._run_test("DNS resolution", self.test_dns)

        print("\n[4/5] Site Accessibility")
        default_sites = ["google.com", "youtube.com", "github.com", "telegram.org"]
        test_sites = sites if sites else default_sites
        for site in test_sites:
            self._run_test(f"Site: {site}", lambda s=site: self.test_site(s))

        print("\n[5/5] Speed Test")
        self._run_test("Download speed", self.test_speed)

        # Итоги
        print("\n=== Results ===")
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"Passed: {passed}/{total}")

        if passed == total:
            print("\n✓ All tests passed!")
            return True
        else:
            failed = [r for r in self.results if not r.passed]
            print(f"\n✗ Failed tests: {', '.join(r.name for r in failed)}")
            return False


def main() -> int:
    parser = argparse.ArgumentParser(description="VPN Connection Tester")
    parser.add_argument("--env", default=str(Path(__file__).resolve().parents[1] / "3x-ui.env"))
    parser.add_argument("--singbox", default=os.environ.get("SING_BOX_BIN"))
    parser.add_argument("--socks-port", type=int, default=1080)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--sites", help="Comma-separated list of sites to test")
    args = parser.parse_args()

    sites = args.sites.split(",") if args.sites else None

    tester = VPNTester(
        env_path=Path(args.env),
        singbox_path=args.singbox,
        socks_port=args.socks_port,
        verbose=args.verbose,
    )

    try:
        success = tester.run_all_tests(sites)
        return 0 if success else 1
    finally:
        tester.stop_proxy()


if __name__ == "__main__":
    sys.exit(main())
