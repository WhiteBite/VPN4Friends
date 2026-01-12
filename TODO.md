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

## 7. Implementation Status & Tasks

This section reflects the **current** state of implementation and a detailed list of
remaining work. It is split into **Completed** and **Planned** items so another
developer can immediately understand what is done and what is left.

### 7.1. Completed

1. **DB & models**
   - `VpnProfile` extended with:
     - `label: str | None` — optional human‑friendly label.
     - `settings: JSON | None` — user‑level overrides (e.g. selected SNI).
   - New model `ConnectionPreset` added with fields:
     - `user_id`, `profile_id`, `name`, `app_type`, `format`, `options`.
   - Relationships:
     - `User.profiles` and `User.presets` wired with cascade delete.
     - `ConnectionPreset.profile` references `VpnProfile`.

2. **Repositories**
   - `PresetRepository` implemented:
     - `create(user, profile, name, app_type, format, options)`.
     - `get_by_id(preset_id)`.
     - `get_by_user(user)`.
     - `delete(preset)`.
   - `UserRepository` updated:
     - `create_vpn_profile`, `deactivate_all_profiles`, `delete_active_profile`,
       `update_vpn_profile` for working with `VpnProfile`.

3. **Services (business logic)**
   - `VPNService`:
     - Базовые методы: `create_request`, `approve_request`, `reject_request`,
       `revoke_vpn`, `get_user_stats`, `get_active_vpn_link`, `get_pending_requests`,
       `get_all_users_with_vpn`.
     - Расширения для мульти‑протокола и SNI:
       - `approve_request(request_id, protocol_name)` — создаёт клиента в нужном
         inbound, сохраняет `VpnProfile`, генерирует ссылку через
         `generate_vpn_link`.
       - `switch_protocol(user, protocol_name)` — ревокнет старый профиль,
         создаст новый в другом inbound и вернёт свежую ссылку.
       - `update_profile_settings(user, sni)` — валидирует SNI по списку из
         `XUIApi.get_protocol_settings` и сохраняет в `VpnProfile.settings`.
       - `get_active_vpn_link(user)` — генерирует ссылку, учитывая
         `VpnProfile.settings` (например, выбранный SNI).
   - `PresetService`:
     - `create_preset(user, name, app_type, format, options)` — создаёт пресет для
       активного профиля.
     - `get_user_presets(user)` — список пресетов пользователя.
     - `delete_preset(user, preset_id)` и `get_preset_for_user(user, preset_id)` —
       безопасная работа только со «своими» пресетами.
     - `generate_config(preset)` — для форматов `*_uri` возвращает структуру
       `{ "type": "uri", "value": "vless://..." }` с учётом `profile.settings`.

4. **XUI API enhancements**
   - `XUIApi.get_protocol_settings(inbound_id)` реализован для VLESS‑Reality:
     - Парсит `streamSettings.realitySettings` и возвращает:
       - `port`, `remark`.
       - `reality.public_key`, `fingerprint`, `sni_options`, `default_sni`,
         `short_id_options`, `default_short_id`, `spider_x`.
   - `create_client` / `delete_client` работают через модификацию JSON `settings`.

5. **URL генератор (VLESS / мульти‑протокол)**
   - `url_generator.py`:
     - `merge_profile_settings(profile_data, settings_overrides)` — аккуратно
       мёрджит `VpnProfile.settings` (в т.ч. выбранный SNI) в
       `profile_data["reality"]`, с fallback’ами `default_sni` и
       `default_short_id`.
     - `generate_vless_url(profile_data)` — собирает VLESS‑URL из подготовленных
       данных (`public_key`, `fingerprint`, `sni`, `short_id`, `spider_x`).
     - `generate_vpn_link(protocol_name, profile_data, settings_overrides=None)` —
       единая точка генерации ссылки по протоколу (с учётом SNI‑overrides).
   - Тесты `tests/test_vless_url.py` и `tests/test_qr_generator.py` покрывают
     корректность URL и его пригодность для QR.

