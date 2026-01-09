#!/usr/bin/env python3
"""Check 3X-UI connection and inbound configuration."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.config import settings
from src.services.xui_api import XUIApi, XUIApiError


async def main() -> None:
    """Check 3X-UI panel connection and configuration."""
    print(f"Checking 3X-UI panel at {settings.xui_api_url}")
    print(f"Inbound ID: {settings.inbound_id}")
    print()

    try:
        async with XUIApi() as api:
            print("✓ Successfully connected to 3X-UI panel")
            
            # Check inbound
            try:
                inbound = await api.get_inbound(settings.inbound_id)
                print(f"✓ Inbound #{settings.inbound_id} found")
                print(f"  Protocol: {inbound['protocol']}")
                print(f"  Port: {inbound['port']}")
                print(f"  Remark: {inbound['remark']}")
                print(f"  Enabled: {inbound['enable']}")
                
                # Check Reality settings
                stream_settings = json.loads(inbound['streamSettings'])
                reality_settings = stream_settings.get('realitySettings', {})
                
                if reality_settings:
                    print("✓ Reality settings found")
                    reality_inner = reality_settings.get('settings', {})
                    server_names = reality_settings.get('serverNames', [])
                    short_ids = reality_settings.get('shortIds', [])
                    
                    print(f"  Public Key: {reality_inner.get('publicKey', 'N/A')[:30]}...")
                    print(f"  SNI: {server_names}")
                    print(f"  Short IDs: {short_ids}")
                    print(f"  Fingerprint: {reality_inner.get('fingerprint', stream_settings.get('fingerprint', 'N/A'))}")
                else:
                    print("✗ No Reality settings found in inbound!")
                    print("  You need to configure Reality in 3X-UI panel first")
                    return
                
                # Check clients
                settings_data = json.loads(inbound['settings'])
                clients = settings_data.get('clients', [])
                print(f"\n✓ Current clients: {len(clients)}")
                for client in clients:
                    print(f"  - {client['email']} (enabled: {client.get('enable', True)})")
                
            except XUIApiError as e:
                print(f"✗ Failed to get inbound: {e}")
                print("\nMake sure:")
                print("1. Inbound ID is correct in .env file")
                print("2. Reality inbound is created in 3X-UI panel")
                return
                
    except XUIApiError as e:
        print(f"✗ Failed to connect: {e}")
        print("\nCheck:")
        print("1. 3X-UI panel is running")
        print("2. URL and credentials in .env are correct")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
