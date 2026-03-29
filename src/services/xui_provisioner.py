"""Auto-provisioning logic for 3X-UI servers."""

import json
import logging
from typing import Any

from src.bot.config import ServerEndpoint, settings
from src.services.xui_api import XUIApi, XUIApiError

logger = logging.getLogger(__name__)


def generate_inbound_config(endpoint: ServerEndpoint) -> dict[str, Any]:
    """Generate the full inbound configuration for 3X-UI API based on ServerEndpoint."""
    protocol = endpoint.protocol or "vless"
    port = endpoint.port
    remark = endpoint.name

    # Check if this endpoint uses Reality
    is_reality = endpoint.security == "reality"

    # Common payload
    payload = {
        "up": 0,
        "down": 0,
        "total": 0,
        "remark": remark,
        "enable": True,
        "expiryTime": 0,
        "listen": "",
        "port": port,
        "protocol": protocol,
    }

    # Settings and streamSettings based on protocol
    settings_data: dict[str, Any] = {"clients": []}
    stream_settings: dict[str, Any] = {
        "network": endpoint.transport or "tcp",
        "security": endpoint.security or "none",
        "externalProxy": [],
    }

    if protocol == "vless":
        settings_data["decryption"] = "none"
        settings_data["encryption"] = "none"
        settings_data["fallbacks"] = []

        if endpoint.transport == "tcp":
            stream_settings["tcpSettings"] = {
                "acceptProxyProtocol": False,
                "header": {"type": "none"},
            }
        elif endpoint.transport == "grpc":
            stream_settings["grpcSettings"] = {
                "serviceName": endpoint.serviceName or "grpc",
                "authority": "",
                "multiMode": True,
            }

        if is_reality:
            sni = endpoint.sni or "google.com"
            pbk = endpoint.pbk or settings.reality_public_key
            pk = endpoint.pk or settings.reality_private_key
            sid = endpoint.sid or settings.reality_short_id

            stream_settings["realitySettings"] = {
                "show": False,
                "xver": 0,
                "target": f"{sni}:443",
                "serverNames": [sni],
                "privateKey": pk,  # Used to sign
                "minClientVer": "",
                "maxClientVer": "",
                "maxTimediff": 0,
                "shortIds": [sid],
                "mldsa65Seed": "",
                "settings": {
                    "publicKey": pbk,
                    "fingerprint": endpoint.fp or "chrome",
                    "serverName": "",
                    "spiderX": endpoint.spx or "/",
                    "mldsa65Verify": "",
                },
            }

    payload["settings"] = json.dumps(settings_data)
    payload["streamSettings"] = json.dumps(stream_settings)
    payload["sniffing"] = json.dumps(
        {
            "enabled": True,
            "destOverride": ["http", "tls", "quic", "fakedns"],
            "metadataOnly": False,
            "routeOnly": False,
        }
    )

    return payload


async def sync_node_inbounds(node_endpoint: ServerEndpoint) -> bool:
    """Synchronize the node's inbounds with the central configuration."""
    if node_endpoint.panel_type != "3xui" or not node_endpoint.panel_config:
        logger.warning(f"Cannot sync node {node_endpoint.name}, missing panel config")
        return False

    try:
        async with XUIApi(node_endpoint.panel_config) as api:
            server_inbounds = await api.list_inbounds()
            expected_payload = generate_inbound_config(node_endpoint)

            # Find if there is an existing inbound with the same port and protocol
            existing_id = None
            protocol = node_endpoint.protocol or "vless"
            for ib in server_inbounds:
                if ib.get("port") == node_endpoint.port and ib.get("protocol") == protocol:
                    existing_id = ib["id"]
                    break

            if existing_id is not None:
                # Update existing inbound
                logger.info(f"Updating inbound {existing_id} on {node_endpoint.name}")
                # For update, we need to pass the ID in the payload as well
                expected_payload["id"] = existing_id

                # Fetch existing client list to preserve it
                try:
                    existing_ib = await api.get_inbound(existing_id)
                    old_settings = json.loads(existing_ib["settings"])
                    if "clients" in old_settings:
                        new_settings = json.loads(expected_payload["settings"])
                        new_settings["clients"] = old_settings["clients"]
                        expected_payload["settings"] = json.dumps(new_settings)

                        # Preserve data usages
                        expected_payload["up"] = existing_ib.get("up", 0)
                        expected_payload["down"] = existing_ib.get("down", 0)
                        expected_payload["total"] = existing_ib.get("total", 0)
                except Exception as e:
                    logger.warning(f"Failed to preserve clients for {existing_id}: {e}")

                success = await api.update_inbound(existing_id, expected_payload)
            else:
                # Add new inbound
                logger.info(f"Adding new inbound {node_endpoint.name}")
                success = await api.add_inbound(expected_payload)

            return success
    except Exception as e:
        logger.error(f"Failed to sync node {node_endpoint.name}: {e}")
        return False


async def sync_node_clients(node_endpoint: ServerEndpoint, users: list[Any]) -> bool:
    """Synchronize all existing clients from the database to the node's inbound."""
    if node_endpoint.panel_type != "3xui" or not node_endpoint.panel_config:
        return False

    protocol = node_endpoint.protocol or "vless"
    clients_info = []

    for user in users:
        active_profile = getattr(user, "active_profile", None)
        if not active_profile:
            continue

        profile_data = getattr(active_profile, "profile_data", {})
        email = profile_data.get("email")
        client_id = profile_data.get("client_id")

        if email and client_id:
            clients_info.append((email, client_id))

    if not clients_info:
        logger.info(f"No active clients to sync to {node_endpoint.name}")
        return True

    try:
        async with XUIApi(node_endpoint.panel_config) as api:
            server_inbounds = await api.list_inbounds()

            # Find the target inbound created for this node
            target_id = None
            for ib in server_inbounds:
                if ib.get("port") == node_endpoint.port and ib.get("protocol") == protocol:
                    target_id = ib["id"]
                    break

            if target_id is None:
                logger.warning(f"Target inbound '{node_endpoint.name}' not found for client sync")
                return False

            logger.info(
                f"Syncing {len(clients_info)} clients to node {node_endpoint.name} (inbound {target_id})"
            )
            return await api.batch_add_clients(target_id, clients_info, protocol=protocol)

    except XUIApiError as e:
        logger.error(f"Failed to sync clients to node {node_endpoint.name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error syncing clients to {node_endpoint.name}: {e}")
        return False
