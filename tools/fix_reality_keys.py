#!/usr/bin/env python3
"""Fix Reality keys by syncing database keys to running Xray config."""

import json
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path


def get_xray_pid() -> int:
    """Get Xray process ID."""
    result = subprocess.run(
        ["pgrep", "-f", "xray-linux-amd64"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip())


def get_config_path(pid: int) -> Path:
    """Get path to Xray config.json."""
    return Path(f"/proc/{pid}/cwd/bin/config.json")


def backup_config(config_path: Path) -> Path:
    """Create backup of current config."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"/root/config.json.backup_{timestamp}")
    
    with open(config_path) as f:
        config = f.read()
    
    with open(backup_path, "w") as f:
        f.write(config)
    
    print(f"✅ Backup created: {backup_path}")
    return backup_path


def get_db_reality_settings() -> dict:
    """Get Reality settings from 3X-UI database."""
    conn = sqlite3.connect("/opt/3x-ui/db/x-ui.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT stream_settings FROM inbounds WHERE port = 443 LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise ValueError("No inbound found on port 443")
    
    stream_settings = json.loads(row[0])
    return stream_settings.get("realitySettings", {})


def update_config_reality_keys(
    config_path: Path,
    private_key: str,
    public_key: str,
    server_names: list[str],
    short_ids: list[str],
) -> None:
    """Update Reality keys in Xray config."""
    with open(config_path) as f:
        config = json.load(f)
    
    # Find the inbound with Reality
    for inbound in config.get("inbounds", []):
        stream_settings = inbound.get("streamSettings", {})
        reality_settings = stream_settings.get("realitySettings")
        
        if reality_settings:
            print(f"\n📝 Updating inbound on port {inbound['port']}:")
            print(f"   Old private key: {reality_settings.get('privateKey')}")
            print(f"   Old public key: {reality_settings.get('publicKey')}")
            print(f"   Old SNI: {reality_settings.get('serverNames')}")
            
            # Update keys
            reality_settings["privateKey"] = private_key
            reality_settings["publicKey"] = public_key
            reality_settings["serverNames"] = server_names
            reality_settings["shortIds"] = short_ids
            
            # Update target to match SNI
            if server_names:
                reality_settings["target"] = f"{server_names[0]}:443"
            
            print(f"   New private key: {private_key}")
            print(f"   New public key: {public_key}")
            print(f"   New SNI: {server_names}")
            print(f"   New short IDs: {short_ids}")
    
    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Config updated: {config_path}")


def main() -> None:
    """Main execution."""
    print("=== Reality Keys Fix Script ===\n")
    
    try:
        # Get Xray process info
        print("1. Finding Xray process...")
        pid = get_xray_pid()
        config_path = get_config_path(pid)
        print(f"   PID: {pid}")
        print(f"   Config: {config_path}")
        
        # Backup current config
        print("\n2. Creating backup...")
        backup_path = backup_config(config_path)
        
        # Get valid keys from database
        print("\n3. Reading valid keys from database...")
        db_reality = get_db_reality_settings()
        
        private_key = db_reality.get("privateKey")
        # Public key is in settings.publicKey in database
        public_key = db_reality.get("settings", {}).get("publicKey")
        server_names = db_reality.get("serverNames", [])
        short_ids = db_reality.get("shortIds", [])
        
        print(f"   Private key: {private_key}")
        print(f"   Public key: {public_key}")
        print(f"   SNI: {server_names}")
        print(f"   Short IDs: {short_ids}")
        
        if not private_key or not public_key:
            raise ValueError("Missing keys in database")
        
        # Update config
        print("\n4. Updating Xray config...")
        update_config_reality_keys(
            config_path,
            private_key,
            public_key,
            server_names,
            short_ids,
        )
        
        print("\n" + "=" * 50)
        print("✅ Configuration updated successfully!")
        print("=" * 50)
        print("\n⚠️  NEXT STEPS:")
        print("1. Restart Xray: systemctl restart x-ui")
        print("2. Regenerate ALL client configs through 3X-UI panel")
        print("3. Distribute new configs to users")
        print(f"\n📦 Backup saved at: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
