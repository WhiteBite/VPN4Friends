"""Generates connection URLs for different VPN protocols."""

from typing import Any
from urllib.parse import quote

from src.bot.config import settings

def generate_vless_url(profile_data: dict[str, Any]) -> str:
    """Generate VLESS connection URL from profile data."""
    remark = profile_data.get("remark", "")
    email = profile_data["email"]
    fragment = f"{remark}-{email}" if remark else email

    # Get Reality settings from profile (fetched from panel)
    reality = profile_data.get("reality", {})
    public_key = reality.get("public_key", "")
    fingerprint = reality.get("fingerprint", "chrome")
    sni = reality.get("sni", "")
    short_id = reality.get("short_id", "")
    spider_x = reality.get("spider_x", "/")

    spider_x_encoded = quote(spider_x, safe="")

    return (
        f"vless://{profile_data['client_id']}@{settings.xui_host}:{profile_data['port']}"
        f"?type=tcp&security=reality"
        f"&pbk={public_key}"
        f"&fp={fingerprint}"
        f"&sni={sni}"
        f"&sid={short_id}"
        f"&spx={spider_x_encoded}"
        f"&flow=xtls-rprx-vision"
        f"#{fragment}"
    )

def generate_shadowsocks_url(profile_data: dict[str, Any]) -> str:
    """Generate Shadowsocks connection URL from profile data."""
    # Placeholder for Shadowsocks URL generation logic
    # You will need to extract method, password from protocol_settings
    return "ss://..."


def generate_vpn_link(protocol_name: str, profile_data: dict[str, Any]) -> str | None:
    """Generate a VPN link for the given protocol."""
    if protocol_name == "vless":
        return generate_vless_url(profile_data)
    if protocol_name == "shadowsocks":
        return generate_shadowsocks_url(profile_data)
    # Add other protocols here
    return None