6. **Mini App backend (FastAPI)**
   - Реализованы файлы:
     - `src/api/dependencies.py` — валидация `X-Telegram-Init-Data`, загрузка
       текущего пользователя.
     - `src/api/schemas.py` — схемы `MeResponse`, `ProfileSchema`, `PresetSchema`,
       запросы/ответы для смены протокола, SNI, пресетов.
     - `src/api/main.py` — FastAPI‑приложение с эндпоинтами:
       - `GET /me` — агрегированное состояние пользователя.
       - `POST /me/protocol` — смена протокола.
       - `POST /me/sni` — смена SNI.
       - `GET /presets`, `POST /presets`, `DELETE /presets/{id}`,
         `GET /presets/{id}/config`.
   - DI для `AsyncSession`, `VPNService`, `PresetService` настроен через
     `get_session` и зависимости FastAPI.

7. **Mini App frontend (React + Vite)**
   - Папка `miniapp/`:
     - `package.json`, `vite.config.js`, `index.html`.
     - `src/main.jsx`, `src/App.jsx`, `src/styles.css`.
     - `src/api.js` — клиент для Mini App API (`/me`, `/me/protocol`, `/me/sni`,
       `/presets`, `/presets/{id}/config`) с заголовком `X-Telegram-Init-Data`.
     - `src/telegram.js` — helper для работы с `window.Telegram.WebApp` и initData.
   - UI Mini App:
     - блок пользователя (имя, username),
     - текущий профиль (протокол, label, SNI, доступные SNI),
     - чипы выбора протокола,
     - чипы выбора SNI,
     - список пресетов + форма создания пресета,
     - превью конфига пресета и копирование URI в буфер.
   - Интеграция с Telegram WebApp: `tg.ready()`, `tg.expand()`, учёт темы
     (`colorScheme`) и размер экрана.

8. **Bot & handlers**
   - Админские/юзерские хендлеры обновлены под мульти‑протоколную схему:
     - при выдаче ссылки и статистики отображается текущий протокол.
     - админ‑флоу одобрения заявки учитывает выбор протокола.

9. **DevOps / CI/CD**
   - `Dockerfile`:
     - копирует `src/`, `alembic.ini`, `alembic/` и `start.sh`.
     - `CMD ["./start.sh"]`, где:
       - выполняются миграции Alembic,
       - запускается бот (`python -m src.bot.app`).
   - `docker-compose.yml`:
     - один сервис `vpn4friends` с `network_mode: "host"`, монтированием `./data`.
   - GitHub Actions `ci.yml`:
     - job `lint` (Ruff),
     - job `deploy` — ssh на сервер, `git pull`, `docker compose up -d --build`,
       `docker image prune -f`.

---

### 7.2. Remaining Tasks / Future Work

Ниже — полный список задач, которые можно/нужно сделать дальше. Они сгруппированы
по областям. Не все критичны для запуска, но описаны, чтобы было понятно, где
ещё можно улучшать систему.

#### 7.2.1. Core VPN & Protocols

- **Shadowsocks (полная поддержка)**
  - В `XUIApi.get_protocol_settings` реализовать ветку для `protocol == "shadowsocks"`:
    - парсить `method`, `password` и прочие нужные поля из inbound `settings`.
  - В `url_generator.generate_shadowsocks_url` реализовать корректную сборку
    `ss://` URI по стандарту (base64 части, remark и т.п.).
  - Добавить тест(ы) для ss‑URL (аналогично VLESS тестам).

- **Дополнительные протоколы (опционально)**
  - При необходимости добавить новые записи в `PROTOCOLS_CONFIG` и соответствующую
    логику в `XUIApi` и `url_generator`.

#### 7.2.2. Mini App Backend (расширения)

- **API для списка протоколов**
  - Добавить эндпоинт (например, `GET /protocols`), который отдаёт список доступных
    протоколов из `settings.protocols` (name, label, description, recommended).

