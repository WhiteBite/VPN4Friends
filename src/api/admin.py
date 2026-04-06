"""Admin API routes for managing VPN requests."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import (
    AdminRequestSchema,
    BroadcastRequestSchema,
    ChatMessageSchema,
    ChatPreviewSchema,
    GenericResponse,
    SendMessageSchema,
)
from src.bot.config import settings
from src.database.models import User
from src.database.repositories import RequestRepository, SupportRepository, UserRepository
from src.database.session import get_session
from src.services.vpn_service import VPNService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staff", tags=["admin"])


async def _send_broadcast_task(message: str, target: str):
    from src.api.bot_utils import create_bot
    from src.database.session import session_factory

    async with create_bot() as bot:
        async with session_factory() as session:
            user_repo = UserRepository(session)
            if target == "all":
                users = await user_repo.get_all()
            elif target == "with_vpn":
                users = await user_repo.get_all_with_vpn()
            else:
                all_users = await user_repo.get_all()
                users = [u for u in all_users if not u.has_vpn]

        success = 0
        for u in users:
            try:
                await bot.send_message(
                    u.telegram_id, f"📢 <b>Объявление:</b>\n\n{message}", parse_mode="HTML"
                )
                success += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast from API to {u.telegram_id}: {e}")
            await asyncio.sleep(0.05)

        logger.info(f"API Broadcast finished. Sent to {success}/{len(users)}")


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to check if current user is admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin privileges",
        )
    return user


@router.get("/requests", response_model=list[AdminRequestSchema])
async def get_requests(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[AdminRequestSchema]:
    """Get all pending VPN requests."""
    req_repo = RequestRepository(session)
    requests = await req_repo.get_all_pending()

    return [
        AdminRequestSchema(
            id=req.id,
            user_id=req.user.id,
            telegram_id=req.user.telegram_id,
            full_name=req.user.full_name,
            username=req.user.username,
            status=req.status.value,
            created_at=req.created_at,
            user_comment=req.user_comment,
            protocol=req.protocol,
            location=req.location,
        )
        for req in requests
    ]


@router.post("/requests/{request_id}/approve", response_model=GenericResponse)
async def approve_request(
    request_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Approve a VPN request."""

    req_repo = RequestRepository(session)
    request = await req_repo.get_by_id(request_id)
    if not request or request.status.value != "pending":
        raise HTTPException(status_code=404, detail="Pending request not found")

    vpn_service = VPNService(session)
    # Let VPNService find the best endpoint based on user request (protocol/location)
    success, message = await vpn_service.approve_request(request_id)

    if not success:
        return GenericResponse(success=False, message=message)

    # Notify user via WebSockets
    from src.api.ws import manager as ws_manager

    await ws_manager.send_personal_message({"type": "REQUEST_APPROVED"}, request.user.id)
    await ws_manager.broadcast_to_admins(
        {"type": "REQUEST_STATUS_CHANGED", "request_id": request.id, "status": "approved"}
    )

    # Notify user via Telegram bot
    from src.api.bot_utils import notify_user

    await notify_user(
        request.user.telegram_id,
        "✅ <b>Заявка одобрена!</b>\n\n"
        "Твой VPN готов. Открой приложение, чтобы получить настройки.",
        parse_mode="HTML",
    )

    return GenericResponse(success=True, message="Заявка одобрена.")


