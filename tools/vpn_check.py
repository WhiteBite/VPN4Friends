import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"env file not found: {path}")

    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env[k] = v
    return env


def _tcp_wait(host: str, port: int, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _tcp_check(host: str, port: int, timeout_s: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _find_singbox(explicit: str | None) -> str:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        raise FileNotFoundError(f"sing-box not found at: {explicit}")

    local = Path(__file__).resolve().parent / "sing-box.exe"
    if local.exists():
        return str(local)

    which = shutil.which("sing-box") or shutil.which("sing-box.exe")
    if which:
        return which

    raise FileNotFoundError(
        "sing-box executable not found. Put sing-box.exe next to tools/vpn_check.py "
        "or add sing-box to PATH (https://github.com/SagerNet/sing-box/releases)."
    )


def _find_curl() -> str | None:
    return shutil.which("curl") or shutil.which("curl.exe")


def _run(cmd: list[str], timeout_s: float) -> tuple[int, str, str]:
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_s,
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def _tail_file(path: Path, lines: int = 80) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.splitlines()
    return "\n".join(parts[-lines:])


def _socks_proxy_url(host: str, port: int) -> str:
    # curl expects socks5h:// for remote DNS resolution
    return f"socks5h://{host}:{port}"


def _curl_get_ip_through_proxy(
    curl: str,
    proxy_url: str,
    timeout_s: float,
) -> tuple[bool, str, str, str]:
    endpoints = [
        "http://api.ipify.org",
        "http://icanhazip.com",
        "http://ifconfig.me/ip",
    ]
    for url in endpoints:
        rc, out, err = _run([curl, "-4", "-s", "--proxy", proxy_url, url], timeout_s=timeout_s)
        ip = out.strip()
        if rc == 0 and ip and any(ch.isdigit() for ch in ip):
            return True, ip, url, err
    return False, "", endpoints[-1], err


def _build_singbox_config(env: dict[str, str], socks_host: str, socks_port: int) -> dict[str, Any]:
    required = [
        "VLESS_SERVER",
        "VLESS_PORT",
        "VLESS_UUID",
        "VLESS_FLOW",
        "REALITY_PUBLIC_KEY",
        "REALITY_SHORT_ID",
        "REALITY_SNI",
        "REALITY_FINGERPRINT",
        "REALITY_SPIDERX",
    ]
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise ValueError(f"Missing keys in env: {', '.join(missing)}")

    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "strategy": "prefer_ipv4",
            "servers": [
                {
                    "tag": "bootstrap",
                    "address": "1.1.1.1",
                },
                {
                    "tag": "doh-cloudflare",
                    "address": "https://cloudflare-dns.com/dns-query",
                    "address_resolver": "bootstrap",
                },
                {
                    "tag": "doh-google",
                    "address": "https://dns.google/dns-query",
                    "address_resolver": "bootstrap",
                },
            ],
            "final": "doh-cloudflare",
        },
        "inbounds": [
            {
                "type": "socks",
                "tag": "socks-in",
                "listen": socks_host,
                "listen_port": socks_port,
                "sniff": True,
            }
        ],
        "outbounds": [
            {
                "type": "vless",
                "tag": "proxy",
                "server": env["VLESS_SERVER"],
                "server_port": int(env["VLESS_PORT"]),
                "uuid": env["VLESS_UUID"],
                "flow": env["VLESS_FLOW"],
                "packet_encoding": "xudp",
                "tls": {
                    "enabled": True,
                    "server_name": env["REALITY_SNI"],
                    "utls": {
                        "enabled": True,
                        "fingerprint": env["REALITY_FINGERPRINT"],
                    },
                    "reality": {
                        "enabled": True,
                        "public_key": env["REALITY_PUBLIC_KEY"],
                        "short_id": env["REALITY_SHORT_ID"],
                    },
                },
            },
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
        ],
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "direct"},
            ],
            "final": "proxy",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="VLESS/REALITY VPN connectivity checker")
    parser.add_argument(
        "--env",
        default=str(Path(__file__).resolve().parents[1] / "3x-ui.env"),
        help="Path to 3x-ui.env",
    )
    parser.add_argument(
        "--singbox",
        default=os.environ.get("SING_BOX_BIN"),
        help="Path to sing-box executable (or set SING_BOX_BIN)",
    )
    parser.add_argument("--socks-host", default="127.0.0.1")
    parser.add_argument("--socks-port", type=int, default=1080)
    parser.add_argument("--startup-timeout", type=float, default=20.0)
    parser.add_argument("--curl-timeout", type=float, default=20.0)
    parser.add_argument(
        "--strict-https",
        action="store_true",
        help="Fail if HTTPS checks through proxy fail (default: warn only)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for sing-box (useful for diagnosing failures)",
    )
    args = parser.parse_args()

    env_path = Path(args.env).resolve()
    env = _parse_env_file(env_path)

    server = env.get("VLESS_SERVER", "")
    port = int(env.get("VLESS_PORT", "443") or "443")

    print(f"[info] env: {env_path}")
    print(f"[info] target: {server}:{port}")

    if not server:
        print("[fail] VLESS_SERVER is empty")
        return 2

    print("[step] tcp check to server:443")
    if not _tcp_check(server, port, timeout_s=3.0):
        print("[fail] cannot connect to server tcp port")
        return 3
    print("[ok] tcp reachable")

    singbox = _find_singbox(args.singbox)
    print(f"[info] sing-box: {singbox}")

    cfg = _build_singbox_config(env, args.socks_host, args.socks_port)
    if args.debug:
        cfg.setdefault("log", {})["level"] = "debug"

    curl = _find_curl()
    if not curl:
        print("[fail] curl not found in PATH. Install curl or add it to PATH.")
        return 4

    with tempfile.TemporaryDirectory(prefix="vpn_check_") as tmp:
        cfg_path = Path(tmp) / "sing-box.json"
        log_path = Path(tmp) / "sing-box.log"
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

        print("[step] starting sing-box")
        with log_path.open("w", encoding="utf-8", errors="replace") as log_f:
            proc = subprocess.Popen(
                [singbox, "run", "-c", str(cfg_path)],
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True,
            )

        try:
            print(f"[step] waiting for local socks {args.socks_host}:{args.socks_port}")
            if not _tcp_wait(args.socks_host, args.socks_port, timeout_s=args.startup_timeout):
                print("[fail] sing-box did not open socks port in time")
                tail = _tail_file(log_path)
                if tail:
                    print("[sing-box last logs]\n" + tail)
                return 5

            print("[ok] socks is up")

            # Let it settle a bit (helps on some Windows setups)
            time.sleep(0.5)

            print("[step] fetch direct ip")
            rc, direct_ip, err = _run([curl, "-4", "-s", "https://api.ipify.org"], timeout_s=args.curl_timeout)
            if rc != 0 or not direct_ip:
                print(f"[fail] direct ipify failed: rc={rc} err={err}")
                return 6
            print(f"[ok] direct ip: {direct_ip}")

            print("[step] fetch proxy ip")
            proxy_url = _socks_proxy_url(args.socks_host, args.socks_port)
            ok, proxy_ip, used_url, err = _curl_get_ip_through_proxy(curl, proxy_url, timeout_s=args.curl_timeout)
            if not ok:
                print(f"[fail] proxy ip check failed (last url: {used_url}) err={err}")
                _, _, verr = _run(
                    [curl, "-4", "-v", "--proxy", proxy_url, used_url],
                    timeout_s=args.curl_timeout,
                )
                if verr:
                    print("[curl -v]\n" + verr)
                tail = _tail_file(log_path)
                if tail:
                    print("[sing-box last logs]\n" + tail)
                return 7
            print(f"[ok] proxy ip: {proxy_ip}")

            if proxy_ip == direct_ip:
                # This is actually OK for selective routing - non-geosite traffic goes direct
                print("[info] proxy ip equals direct ip (expected for selective routing)")
                print("[info] non-geosite traffic goes direct through server IP")

            if proxy_ip == server:
                print(f"[ok] proxy ip matches server ip (direct routing working)")
            elif proxy_ip != server:
                print(f"[info] proxy ip ({proxy_ip}) != server ip ({server}). Traffic may go through WARP/CDN.")

            print("[step] fetch cloudflare trace through proxy")
            rc, trace, err = _run(
                [
                    curl,
                    "-4",
                    "-s",
                    "--proxy",
                    proxy_url,
                    "http://www.cloudflare.com/cdn-cgi/trace",
                ],
                timeout_s=args.curl_timeout,
            )
            if rc != 0 or "ip=" not in trace:
                print(f"[fail] cloudflare trace failed: rc={rc} err={err}")
                tail = _tail_file(log_path)
                if tail:
                    print("[sing-box last logs]\n" + tail)
                return 9
            print("[ok] cloudflare trace looks good")

            print("[step] HTTPS check through proxy (optional)")
            rc, _, err = _run(
                [
                    curl,
                    "-4",
                    "-s",
                    "--proxy",
                    proxy_url,
                    "https://api.ipify.org",
                ],
                timeout_s=args.curl_timeout,
            )
            if rc != 0:
                msg = f"HTTPS through proxy failed (rc={rc})."
                if args.strict_https:
                    print(f"[fail] {msg} err={err}")
                    tail = _tail_file(log_path)
                    if tail:
                        print("[sing-box last logs]\n" + tail)
                    return 10
                print(f"[warn] {msg} err={err}")

            sub = env.get("SUBSCRIPTION_LINK")
            if sub:
                print("[step] check subscription link (through proxy)")
                rc, _, err = _run(
                    [
                        curl,
                        "-4",
                        "-s",
                        "-o",
                        os.devnull,
                        "-w",
                        "%{http_code}",
                        "--proxy",
                        proxy_url,
                        sub,
                    ],
                    timeout_s=args.curl_timeout,
                )
                if rc == 0:
                    print("[ok] subscription reachable")
                else:
                    print(f"[warn] subscription check failed: rc={rc} err={err}")

            print("[pass] VPN connectivity test succeeded")
            return 0

        finally:
            print("[step] stopping sing-box")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
