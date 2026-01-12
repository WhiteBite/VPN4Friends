# TODO / Roadmap for VPN4Friends (Architecture & Mini App)

This document fixes the current architectural vision and feature roadmap so that another AI (or developer) can continue work without re‑designing everything from scratch.

The project is a Telegram bot (aiogram) + 3X-UI panel on a single VPS. The goal is to let users manage **their VPN connection options themselves** (protocol, SNI, app‑specific configs) while keeping all dangerous server settings under the owner’s control.

---

## 1. High‑Level Goals

- **Single VPS + 3X-UI**: all server‑side protocol/inbound settings are configured only by the owner in the panel.
- **User self‑service**:
  - request VPN access through the bot;
  - choose **protocol** (VLESS / Shadowsocks / others configured in `PROTOCOLS_CONFIG`);
  - choose **SNI / domain** from a safe, preconfigured list;
  - generate configs for different apps (Throne, V2RayN, Nekoray, Hiddify, etc.).
- **Safety constraints**:
  - user must **not** be able to change shared inbound settings in 3X‑UI (port, reality keys, flow, etc.);
  - user may only choose from variants explicitly allowed by server configuration (protocol list, SNI list).
- **Production‑ready architecture**: clear separation of
  - domain models,
  - repositories (DB access),
  - business services,
  - Telegram bot layer,
  - Mini App backend (FastAPI).

---

## 2. Domain & Data Model

Existing models (see `src/database/models.py`):

- `User`
- `VpnProfile` (user’s VPN profile linked to a client in 3X-UI)
- `VPNRequest` (request from user to admin)

### 2.1. Extend `VpnProfile`

Target shape (conceptual):

- `id: int`
- `user_id: int -> users.id`
- `protocol_name: str`  
  Name of protocol (`"vless"`, `"shadowsocks"`, …), matching `Protocol.name` from config.
- `profile_data: JSON`  
  Data returned from `XUIApi` when creating client **plus** protocol‑specific settings fetched from `get_protocol_settings` (e.g. port, remark, reality settings).
- `is_active: bool` (already exists)
- **NEW** `label: str | None`  
  Optional human‑friendly label, e.g. `"Main VLESS"`.
- **NEW** `settings: JSON`  
  User‑level overrides, especially:
  - selected SNI (from allowed list),
  - possibly other per‑user flags for generation.

Notes:

- For now we still keep a single “main” active profile per user, but the model should not hard‑enforce this (no uniqueness constraint at DB level). Higher‑level logic may enforce “one active per user” if needed.

### 2.2. New entity: `ConnectionPreset`

Add a new table/model `ConnectionPreset` (not yet implemented in code):

Fields (conceptual):

- `id: int`
- `user_id: int -> users.id`
- `profile_id: int -> vpn_profiles.id`
- `name: str`  
  Example: `"Throne / PC"`, `"Phone / V2RayNG"`.
- `app_type: str`  
  Enum‑like string: `"throne"`, `"v2rayn"`, `"nekoray"`, `"hiddify"`, etc.
- `format: str`  
  How config is represented: `"vless_uri"`, `"ss_uri"`, `"clash_yaml"`, …
- `options: JSON`  
  Client‑side preferences, e.g.: DNS, additional flags, etc.

Semantics:

- One `VpnProfile` (real client in 3X‑UI) can have **multiple** `ConnectionPreset` records: different devices / apps / formats.

---

## 3. Configuration (`PROTOCOLS_CONFIG`)

`src/bot/config.py` already defines:

```python
class Protocol(BaseModel):
    name: str
    inbound_id: int
    label: str
    description: str
    recommended: bool = False
```

and `Settings.protocols: list[Protocol]` populated from `PROTOCOLS_CONFIG`.

Convention for `PROTOCOLS_CONFIG` in `.env` (JSON array):

