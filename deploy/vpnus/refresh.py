#!/usr/bin/env python3
"""Refresh the dedicated VPNUS Xray client config from the upstream subscription.

Runs on the HOST (not in the bot container) via a systemd timer. It fetches the
VPNUS subscription, parses the VLESS servers, and rebuilds the dedicated Xray
client's config so each upstream location is reachable via a stable local SOCKS
port. The 3X-UI panel points static outbounds at those local SOCKS ports, so
upstream rotation never touches the panel or disconnects users.

Stdlib-only (targets system python3 on Debian). No external dependencies.
"""

from __future__ import annotations

import base64
import http.cookiejar
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

CONFIG_PATH = os.environ.get("VPNUS_CONFIG", "/opt/vpnus-xray/config.json")
SERVICE = os.environ.get("VPNUS_SERVICE", "vpnus-xray")
SUB_URL = os.environ.get("VPNUS_SUB_URL", "")
SUB_URL_FILE = os.environ.get("VPNUS_SUB_URL_FILE", "/opt/vpnus-xray/sub_url.txt")
USER_AGENT = os.environ.get("VPNUS_UA", "v2rayNG/1.8.19")

# Every upstream location -> (stable local SOCKS port, exact subscription name).
# Ports are stable per location so the panel's static outbounds never change.
SERVERS: list[tuple[str, int, str]] = [
    ("us", 40010, "США 🇺🇸"),
    ("uk", 40011, "Великобритания 🇬🇧"),
    ("fr", 40012, "Франция 🇫🇷"),
    ("nl", 40013, "Нидерланды 🇳🇱"),
    ("tr", 40014, "Турция 🇹🇷"),
    ("kz", 40015, "Казахстан 🇰🇿"),
    ("de", 40016, "Германия 🇩🇪"),
    ("se", 40017, "Швеция 🇸🇪"),
    ("fi", 40018, "Финляндия 🇫🇮"),
    ("ee", 40019, "🇪🇪 Эстония"),
    ("pl", 40020, "🇵🇱 Польша"),
    ("ru", 40021, "Россия 🇷🇺"),
    ("lt", 40022, "Литва 🇱🇹"),
    ("lv", 40023, "Латвия 🇱🇻"),
    ("game1", 40024, "🇫🇮 🎮 Игровой 1"),
    ("game2", 40025, "🇪🇪 🎮 Игровой 2"),
    ("game3", 40026, "🇸🇪 🎮 Игровой 3"),
    ("bypde", 40027, "🇩🇪 Обход Резерв (только Wi-Fi)"),
    ("lte1", 40028, "🇫🇮 LTE #1"),
    ("lte2", 40029, "🇫🇮 LTE #2"),
    ("lte3", 40030, "🇫🇮 LTE #3"),
    ("lter", 40031, "🇫🇮 LTE Reserve"),
]

VALID_FP = {"chrome", "firefox", "safari", "ios", "android", "edge", "qq", "random", "randomized"}


