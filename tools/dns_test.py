"""Test DNS resolution through VPN with routeOnly enabled."""
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
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


def _build_config(env: dict[str, str], socks_port: int) -> dict:
    """Config that lets client handle DNS (no sniffing override)."""
    return {
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "google-doh", "address": "https://8.8.8.8/dns-query"},
                {"tag": "cloudflare", "address": "1.1.1.1"},
            ],
            "final": "cloudflare",
        },
        "inbounds": [{
            "type": "socks",
            "tag": "socks-in",
            "listen": "127.0.0.1",
            "listen_port": socks_port,
            "sniff": False,  # Let server handle sniffing with routeOnly
        }],
        "outbounds": [{
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
                "utls": {"enabled": True, "fingerprint": env["REALITY_FINGERPRINT"]},
                "reality": {
                    "enabled": True,
                    "public_key": env["REALITY_PUBLIC_KEY"],
                    "short_id": env["REALITY_SHORT_ID"],
                },
            },
        }],
        "route": {"final": "proxy"},
    }


def main() -> int:
    env_path = Path(__file__).resolve().parents[1] / "3x-ui.env"
    env = _parse_env_file(env_path)
    
    singbox = Path(__file__).resolve().parent / "sing-box.exe"
    curl = shutil.which("curl")
    
    if not singbox.exists():
        print("[fail] sing-box.exe not found")
        return 1
    if not curl:
        print("[fail] curl not found")
        return 1
    
    socks_port = 1082
    cfg = _build_config(env, socks_port)
    
    with tempfile.TemporaryDirectory(prefix="dns_test_") as tmp:
        cfg_path = Path(tmp) / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2))
        
        print("[step] Starting sing-box...")
        proc = subprocess.Popen(
            [str(singbox), "run", "-c", str(cfg_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        
        try:
            if not _tcp_wait("127.0.0.1", socks_port, 15):
                print("[fail] sing-box didn't start")
                # Show logs
                if proc.stdout:
                    print(proc.stdout.read())
                return 2
            
            time.sleep(1)
            proxy = f"socks5h://127.0.0.1:{socks_port}"
            
            print("\n" + "="*60)
            print("DNS THROUGH VPN TEST (routeOnly: true)")
            print("="*60)
            
            tests = [
                ("Google (HTTPS)", "https://www.google.com/generate_204"),
                ("Cloudflare", "https://1.1.1.1/cdn-cgi/trace"),
                ("ipify", "https://api.ipify.org"),
                ("httpbin", "https://httpbin.org/ip"),
            ]
            
            passed = 0
            failed = 0
            
            print("\n[1] Testing HTTPS connections through VPN:")
            print("-" * 50)
            
            for name, url in tests:
                try:
                    result = subprocess.run(
                        [curl, "-4", "-s", "-m", "10", "--proxy", proxy, url],
                        capture_output=True, text=True, timeout=15
                    )
                    if result.returncode == 0 and result.stdout:
                        short = result.stdout[:50].replace('\n', ' ')
                        print(f"  ✓ {name}: OK ({short}...)")
                        passed += 1
                    else:
                        print(f"  ✗ {name}: FAILED (code={result.returncode})")
                        if result.stderr:
                            print(f"      {result.stderr[:100]}")
                        failed += 1
                except Exception as e:
                    print(f"  ✗ {name}: {e}")
                    failed += 1
            
            print("\n[2] Testing DNS resolution (DoH through VPN):")
            print("-" * 50)
            
            # Test DoH through VPN
            doh_tests = [
                ("Google DoH", "https://8.8.8.8/resolve?name=google.com&type=A"),
                ("Cloudflare DoH", "https://1.1.1.1/dns-query?name=google.com&type=A"),
            ]
            
            for name, url in doh_tests:
                try:
                    result = subprocess.run(
                        [curl, "-4", "-s", "-m", "10", "--proxy", proxy, 
                         "-H", "Accept: application/dns-json", url],
                        capture_output=True, text=True, timeout=15
                    )
                    if result.returncode == 0 and "google" in result.stdout.lower():
                        print(f"  ✓ {name}: OK")
                        passed += 1
                    else:
                        print(f"  ✗ {name}: FAILED")
                        failed += 1
                except Exception as e:
                    print(f"  ✗ {name}: {e}")
                    failed += 1
            
            print("\n" + "="*60)
            print(f"RESULT: {passed} passed, {failed} failed")
            print("="*60)
            
            if failed == 0:
                print("\n✓ DNS and HTTPS work through VPN!")
                print("  routeOnly: true is working correctly.")
                return 0
            else:
                print("\n✗ Some tests failed.")
                return 1
            
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
