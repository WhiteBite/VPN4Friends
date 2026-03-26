"""Unit tests for URL generator."""

import pytest

from src.services.url_generator import generate_vless_url, generate_vpn_link, merge_profile_settings


class TestMergeProfileSettings:
    """Tests for merge_profile_settings function."""

    def test_merge_with_no_overrides(self):
        """Test merging without overrides."""
        profile_data = {
            "reality": {
                "public_key": "test_key",
                "default_sni": "google.com",
                "default_short_id": "abcd1234",
            }
        }

        result = merge_profile_settings(profile_data, None)

        assert result["reality"]["sni"] == "google.com"
        assert result["reality"]["short_id"] == "abcd1234"
        assert result["reality"]["public_key"] == "test_key"

    def test_merge_with_sni_override(self):
        """Test merging with SNI override."""
        profile_data = {
            "reality": {
                "public_key": "test_key",
                "default_sni": "google.com",
                "default_short_id": "abcd1234",
            }
        }

        result = merge_profile_settings(profile_data, {"sni": "max.ru"})

        assert result["reality"]["sni"] == "max.ru"
        assert result["reality"]["short_id"] == "abcd1234"

    def test_merge_without_default_sni(self):
        """Test merging when no default_sni is present."""
        profile_data = {
            "reality": {
                "public_key": "test_key",
                "sni": "custom.com",
            }
        }

        result = merge_profile_settings(profile_data, None)

        assert result["reality"]["sni"] == "custom.com"

    def test_merge_empty_overrides(self):
        """Test merging with empty overrides dict."""
        profile_data = {
            "reality": {
                "public_key": "test_key",
                "default_sni": "google.com",
            }
        }

        result = merge_profile_settings(profile_data, {})

        assert result["reality"]["sni"] == "google.com"


class TestGenerateVlessUrl:
    """Tests for generate_vless_url function."""

    def test_generate_vless_reality_xtls(self):
        """Test generating VLESS Reality URL with xtls-rprx-vision."""
        profile_data = {
            "uuid": "test-uuid-1234",
            "host": "test.example.com",
            "port": 443,
            "reality": {
                "public_key": "test_public_key",
                "sni": "max.ru",
                "short_id": "abcd1234",
                "fingerprint": "chrome",
            },
            "security": "reality",
            "flow": "xtls-rprx-vision",
        }

        url = generate_vless_url(profile_data)

        assert url.startswith("vless://test-uuid-1234@test.example.com:443")
        assert "security=reality" in url
        assert "sni=max.ru" in url
        assert "flow=xtls-rprx-vision" in url
        assert "pbk=test_public_key" in url

    def test_generate_vless_grpc(self):
        """Test generating VLESS gRPC URL."""
        profile_data = {
            "uuid": "test-uuid-5678",
            "host": "grpc.example.com",
            "port": 8444,
            "reality": {
                "public_key": "grpc_public_key",
                "sni": "google.com",
                "short_id": "efgh5678",
            },
            "security": "reality",
            "type": "grpc",
            "serviceName": "grpc",
        }

        url = generate_vless_url(profile_data)

        assert url.startswith("vless://test-uuid-5678@grpc.example.com:8444")
        assert "type=grpc" in url
        assert "serviceName=grpc" in url
        assert "security=reality" in url

    def test_generate_vless_with_endpoint_override(self):
        """Test generating URL with endpoint override."""
        from src.bot.config import ServerEndpoint

        profile_data = {
            "uuid": "test-uuid-9999",
            "host": "original.example.com",
            "port": 443,
            "reality": {
                "public_key": "test_key",
                "sni": "max.ru",
                "short_id": "ijkl9999",
            },
            "security": "reality",
        }

        endpoint = ServerEndpoint(
            name="finland_xhttp",
            label="🇫🇮 Финляндия (xHTTP)",
            host="override.example.com",
            port=443,
            protocol="vless",
        )

        url = generate_vless_url(profile_data, endpoint=endpoint)

        assert "override.example.com:443" in url
        assert "original.example.com" not in url


class TestGenerateVpnLink:
    """Tests for generate_vpn_link function."""

    def test_generate_vless_link(self):
        """Test generating VLESS link."""
        profile_data = {
            "uuid": "test-uuid",
            "host": "test.example.com",
            "port": 443,
            "reality": {
                "public_key": "test_key",
                "sni": "max.ru",
                "short_id": "test1234",
            },
            "security": "reality",
            "flow": "xtls-rprx-vision",
        }

        link = generate_vpn_link("vless", profile_data)

        assert link is not None
        assert link.startswith("vless://")

    def test_generate_shadowsocks_link(self):
        """Test generating Shadowsocks link."""
        profile_data = {
            "shadowsocks": {
                "method": "chacha20-ietf-poly1305",
                "password": "test_password",
            },
            "host": "ss.example.com",
            "port": 8388,
            "remark": "Test SS",
            "email": "testuser",
        }

        link = generate_vpn_link("shadowsocks", profile_data)

        assert link is not None
        assert link.startswith("ss://")

    def test_generate_unknown_protocol(self):
        """Test generating link for unknown protocol."""
        profile_data = {"host": "test.example.com", "port": 443}

        link = generate_vpn_link("unknown_protocol", profile_data)

        assert link is None

    def test_generate_with_settings_overrides(self):
        """Test generating link with settings overrides."""
        profile_data = {
            "uuid": "test-uuid",
            "host": "test.example.com",
            "port": 443,
            "reality": {
                "public_key": "test_key",
                "default_sni": "google.com",
                "default_short_id": "test1234",
            },
            "security": "reality",
        }

        settings_overrides = {"sni": "max.ru"}

        link = generate_vpn_link("vless", profile_data, settings_overrides)

        assert link is not None
        assert "sni=max.ru" in link