```json
[
  {
    "name": "vless",
    "inbound_id": 1,
    "label": "VLESS Reality (recommended)",
    "description": "Fast and stable for most users",
    "recommended": true
  },
  {
    "name": "shadowsocks",
    "inbound_id": 2,
    "label": "Shadowsocks",
    "description": "For legacy clients or some networks",
    "recommended": false
  }
]
```

Notes:

- Owner of the VPS adds more entries as needed.
- Each `Protocol` corresponds to a specific inbound in 3X‑UI.

---

## 4. Services (Business Logic)

### 4.1. `VPNService` (exists, to be extended)

Current responsibilities:

- create request (`create_request`)
- approve request (`approve_request`) → creates client in X‑UI, stores `VpnProfile`
- reject request
- revoke VPN (`revoke_vpn`)
- get user stats, get active VPN link, get pending requests, etc.

**Planned extensions (to implement):**

1. `switch_protocol(user: User, protocol_name: str) -> VpnProfile`

   - Load current active profile for the user (if any).
   - If a profile exists:
     - use `XUIApi.delete_client(inbound_id, email)` to remove the old client from the old inbound;
     - deactivate or mark old profile as inactive.
   - Look up `Protocol` by name via `settings.get_protocol(protocol_name)`.
   - Use `XUIApi.create_client(inbound_id=protocol.inbound_id, email=..., protocol=protocol.name)` to create a new client.
   - Use `XUIApi.get_protocol_settings(protocol.inbound_id)` to fetch inbound‑level settings (including SNI list for VLESS).
   - Store combined data into `VpnProfile.profile_data` and set `protocol_name`.
   - Initialize `settings` JSON (e.g. default selected SNI).
   - Return the new active `VpnProfile`.

2. `update_profile_settings(user: User, *, sni: str | None = None, **kwargs) -> VpnProfile`

   - Load user’s active profile.
   - Fetch protocol settings for the corresponding inbound (optional cache):
     - for VLESS, we care about `realitySettings.serverNames`.
   - If `sni` is provided:
     - verify that it is included in the allowed `serverNames` list;
     - store chosen SNI in `VpnProfile.settings` (e.g. under `{"sni": "..."}`).
   - Do **not** call `update_inbound` – we never modify shared inbound settings.
   - Return updated profile.

3. `get_user_profile(user: User) -> VpnProfile | None`

   - Utility to obtain current active profile (existing logic via `user.active_profile`).

### 4.2. `PresetService` (new service)

Responsibilities:

- CRUD for `ConnectionPreset`.
- Generating final configs for clients.

Methods (conceptual):

- `list_presets(user: User) -> list[ConnectionPreset]`
- `create_preset(user: User, app_type: str, format: str, options: dict) -> ConnectionPreset`
  - Use user’s active `VpnProfile` as `profile_id`.
- `update_preset(user: User, preset_id: int, ...) -> ConnectionPreset`
- `delete_preset(user: User, preset_id: int) -> None`
- `generate_config(user: User, preset_id: int) -> dict`
  - Load preset and associated profile.
  - Combine:
    - `VpnProfile.profile_data` (raw client + inbound info),
    - `VpnProfile.settings` (selected SNI, etc.),
    - `preset.options`.
  - Delegate to proper generator based on `preset.format`:
    - `generate_vless_url(profile_data_with_overrides)`;
    - `generate_shadowsocks_url(...)` (to be truly implemented – currently placeholder);
    - potential YAML generators for Clash/Hiddify.
  - Return a structure that Mini App can render, e.g.:

    ```json
    { "type": "uri", "value": "vless://..." }
    ```

    or

    ```json
    { "type": "file", "filename": "config.yaml", "content": "..." }
    ```

---

## 5. Mini App Backend (FastAPI)

Location: new module `src/api/main.py` (not implemented yet).

### 5.1. Authentication of Mini App

- UI is a Telegram WebApp launched from the bot (button with `web_app`).
- In the browser, JS gets `window.Telegram.WebApp.initData`.
- All requests to backend include `X-Telegram-Init-Data` header.
- FastAPI dependency:
  - validates `initData` signature using `bot_token` (standard Telegram WebApp auth);
  - extracts `user_id` and basic user info;
  - loads or creates `User` in DB;
  - provides `current_user` to endpoints.

