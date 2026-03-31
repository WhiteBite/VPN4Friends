import argparse
import json
import socket
import time
from pathlib import Path


def test_proxy(host, port, protocol):
    """Simple TCP check for proxy presence."""
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=5):
            duration = (time.time() - start) * 1000
            return True, f"Connected in {duration:.0f}ms"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Test MTProto and SOCKS5 proxies from config")
    parser.add_argument("--config", default="vpn-config.json")
    args = parser.parse_args()

    # Try to find config in parent if not in current
    config_path = Path(args.config)
    if not config_path.exists():
        config_path = Path(__file__).parents[1] / "vpn-config.json"

    if not config_path.exists():
        print(f"Error: {args.config} not found")
        return

    print(f"Loading config from {config_path}")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    endpoints = config.get("endpoints", [])
    tg_proxies = [e for e in endpoints if e.get("category") == "telegram"]

    if not tg_proxies:
        print("No Telegram proxies found in config.")
        return

    print(f"\n--- Testing Telegram Proxies ({len(tg_proxies)}) ---\n")

    for ep in tg_proxies:
        name = ep.get("name")
        host = ep.get("host")
        port = ep.get("port")
        proto = ep.get("protocol")

        print(f"Testing {name} [{proto}] ({host}:{port})... ", end="", flush=True)
        ok, msg = test_proxy(host, port, proto)
        if ok:
            print(f"OK ({msg})")
        else:
            print(f"FAILED ({msg})")


if __name__ == "__main__":
    main()
