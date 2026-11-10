"""Check every VPN endpoint from a subscription with a local Xray client.

Fetches the subscription, decodes the vless:// links and connects through each
endpoint (tcp/grpc/xhttp, reality), reporting the exit IP and latency.

Usage:
    python tools/check_endpoints.py --uuid 824908c7-...
    python tools/check_endpoints.py --sub https://host/api/sub/<uuid>
    python tools/check_endpoints.py --uuid <uuid> --only 8443,8448
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API = "https://vpn4friends-api.whitebite.ru/api/sub"
XPORTS = ("tcp", "grpc", "xhttp", "splithttp", "ws", "httpupgrade")


@dataclass
class Endpoint:
    name: str
    host: str
    port: int
    uuid: str
    transport: str
    sni: str
    pbk: str
    sid: str
    flow: str
    service_name: str
    path: str
    host_header: str


@dataclass
class Result:
    endpoint: Endpoint
    ok: bool
    exit_ip: str = ""
    latency_ms: float = 0.0
    error: str = ""


def find_xray(explicit: str | None) -> str:
    candidates = [explicit] if explicit else []
    if os.name == "nt":
        candidates += [str(ROOT / "tools" / "xray" / "xray.exe"), "xray"]
    else:
        candidates += [str(ROOT / "tools" / "xray" / "xray"), "xray"]
    for cand in candidates:
        if not cand:
            continue
        try:
            subprocess.run([cand, "version"], capture_output=True, timeout=10, check=True)
            return cand
        except (OSError, subprocess.SubprocessError):
            continue
    raise SystemExit("xray binary not found (pass --xray /path/to/xray)")


def fetch_subscription(args: argparse.Namespace) -> str:
    import urllib.request

    url = args.sub or f"{DEFAULT_API}/{args.uuid}"
    with urllib.request.urlopen(url, timeout=25) as resp:
        return resp.read().decode("utf-8").strip()


def parse_links(sub_text: str) -> list[Endpoint]:
    raw = sub_text.strip()
    if "://" not in raw:
        padded = raw + "=" * (-len(raw) % 4)
        raw = base64.b64decode(padded).decode("utf-8")
    links = [ln.strip() for ln in raw.splitlines() if ln.strip().startswith("vless://")]

    endpoints: list[Endpoint] = []
    for link in links:
        parsed = urlparse(link)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        name = unquote(parsed.fragment) or f"{parsed.hostname}:{parsed.port}"
        endpoints.append(
            Endpoint(
                name=name,
                host=parsed.hostname or "",
                port=parsed.port or 443,
                uuid=parsed.username or "",
                transport=query.get("type", "tcp"),
                sni=query.get("sni", ""),
                pbk=query.get("pbk", ""),
                sid=query.get("sid", ""),
                flow=query.get("flow", ""),
                service_name=query.get("serviceName", ""),
                path=unquote(query.get("path", "")) or "/",
                host_header=query.get("host", ""),
            )
        )
    return endpoints


def build_client_config(ep: Endpoint, socks_port: int) -> dict:
    user = {"id": ep.uuid, "encryption": "none"}
    if ep.flow and ep.transport == "tcp":
        user["flow"] = ep.flow

    stream: dict = {
        "network": ep.transport,
        "security": "reality",
        "realitySettings": {
            "serverName": ep.sni,
            "fingerprint": "chrome",
            "publicKey": ep.pbk,
            "shortId": ep.sid,
            "spiderX": "/",
        },
    }
    if ep.transport == "grpc":
        stream["grpcSettings"] = {"serviceName": ep.service_name}
    elif ep.transport in ("xhttp", "splithttp"):
        stream["xhttpSettings"] = {"path": ep.path, "host": ep.host_header}

    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": socks_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": False, "auth": "noauth"},
            }
        ],
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {"vnext": [{"address": ep.host, "port": ep.port, "users": [user]}]},
                "streamSettings": stream,
            }
        ],
    }


def port_free(port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_for_port(port: int, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            try:
                sock.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def curl_through(port: int, url: str, timeout_s: int) -> tuple[str, float]:
    started = time.time()
    proc = subprocess.run(
        ["curl", "-s", "-m", str(timeout_s), "--proxy", f"socks5h://127.0.0.1:{port}", url],
        capture_output=True,
        text=True,
        timeout=timeout_s + 10,
    )
    return proc.stdout.strip(), (time.time() - started) * 1000


def test_endpoint(xray: str, ep: Endpoint, socks_port: int, ip_url: str, timeout_s: int) -> Result:
    config = build_client_config(ep, socks_port)
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "client.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")
        proc = subprocess.Popen(
            [xray, "run", "-c", str(cfg_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            if not wait_for_port(socks_port, 8):
                return Result(ep, False, error="xray client did not start")
            exit_ip, latency = curl_through(socks_port, ip_url, timeout_s)
            if not exit_ip:
                return Result(ep, False, error="no response through tunnel")
            return Result(ep, True, exit_ip=exit_ip, latency_ms=latency)
        except subprocess.TimeoutExpired:
            return Result(ep, False, error="timeout")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Probe VPN subscription endpoints")
    parser.add_argument("--uuid", help="subscription token (client uuid)")
    parser.add_argument("--sub", help="full subscription URL")
    parser.add_argument("--only", help="comma separated ports to test")
    parser.add_argument("--xray", help="path to xray binary")
    parser.add_argument(
        "--ip-url", default="https://api.ipify.org", help="url used to read the exit ip"
    )
    parser.add_argument("--timeout", type=int, default=15, help="per-endpoint timeout in seconds")
    args = parser.parse_args()

    if not args.uuid and not args.sub:
        parser.error("pass --uuid or --sub")

    xray = find_xray(args.xray)
    endpoints = parse_links(fetch_subscription(args))
    if args.only:
        wanted = {p.strip() for p in args.only.split(",")}
        endpoints = [ep for ep in endpoints if str(ep.port) in wanted]
    if not endpoints:
        print("no endpoints to test")
        return 1

    print(f"xray: {xray}")
    print(f"endpoints: {len(endpoints)}\n")
    passed = 0
    for index, ep in enumerate(endpoints):
        socks_port = 10911 + index
        while not port_free(socks_port):
            socks_port += 1
        result = test_endpoint(xray, ep, socks_port, args.ip_url, args.timeout)
        if result.ok:
            passed += 1
            print(
                f"[ OK ] :{ep.port:<5} {ep.transport:<10} {result.exit_ip:<16} {result.latency_ms:6.0f} ms  {ep.name}"
            )
        else:
            print(
                f"[FAIL] :{ep.port:<5} {ep.transport:<10} {'-':<16} {'-':>7}     {ep.name}  ({result.error})"
            )

    print(f"\n{passed}/{len(endpoints)} endpoints connected")
    return 0 if passed == len(endpoints) else 2


if __name__ == "__main__":
    sys.exit(main())