### 5.2. Planned API endpoints

**`GET /me`**

- Returns consolidated state for current user:

```json
{
  "user": {
    "full_name": "...",
    "username": "..."
  },
  "profile": {
    "has_profile": true,
    "protocol": "vless",
    "label": "VLESS Reality (recommended)",
    "sni": "current.sni.example",
    "available_snis": ["current.sni.example", "alt.sni.example"]
  },
  "presets": [
    {
      "id": 1,
      "name": "Throne / PC",
      "app_type": "throne",
      "format": "vless_uri"
    }
  ]
}
```

**`POST /me/protocol`**

- Body:

```json
{ "protocol_name": "vless" }
```

- Uses `VPNService.switch_protocol`.
- Response: updated `profile` block as in `/me`.

**`POST /me/sni`**

- Body:

```json
{ "sni": "chosen.sni.example" }
```

- Uses `VPNService.update_profile_settings` with SNI.
- Validates that `sni` is allowed for the current inbound.
- Response: updated `profile` block.

**`GET /presets`**

- Returns list of user’s presets:

```json
[
  {"id": 1, "name": "Throne / PC", "app_type": "throne", "format": "vless_uri"}
]
```

**`POST /presets`**

- Body:

```json
{
  "name": "Throne / PC",
  "app_type": "throne",
  "format": "vless_uri",
  "options": {"dns": "1.1.1.1"}
}
```

- Creates new `ConnectionPreset` linked to current active `VpnProfile`.

**`GET /presets/{id}/config`**

- Returns generated config for given preset:

```json
{ "type": "uri", "value": "vless://..." }
```

or (for file‑based formats):

```json
{
  "type": "file",
  "filename": "config.yaml",
  "content": "..."  // raw text or base64; to be decided on implementation
}
```

---

## 6. Bot UX integration

Telegram bot (aiogram) will:

- keep basic flows as‑is:
  - `/start`, `/menu`, `/link`, `/stats`, `/support`, admin panel, approvals;
- add a button in main user menu: **"Мои настройки VPN"** that opens the Mini App via `web_app`.

The Mini App will handle:

- protocol switching;
- SNI selection (from allowed list);
- preset management (per‑app configs);
- obtaining final configs/links/QR codes.

The bot itself will continue to support quick commands like `/link` for basic users who don’t need the Mini App.

---

## 7. Implementation Tasks (for future work)

1. **DB & models**
   - Add `settings` and optional `label` to `VpnProfile`.
   - Introduce `ConnectionPreset` model and table.
   - Add corresponding repositories (`PresetRepository`) and update existing ones if needed.

2. **Services**
   - Extend `VPNService` with `switch_protocol`, `update_profile_settings`, `get_user_profile`.
   - Implement `PresetService` with CRUD + `generate_config` using existing `url_generator` and future format generators.

3. **XUI API enhancements**
   - Ensure `XUIApi.get_protocol_settings` returns **full** SNI/serverNames list (not just first value).
   - Keep `create_client` / `delete_client` stable for all supported protocols.

4. **Mini App backend (FastAPI)**
   - Create `src/api/main.py` with described endpoints.
   - Implement Telegram WebApp auth (validating `initData`).
   - Wire DI for `AsyncSession`, `VPNService`, `PresetService`.

5. **Bot integration**
   - Add `web_app` button to open Mini App in main user menu.
   - Optionally add simple text‑only fallbacks for users without WebApp support.

6. **DevOps**
   - Update `Dockerfile` / `docker-compose.yml` to run both bot and FastAPI (either in one process manager or separate services).
   - Extend CI/CD to build & deploy the updated backend.

This document should be treated as the authoritative high‑level specification for future refactors and Mini App integration. Another AI can use it as a starting point to implement the remaining pieces without re‑discovering the design decisions.
