"""Subscription API — generates base64-encoded VLESS links for VPN clients.

Usage: User adds the subscription URL to their VPN client (Throne, v2rayNG, Hiddify).
The client periodically fetches this URL and auto-updates the server list.

Endpoint: GET /api/sub/{token}
Token = user's client_id (UUID) from their VPN profile.
"""

import base64
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.bot.config import ServerEndpoint, settings
from src.database.models import VpnProfile
from src.database.session import session_factory
from src.services.url_generator import generate_vless_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sub", tags=["subscription"])

# Group display order and labels
GROUP_ORDER = {
    "fast": (1, "⚡ Быстрый"),
    "warp": (2, "🎬 Разблокировка"),
    "stealth": (3, "🛡 Стойкий"),
    "stealth_warp": (4, "🛡🎬 Стойкий + Разблокировка"),
    "moscow": (5, "📱 Через Москву"),
    "cdn": (6, "☁️ CDN Fallback"),
}


def _build_sub_label(endpoint: ServerEndpoint) -> str:
    """Build display label for the subscription link."""
    if endpoint.sub_label:
        return endpoint.sub_label

    # Auto-generate from endpoint fields
    country_flag = "🇫🇮" if "финл" in endpoint.country.lower() else "🇩🇪"
    group_prefix = GROUP_ORDER.get(endpoint.group, (99, ""))[1].split(" ")[0]  # emoji only

    transport_suffix = ""
    if endpoint.transport and endpoint.transport not in ("tcp",):
        transport_suffix = f" {endpoint.transport.upper()}"

    warp_suffix = ""
    if endpoint.routing_tag == "warp" or "warp" in endpoint.name.lower():
        warp_suffix = " WARP"

    relay_suffix = ""
    if endpoint.is_relay:
        relay_suffix = " МСК"

    return f"{group_prefix} {country_flag} {endpoint.country}{transport_suffix}{warp_suffix}{relay_suffix}"


def _generate_endpoint_link(
    endpoint: ServerEndpoint,
    client_id: str,
    email: str,
) -> str | None:
    """Generate a single VLESS link for a subscription endpoint."""
    if endpoint.protocol != "vless":
        return None
    if endpoint.category != "vpn":
        return None
    if not endpoint.visible_in_sub:
        return None

    # Build profile_data with the user's UUID
    profile_data = {
        "client_id": client_id,
        "email": email,
    }

    # Build the label
    label = _build_sub_label(endpoint)

    # Fragment = display name in client (clean label, no duplication)
    fragment = f"{label} - {email}"

    # Use generate_vless_url with endpoint override
    try:
        url = generate_vless_url(profile_data, endpoint=endpoint)
        # Replace the auto-generated fragment with our custom one
        if "#" in url:
            url_base = url.rsplit("#", 1)[0]
            from urllib.parse import quote

            url = f"{url_base}#{quote(fragment)}"
        return url
    except Exception as e:
        logger.warning(f"Failed to generate link for {endpoint.name}: {e}")
        return None


@router.get("/{token}", response_class=PlainTextResponse)
async def get_subscription(token: str) -> PlainTextResponse:
    """Return base64-encoded subscription content for a VPN client.

    The token is the user's client_id (UUID) from their VPN profile.
    """

    # Find the user by their client_id
    async with session_factory() as session:
        stmt = (
            select(VpnProfile)
            .where(VpnProfile.is_active == True)  # noqa: E712
            .options(selectinload(VpnProfile.user))
        )
        result = await session.execute(stmt)
        profiles = result.scalars().all()

        # Find profile matching the token (client_id)
        target_profile = None
        for p in profiles:
            if p.profile_data.get("client_id") == token:
                target_profile = p
                break

    if not target_profile:
        raise HTTPException(status_code=404, detail="Invalid subscription token")

    client_id = target_profile.profile_data.get("client_id", token)
    email = target_profile.profile_data.get("email", "User")

    # Generate links for all VPN endpoints
    links: list[str] = []
    sorted_endpoints = sorted(
        settings.endpoints,
        key=lambda ep: (
            GROUP_ORDER.get(ep.group, (99, ""))[0],
            ep.sort_order,
            ep.name,
        ),
    )

    for endpoint in sorted_endpoints:
        link = _generate_endpoint_link(endpoint, client_id, email)
        if link:
            links.append(link)

    if not links:
        raise HTTPException(status_code=404, detail="No endpoints configured")

    # Encode as base64 (standard subscription format)
    raw_content = "\n".join(links)
    b64_content = base64.b64encode(raw_content.encode("utf-8")).decode("utf-8")

    return PlainTextResponse(
        content=b64_content,
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Profile-Update-Interval": "6",  # Update every 6 hours
            "Subscription-Userinfo": "upload=0; download=0; total=0; expire=0",
            "Profile-Title": "base64:VlBONEZyaWVuZHM=",  # "VPN4Friends" in base64
        },
    )
