"""Pydantic schemas for the API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class UserSchema(BaseModel):
    """User information."""

    full_name: str
    username: str | None
    is_admin: bool = False


class PresetSchema(BaseModel):
    """Connection preset information."""

    id: int
    name: str
    app_type: str
    format: str


class ProfileSchema(BaseModel):
    """VPN profile information."""

    has_profile: bool
    request_status: str | None = None
    protocol: str | None = None
    label: str | None = None
    client_id: str | None = None
    sni: str | None = None


class MeResponse(BaseModel):
    """Response model for the /me endpoint."""

    user: UserSchema
    profile: ProfileSchema
    presets: list[PresetSchema]
    subscription_url: str | None = None


class SwitchProtocolRequest(BaseModel):
    protocol: str


class RequestVPNSchema(BaseModel):
    comment: str | None = None


class SupportMessageRequest(BaseModel):
    text: str




class CreatePresetRequest(BaseModel):
    name: str
    app_type: str
    format: str
    options: dict[str, Any] | None = None


class ProtocolSchema(BaseModel):
    """VPN protocol information exposed to the Mini App."""

    name: str
    label: str
    description: str
    recommended: bool


class SwitchProtocolResponse(BaseModel):
    success: bool
    message: str
    protocol: str | None = None
    link: str | None = None




class GenericResponse(BaseModel):
    success: bool
    message: str


class PresetConfigResponse(BaseModel):
    type: str
    value: str


# ----- New schemas for Mini App redesign -----


class LinkResponse(BaseModel):
    """Direct VPN link (no preset needed)."""

    link: str
    protocol: str
    endpoint: str | None = None


class StatsResponse(BaseModel):
    """Traffic statistics."""

    protocol: str
    upload: int
    download: int
    upload_formatted: str
    download_formatted: str


class EndpointSchema(BaseModel):
    """Server endpoint information."""

    name: str
    label: str
    host: str
    port: int
    is_relay: bool
    description: str
    category: str = "vpn"
    country: str = "Unknown"
    transport: str = "vless"
    status: str = "unknown"
    latency: float | None = None


class SelectEndpointRequest(BaseModel):
    endpoint: str


class ChatPreviewSchema(BaseModel):
    user_id: int
    telegram_id: int
    full_name: str
    username: str | None
    last_message: str
    last_message_at: datetime
    is_last_from_admin: bool


class ChatMessageSchema(BaseModel):
    id: int
    is_from_admin: bool
    text: str
    created_at: datetime


class SendMessageSchema(BaseModel):
    text: str


class AdminRequestSchema(BaseModel):
    id: int
    user_id: int
    telegram_id: int
    full_name: str
    username: str | None
    status: str
    created_at: datetime
    user_comment: str | None = None


class BroadcastRequestSchema(BaseModel):
    message: str
    target: str = "all"  # all, with_vpn, without_vpn
