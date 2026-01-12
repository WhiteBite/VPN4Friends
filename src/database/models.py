"""SQLAlchemy models for the VPN bot."""

import enum
from datetime import datetime

from sqlalchemy import (JSON, BigInteger, Boolean, DateTime, Enum, ForeignKey,
                        String, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class RequestStatus(enum.Enum):
    """Status of VPN access request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    """Telegram user model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    requests: Mapped[list["VPNRequest"]] = relationship(back_populates="user")
    profiles: Mapped[list["VpnProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_vpn(self) -> bool:
        """Check if user has any active VPN profile."""
        return any(p.is_active for p in self.profiles)

    @property
    def active_profile(self) -> "VpnProfile | None":
        """Get the currently active VPN profile."""
        for profile in self.profiles:
            if profile.is_active:
                return profile
        return None

    @property
    def display_name(self) -> str:
        """Get display name with username if available."""
        if self.username:
            return f"{self.full_name} (@{self.username})"
        return self.full_name


class VpnProfile(Base):
    """Represents a user's VPN profile for a specific protocol."""

    __tablename__ = "vpn_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    protocol_name: Mapped[str] = mapped_column(String(50))
    profile_data: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profiles")


class VPNRequest(Base):
    """VPN access request from user to admin."""

    __tablename__ = "vpn_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    admin_comment: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="requests")
