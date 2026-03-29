import json
import subprocess
import urllib.request


def register_warp():
    """Register a new WARP account using the Cloudflare API."""
    # 1. Generate keys
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public_key = subprocess.check_output(["echo", private_key], shell=True)
    public_key = subprocess.check_output(["wg", "pubkey"], input=public_key).decode().strip()

    # 2. Register
    url = "https://api.cloudflareclient.com/v0a2405/reg"
    headers = {"Content-Type": "application/json; charset=UTF-8", "User-Agent": "okhttp/3.12.1"}
    data = {
        "install_id": "",
        "tos": "2020-09-01T00:00:00.000+00:00",
        "key": public_key,
        "fcm_token": "",
        "type": "ios",
        "model": "iPhone12,1",
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        config = res["config"]
        peer = config["peers"][0]
        v4 = config["interface"]["addresses"]["v4"]
        v6 = config["interface"]["addresses"]["v6"]

    print(f"PrivateKey: {private_key}")
    print(f"Address: {v4}, {v6}")
    print(f"Peer: {peer['public_key']} @ {peer['endpoint']['host']}")


if __name__ == "__main__":
    register_warp()
