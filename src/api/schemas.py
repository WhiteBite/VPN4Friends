"""Pydantic schemas for the API."""

from typing import Any

from pydantic import BaseModel


class UserSchema(BaseModel):
    """User information."""

    full_name: str
    username: str | None


class PresetSchema(BaseModel):
    """Connection preset information."""

    id: int
    name: str
    app_type: str
    format: str


class ProfileSchema(BaseModel):
    """VPN profile information."""

    has_profile: bool
    protocol: str | None
    label: str | None
    sni: str | None
    available_snis: list[str] = []


class MeResponse(BaseModel):
    """Response model for the /me endpoint."""

    user: UserSchema
    profile: ProfileSchema
    presets: list[PresetSchema]


class SwitchProtocolRequest(BaseModel):
    protocol: str


class UpdateSNIRequest(BaseModel):
    sni: str


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


class UpdateSNIResponse(BaseModel):
    success: bool
    message: str
    sni: str | None = None


class GenericResponse(BaseModel):
    success: bool
    message: str


class PresetConfigResponse(BaseModel):
    type: str
    value: str
