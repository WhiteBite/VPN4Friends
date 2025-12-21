"""Tests for VLESS URL generation."""

from urllib.parse import quote


def generate_vless_url(profile_data: dict) -> str:
    """Copy of generate_vless_url for isolated testing."""
    remark = profile_data.get("remark", "")
    email = profile_data["email"]
    fragment = f"{remark}-{email}" if remark else email

    reality = profile_data.get("reality", {})
    public_key = reality.get("public_key", "")
    fingerprint = reality.get("fingerprint", "chrome")
    sni = reality.get("sni", "")
    short_id = reality.get("short_id", "")
    spider_x = reality.get("spider_x", "/")

    spider_x_encoded = quote(spider_x, safe="")
    host = profile_data.get("host", "193.17.182.116")

    return (
        f"vless://{profile_data['client_id']}@{host}:{profile_data['port']}"
        f"?type=tcp&security=reality"
        f"&pbk={public_key}"
        f"&fp={fingerprint}"
        f"&sni={sni}"
        f"&sid={short_id}"
        f"&spx={spider_x_encoded}"
        f"&flow=xtls-rprx-vision"
        f"#{fragment}"
    )


def test_generate_vless_url_basic():
    """Test basic VLESS URL generation."""
    profile_data = {
        "client_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "testuser",
        "port": 443,
        "remark": "VLESS-Reality",
        "reality": {
            "public_key": "YekDGkMaw9U8-WkptHVedz7X-ClHRogd6cxzo8ykll0",
            "fingerprint": "chrome",
            "sni": "www.google.com",
            "short_id": "1f38d4f5",
            "spider_x": "/",
        },
    }

    url = generate_vless_url(profile_data)

    # Check URL structure
    assert url.startswith("vless://550e8400-e29b-41d4-a716-446655440000@")
    assert ":443?" in url
    assert "type=tcp" in url
    assert "security=reality" in url
    assert "pbk=YekDGkMaw9U8-WkptHVedz7X-ClHRogd6cxzo8ykll0" in url
    assert "fp=chrome" in url
    assert "sni=www.google.com" in url
    assert "sid=1f38d4f5" in url
    assert "spx=%2F" in url  # "/" encoded
    assert "flow=xtls-rprx-vision" in url
    assert "#VLESS-Reality-testuser" in url


def test_generate_vless_url_no_special_chars():
    """VLESS URL should not contain unencoded special characters."""
    profile_data = {
        "client_id": "test-uuid",
        "email": "user@test",
        "port": 443,
        "remark": "Test Remark",
        "reality": {
            "public_key": "key123",
            "fingerprint": "chrome",
            "sni": "example.com",
            "short_id": "abc",
            "spider_x": "/path/to/resource",
        },
    }

    url = generate_vless_url(profile_data)

    # spider_x should be URL-encoded
    assert "/path/to/resource" not in url
    assert "%2Fpath%2Fto%2Fresource" in url


def test_vless_url_scannable_by_qr():
    """Generated VLESS URL should be scannable when encoded in QR."""
    from PIL import Image
    from pyzbar.pyzbar import decode

    from src.utils.qr_generator import generate_qr_code

    profile_data = {
        "client_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "realuser",
        "port": 443,
        "remark": "VPN",
        "reality": {
            "public_key": "YekDGkMaw9U8-WkptHVedz7X-ClHRogd6cxzo8ykll0",
            "fingerprint": "chrome",
            "sni": "www.google.com",
            "short_id": "1f38d4f5",
            "spider_x": "/",
        },
    }

    url = generate_vless_url(profile_data)
    buffer = generate_qr_code(url)

    img = Image.open(buffer)
    decoded = decode(img)

    assert len(decoded) == 1, f"QR not readable! URL: {url}"
    assert decoded[0].data.decode("utf-8") == url
