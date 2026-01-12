#!/usr/bin/env python3
"""Test VPN speed through VLESS proxy."""

import asyncio
import time
import aiohttp
from urllib.parse import urlparse


async def test_speed(proxy_url: str, test_size_mb: int = 10) -> dict:
    """
    Test download speed through VLESS proxy.
    
    Args:
        proxy_url: VLESS URL (vless://uuid@host:port?params)
        test_size_mb: Size of test file in MB
    
    Returns:
        dict with speed results
    """
    # Parse VLESS URL
    parsed = urlparse(proxy_url)
    
    # For testing, we'll use a simple HTTP proxy approach
    # Note: aiohttp doesn't support VLESS directly, need xray-core
    
    print(f"⏳ Testing speed through proxy...")
    print(f"📦 Test file size: {test_size_mb} MB")
    
    # Test URLs
    test_urls = [
        f"http://speedtest.tele2.net/10MB.zip",
        f"http://ipv4.download.thinkbroadband.com/10MB.zip",
    ]
    
    results = []
    
    for url in test_urls:
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        downloaded = 0
                        async for chunk in response.content.iter_chunked(8192):
                            downloaded += len(chunk)
                        
                        elapsed = time.time() - start_time
                        speed_mbps = (downloaded * 8) / (elapsed * 1_000_000)
                        
                        results.append({
                            "url": url,
                            "size_mb": downloaded / (1024 * 1024),
                            "time_sec": elapsed,
                            "speed_mbps": speed_mbps
                        })
                        
                        print(f"✅ {url.split('/')[-1]}: {speed_mbps:.2f} Mbps ({elapsed:.1f}s)")
                    else:
                        print(f"❌ {url}: HTTP {response.status}")
        except Exception as e:
            print(f"❌ {url}: {e}")
    
    if results:
        avg_speed = sum(r["speed_mbps"] for r in results) / len(results)
        return {
            "average_mbps": avg_speed,
            "tests": results
        }
    
    return {"error": "All tests failed"}


async def test_with_xray(vless_url: str) -> dict:
    """Test speed using xray-core subprocess."""
    import json
    import subprocess
    import tempfile
    from pathlib import Path
    
    # Parse VLESS URL to extract config
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(vless_url)
    uuid = parsed.username
    host = parsed.hostname
    port = parsed.port or 443
    params = parse_qs(parsed.query)
    
    # Create xray config
    config = {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "port": 10808,
            "protocol": "socks",
            "settings": {"udp": True}
        }],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": host,
                    "port": port,
                    "users": [{
                        "id": uuid,
                        "encryption": params.get("encryption", ["none"])[0],
                        "flow": params.get("flow", [""])[0]
                    }]
                }]
            },
            "streamSettings": {
                "network": params.get("type", ["tcp"])[0],
                "security": params.get("security", ["none"])[0],
                "realitySettings": {
                    "serverName": params.get("sni", [""])[0],
                    "fingerprint": params.get("fp", ["chrome"])[0],
                    "publicKey": params.get("pbk", [""])[0],
                    "shortId": params.get("sid", [""])[0]
                } if params.get("security", [""])[0] == "reality" else None
            }
        }]
    }
    
    # Write config to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_path = f.name
    
    print(f"📝 Xray config: {config_path}")
    print(f"🚀 Starting xray-core on SOCKS5 localhost:10808...")
    
    # Start xray
    try:
        proc = subprocess.Popen(
            ["xray", "run", "-c", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for xray to start
        await asyncio.sleep(2)
        
        # Test speed through SOCKS5 proxy
        print("⏳ Testing speed through VLESS proxy...")
        
        start_time = time.time()
        
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            # Use proxy
            proxy = "socks5://127.0.0.1:10808"
            
            test_url = "http://speedtest.tele2.net/10MB.zip"
            
            async with session.get(test_url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=60)) as response:
                downloaded = 0
                async for chunk in response.content.iter_chunked(8192):
                    downloaded += len(chunk)
                
                elapsed = time.time() - start_time
                speed_mbps = (downloaded * 8) / (elapsed * 1_000_000)
                
                print(f"✅ Downloaded: {downloaded / (1024*1024):.2f} MB")
                print(f"⏱️  Time: {elapsed:.1f}s")
                print(f"🚀 Speed: {speed_mbps:.2f} Mbps")
                
                return {
                    "size_mb": downloaded / (1024 * 1024),
                    "time_sec": elapsed,
                    "speed_mbps": speed_mbps
                }
    
    except FileNotFoundError:
        print("❌ xray-core not found. Install: https://github.com/XTLS/Xray-core/releases")
        return {"error": "xray-core not installed"}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}
    finally:
        if 'proc' in locals():
            proc.terminate()
            proc.wait()
        Path(config_path).unlink(missing_ok=True)


async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_vpn_speed.py <vless_url>")
        print("\nExample:")
        print("  python test_vpn_speed.py 'vless://uuid@host:443?...'")
        sys.exit(1)
    
    vless_url = sys.argv[1]
    
    print("=" * 60)
    print("🔍 VPN Speed Test")
    print("=" * 60)
    
    result = await test_with_xray(vless_url)
    
    print("\n" + "=" * 60)
    if "error" not in result:
        print(f"📊 Final Result: {result['speed_mbps']:.2f} Mbps")
    else:
        print(f"❌ Test failed: {result['error']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
