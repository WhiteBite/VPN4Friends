#!/usr/bin/env python3
"""Update Reality keys on 3X-UI panel."""

import os
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
print(f"\nCurrent inbound: {inbound_data['success']}")

if inbound_data["success"]:
    obj = inbound_data["obj"]
    print(f"Port: {obj['port']}")
    print(f"Protocol: {obj['protocol']}")
    
    # Parse streamSettings
    import json
    stream_settings = json.loads(obj["streamSettings"])
    reality = stream_settings.get("realitySettings", {})
    
    print(f"\nCurrent Reality settings:")
    print(f"Public Key: {reality.get('publicKey')}")
    print(f"Private Key: {reality.get('privateKey')}")
    print(f"SNI: {reality.get('serverNames')}")
    print(f"Short IDs: {reality.get('shortIds')}")
