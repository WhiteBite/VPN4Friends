#!/usr/bin/env python3
"""Fix Reality keys by generating new pair and updating server."""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Login to panel
session = requests.Session()
login_response = session.post(
    f"{os.getenv('XUI_API_URL')}/login",
    json={
        "username": os.getenv("XUI_USERNAME"),
        "password": os.getenv("XUI_PASSWORD"),
    },
)
print(f"Login: {login_response.json()}")

# Get current inbound
inbound_id = os.getenv("INBOUND_ID")
inbound_response = session.get(
    f"{os.getenv('XUI_API_URL')}/panel/api/inbounds/get/{inbound_id}"
)
inbound_data = inbound_response.json()

if inbound_data["success"]:
    obj = inbound_data["obj"]
    stream_settings = json.loads(obj["streamSettings"])
    reality = stream_settings.get("realitySettings", {})
    
    print(f"\nCurrent Reality settings:")
    print(f"Public Key: {reality.get('publicKey')}")
    print(f"Private Key: {reality.get('privateKey')}")
    
    # Generate new Reality keys using xray
    import subprocess
    result = subprocess.run(
        ["docker", "exec", "3x-ui", "/app/bin/xray-linux-amd64", "x25519"],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.strip().split('\n')
    new_private = None
    new_public = None
    
    for line in lines:
        if line.startswith('Private key:'):
            new_private = line.split(':', 1)[1].strip()
        elif line.startswith('Public key:'):
            new_public = line.split(':', 1)[1].strip()
    
    if new_private and new_public:
        print(f"\nNew Reality keys generated:")
        print(f"Private: {new_private}")
        print(f"Public: {new_public}")
        
        # Update Reality settings
        reality['privateKey'] = new_private
        reality['publicKey'] = new_public
        stream_settings['realitySettings'] = reality
        
        # Update inbound
        update_data = {
            "id": obj["id"],
            "up": obj["up"],
            "down": obj["down"],
            "total": obj["total"],
            "remark": obj["remark"],
            "enable": obj["enable"],
            "expiryTime": obj["expiryTime"],
            "listen": obj["listen"],
            "port": obj["port"],
            "protocol": obj["protocol"],
            "settings": obj["settings"],
            "streamSettings": json.dumps(stream_settings),
            "sniffing": obj["sniffing"],
        }
        
        update_response = session.post(
            f"{os.getenv('XUI_API_URL')}/panel/api/inbounds/update/{inbound_id}",
            json=update_data
        )
        
        print(f"\nUpdate response: {update_response.json()}")
        
        # Save to .env
        print(f"\nUpdate .env file with:")
        print(f"REALITY_PUBLIC_KEY={new_public}")
    else:
        print("Failed to generate new keys")