def _sub_url() -> str:
    if SUB_URL:
        return SUB_URL.strip()
    try:
        with open(SUB_URL_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        print(f"ERROR: no subscription URL (set VPNUS_SUB_URL or {SUB_URL_FILE})", file=sys.stderr)
        sys.exit(1)


def fetch_servers() -> list[dict]:
    """Fetch + decode the subscription into a list of parsed VLESS server dicts."""
    # The subscription gates access behind a cookie challenge: the first request
    # returns 302 + Set-Cookie and redirects to itself. A cookie jar carries the
    # cookie through the redirect so the second hop returns the real payload.
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    req = urllib.request.Request(_sub_url(), headers={"User-Agent": USER_AGENT})
    with opener.open(req, timeout=20) as resp:
        raw = resp.read()
    try:
        decoded = base64.b64decode(raw + b"==").decode("utf-8", errors="replace")
    except Exception:
        decoded = raw.decode("utf-8", errors="replace")

    servers: list[dict] = []
    for line in decoded.splitlines():
        line = line.strip()
        if not line.startswith("vless://"):
            continue
        rest = line[len("vless://") :]
        cred, _, after = rest.partition("@")
        hostport, _, tail = after.partition("?")
        query, _, frag = tail.partition("#")
        host, _, port = hostport.partition(":")
        params = dict(urllib.parse.parse_qsl(query))
        servers.append(
            {
                "uuid": cred,
                "host": host,
                "port": int(port) if port.isdigit() else 443,
                "name": urllib.parse.unquote(frag),
                "network": params.get("type", "tcp"),
                "security": params.get("security", "none"),
                "sni": params.get("sni", ""),
                "pbk": params.get("pbk", ""),
                "sid": params.get("sid", ""),
                "fp": params.get("fp", "chrome"),
                "flow": params.get("flow", ""),
                "serviceName": params.get("serviceName", ""),
                "path": params.get("path", ""),
                "mode": params.get("mode", ""),
            }
        )
    return servers


def pick_server(servers: list[dict], name: str) -> dict | None:
    """Pick the upstream server matching the given exact name (substring fallback)."""
    for s in servers:
        if s["name"] == name:
            return s
    for s in servers:
        if name in s["name"]:
            return s
    return None


def build_outbound(code: str, srv: dict) -> dict:
    """Build a transport-aware (tcp / grpc / xhttp) VLESS+REALITY outbound."""
    fp = srv["fp"] if srv["fp"] in VALID_FP else "chrome"
    net = srv["network"]
    stream = {
        "network": net,
        "security": "reality",
        "realitySettings": {
            "serverName": srv["sni"],
            "fingerprint": fp,
            "publicKey": srv["pbk"],
            "shortId": srv["sid"],
            "spiderX": "/",
        },
    }
    if net == "grpc":
        stream["grpcSettings"] = {
            "serviceName": srv.get("serviceName", ""),
            "multiMode": srv.get("mode") == "multi",
        }
    elif net in ("xhttp", "splithttp"):
        stream["xhttpSettings"] = {"path": srv.get("path") or "/", "host": srv.get("sni", "")}
    return {
        "tag": f"out-{code}",
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": srv["host"],
                    "port": srv["port"],
                    "users": [{"id": srv["uuid"], "encryption": "none", "flow": srv["flow"] or ""}],
                }
            ]
        },
        "streamSettings": stream,
    }


def load_existing() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def build_config(servers: list[dict], previous: dict) -> tuple[dict, list[str], list[str]]:
    """Build the dedicated client config. Returns (config, found, missing)."""
    prev_outbounds = {o.get("tag"): o for o in (previous.get("outbounds") or [])}

    inbounds = []
    outbounds = []
    rules = []
    found: list[str] = []
    missing: list[str] = []

    for code, port, name in SERVERS:
        inbounds.append(
            {
                "tag": f"in-{code}",
                "listen": "127.0.0.1",
                "port": port,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
            }
        )
        srv = pick_server(servers, name)
        if srv:
            outbounds.append(build_outbound(code, srv))
            found.append(code)
        elif f"out-{code}" in prev_outbounds:
            # Preserve last-known good outbound if this refresh missed the location.
            outbounds.append(prev_outbounds[f"out-{code}"])
            missing.append(code)
        else:
            missing.append(code)
            continue
        rules.append({"type": "field", "inboundTag": [f"in-{code}"], "outboundTag": f"out-{code}"})

    outbounds.append({"tag": "direct", "protocol": "freedom", "settings": {}})
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": inbounds,
        "outbounds": outbounds,
        "routing": {"domainStrategy": "AsIs", "rules": rules},
    }
    return config, found, missing


def main() -> int:
    servers = fetch_servers()
    previous = load_existing()
    config, found, missing = build_config(servers, previous)

    if not found and not previous:
        print("ERROR: no target servers found and no previous config; aborting", file=sys.stderr)
        return 1
    if config == previous:
        print(f"VPNUS: no change (found={len(found)} missing={missing})")
        return 0

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)
    print(f"VPNUS: config updated (found={len(found)} missing={missing}); restarting {SERVICE}")

    result = subprocess.run(["systemctl", "restart", SERVICE], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARNING: restart failed: {result.stderr.strip()}", file=sys.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
