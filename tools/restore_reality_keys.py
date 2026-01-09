#!/usr/bin/env python3
"""
Restore Reality VPN with NEW valid keypair.

CRITICAL: The original private key for public key 4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4
is LOST and cannot be recovered. This script generates a NEW valid keypair.

ALL users will need NEW configs after this fix.
"""

import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path


# NEW VALID KEYPAIR (generated fresh)
NEW_PRIVATE_KEY = "AAZI_hbzcWQsfvmlYh9iP8De0nbTbxq5CqGRgmtqWEI"
NEW_PUBLIC_KEY = "bxOgD6CIWGhrRZOXx9v0-JcfAsoXjWntB_Sz-yjZ0Wg"

# Keep original settings
SNI = "google.com"
SHORT_IDS = ["33189997caa12349", "6c4a80"]
FINGERPRINT = "chrome"
SPIDER_X = "/"


def backup_database() -> Path:
    """Backup 3X-UI database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"/root/x-ui.db.backup_{timestamp}")
    
    subprocess.run(
        ["cp", "/opt/3x-ui/db/x-ui.db", str(backup_path)],
        check=True,
    )
    
    print(f"✅ Database backup: {backup_path}")
    return backup_path


def update_database_reality_keys() -> None:
    """Update Reality keys in 3X-UI database."""
    conn = sqlite3.connect("/opt/3x-ui/db/x-ui.db")
    cursor = conn.cursor()
    
    # Get current inbound config
    cursor.execute(
        "SELECT id, stream_settings FROM inbounds WHERE port = 443 LIMIT 1"
    )
    row = cursor.fetchone()
    
    if not row:
        raise ValueError("No inbound found on port 443")
    
    inbound_id, stream_settings_str = row
    stream_settings = json.loads(stream_settings_str)
    
    # Update Reality settings
    reality = stream_settings.get("realitySettings", {})
    
    print(f"\n📝 Updating inbound ID {inbound_id}:")
    print(f"   Old private key: {reality.get('privateKey')}")
    print(f"   Old public key: {reality.get('publicKey')}")
    print(f"   Old settings.publicKey: {reality.get('settings', {}).get('publicKey')}")
    
    # Update with NEW valid keypair
    reality["privateKey"] = NEW_PRIVATE_KEY
    reality["publicKey"] = NEW_PUBLIC_KEY
    reality["target"] = f"{SNI}:443"
    reality["serverNames"] = [SNI]
    reality["shortIds"] = SHORT_IDS
    
    # Update settings.publicKey to match
    if "settings" not in reality:
        reality["settings"] = {}
    reality["settings"]["publicKey"] = NEW_PUBLIC_KEY
    reality["settings"]["fingerprint"] = FINGERPRINT
    reality["settings"]["spiderX"] = SPIDER_X
    
    print(f"   New private key: {NEW_PRIVATE_KEY}")
    print(f"   New public key: {NEW_PUBLIC_KEY}")
    print(f"   SNI: {SNI}")
    print(f"   Short IDs: {SHORT_IDS}")
    
    # Save updated config
    stream_settings["realitySettings"] = reality
    updated_json = json.dumps(stream_settings)
    
    cursor.execute(
        "UPDATE inbounds SET stream_settings = ? WHERE id = ?",
        (updated_json, inbound_id),
    )
    
    conn.commit()
    conn.close()
    
    print("✅ Database updated")


def get_xray_config_path() -> Path:
    """Get path to running Xray config."""
    result = subprocess.run(
        ["pgrep", "-f", "xray-linux-amd64"],
        capture_output=True,
        text=True,
        check=True,
    )
    pid = result.stdout.strip()
    return Path(f"/proc/{pid}/cwd/bin/config.json")


def update_xray_config() -> None:
    """Update running Xray config."""
    config_path = get_xray_config_path()
    
    # Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"/root/config.json.backup_{timestamp}")
    subprocess.run(["cp", str(config_path), str(backup_path)], check=True)
    print(f"✅ Config backup: {backup_path}")
    
    # Load and update
    with open(config_path) as f:
        config = json.load(f)
    
    # Find Reality inbound
    for inbound in config.get("inbounds", []):
        reality = inbound.get("streamSettings", {}).get("realitySettings")
        if reality:
            print(f"\n📝 Updating Xray config port {inbound['port']}:")
            print(f"   Old private key: {reality.get('privateKey')}")
            print(f"   Old public key: {reality.get('publicKey')}")
            
            reality["privateKey"] = NEW_PRIVATE_KEY
            reality["publicKey"] = NEW_PUBLIC_KEY
            reality["target"] = f"{SNI}:443"
            reality["serverNames"] = [SNI]
            reality["shortIds"] = SHORT_IDS
            
            print(f"   New private key: {NEW_PRIVATE_KEY}")
            print(f"   New public key: {NEW_PUBLIC_KEY}")
    
    # Save
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print("✅ Xray config updated")


def main() -> None:
    """Execute Reality keys restoration."""
    print("=" * 60)
    print("Reality VPN Keys Restoration")
    print("=" * 60)
    print("\n⚠️  WARNING:")
    print("The original private key is LOST and cannot be recovered.")
    print("This script will install a NEW valid keypair.")
    print("ALL users will need NEW configs after this fix.")
    print("\n" + "=" * 60)
    
    input("\nPress Enter to continue or Ctrl+C to abort...")
    
    try:
        # Step 1: Backup database
        print("\n1. Backing up database...")
        db_backup = backup_database()
        
        # Step 2: Update database
        print("\n2. Updating database with new keys...")
        update_database_reality_keys()
        
        # Step 3: Update running config
        print("\n3. Updating running Xray config...")
        update_xray_config()
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Reality keys restored.")
        print("=" * 60)
        print("\n📋 NEXT STEPS:")
        print("1. Restart 3x-ui: docker restart 3x-ui")
        print("2. Wait 10 seconds for restart")
        print("3. Generate NEW client configs through 3X-UI panel")
        print("4. Update .env file with new public key:")
        print(f"   REALITY_PUBLIC_KEY={NEW_PUBLIC_KEY}")
        print("5. Distribute NEW configs to ALL users")
        print("\n⚠️  OLD CONFIGS WILL NOT WORK!")
        print(f"\n📦 Backups:")
        print(f"   Database: {db_backup}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
