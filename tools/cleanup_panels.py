import asyncio
import logging

from sqlalchemy import select

from src.bot.config import settings
from src.database.models import VpnProfile
from src.database.session import session_factory
from src.services.xui_api import XUIApi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup")


async def cleanup_panels(dry_run: bool = True):
    """
    Remove all clients from the 3X-UI panels that do not exist
    in the bot's 'vpn_profiles' database table.
    """
    logger.info(f"Starting panel cleanup (Dry Run: {dry_run})")

    # 1. Get all active UUIDs and emails from our database
    async with session_factory() as session:
        result = await session.execute(select(VpnProfile).where(VpnProfile.is_active.is_(True)))
        active_profiles = result.scalars().all()

    db_uuids = {p.client_id for p in active_profiles if p.client_id}
    db_emails = {p.profile_data.get("email") for p in active_profiles if p.profile_data}

    logger.info(f"Loaded {len(db_uuids)} active UUIDs and {len(db_emails)} emails from DB.")

    # 2. Iterate through all configured panels
    # (Simplified: logic for default panel + others from endpoints)
    panels_to_sync = [XUIApi()]
    seen_urls = {settings.xui_api_url}

    for ep in settings.endpoints:
        if ep.panel_config and ep.panel_type == "3xui":
            api_url = ep.panel_config.get("api_url")
            if api_url and api_url not in seen_urls:
                panels_to_sync.append(XUIApi(ep.panel_config))
                seen_urls.add(api_url)

    for panel in panels_to_sync:
        try:
            async with panel:
                logger.info(f"Checking panel: {panel._cfg['api_url']}")
                inbounds = await panel.list_inbounds()

                for inbound in inbounds:
                    import json

                    try:
                        s_data = json.loads(inbound.get("settings", "{}"))
                    except Exception:
                        continue

                    clients = s_data.get("clients", [])
                    new_clients = []
                    removed_count = 0

                    for client in clients:
                        client_id = client.get("id")
                        email = client.get("email", "")

                        # Strip port-suffix from email for comparison if needed
                        base_email = email.split("-")[0] if "-" in email else email

                        is_valid = (client_id in db_uuids) or (base_email in db_emails)

                        if is_valid:
                            new_clients.append(client)
                        else:
                            logger.info(
                                f"  [DELETE] Ghost client: {email} (ID: {client_id}) from inbound {inbound['id']}"
                            )
                            removed_count += 1

                    if removed_count > 0 and not dry_run:
                        inbound["settings"] = json.dumps({"clients": new_clients})
                        success = await panel.update_inbound(inbound["id"], inbound)
                        if success:
                            logger.info(
                                f"  Successfully updated inbound {inbound['id']} (removed {removed_count})"
                            )
                        else:
                            logger.error(f"  Failed to update inbound {inbound['id']}")

        except Exception as e:
            logger.error(f"Failed to cleanup panel {panel._cfg['api_url']}: {e}")


if __name__ == "__main__":
    import sys

    is_dry = "--commit" not in sys.argv
    asyncio.run(cleanup_panels(dry_run=is_dry))
    if is_dry:
        print("\n[!] THIS WAS A DRY RUN. Use '--commit' to actually delete clients.")
