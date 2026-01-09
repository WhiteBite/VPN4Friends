#!/usr/bin/env python3
"""Update Reality keys on server."""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NEW_PRIVATE = "EO4qSUc0sXP2WFTLS1hHt+PTit04DqrxvNeX6h6jqV4="
NEW_PUBLIC = "rvwDomxegmqsH6km5LI8cMrSFnNEpr1vOBujkYszLiU="

# Login
session = requests.Session()
login = session.post(
    f"{os.getenv('XUI_API_URL')}/login",
    json={"username": os.getenv("XUI_USERNAME"), "password": os.getenv("XUI_PASSWORD")}
)
print(f"Login: {login.json()['success']}")

# Get inbound
inbound_id = os.getenv("INBOUND_ID")
resp = session.get(f"{os.getenv('XUI_API_URL')}/panel/api/inbounds/get/{inbound_id}")
data = resp.json()

if data["success"]:
    obj = data["obj"]
    stream = json.loads(obj["streamSettings"])
    
    # Update Reality keys
    stream["realitySettings"]["privateKey"] = NEW_PRIVATE
    stream["realitySettings"]["publicKey"] = NEW_PUBLIC
    
    # Update inbound
    update = session.post(
        f"{os.getenv('XUI_API_URL')}/panel/api/inbounds/update/{inbound_id}",
        json={
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
            "streamSettings": json.dumps(stream),
            "sniffing": obj["sniffing"],
        }
    )
    
    print(f"Update: {update.json()}")
    print(f"\nNew Public Key: {NEW_PUBLIC}")
