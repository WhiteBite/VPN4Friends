#!/usr/bin/env python3
"""
VPN Speed Test v3.0 - полное сравнение прямого и VPN подключения.
Измеряет пинг, скорость загрузки и отдачи.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import aiohttp

# Конфигурация - ОБНОВЛЕНО 20.12.2025
VLESS_CONFIG = {
    "server": "185.232.205.172",
    "port": 443,
    "uuid": "caa5997e-5da1-4ca2-a37b-3ef227d510bb",
    "flow": "xtls-rprx-vision",
    "public_key": "4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4",
    "short_id": "33189997caa12349",
    "sni": "google.com",
    "fingerprint": "chrome",
}

SOCKS_PORT = 10809
SING_BOX_PATH = Path(__file__).parent / "sing-box-1.12.exe"

# Тестовые URL
DOWNLOAD_URLS = [
    ("Cloudflare 10MB", "https://speed.cloudflare.com/__down?bytes=10000000"),
    ("Cloudflare 25MB", "https://speed.cloudflare.com/__down?bytes=25000000"),
    ("Cloudflare 100MB", "https://speed.cloudflare.com/__down?bytes=100000000"),
]

UPLOAD_SIZES = [1_000_000, 5_000_000]  # 1MB, 5MB
PING_COUNT = 10
PING_URL = "https://www.google.com/generate_204"


def create_singbox_config() -> dict:
    """Создаёт конфиг sing-box для VLESS-REALITY."""
    return {
        "log": {"level": "warn"},
        "inbounds": [
            {
                "type": "socks",
                "tag": "socks-in",
                "listen": "127.0.0.1",
                "listen_port": SOCKS_PORT,
            }
        ],
        "outbounds": [
            {
                "type": "vless",
                "tag": "proxy",
                "server": VLESS_CONFIG["server"],
                "server_port": VLESS_CONFIG["port"],
                "uuid": VLESS_CONFIG["uuid"],
                "flow": VLESS_CONFIG["flow"],
                "tls": {
                    "enabled": True,
                    "server_name": VLESS_CONFIG["sni"],
                    "utls": {"enabled": True, "fingerprint": VLESS_CONFIG["fingerprint"]},
                    "reality": {
                        "enabled": True,
                        "public_key": VLESS_CONFIG["public_key"],
                        "short_id": VLESS_CONFIG["short_id"],
                    },
                },
            },
            {"type": "direct", "tag": "direct"},
        ],
        "route": {"final": "proxy"},
    }


async def ping_test(session: aiohttp.ClientSession, count: int = PING_COUNT) -> dict:
    """Измеряет латентность."""
    latencies = []
    
    for i in range(count):
        try:
            start = time.time()
            async with session.get(PING_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                await resp.read()
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        except Exception:
            pass
    
    if not latencies:
        return {"min": 0, "avg": 0, "max": 0, "loss": 100}
    
    return {
        "min": min(latencies),
        "avg": sum(latencies) / len(latencies),
        "max": max(latencies),
        "loss": ((count - len(latencies)) / count) * 100,
    }


async def download_test(session: aiohttp.ClientSession, url: str, size_mb: int) -> dict | None:
    """Тестирует скорость загрузки."""
    try:
        start_time = time.time()
        total_bytes = 0
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
            if resp.status != 200:
                return None
            async for chunk in resp.content.iter_chunked(65536):
                total_bytes += len(chunk)
        
        elapsed = time.time() - start_time
        speed_mbps = (total_bytes * 8 / elapsed) / (1024 * 1024)
        
        return {"bytes": total_bytes, "time": elapsed, "speed_mbps": speed_mbps}
    except Exception:
        return None


async def upload_test(session: aiohttp.ClientSession, size_bytes: int) -> dict | None:
    """Тестирует скорость отдачи."""
    try:
        import os
        data = os.urandom(size_bytes)
        
        start_time = time.time()
        async with session.post(
            "https://speed.cloudflare.com/__up",
            data=data,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            if resp.status != 200:
                return None
            await resp.read()
        
        elapsed = time.time() - start_time
        speed_mbps = (size_bytes * 8 / elapsed) / (1024 * 1024)
        
        return {"bytes": size_bytes, "time": elapsed, "speed_mbps": speed_mbps}
    except Exception:
        return None


async def run_full_test(use_proxy: bool = False, quick: bool = False) -> dict:
    """Запускает полный тест."""
    results = {"ping": {}, "download": [], "upload": []}
    
    if use_proxy:
        try:
            from aiohttp_socks import ProxyConnector
            connector = ProxyConnector.from_url(f"socks5://127.0.0.1:{SOCKS_PORT}")
        except ImportError:
            print("⚠️  pip install aiohttp-socks")
            return results
    else:
        connector = None
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Ping
        print("   🏓 Пинг...", end=" ", flush=True)
        results["ping"] = await ping_test(session, 5 if quick else PING_COUNT)
        print(f"{results['ping']['avg']:.0f}ms")
        
        # Download
        urls = DOWNLOAD_URLS[:2] if quick else DOWNLOAD_URLS
        for name, url in urls:
            print(f"   📥 {name}...", end=" ", flush=True)
            result = await download_test(session, url, 0)
            if result:
                results["download"].append(result)
                print(f"{result['speed_mbps']:.1f} Mbps")
            else:
                print("❌")
        
        # Upload
        sizes = UPLOAD_SIZES[:1] if quick else UPLOAD_SIZES
        for size in sizes:
            size_mb = size // 1_000_000
            print(f"   📤 Upload {size_mb}MB...", end=" ", flush=True)
            result = await upload_test(session, size)
            if result:
                results["upload"].append(result)
                print(f"{result['speed_mbps']:.1f} Mbps")
            else:
                print("❌")
    
    return results


def start_singbox() -> subprocess.Popen | None:
    """Запускает sing-box."""
    if not SING_BOX_PATH.exists():
        print(f"❌ sing-box не найден: {SING_BOX_PATH}")
        return None
    
    config = create_singbox_config()
    config_path = Path(tempfile.gettempdir()) / "singbox_speedtest.json"
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    process = subprocess.Popen(
        [str(SING_BOX_PATH), "run", "-c", str(config_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    
    time.sleep(2)
    
    if process.poll() is not None:
        return None
    
    return process


def stop_singbox(process: subprocess.Popen) -> None:
    """Останавливает sing-box."""
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def print_comparison(direct: dict, vpn: dict) -> None:
    """Выводит сравнительную таблицу."""
    print("\n" + "=" * 60)
    print("📊 СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("=" * 60)
    
    # Header
    print(f"{'Метрика':<25} {'Прямое':<15} {'VPN':<15} {'Разница':<10}")
    print("-" * 60)
    
    # Ping
    d_ping = direct["ping"]["avg"] if direct["ping"] else 0
    v_ping = vpn["ping"]["avg"] if vpn["ping"] else 0
    diff_ping = v_ping - d_ping if d_ping and v_ping else 0
    print(f"{'Пинг (avg)':<25} {d_ping:>10.0f} ms   {v_ping:>10.0f} ms   {diff_ping:>+.0f} ms")
    
    # Download
    d_dl = sum(r["speed_mbps"] for r in direct["download"]) / len(direct["download"]) if direct["download"] else 0
    v_dl = sum(r["speed_mbps"] for r in vpn["download"]) / len(vpn["download"]) if vpn["download"] else 0
    diff_dl = ((v_dl - d_dl) / d_dl * 100) if d_dl else 0
    print(f"{'Download (avg)':<25} {d_dl:>10.1f} Mbps {v_dl:>10.1f} Mbps {diff_dl:>+.0f}%")
    
    # Upload
    d_ul = sum(r["speed_mbps"] for r in direct["upload"]) / len(direct["upload"]) if direct["upload"] else 0
    v_ul = sum(r["speed_mbps"] for r in vpn["upload"]) / len(vpn["upload"]) if vpn["upload"] else 0
    diff_ul = ((v_ul - d_ul) / d_ul * 100) if d_ul else 0
    print(f"{'Upload (avg)':<25} {d_ul:>10.1f} Mbps {v_ul:>10.1f} Mbps {diff_ul:>+.0f}%")
    
    print("-" * 60)
    
    # Verdict
    if v_dl > 0 and d_dl > 0:
        efficiency = (v_dl / d_dl) * 100
        print(f"\n📈 Эффективность VPN: {efficiency:.0f}% от прямого подключения")
        
        if efficiency >= 80:
            print("✅ Отличный результат!")
        elif efficiency >= 50:
            print("✅ Хороший результат для VPN")
        elif efficiency >= 30:
            print("⚠️  Средний результат — возможны улучшения")
        else:
            print("❌ Низкая эффективность — проверь настройки")


async def main() -> None:
    """Главная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="VPN Speed Test v3.0")
    parser.add_argument("--quick", "-q", action="store_true", help="Быстрый тест")
    parser.add_argument("--vpn-only", "-v", action="store_true", help="Только VPN")
    parser.add_argument("--direct-only", "-d", action="store_true", help="Только прямое")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 VPN Speed Test v3.0")
    print("=" * 60)
    print(f"📡 VPN Server: {VLESS_CONFIG['server']}:{VLESS_CONFIG['port']}")
    print(f"🔐 Protocol: VLESS + Reality + XTLS-Vision")
    print(f"🌐 SNI: {VLESS_CONFIG['sni']}")
    
    # Проверяем зависимости
    try:
        import aiohttp_socks
    except ImportError:
        print("\n⚠️  Устанавливаю aiohttp-socks...")
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp-socks", "-q"])
    
    direct_results = None
    vpn_results = None
    
    # Тест прямого подключения
    if not args.vpn_only:
        print("\n" + "-" * 60)
        print("🌐 ПРЯМОЕ ПОДКЛЮЧЕНИЕ (без VPN)")
        print("-" * 60)
        direct_results = await run_full_test(use_proxy=False, quick=args.quick)
    
    # Тест через VPN
    if not args.direct_only:
        process = start_singbox()
        if not process:
            print("❌ Не удалось запустить sing-box")
            if direct_results:
                print("\nРезультаты прямого подключения:")
                print(f"   Пинг: {direct_results['ping']['avg']:.0f}ms")
            return
        
        try:
            print("\n" + "-" * 60)
            print(f"🔒 ЧЕРЕЗ VPN ({VLESS_CONFIG['server']})")
            print("-" * 60)
            vpn_results = await run_full_test(use_proxy=True, quick=args.quick)
        finally:
            stop_singbox(process)
    
    # Сравнение
    if direct_results and vpn_results:
        print_comparison(direct_results, vpn_results)
    elif vpn_results:
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ VPN")
        print("=" * 60)
        print(f"🏓 Пинг: {vpn_results['ping']['avg']:.0f}ms (min: {vpn_results['ping']['min']:.0f}, max: {vpn_results['ping']['max']:.0f})")
        if vpn_results["download"]:
            avg_dl = sum(r["speed_mbps"] for r in vpn_results["download"]) / len(vpn_results["download"])
            print(f"📥 Download: {avg_dl:.1f} Mbps")
        if vpn_results["upload"]:
            avg_ul = sum(r["speed_mbps"] for r in vpn_results["upload"]) / len(vpn_results["upload"])
            print(f"📤 Upload: {avg_ul:.1f} Mbps")
    elif direct_results:
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ ПРЯМОГО ПОДКЛЮЧЕНИЯ")
        print("=" * 60)
        print(f"🏓 Пинг: {direct_results['ping']['avg']:.0f}ms")
        if direct_results["download"]:
            avg_dl = sum(r["speed_mbps"] for r in direct_results["download"]) / len(direct_results["download"])
            print(f"📥 Download: {avg_dl:.1f} Mbps")
        if direct_results["upload"]:
            avg_ul = sum(r["speed_mbps"] for r in direct_results["upload"]) / len(direct_results["upload"])
            print(f"📤 Upload: {avg_ul:.1f} Mbps")


if __name__ == "__main__":
    asyncio.run(main())
