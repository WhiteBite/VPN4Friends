#!/usr/bin/env python3
"""
MIGRATION SCRIPT: Sync users to all panels.
Usage: python -m src.scripts.sync_users

Reads all active VPN profiles from the database and broadcasts their UUID
and email to all configured 3x-ui and Hiddify panels in the .env endpoints.
"""

import asyncio
import logging
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.bot.config import settings
from src.database.models import User, VpnProfile
from src.services.vpn_service import VPNService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sync_users")


async def main():
    logger.info("Starting multi-panel sync for all active users...")

    # Initialize DB engine
    target_db = settings.database_url
    if target_db.startswith("sqlite") and not target_db.startswith("sqlite+aiosqlite"):
        target_db = target_db.replace("sqlite://", "sqlite+aiosqlite://")

    engine = create_async_engine(target_db, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    success_count = 0
    fail_count = 0

    async with async_session() as session:
        # Get all active VPN profiles and their associated users
        result = await session.execute(
            select(VpnProfile, User).join(User).where(VpnProfile.is_active)
        )
        profiles_chunk = result.all()

        if not profiles_chunk:
            logger.info("No active users found to sync.")
            await engine.dispose()
            return

        logger.info(f"Found {len(profiles_chunk)} active profiles to sync.")
        vpn_service = VPNService(session)

        for profile, user in profiles_chunk:
            client_id = profile.profile_data.get("client_id")
            email = profile.profile_data.get("email")

            if not client_id or not email:
                logger.warning(
                    f"Profile {profile.id} for user {user.telegram_id} is missing client_id or email, skipping."
                )
                fail_count += 1
                continue

            # Most legacy ones are "vless". Might be able to read protocol_name.
            protocol = profile.protocol_name.lower()
            if "finland_xhttp" in protocol or "reality" in protocol or "grpc" in protocol:
                protocol = "vless"
            elif protocol not in ["vless", "shadowsocks", "trojan", "vmess"]:
                protocol = "vless"  # Default to vless for 3xui

            logger.info(f"Syncing user {email} (UUID: {client_id}) across all panels...")
            try:
                synced = await vpn_service.sync_client_to_all_panels(email, client_id, protocol)
                if synced:
                    success_count += 1
                else:
                    logger.warning(f"User {email} could not be fully synced to all panels.")
                    fail_count += 1
            except Exception as e:
                logger.error(f"Error syncing user {email}: {e}")
                fail_count += 1

    logger.info("=" * 40)
    logger.info(
        f"SYNC COMPLETED. Successfully synced: {success_count}, Failed/Skipped: {fail_count}"
    )
    logger.info("=" * 40)

    await engine.dispose()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
