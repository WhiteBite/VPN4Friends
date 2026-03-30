"""Main FastAPI application for the Mini App backend."""

import json
import logging
import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect

from src.api.admin import router as admin_router
from src.api.routers.me import router as me_router
from src.api.routers.presets import router as presets_router
from src.api.routers.subscription import router as sub_router
from src.api.routers.system import router as system_router
from src.api.ws import manager as ws_manager
from src.database.repositories import UserRepository

logger = logging.getLogger(__name__)

app = FastAPI(
    title="VPN4Friends Mini App API",
    version="1.0.0",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    headers = getattr(exc, "headers", None) or {}
    headers["Access-Control-Allow-Origin"] = "*"
    headers["Access-Control-Allow-Methods"] = "*"
    headers["Access-Control-Allow-Headers"] = "*"
    return JSONResponse(
        {"detail": exc.detail},
        status_code=exc.status_code,
        headers=headers,
    )


# Allow Mini App frontend to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Mini App static files
# Priority: /app or other specific paths first, catch-all / last.
frontend_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "miniapp", "dist"
)

# API routes MUST be included before the catch-all static mount
app.include_router(admin_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(me_router, prefix="/api")
app.include_router(presets_router, prefix="/api")
app.include_router(sub_router, prefix="/api")

# Also mount WITHOUT prefix for Cloudflare tunnel (strips /api path)
app.include_router(admin_router)
app.include_router(system_router)
app.include_router(me_router)
app.include_router(presets_router)
app.include_router(sub_router)

if os.path.exists(frontend_path):
    # Mount specific /app path for the SPA
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="app")
    # The root mount should be the very LAST thing to avoid intercepting valid API routes
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, init_data: str = "", token: str = ""):
    """WebSocket endpoint for real-time notifications."""
    if not init_data and not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    import jwt

    from src.api.dependencies import JWT_ALGORITHM, _validate_telegram_data
    from src.bot.config import settings
    from src.database.session import session_factory

    telegram_id: int | None = None

    # 1. Try Token first
    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
            telegram_id = int(payload.get("sub"))
        except (jwt.PyJWTError, ValueError, TypeError):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    # 2. Fallback to initData
    if not telegram_id and init_data:
        try:
            validated_data = _validate_telegram_data(init_data)
            user_data = json.loads(validated_data.get("user", "{}"))
            telegram_id = int(user_data.get("id"))
        except (HTTPException, ValueError, TypeError):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    if not telegram_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        is_admin = user.is_admin
        await ws_manager.connect(websocket, user.id, is_admin)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            ws_manager.disconnect(websocket, user.id, is_admin)
