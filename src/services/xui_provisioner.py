"""Auto-provisioning logic for 3X-UI servers."""

import json
import logging
from typing import Any

import asyncssh

from src.bot.config import ServerEndpoint, settings
from src.services.xui_api import XUIApi, XUIApiError

logger = logging.getLogger(__name__)


async def self_heal_database(endpoint: ServerEndpoint) -> bool:
    """Attempt to remotely patch the 3x-ui database to remove UNIQUE constraints.

    Requires ssh_host, ssh_user, and optionally ssh_key in the endpoint config.
    """
    if not endpoint.ssh_host:
        logger.warning(f"Node {endpoint.name}: No SSH host configured, self-healing skipped")
        return False

    host = endpoint.ssh_host
    user = endpoint.ssh_user or "root"
    port = endpoint.ssh_port or 22

    logger.info(
        f"Node {endpoint.name}: Starting remote self-healing (patching DB) via {user}@{host}:{port}"
    )

    sql_patch = """
    BEGIN TRANSACTION;
    CREATE TABLE IF NOT EXISTS client_traffics_new (
        id integer PRIMARY KEY AUTOINCREMENT,
        inbound_id integer,
        enable numeric,
        email text,
        up integer,
        down integer,
        all_time integer,
        expiry_time integer,
        total integer,
        reset integer DEFAULT 0,
        last_online integer DEFAULT 0,
        CONSTRAINT fk_inbounds_client_stats FOREIGN KEY (inbound_id) REFERENCES inbounds(id)
    );
    INSERT INTO client_traffics_new SELECT id, inbound_id, enable, email, up, down, all_time, expiry_time, total, reset, last_online FROM client_traffics;
    DROP TABLE client_traffics;
    ALTER TABLE client_traffics_new RENAME TO client_traffics;
    COMMIT;
    """

    try:
        # Use simple key-based or agent-based auth
        # If key is provided as content, it would need a temporary file or specific asyncssh handling
        async with asyncssh.connect(host, port=port, username=user) as conn:
            # Check for DB path (different for Docker vs host-based)
            # 1. Host-based (Finland style)
            # 2. Docker-based (Germany style)
            cmd = f'sqlite3 /etc/x-ui/x-ui.db "{sql_patch}"'
            await conn.run(cmd, check=True)
            logger.info(f"Node {endpoint.name}: DB patch applied successfully via SSH")
            return True
    except Exception as e:
        logger.error(f"Node {endpoint.name}: Self-healing failed: {e}")
        # Log the fallback manual command for the user
        logger.info(
            f"Manual fix for {endpoint.name}: 'sqlite3 /etc/x-ui/x-ui.db \"{sql_patch.strip()}\"'"
        )
        return False


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
        elif endpoint.transport == "xhttp":
            stream_settings["xhttpSettings"] = {
                "path": endpoint.path or "/xhttp",
                "host": "",
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
        # Prioritize the DB column (repaired by get_by_telegram_id) over JSON
        client_id = active_profile.client_id or profile_data.get("client_id")

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

            transport = node_endpoint.transport or "tcp"
            logger.info(
                f"Syncing {len(clients_info)} clients to node {node_endpoint.name} "
                f"(inbound {target_id}, transport={transport})"
            )
            return await api.batch_add_clients(
                target_id, clients_info, protocol=protocol, transport=transport
            )

    except XUIApiError as e:
        error_msg = str(e)
        if "UNIQUE constraint failed" in error_msg:
            logger.warning(
                f"Node {node_endpoint.name}: Detected UNIQUE constraint failure. "
                "The database likely requires patching to allow multiple inbounds for the same email."
            )
            # Trigger self-healing
            if await self_heal_database(node_endpoint):
                logger.info(
                    f"Node {node_endpoint.name}: Retrying client sync after self-healing..."
                )
                # Retry once
                transport = node_endpoint.transport or "tcp"
                try:
                    async with XUIApi(node_endpoint.panel_config) as api:
                        return await api.batch_add_clients(
                            target_id, clients_info, protocol=protocol, transport=transport
                        )
                except Exception as retry_err:
                    logger.error(f"Node {node_endpoint.name}: Retry failed: {retry_err}")
            else:
                logger.error(
                    f"Node {node_endpoint.name}: Sync failed and automated self-healing was not possible. "
                    "Please run the bootstrap script or manually patch the database."
                )
        else:
            logger.error(f"Failed to sync clients to node {node_endpoint.name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error syncing clients to {node_endpoint.name}: {e}")
        return False


async def sync_node_routing(node_name: str, node_config: dict) -> bool:
    """Synchronize outbounds and routing rules for a node.

    Reads the node definition from vpn-config.json nodes section,
    compares with the current Xray template config on the panel,
    and updates if there are differences.

    Args:
        node_name: Name of the node (e.g., "germany", "finland")
        node_config: Node configuration dict with panel_config, outbounds, routing
    """
    panel_config = node_config.get("panel_config")
    if not panel_config or "api_url" not in panel_config:
        logger.warning(f"Node {node_name}: no panel_config, skipping routing sync")
        return False

    expected_outbounds = node_config.get("outbounds", [])
    expected_routing = node_config.get("routing", {})

    # Remove non-routing keys like _comment
    expected_routing = {k: v for k, v in expected_routing.items() if not k.startswith("_")}

    if not expected_outbounds and not expected_routing:
        logger.info(f"Node {node_name}: no outbounds/routing defined, skipping")
        return True

    try:
        async with XUIApi(panel_config) as api:
            # Get current template and all settings (needed for update)
            template, full_settings = await api.get_xray_template_config()

            # If template is empty (configured via UI only), build a minimal base
            if not template or not template.get("outbounds"):
                logger.info(
                    f"Node {node_name}: xrayTemplateConfig is empty, building base template"
                )
                template = {
                    "log": {
                        "loglevel": "warning",
                        "access": "",
                        "error": "",
                    },
                    "api": {
                        "tag": "api",
                        "services": ["HandlerService", "LoggerService", "StatsService"],
                    },
                    "inbounds": [
                        {
                            "tag": "api",
                            "listen": "127.0.0.1",
                            "port": 62789,
                            "protocol": "dokodemo-door",
                            "settings": {"address": "127.0.0.1"},
                        }
                    ],
                    "outbounds": [],
                    "routing": {
                        "domainStrategy": "AsIs",
                        "rules": [
                            {
                                "type": "field",
                                "inboundTag": ["api"],
                                "outboundTag": "api",
                            }
                        ],
                    },
                    "policy": {
                        "system": {
                            "statsInboundDownlink": True,
                            "statsInboundUplink": True,
                        }
                    },
                    "stats": {},
                }

            current_outbounds = template.get("outbounds", [])
            current_routing = template.get("routing", {})
            current_rules = current_routing.get("rules", [])

            changed = False

            # --- Sync outbounds ---
            current_tags = {o.get("tag") for o in current_outbounds}
            for expected_ob in expected_outbounds:
                tag = expected_ob.get("tag")
                if tag not in current_tags:
                    logger.info(f"Node {node_name}: adding outbound '{tag}'")
                    current_outbounds.append(expected_ob)
                    changed = True
                else:
                    # Update existing outbound settings if different
                    for i, co in enumerate(current_outbounds):
                        if co.get("tag") == tag:
                            if co.get("protocol") != expected_ob.get("protocol") or co.get(
                                "settings"
                            ) != expected_ob.get("settings"):
                                current_outbounds[i] = expected_ob
                                changed = True
                            break

            # --- Sync routing rules ---
            # Build expected rules from the routing map
            # Group inbound tags by outbound tag for efficient rules
            outbound_to_inbounds: dict[str, list[str]] = {}
            for inbound_tag, outbound_tag in expected_routing.items():
                outbound_to_inbounds.setdefault(outbound_tag, []).append(inbound_tag)

            # Check if current rules already match
            current_inbound_routing: dict[str, str] = {}
            for rule in current_rules:
                inbound_tags = rule.get("inboundTag", [])
                outbound_tag = rule.get("outboundTag", "")
                for it in inbound_tags:
                    current_inbound_routing[it] = outbound_tag

            if current_inbound_routing != dict(expected_routing):
                logger.info(
                    f"Node {node_name}: routing mismatch, updating "
                    f"(current={current_inbound_routing}, expected={dict(expected_routing)})"
                )

                # Rebuild rules: keep api rule, add our inbound rules, keep system rules
                new_rules = []

                # 1. Keep the API rule
                for rule in current_rules:
                    if rule.get("inboundTag") == ["api"]:
                        new_rules.append(rule)
                        break

                # 2. Add our inbound routing rules
                for outbound_tag, inbound_tags in outbound_to_inbounds.items():
                    new_rules.append(
                        {
                            "type": "field",
                            "inboundTag": sorted(inbound_tags),
                            "outboundTag": outbound_tag,
                        }
                    )

                # 3. Keep system rules (geoip:private → blocked, bittorrent → blocked)
                for rule in current_rules:
                    if rule.get("ip") or rule.get("protocol"):
                        new_rules.append(rule)

                current_routing["rules"] = new_rules
                changed = True

            if changed:
                template["outbounds"] = current_outbounds
                template["routing"] = current_routing
                success = await api.update_xray_template_config(template, full_settings)
                if success:
                    logger.info(f"Node {node_name}: routing synced successfully")
                else:
                    logger.error(f"Node {node_name}: failed to update routing")
                return success
            else:
                logger.info(f"Node {node_name}: routing already in sync")
                return True

    except XUIApiError as e:
        logger.error(f"Failed to sync routing for node {node_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error syncing routing for {node_name}: {e}")
        return False
