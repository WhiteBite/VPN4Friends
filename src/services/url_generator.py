"""Generates connection URLs for different VPN protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from src.bot.config import settings

if TYPE_CHECKING:
    from src.bot.config import ServerEndpoint


def merge_profile_settings(
    profile_data: dict[str, Any], settings_overrides: dict | None
) -> dict[str, Any]:
    """Merge per-user settings (e.g. SNI) into raw profile data from 3X-UI.

    The `profile_data` dict is expected to contain a ``reality`` section with
    keys like ``public_key``, ``fingerprint``, ``default_sni`` and
    ``default_short_id`` (as returned by :func:`XUIApi.get_protocol_settings`).

    This helper produces a new dict where:
    - ``reality['sni']`` is set either from user overrides or from ``default_sni``;
    - ``reality['short_id']`` is set either from its existing value or from
      ``default_short_id``.
    """

    combined: dict[str, Any] = dict(profile_data)
    reality = dict(profile_data.get("reality", {}))

    # Apply user-selected SNI (if any)
    sni_override: str | None = None
    if settings_overrides:
        sni_override = settings_overrides.get("sni")
    if sni_override:
        reality["sni"] = sni_override

    # Fallback SNI from default_sni if explicit "sni" is not set
    if "sni" not in reality:
        default_sni = reality.get("default_sni")
        if default_sni:
            reality["sni"] = default_sni

    # Ensure short_id is present, fall back to default_short_id if needed
    if "short_id" not in reality:
        default_short_id = reality.get("default_short_id")
        if default_short_id:
            reality["short_id"] = default_short_id

    combined["reality"] = reality
    return combined


def generate_vless_url(
    profile_data: dict[str, Any],
    endpoint: ServerEndpoint | None = None,
) -> str:
    """Generate VLESS connection URL from prepared profile data.

    The ``profile_data`` dict should already contain a ``reality`` section with
    keys: ``public_key``, ``fingerprint``, ``sni``, ``short_id`` and
    ``spider_x``.

    If *endpoint* is provided, its ``host`` and ``port`` override the values
    from ``profile_data`` / ``settings.xui_host``.
    """

    remark = profile_data.get("remark", "")
    email = profile_data.get("email", "")
    fragment = f"{remark}-{email}" if remark and email else (remark or email)

    reality = profile_data.get("reality", {})
    public_key = reality.get("public_key", "")
    fingerprint = reality.get("fingerprint", "chrome")
    sni = reality.get("sni", "")
    short_id = reality.get("short_id", "")
    spider_x = reality.get("spider_x", "/")

    spider_x_encoded = quote(spider_x, safe="")

    # Default transport parameters
    transport = "tcp"
    security = "reality"
    flow_param = "xtls-rprx-vision"
    service_name = ""

    # Endpoint override takes priority over profile_data and settings
    if endpoint:
        host = endpoint.host
        port = endpoint.port
        if getattr(endpoint, "sni", None):
            sni = endpoint.sni
        if getattr(endpoint, "transport", None):
            transport = endpoint.transport
        if getattr(endpoint, "security", None):
            security = endpoint.security
        if getattr(endpoint, "flow", None):
            flow_param = endpoint.flow
        if getattr(endpoint, "serviceName", None):
            service_name = endpoint.serviceName
    else:
        host = profile_data.get("host", settings.xui_host)
        port = profile_data.get("port", 443)

    url_params = [
        f"type={transport}",
        f"security={security}",
        f"pbk={public_key}",
        f"fp={fingerprint}",
        f"sni={sni}",
        f"sid={short_id}",
        f"spx={spider_x_encoded}",
    ]

    if flow_param and transport == "tcp":
        url_params.append(f"flow={flow_param}")
    if service_name and transport in ("grpc", "ws"):
        url_params.append(f"serviceName={service_name}")

    query_string = "&".join(url_params)

    return f"vless://{profile_data['client_id']}@{host}:{port}?{query_string}#{fragment}"


def generate_shadowsocks_url(profile_data: dict[str, Any]) -> str:
    """Generate Shadowsocks connection URL from profile data.

    Expects ``profile_data['shadowsocks']`` to contain at least
    ``method`` and ``password``. Host is taken from ``profile_data['host']``
    if present, otherwise from ``settings.xui_host``.
    """

    shadowsocks = profile_data.get("shadowsocks", {})
    method = shadowsocks.get("method", "")
    password = shadowsocks.get("password", "")
    host = profile_data.get("host", settings.xui_host)
    port = profile_data["port"]

    remark = profile_data.get("remark", "")
    email = profile_data.get("email", "")
    fragment = f"{remark}-{email}" if remark and email else (remark or email)

    # Standard Shadowsocks URI: ss://BASE64(method:password@host:port)#TAG
    userinfo = f"{method}:{password}@{host}:{port}"

    import base64

    # urlsafe base64 without padding
    userinfo_b64 = base64.urlsafe_b64encode(userinfo.encode("utf-8")).decode("utf-8").rstrip("=")

    return f"ss://{userinfo_b64}#{fragment}"


def generate_vpn_link(
    protocol_name: str,
    profile_data: dict[str, Any],
    settings_overrides: dict | None = None,
    endpoint: ServerEndpoint | None = None,
) -> str | None:
    """Generate a VPN link for the given protocol.

    For protocols that support per-user settings (like VLESS Reality SNI),
    the ``settings_overrides`` dict is merged into ``profile_data`` before
    constructing the final URL.

    If *endpoint* is provided, it overrides the host/port in the generated URL.
    """
    if endpoint and getattr(endpoint, "protocol", None) == "mtproto":
        # Check if the MTProto details are provided via env variables or endpoint config
        # Assuming MTPROTO_HOST etc are not needed if we have them in the endpoint kwargs
        # But we'll use the hardcoded format for now or extract from endpoint host/port
        import os

        m_host = os.getenv("MTPROTO_HOST", endpoint.host)
        m_port = os.getenv("MTPROTO_PORT", str(endpoint.port))
        m_secret = os.getenv("MTPROTO_SECRET", "")
        if "secret" in endpoint.panel_config:
            m_secret = endpoint.panel_config["secret"]
        return f"tg://proxy?server={m_host}&port={m_port}&secret={m_secret}"

    if protocol_name == "vless":
        prepared = merge_profile_settings(profile_data, settings_overrides)
        return generate_vless_url(prepared, endpoint=endpoint)
    if protocol_name == "shadowsocks":
        return generate_shadowsocks_url(profile_data)
    # Add other protocols here
    return None