- **Расширение пресетов и форматов**
  - Поддержать форматы конфигов помимо `*_uri`:
    - `clash_yaml` — генерация YAML профиля для Clash/Hiddify.
    - другие форматы по мере необходимости.
  - Расширить `PresetService.generate_config`, чтобы для таких форматов
    возвращался `{ "type": "file", "filename": "config.yaml", "content": "..." }`.

- **Более точный контракт ошибок API**
  - Стандартизировать формат ошибок (например, `{ "success": false, "message": "..." }`)
    для тех эндпоинтов, где сейчас используются HTTP‑исключения.

#### 7.2.3. Mini App Frontend (UX/функционал)

- **Динамический список протоколов**
  - Перейти от захардкоженного `AVAILABLE_PROTOCOLS` к данным с backend
    (`/protocols` или расширенный `/me`).

- **Улучшение UX и визуала**
  - Добавить skeleton‑лоадеры вместо простого текста "Загрузка...".
  - Более детальные сообщения об ошибках в зависимости от ответа API.
  - Поддержка разных языков интерфейса (i18n), если потребуется.

- **Работа с файлами (если будут YAML/профили)**
  - Для форматов `type == "file"` реализовать скачивание файла/открытие в
    приложении (вместо копирования URI).

#### 7.2.4. Bot Integration & UX

- **Кнопка открытия Mini App**
  - В основном меню бота добавить кнопку "Мои настройки VPN" с `web_app` ссылкой
    на Mini App.
  - Описать в README шаги по настройке WebApp URL в BotFather.

- **Fallback‑поведение**
  - Продумать простой текстовый флоу для пользователей без поддержки WebApp
    (например, команда, которая просто даёт ссылку/инструкцию).

#### 7.2.5. Testing & QA

- **Unit‑тесты бизнес‑логики**
  - `VPNService.switch_protocol` —
    - сценарий с существующим активным профилем;
    - ошибка при несуществующем протоколе;
    - ошибка при сбое `create_client`.
  - `VPNService.update_profile_settings` —
    - валидный/невалидный SNI;
    - отсутствие активного профиля.
  - `merge_profile_settings` / `generate_vpn_link` — корректное использование
    `default_sni`, `default_short_id` и overrides.

- **API‑тесты Mini App backend**
  - `GET /me`, `POST /me/protocol`, `POST /me/sni`, `/presets*` — happy‑path и
    базовые ошибки (нет профиля, нет пресета, невалидный SNI).

#### 7.2.6. DevOps & Deployment

- **Отдельный сервис для API (при необходимости)**
  - Добавить во `docker-compose.yml` второй сервис `api`:
    - команда `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`;
    - общая сеть с ботом или `network_mode: "host"`.
  - При желании — раздавать Mini App статику тем же сервисом или отдельным nginx.

- **Обновление CI/CD при появлении API‑сервиса**
  - При добавлении второго сервиса в compose убедиться, что пайплайн деплоя
    корректно пересобирает и перезапускает оба.

- **Наблюдаемость (по желанию)**
  - Добавить базовое логирование запросов в FastAPI.
  - Рассмотреть метрики (Prometheus) для числа активных пользователей/заявок.

#### 7.2.7. Docs & Cleanup

- **Актуализация корневого README**
  - Обновить разделы:
    - конфигурация `PROTOCOLS_CONFIG` и мульти‑протокол;
    - наличие Mini App backend и фронта;
    - упрощённый Docker‑запуск (один контейнер с ботом и миграциями).

- **Отдельный README для `miniapp/`**
  - Как запустить:
    - `npm install`, `npm run dev`;
    - использование `VITE_API_BASE_URL`.
  - Как подключить Mini App к боту (BotFather, WebApp URL).

- **Удаление легаси и артефактов**
  - Удалить `supervisord.conf` и любые упоминания про supervisord, так как
    сейчас контейнер запускает только бот через `start.sh`.
  - При необходимости удалить/обновить другие неактуальные файлы/комментарии.

---

This document should be treated as the authoritative high‑level specification and
roadmap for future refactors and Mini App integration. Another AI (or developer)
can use it as a starting point to understand what has already been built and what
remains to be done without re‑discovering the design decisions.
