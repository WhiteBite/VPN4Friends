from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import EndpointSchema, GenericResponse, ProtocolSchema, SupportMessageRequest
from src.bot.config import settings
from src.database.models import User
from src.database.session import get_session

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/ready")
async def ready_check() -> dict:
    """Readiness check endpoint."""
    return {"ready": True}


@router.get("/protocols", response_model=list[ProtocolSchema])
async def list_protocols() -> list[ProtocolSchema]:
    """Return available VPN protocols configured on the server.

    This endpoint is used by the Mini App frontend to render protocol
    selection chips instead of relying on hardcoded values.
    """
    # Use endpoints instead of protocols
    protocols = []
    seen = set()
    for ep in settings.endpoints:
        protocol_type = getattr(ep, "protocol", "vless")
        if protocol_type not in seen and protocol_type != "mtproto":
            seen.add(protocol_type)
            protocols.append(
                ProtocolSchema(
                    name=protocol_type,
                    label=protocol_type.upper(),
                    description=f"{protocol_type} protocol",
                    recommended=(protocol_type == "vless"),
                )
            )
    return protocols


@router.get("/endpoints", response_model=list[EndpointSchema])
async def list_endpoints() -> list[EndpointSchema]:
    """Return available server endpoints.

    This endpoint is used by the Mini App to show server selection.
    """
    return [
        EndpointSchema(
            name=ep.name,
            label=ep.label,
            host=ep.host,
            port=ep.port,
            is_relay=ep.is_relay,
            description=ep.description,
            category=getattr(ep, "category", "vpn"),
            country=getattr(ep, "country", "Unknown"),
            transport=getattr(ep, "transport", "vless") or "vless",
        )
        for ep in settings.endpoints
    ]


@router.post("/support", response_model=GenericResponse)
async def send_support_message(
    payload: SupportMessageRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Send a support message to admins."""
    from src.api.bot_utils import notify_admins
    from src.database.repositories.support_repo import SupportRepository

    repo = SupportRepository(session)
    await repo.save_message(user.id, payload.text)

    await notify_admins(
        f"📩 <b>Новое обращение в поддержку (через Mini App)</b>\n"
        f"👤 {user.full_name} (@{user.username or 'без_юзернейма'})\n\n"
        f"💬 {payload.text}",
        parse_mode="HTML",
    )

    await session.commit()
    return GenericResponse(success=True, message="Сообщение отправлено!")
