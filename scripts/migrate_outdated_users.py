import asyncio
import logging
import uuid

from src.database.repositories import UserRepository
from src.database.session import session_factory
from src.services.vpn_service import VPNService
from src.services.xui_api import generate_client_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    async with session_factory() as session:
        user_repo = UserRepository(session)
        vpn_svc = VPNService(session)

        users = await user_repo.get_all_with_vpn()
        migrated = 0

        for user in users:
            profile = user.active_profile
            if not profile:
                continue

            p_data = profile.profile_data or {}

            # Use 'is not False' implicitly, but strictly check if client_id exists
            client_id = profile.client_id or p_data.get("client_id")

            if not client_id:
                # User has no client_id (outdated format)
                # We need to give them a new client_id, and re-sync.

                # First delete from all panels using their email (if exist)
                email = p_data.get("email")
                if email:
                    logger.info(
                        f"Removing old config for {user.telegram_id} ({email}) from panels..."
                    )
                    # await vpn_svc.remove_client_from_all_panels(email)

                # Now generate new identity and save it
                new_client_id = str(uuid.uuid4())
                client_name = generate_client_name(user.username, user.telegram_id)

                new_profile_data = {
                    **p_data,
                    "client_id": new_client_id,
                    "email": client_name,
                    "remark": f"VPN4Friends ({user.telegram_id}) MIGRATED",
                }

                # We remove legacy specific identifiers
                if "config_url" in new_profile_data:
                    del new_profile_data["config_url"]

                profile.profile_data = new_profile_data
                await user_repo.update_vpn_profile(profile)

                logger.info(f"Migrated user {user.telegram_id} in DB. Syncing to panel...")
                res = await vpn_svc.sync_client_to_all_panels(
                    email=client_name,
                    client_id=new_client_id,
                    protocol=profile.protocol_name or "vless",
                )

                if res:
                    logger.info(f"Successfully synced user {user.telegram_id}")
                    migrated += 1
                else:
                    logger.error(f"Failed to sync user {user.telegram_id}")

            elif not profile.client_id and client_id:
                # Quick fix if it's only missing in the column but is in profile_data
                profile.client_id = client_id
                await user_repo.update_vpn_profile(profile)

            await asyncio.sleep(0.1)  # be nice

        logger.info(f"Migration completed! Migrated {migrated} users to new Unified Access system.")


if __name__ == "__main__":
    asyncio.run(migrate())