@router.post("/requests/{request_id}/reject", response_model=GenericResponse)
async def reject_request(
    request_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Reject a VPN request."""
    req_repo = RequestRepository(session)
    request = await req_repo.get_by_id(request_id)
    if not request or request.status.value != "pending":
        raise HTTPException(status_code=404, detail="Pending request not found")

    await req_repo.reject(request)

    # Notify user via WebSockets
    from src.api.ws import manager as ws_manager

    await ws_manager.send_personal_message({"type": "REQUEST_REJECTED"}, request.user.id)
    await ws_manager.broadcast_to_admins(
        {"type": "REQUEST_STATUS_CHANGED", "request_id": request.id, "status": "rejected"}
    )

    from src.api.bot_utils import notify_user

    await notify_user(
        request.user.telegram_id,
        "❌ <b>Заявка отклонена.</b>\n\nМодератор отклонил запрос.",
        parse_mode="HTML",
    )

    return GenericResponse(success=True, message="Заявка отклонена.")


@router.post("/broadcast", response_model=GenericResponse)
async def broadcast_message(
    payload: BroadcastRequestSchema,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_admin),
) -> GenericResponse:
    """Trigger a bot broadcast to users from the Mini App."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    background_tasks.add_task(_send_broadcast_task, payload.message, payload.target)
    return GenericResponse(success=True, message="Рассылка началась в фоновом режиме.")


@router.get("/chats", response_model=list[ChatPreviewSchema])
async def get_chats(
    user: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> list[ChatPreviewSchema]:
    support_repo = SupportRepository(session)
    chats = await support_repo.get_all_chats()

    return [
        ChatPreviewSchema(
            user_id=ch["user"].id,
            telegram_id=ch["user"].telegram_id,
            full_name=ch["user"].full_name,
            username=ch["user"].username,
            last_message=ch["last_message"].text,
            last_message_at=ch["last_message"].created_at,
            is_last_from_admin=ch["last_message"].is_from_admin,
        )
        for ch in chats
    ]


@router.get("/chats/{user_id}", response_model=list[ChatMessageSchema])
async def get_chat_history(
    user_id: int, user: User = Depends(require_admin), session: AsyncSession = Depends(get_session)
) -> list[ChatMessageSchema]:
    support_repo = SupportRepository(session)
    messages = await support_repo.get_user_chat_history(user_id)
    return [
        ChatMessageSchema(
            id=m.id, is_from_admin=m.is_from_admin, text=m.text, created_at=m.created_at
        )
        for m in messages
    ]


@router.post("/chats/{user_id}", response_model=ChatMessageSchema)
async def send_chat_message(
    user_id: int,
    payload: SendMessageSchema,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ChatMessageSchema:
    import logging

    from src.keyboards.user_reply_kb import get_reply_to_admin_kb

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    support_repo = SupportRepository(session)
    saved_msg = await support_repo.save_message(user_id, payload.text, is_from_admin=True)
    await session.commit()

    # Dispatch to Telegram Bot
    from src.api.bot_utils import create_bot

    async with create_bot() as bot:
        try:
            await bot.send_message(
                target_user.telegram_id,
                f"💬 Сообщение от админа:\n\n{payload.text}",
                reply_markup=get_reply_to_admin_kb(),
            )
        except Exception as e:
            logging.warning(f"Failed to send direct message to {target_user.telegram_id}: {e}")

    return ChatMessageSchema(
        id=saved_msg.id,
        is_from_admin=saved_msg.is_from_admin,
        text=saved_msg.text,
        created_at=saved_msg.created_at,
    )


@router.delete("/users/{user_id}/vpn", response_model=GenericResponse)
async def revoke_user_vpn(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Fully revoke a user's VPN access.

    Removes the client from all X-UI panels and deletes the profile from the bot DB.
    After this, the user can request VPN again from scratch.
    """
    user_repo = UserRepository(session)
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not target_user.has_vpn:
        return GenericResponse(success=False, message="У пользователя нет активного VPN.")

    vpn_service = VPNService(session)
    revoked = await vpn_service.revoke_vpn(target_user)

    if not revoked:
        return GenericResponse(success=False, message="Не удалось отозвать VPN.")

    # Notify via WebSocket
    from src.api.ws import manager as ws_manager

    await ws_manager.send_personal_message({"type": "VPN_REVOKED"}, target_user.id)
    await ws_manager.broadcast_to_admins(
        {"type": "USER_VPN_REVOKED", "user_id": target_user.id, "username": target_user.username}
    )

    display = f"@{target_user.username}" if target_user.username else target_user.full_name
    logger.info(f"Admin revoked VPN for user {display} (id={target_user.id})")
    return GenericResponse(success=True, message=f"VPN для {display} полностью удалён.")


@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """List all known users with their VPN status and traffic stats."""
    user_repo = UserRepository(session)
    users = await user_repo.get_all()

    vpn_service = VPNService(session)
    # Fetch stats once for all panels
    all_stats = await vpn_service.get_all_users_stats()

    result = []
    for u in users:
        profile = u.active_profile
        email = profile.profile_data.get("email") if profile else None

        # Get stats from the aggregated map
        user_stats = (
            all_stats.get(email, {"upload": 0, "download": 0})
            if email
            else {"upload": 0, "download": 0}
        )

        # Read from column or fallback to profile.profile_data dictionary for older ones
        client_id = getattr(profile, "client_id", None) if profile else None
        if not client_id and profile and profile.profile_data:
            client_id = profile.profile_data.get("client_id")

        result.append(
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "username": u.username,
                "full_name": u.full_name,
                "has_vpn": u.has_vpn,
                "protocol": profile.protocol_name if profile else None,
                "email": email,
                "client_id": client_id,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "stats": {"upload": user_stats["upload"], "download": user_stats["download"]},
            }
        )
    return result


# ---------------------------------------------------------------------------
#  Hot-reload config + re-provision
# ---------------------------------------------------------------------------


class ConfigReloadRequest(BaseModel):
    """Request body for the config hot-reload endpoint."""

    config_b64: str  # base64-encoded vpn-config.json


class ConfigReloadResponse(BaseModel):
    success: bool
    message: str
    endpoints_count: int = 0
    nodes_count: int = 0


@router.post("/config/reload", response_model=ConfigReloadResponse)
async def reload_config(
    payload: ConfigReloadRequest,
    admin: User = Depends(require_admin),
) -> ConfigReloadResponse:
    """Hot-reload VPN config and re-run provisioning without CI/CD.

    Accepts a base64-encoded ``vpn-config.json``, parses it, swaps the
    global ``settings`` object in-place, and kicks off the auto-provisioner
    in the background.
    """
    import base64
    import json

    from src.bot.config import ServerEndpoint, settings

    # 1. Decode & parse -------------------------------------------------------
    try:
        raw = base64.b64decode(payload.config_b64)
        config = json.loads(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64/JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Config must be a JSON object")

    # 2. Validate & swap endpoints --------------------------------------------
    try:
        new_endpoints = [ServerEndpoint(**e) for e in config.get("endpoints", [])]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse endpoints: {exc}") from exc

    new_nodes = config.get("nodes", {})

    # Hot-swap on the singleton
    settings.endpoints = new_endpoints
    settings.endpoints_config = json.dumps(config.get("endpoints", []))
    settings.nodes_config = new_nodes
    settings.nodes_config_raw = json.dumps(new_nodes)

    logger.info(
        f"Config hot-reloaded by admin {admin.username}: "
        f"{len(new_endpoints)} endpoints, {len(new_nodes)} nodes"
    )

    # 3. Re-provision in background -------------------------------------------
    async def _reprovision():
        from src.database import session_factory
        from src.database.repositories import UserRepository
        from src.services.xui_provisioner import (
            sync_node_clients,
            sync_node_inbounds,
            sync_node_routing,
        )

        try:
            # Phase 1: routing / outbounds
            for node_name, node_cfg in new_nodes.items():
                try:
                    await sync_node_routing(node_name, node_cfg)
                except Exception as e:
                    logger.error(f"Re-provision routing {node_name}: {e}")

            # Phase 2: inbounds + clients
            async with session_factory() as session:
                user_repo = UserRepository(session)
                users_with_vpn = await user_repo.get_all_with_vpn()

                for ep in new_endpoints:
                    if ep.panel_type != "3xui":
                        continue
                    if not ep.panel_config or "api_url" not in ep.panel_config:
                        continue
                    try:
                        ok = await sync_node_inbounds(ep)
                        if ok:
                            await sync_node_clients(ep, users_with_vpn)
                    except Exception as e:
                        logger.error(f"Re-provision {ep.name}: {e}")

            logger.info("Re-provisioning after config reload complete")
        except Exception as exc:
            logger.error(f"Re-provisioning failed: {exc}")

    asyncio.create_task(_reprovision())

    return ConfigReloadResponse(
        success=True,
        message="Config reloaded, provisioning started in background.",
        endpoints_count=len(new_endpoints),
        nodes_count=len(new_nodes),
    )


# ---------------------------------------------------------------------------
#  Endpoint management (CRUD)
# ---------------------------------------------------------------------------


@router.get("/endpoints")
async def list_endpoints(
    admin: User = Depends(require_admin),
) -> list[dict]:
    """List all configured VPN endpoints with their subscription group info."""
    from src.api.routers.subscription import GROUP_ORDER

    result = []
    for ep in settings.endpoints:
        group_order, group_label = GROUP_ORDER.get(ep.group, (99, ep.group))
        result.append(
            {
                "name": ep.name,
                "label": ep.label,
                "host": ep.host,
                "port": ep.port,
                "protocol": ep.protocol,
                "transport": ep.transport,
                "country": ep.country,
                "category": ep.category,
                "is_relay": ep.is_relay,
                "group": ep.group,
                "group_label": group_label,
                "sub_label": ep.sub_label,
                "sort_order": ep.sort_order,
                "visible_in_sub": ep.visible_in_sub,
                "routing_tag": ep.routing_tag,
                "has_panel": bool(ep.panel_config and ep.panel_config.get("api_url")),
            }
        )

    result.sort(key=lambda x: (GROUP_ORDER.get(x["group"], (99, ""))[0], x["sort_order"]))
    return result


class EndpointCreateRequest(BaseModel):
    """Request body for creating a new endpoint."""

    name: str
    label: str
    host: str
    port: int = 443
    protocol: str = "vless"
    transport: str = "tcp"
    security: str = "reality"
    sni: str = "max.ru"
    flow: str | None = None
    country: str = "Финляндия"
    category: str = "vpn"
    is_relay: bool = False
    group: str = "fast"
    sub_label: str = ""
    sort_order: int = 100
    routing_tag: str = "direct"
    node: str | None = None  # Node name from nodes_config (e.g. "finland", "germany")

    # Optional fields for REALITY
    pbk: str | None = None
    sid: str | None = None
    pk: str | None = None
    serviceName: str | None = None
    path: str | None = None


@router.post("/endpoints", response_model=GenericResponse)
async def create_endpoint(
    payload: EndpointCreateRequest,
    admin: User = Depends(require_admin),
) -> GenericResponse:
    """Create a new VPN endpoint and optionally provision it on the server."""
    from src.bot.config import ServerEndpoint

    # Check for duplicate
    existing = [ep for ep in settings.endpoints if ep.name == payload.name]
    if existing:
        return GenericResponse(success=False, message=f"Endpoint '{payload.name}' already exists")

    # Look up panel_config from node
    panel_config = {}
    if payload.node and payload.node in settings.nodes_config:
        node_cfg = settings.nodes_config[payload.node]
        panel_config = node_cfg.get("panel_config", {})

    # Build the endpoint
    ep_data = payload.model_dump(exclude_none=True)
    ep_data.pop("node", None)
    ep_data["panel_config"] = panel_config
    ep_data["panel_type"] = "3xui" if panel_config else "none"
    ep_data["visible_in_sub"] = True

    new_ep = ServerEndpoint(**ep_data)
    settings.endpoints.append(new_ep)

    logger.info(f"Admin {admin.username} created endpoint: {payload.name}")

    # Auto-provision if we have panel config
    if panel_config and panel_config.get("api_url"):
        asyncio.create_task(_provision_single_endpoint(new_ep))

    return GenericResponse(success=True, message=f"Endpoint '{payload.name}' created successfully")


@router.delete("/endpoints/{name}", response_model=GenericResponse)
async def delete_endpoint(
    name: str,
    admin: User = Depends(require_admin),
) -> GenericResponse:
    """Remove an endpoint from the configuration."""
    idx = None
    for i, ep in enumerate(settings.endpoints):
        if ep.name == name:
            idx = i
            break

    if idx is None:
        raise HTTPException(status_code=404, detail=f"Endpoint '{name}' not found")

    settings.endpoints.pop(idx)
    logger.info(f"Admin {admin.username} deleted endpoint: {name}")
    return GenericResponse(success=True, message=f"Endpoint '{name}' deleted")


@router.post("/endpoints/{name}/sync", response_model=GenericResponse)
async def sync_endpoint(
    name: str,
    admin: User = Depends(require_admin),
) -> GenericResponse:
    """Force-sync all clients to a specific endpoint."""
    target_ep = None
    for ep in settings.endpoints:
        if ep.name == name:
            target_ep = ep
            break

    if not target_ep:
        raise HTTPException(status_code=404, detail=f"Endpoint '{name}' not found")

    if not target_ep.panel_config or not target_ep.panel_config.get("api_url"):
        return GenericResponse(success=False, message="Endpoint has no panel config (relay?)")

    asyncio.create_task(_provision_single_endpoint(target_ep))
    return GenericResponse(success=True, message=f"Sync started for '{name}'")


async def _provision_single_endpoint(ep) -> None:
    """Provision a single endpoint: create inbound + sync clients."""
    from src.database import session_factory
    from src.database.repositories import UserRepository
    from src.services.xui_provisioner import sync_node_clients, sync_node_inbounds

    try:
        ok = await sync_node_inbounds(ep)
        if ok:
            async with session_factory() as session:
                user_repo = UserRepository(session)
                users_with_vpn = await user_repo.get_all_with_vpn()
                await sync_node_clients(ep, users_with_vpn)
        logger.info(f"Provisioned endpoint: {ep.name}")
    except Exception as e:
        logger.error(f"Failed to provision endpoint {ep.name}: {e}")


@router.post("/sync-all", response_model=GenericResponse)
async def sync_all_users(
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> GenericResponse:
    """Trigger a global synchronization of all VPN users to all active panels."""
    user_repo = UserRepository(session)
    users = await user_repo.get_all_with_vpn()

    if not users:
        return GenericResponse(success=False, message="Нет пользователей с активным VPN.")

    async def _sync_task():
        # Create a new session for the background task
        from src.database.session import session_factory

        async with session_factory() as bg_session:
            svc = VPNService(bg_session)
            success = 0
            for u in users:
                profile = u.active_profile
                if not profile:
                    continue
                email = profile.profile_data.get("email")
                client_id = profile.client_id or profile.profile_data.get("client_id")
                protocol = profile.protocol_name

                if email and client_id:
                    try:
                        res = await svc.sync_client_to_all_panels(email, client_id, protocol)
                        if res:
                            success += 1
                    except Exception as e:
                        logger.error(f"Background sync error for {email}: {e}")
                await asyncio.sleep(0.1)
            logger.info(f"Global sync finished. {success}/{len(users)} users processed.")

    background_tasks.add_task(_sync_task)
    return GenericResponse(
        success=True,
        message=f"Глобальная синхронизация для {len(users)} пользователей запущена в фоновом режиме.",
    )


@router.get("/servers/status")
async def get_servers_status(admin: User = Depends(require_admin)) -> list[dict]:
    """Fetch live status metrics from all configured endpoints/nodes."""
    from src.services.xui_api import XUIApi

    # We want to check unique instances by api_url to avoid polling the same panel multiple times
    # Wait, the config is per 'node'. Let's iterate over nodes in settings.nodes_config
    results = []

    async def fetch_panel_status(panel_name: str, panel_cfg: dict):
        if not panel_cfg or not panel_cfg.get("api_url"):
            return {"name": panel_name, "status": "offline", "error": "Not a panel"}

        try:
            async with XUIApi(panel_cfg) as api:
                from asyncio import wait_for

                status = await wait_for(api.get_server_status(), timeout=5.0)
                return {"name": panel_name, **status}
        except Exception as e:
            logger.warning(f"Failed to fetch status for {panel_name}: {e}")
            return {"name": panel_name, "status": "offline", "error": str(e)}

    tasks = []
    seen_urls = set()

    for ep in settings.endpoints:
        if ep.panel_type == "3xui" and ep.panel_config:
            api_url = ep.panel_config.get("api_url")
            if api_url and api_url not in seen_urls:
                seen_urls.add(api_url)
                tasks.append(fetch_panel_status(ep.label or ep.name, ep.panel_config))
        elif ep.panel_type in ("mtproto", "socks5"):
            results.append(
                {
                    "name": ep.label or ep.name,
                    "online": True,
                    "clients": "?",
                    "inbounds": 1,
                    "upload": 0,
                    "download": 0,
                }
            )

    if tasks:
        node_statuses = await asyncio.gather(*tasks)
        results.extend(node_statuses)

    return results
