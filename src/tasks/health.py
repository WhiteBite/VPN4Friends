import asyncio
import logging
import time
from typing import Any

from src.bot.config import settings
from src.services.hiddify_api import HiddifyApi
from src.services.xui_api import XUIApi

logger = logging.getLogger(__name__)

# Global state for server health
# Key: api_url, Value: {"status": "up"|"down", "latency": float, "last_check": float}
HEALTH_CACHE: dict[str, Any] = {}


async def check_panel_health(panel_cfg: dict[str, Any], panel_type: str = "3xui"):
    """Check a single panel's health."""
    api_url = panel_cfg.get("api_url") or settings.xui_api_url

    start_time = time.time()
    try:
        online_count = 0
        if panel_type == "3xui":
            async with XUIApi(panel_cfg) as api:
                # Get online clients for real-time load
                onlines = await api.get_online_clients()
                online_count = len(onlines)
                # Also do a status check to ensure panel is responsive
                await api.get_server_status()
        elif panel_type == "hiddify":
            async with HiddifyApi(panel_cfg) as api:
                await api.list_inbounds()

        latency = (time.time() - start_time) * 1000

        # Heuristic for load level (can be refined later)
        # 0-10: Low, 11-40: Medium, 41+: High
        load_level = "low"
        if online_count > 40:
            load_level = "high"
        elif online_count > 10:
            load_level = "medium"

        HEALTH_CACHE[api_url] = {
            "status": "up",
            "latency": round(latency, 2),
            "online_count": online_count,
            "load_level": load_level,
            "last_check": time.time(),
        }
        logger.debug(f"Health check for {api_url}: UP ({latency:.0f}ms, {online_count} users)")
    except Exception as e:
        HEALTH_CACHE[api_url] = {
            "status": "down",
            "error": str(e),
            "online_count": 0,
            "load_level": "unknown",
            "last_check": time.time(),
        }
        logger.warning(f"Health check for {api_url}: DOWN ({e})")


async def health_check_task():
    """Background task to poll all panels."""
    logger.info("Starting background health-check service")

    while True:
        seen_urls = set()
        tasks = []

        # 1. Check default panel
        tasks.append(check_panel_health({}))
        seen_urls.add(settings.xui_api_url)

        # 2. Check all endpoint panels
        for ep in settings.endpoints:
            if not ep.panel_config:
                continue

            api_url = ep.panel_config.get("api_url")
            if api_url and api_url not in seen_urls:
                tasks.append(check_panel_health(ep.panel_config, ep.panel_type))
                seen_urls.add(api_url)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Poll every 5 minutes
        await asyncio.sleep(300)


def get_server_status(api_url: str) -> dict[str, Any]:
    """Get cached status for a given panel URL."""
    return HEALTH_CACHE.get(api_url, {"status": "unknown"})
