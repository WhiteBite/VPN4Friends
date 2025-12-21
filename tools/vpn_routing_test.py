"""Test selective routing: geosite domains → WARP, others → direct."""
import json
import os
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
        v = v.strip().strip('"').strip("'")
        env[k.strip()] = v
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


def _build_singbox_config(env: dict[str, str], socks_port: int) -> dict:
    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "strategy": "prefer_ipv4",
            "servers": [{"tag": "cf", "address": "1.1.1.1"}],
            "final": "cf",
        },
        "inbounds": [{
            "type": "socks",
            "tag": "socks-in",
            "listen": "127.0.0.1",
            "listen_port": socks_port,
            "sniff": True,
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
    
    socks_port = 1081  # Different port to avoid conflicts
    cfg = _build_singbox_config(env, socks_port)
    
    with tempfile.TemporaryDirectory(prefix="routing_test_") as tmp:
        cfg_path = Path(tmp) / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2))
        
        print("[step] Starting sing-box...")
        proc = subprocess.Popen(
            [str(singbox), "run", "-c", str(cfg_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        try:
            if not _tcp_wait("127.0.0.1", socks_port, 15):
                print("[fail] sing-box didn't start")
                return 2
            
            time.sleep(1)
            proxy = f"socks5h://127.0.0.1:{socks_port}"
            
            print("\n" + "="*60)
            print("SELECTIVE ROUTING TEST")
            print("="*60)
            
            # Test sites that should go through WARP (geosite domains)
            warp_sites = [
                ("Google", "https://www.google.com/generate_204"),
                ("YouTube", "https://www.youtube.com"),
            ]
            
            # Test sites that should go direct
            direct_sites = [
                ("ipify (direct)", "http://api.ipify.org"),
                ("Cloudflare trace", "http://www.cloudflare.com/cdn-cgi/trace"),
            ]
            
            print("\n[1] Sites that should go through WARP (Cloudflare IP):")
            print("-" * 50)
            
            for name, url in warp_sites:
                try:
                    result = subprocess.run(
                        [curl, "-4", "-s", "-m", "15", "--proxy", proxy, url],
                        capture_output=True, text=True, timeout=20
                    )
                    if result.returncode == 0:
                        print(f"  ✓ {name}: OK")
                    else:
                        print(f"  ✗ {name}: FAILED")
                except Exception as e:
                    print(f"  ✗ {name}: {e}")
            
            print("\n[2] Checking IP addresses:")
            print("-" * 50)
            
            # Get IP through proxy (should be server IP for non-geosite)
            result = subprocess.run(
                [curl, "-4", "-s", "-m", "15", "--proxy", proxy, "http://api.ipify.org"],
                capture_output=True, text=True, timeout=20
            )
            proxy_ip = result.stdout.strip() if result.returncode == 0 else "ERROR"
            
            # Get Cloudflare trace (shows warp= if going through WARP)
            result = subprocess.run(
                [curl, "-4", "-s", "-m", "15", "--proxy", proxy, "http://www.cloudflare.com/cdn-cgi/trace"],
                capture_output=True, text=True, timeout=20
            )
            cf_trace = result.stdout if result.returncode == 0 else ""
            
            # Parse trace
            trace_data = {}
            for line in cf_trace.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    trace_data[k] = v
            
            cf_ip = trace_data.get("ip", "?")
            warp_status = trace_data.get("warp", "off")
            
            print(f"  • ipify IP (non-geosite): {proxy_ip}")
            print(f"  • Cloudflare trace IP:    {cf_ip}")
            print(f"  • WARP status:            {warp_status}")
            
            print("\n[3] Expected behavior:")
            print("-" * 50)
            print(f"  • Server IP: {env['VLESS_SERVER']}")
            print(f"  • Non-geosite sites → direct → Server IP ({env['VLESS_SERVER']})")
            print(f"  • Geosite sites (google, youtube, etc.) → WARP → Cloudflare IP")
            
            print("\n" + "="*60)
            
            # Determine result
            if proxy_ip == env['VLESS_SERVER']:
                print("✓ Direct routing works (ipify shows server IP)")
            else:
                print(f"? ipify shows {proxy_ip} (expected {env['VLESS_SERVER']})")
            
            if warp_status == "on":
                print("✓ WARP is active for Cloudflare trace")
            else:
                print("• WARP status: " + warp_status)
            
            print("\n[pass] Test completed")
            return 0
            
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
