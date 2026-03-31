from src.services.url_generator import generate_shadowsocks_url


def test_generate_shadowsocks_url_basic():
    profile_data = {
        "client_id": "random-password-123",
        "email": "user_123",
        "host": "vpn.example.com",
        "port": 8443,
        "remark": "MyVPN",
        "shadowsocks": {
            "method": "aes-256-gcm",
        },
    }

    url = generate_shadowsocks_url(profile_data)
    assert url.startswith("ss://")
    assert url.endswith("#MyVPN-user_123")

    # userinfo base64: urlsafe base64 of aes-256-gcm:random-password-123@vpn.example.com:8443
    import base64

    b64_part = url[5 : url.find("#")]
    # Pad to check
    padded = b64_part + "=" * ((4 - len(b64_part) % 4) % 4)
    decoded = base64.urlsafe_b64decode(padded).decode()
    assert decoded == "aes-256-gcm:random-password-123@vpn.example.com:8443"


def test_generate_shadowsocks_url_no_method():
    profile_data = {
        "client_id": "only-password",
        "host": "1.1.1.1",
        "port": 1234,
        "shadowsocks": {},
    }

    url = generate_shadowsocks_url(profile_data)
    assert url.startswith("ss://")
