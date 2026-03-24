"""Abstract base class for VPN panel APIs (3X-UI, Hiddify, etc.)."""

from abc import ABC, abstractmethod
from typing import Any


class PanelAPI(ABC):
    """Common interface for VPN panel management.

    All panel adapters (XUIApi, HiddifyApi) must implement this interface.
    """

    @abstractmethod
    async def __aenter__(self) -> "PanelAPI":
        ...

    @abstractmethod
    async def __aexit__(self, *args: Any) -> None:
        ...

    @abstractmethod
    async def create_client(
        self, inbound_id: int, email: str, protocol: str
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
