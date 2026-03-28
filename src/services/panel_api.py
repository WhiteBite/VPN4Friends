"""Abstract base class for VPN panel APIs (3X-UI, Hiddify, etc.)."""

from abc import ABC, abstractmethod
from typing import Any


class PanelAPI(ABC):
    """Common interface for VPN panel management.

    All panel adapters (XUIApi, HiddifyApi) must implement this interface.
    """

    @abstractmethod
    async def __aenter__(self) -> "PanelAPI": ...

    @abstractmethod
    async def __aexit__(self, *args: Any) -> None: ...

    @abstractmethod
    async def create_client(
        self, inbound_id: int, email: str, protocol: str, client_id: str | None = None
    ) -> dict[str, Any] | None:
        """Create a new VPN client.

        Returns dict with at least: client_id, email, protocol, inbound_id.
        Returns None on failure.
        """
        ...

    @abstractmethod
    async def delete_client(self, inbound_id: int, email: str) -> bool:
        """Delete a VPN client by email."""
        ...

    @abstractmethod
    async def add_client_to_all_inbounds(
        self, email: str, client_id: str, protocol: str = "vless"
    ) -> int:
        """Add a client to all enabled inbounds matching the protocol.

        Returns the number of inbounds successfully updated.
        """
        ...

    @abstractmethod
    async def remove_client_from_all_inbounds(self, email: str) -> int:
        """Remove a client by email from all enabled inbounds.

        Returns the number of inbounds successfully updated.
        """
        ...

    @abstractmethod
    async def get_client_traffic(self, email: str) -> dict[str, Any] | None:
        """Get traffic stats for a client.

        Returns dict with: upload, download (bytes).
        """
        ...

    @abstractmethod
    async def get_protocol_settings(self, inbound_id: int) -> dict[str, Any]:
        """Get protocol-specific settings (Reality keys, etc.)."""
        ...

    @abstractmethod
    async def get_online_clients(self) -> list[str]:
        """Get list of currently connected client emails."""
        ...

    @abstractmethod
    async def get_server_status(self) -> dict[str, Any]:
        """Get server status (uptime, traffic totals, client count)."""
        ...
