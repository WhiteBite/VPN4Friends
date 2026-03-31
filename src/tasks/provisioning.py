"""Background tasks for the bot."""

import logging

from src.bot.config import settings

logger = logging.getLogger(__name__)


async def run_provisioning(session_factory) -> None:
    """Run auto-provisioning for 3X-UI nodes in the background.

    This task synchronizes routing rules, inbounds, and user clients
    for all configured 3X-UI endpoints.
    """
    try:
        from src.database.repositories import UserRepository
        from src.services.xui_provisioner import (
            sync_node_clients,
            sync_node_inbounds,
            sync_node_routing,
        )

        logger.info("Starting auto-provisioning for 3X-UI nodes in background...")

        # Phase 1: Sync outbounds and routing rules per node
        nodes_config = settings.nodes_config
        for node_name, node_cfg in nodes_config.items():
            try:
                await sync_node_routing(node_name, node_cfg)
            except Exception as e:
                logger.error(f"Failed to sync routing for node {node_name}: {e}")

        # Phase 2: Sync inbounds and clients per endpoint
        async with session_factory() as session:
            user_repo = UserRepository(session)
            users_with_vpn = await user_repo.get_all_with_vpn()

            for endpoint in settings.endpoints:
                # Skip endpoints without a proper panel API
                if endpoint.panel_type != "3xui":
                    continue
                if not endpoint.panel_config or "api_url" not in endpoint.panel_config:
                    continue

                try:
                    success = await sync_node_inbounds(endpoint)
                    if success:
                        await sync_node_clients(endpoint, users_with_vpn)
                except Exception as e:
                    logger.error(f"Failed to sync node {endpoint.name}: {e}")

        logger.info("Auto-provisioning complete")
    except Exception as pe:
        logger.error(f"Failed during auto-provisioning: {pe}")
