"""Tests for QR code generator."""

import io

from PIL import Image
from pyzbar.pyzbar import decode

from src.utils.qr_generator import generate_qr_code

# Sample VLESS URL similar to real one
SAMPLE_VLESS_URL = (
    "vless://550e8400-e29b-41d4-a716-446655440000@193.17.182.116:443"
    "?type=tcp&security=reality"
    "&pbk=YekDGkMaw9U8-WkptHVedz7X-ClHRogd6cxzo8ykll0"
    "&fp=chrome"
    "&sni=www.google.com"
    "&sid=1f38d4f5"
    "&spx=%2F"
    "&flow=xtls-rprx-vision"
    "#VLESS-Reality-testuser"
)


def test_qr_generates_valid_png():
    """QR code should generate valid PNG image."""
    buffer = generate_qr_code("test")

    assert isinstance(buffer, io.BytesIO)

    # Check it's valid PNG
    img = Image.open(buffer)
    assert img.format == "PNG"
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_qr_decodes_to_original_data():
    """QR code should decode back to original string."""
    test_data = "https://example.com/test"
    buffer = generate_qr_code(test_data)

    img = Image.open(buffer)
    decoded = decode(img)

    assert len(decoded) == 1
    assert decoded[0].data.decode("utf-8") == test_data


def test_qr_handles_long_vless_url():
    """QR code should handle long VLESS URLs (300+ chars)."""
    buffer = generate_qr_code(SAMPLE_VLESS_URL)

    img = Image.open(buffer)
    decoded = decode(img)

    assert len(decoded) == 1, f"QR code not readable! URL length: {len(SAMPLE_VLESS_URL)}"
    assert decoded[0].data.decode("utf-8") == SAMPLE_VLESS_URL


def test_qr_handles_cyrillic_remark():
    """QR code should handle URLs with cyrillic characters in remark."""
    url_with_cyrillic = SAMPLE_VLESS_URL.replace("testuser", "Тест-Юзер")
    buffer = generate_qr_code(url_with_cyrillic)

    img = Image.open(buffer)
    decoded = decode(img)

    assert len(decoded) == 1
    # pyzbar returns bytes, decode as utf-8
    assert decoded[0].data.decode("utf-8") == url_with_cyrillic
