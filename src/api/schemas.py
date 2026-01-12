"""Pydantic schemas for the API."""

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
