"""Tests for Shadowsocks URL generation."""

import base64

from src.services.url_generator import generate_shadowsocks_url


def _decode_ss_userinfo(uri: str) -> str:
  """Decode the userinfo part of an ss:// URI back to plain text."""
  assert uri.startswith("ss://"), "Not an ss:// URI"
  body = uri[len("ss://") :]
  if "#" in body:
      body = body.split("#", 1)[0]
  # Add padding for base64 decoding
  padding = "=" * (-len(body) % 4)
  return base64.urlsafe_b64decode(body + padding).decode("utf-8")


def test_generate_shadowsocks_url_basic() -> None:
  """Basic Shadowsocks URL generation with method/password/host/port."""
  profile_data = {
      "port": 8388,
      "remark": "SS",
      "email": "testuser",
      "host": "example.com",
      "shadowsocks": {
          "method": "aes-128-gcm",
          "password": "pass123",
      },
  }

  url = generate_shadowsocks_url(profile_data)

  assert url.startswith("ss://")
  assert url.endswith("#SS-testuser")

  userinfo = _decode_ss_userinfo(url)
  assert userinfo == "aes-128-gcm:pass123@example.com:8388"


def test_generate_shadowsocks_url_without_remark() -> None:
  """If remark is missing, fragment should fall back to email only."""
  profile_data = {
      "port": 8388,
      "email": "user@example",
      "host": "host.local",
      "shadowsocks": {
          "method": "chacha20-ietf-poly1305",
          "password": "secret",
      },
  }

  url = generate_shadowsocks_url(profile_data)

  assert url.endswith("#user@example")
  userinfo = _decode_ss_userinfo(url)
  assert userinfo == "chacha20-ietf-poly1305:secret@host.local:8388"
