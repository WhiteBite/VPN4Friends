# 🔐 VPN Bot для друзей

**Multi-Server VPN Relay System** — Netherlands (62YUN) + Finland + Moscow Relay

Telegram-бот для раздачи VPN друзьям с ручным одобрением заявок. Интеграция с панелью 3X-UI. Обход ТСПУ через Moscow relay.

## ✨ Возможности

### Для пользователей
- 🔗 **Выбор сервера** — 🇫🇮 Финляндия или 🇳🇱 Нидерланды
- 🌐 **Обход ТСПУ** — relay через Москву (маскировка под VK трафик)
- 🔑 Отправить заявку на VPN
- 📊 Статистика трафика
- ✉️ Написать админу
- ✈️ **Telegram Proxy** — нативный MTProto для Telegram

### Для админа
- ✅ Одобрить/отклонить заявки
- 👥 Список пользователей с VPN
- 📊 Статистика по каждому пользователю
- 📢 Рассылка сообщений
- ✉️ Личные сообщения пользователям
- 🗑️ Отозвать VPN

## 🌍 Архитектура

```
┌─────────────────┐
│   Client        │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────┐
│ 🇳🇱 NL   │ │ 🇫🇮 Finland │
│ Direct  │ │ Direct       │
└─────────┘ └──────────────┘
    ▲         ▲
    │         │
    └────┬────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────────────────┐
│  🇷🇺 Moscow Relay   │
│  (VK Cloud)         │
│  dokodemo-door      │
│  Port 443 → FI:443  │
│  Port 444 → FI:8444 │
│  Port 445 → NL:443  │
└─────────────────────┘
```

**7 endpoints подключения:**

| # | Название | Маршрут | Порт | Протокол | Для кого |
|---|----------|---------|------|----------|----------|
| 1 | 🇳🇱 Netherlands Direct | Direct | 443 | VLESS | Старые юзеры |
| 2 | 🇳🇱 Netherlands → Moscow | Relay | 445 | VLESS Reality | Обход ТСПУ |
| 3 | ✈️ NL MTProto | Direct | 4443 | MTProto | Только Telegram |
| 4 | 🇫🇮 Finland Direct | Direct | 443 | VLESS | Вне РФ |
| 5 | 🇫🇮 Finland → Moscow (xHTTP) | Relay | 443 | VLESS Reality | **Рекомендуется для РФ** ⭐ |
| 6 | 🇫🇮 Finland → Moscow (gRPC) | Relay | 444 | VLESS gRPC | Альтернатива |
| 7 | ✈️ FI MTProto | Direct | 4443 | MTProto | Только Telegram |

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- Панель [3X-UI](https://github.com/MHSanaei/3x-ui) с настроенным inbound (Reality)
- Telegram бот от [@BotFather](https://t.me/BotFather)
- Docker и Docker Compose (для деплоя)

### Установка (локально)

```bash
# Клонируй репозиторий
git clone https://github.com/your-username/vpn-friends-bot.git
cd vpn-friends-bot

# Создай виртуальное окружение
python -m venv .venv

# Активируй (Windows)
.venv\Scripts\activate
# Или Linux/Mac
source .venv/bin/activate

# Установи зависимости
pip install -r requirements.txt

# Скопируй и настрой конфиг
cp .env.example .env
# Отредактируй .env своими данными

# Запусти бота
python -m src.bot.app
```

### Деплой (Docker + CI/CD)

```bash
# Настрой GitHub Secrets:
# - SERVER_HOST (IP или домен сервера)
# - SERVER_USER (username)
# - SSH_KEY (private key)

# Задеплой
git push origin master
# GitHub Actions автоматически зальёт на сервер
```

**Инструкция по деплою:** См. файлы на сервере в `/home/ubuntu/VPN4Friends/docs/`

## ⚙️ Настройка .env

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен от @BotFather |
| `ADMIN_IDS` | Твой Telegram ID (через запятую если несколько) |
| `ENDPOINTS_CONFIG` | JSON с конфигурацией серверов (7 endpoint'ов) |
| `MTROTO_PROXY_*` | Настройки MTProto для Telegram |
| `REALITY_*` | Параметры Reality из настроек inbound |

**Пример `ENDPOINTS_CONFIG`:**
```json
[
  {
    "name":"finland_xhttp",
    "label":"🇫🇮 Финляндия (xHTTP)",
    "host":"YOUR_MOSCOW_IP",
    "port":443,
    "protocol":"vless",
    "security":"reality",
    "sni":"max.ru",
    "flow":"xtls-rprx-vision"
  },
  {
    "name":"netherlands_direct",
    "label":"🇳🇱 Нидерланды (Direct)",
    "host":"YOUR_NL_IP",
    "port":443,
    "protocol":"vless",
    "panel_type":"3xui",
    "panel_config": {...}
  }
]
```

## 📁 Структура проекта

```
├── src/
│   ├── bot/           # Конфиг, middleware, точка входа
│   ├── handlers/      # Обработчики команд (user, admin, server_selection)
│   ├── keyboards/     # Клавиатуры (user, server selection)
│   ├── database/      # Модели и репозитории
│   ├── services/      # Бизнес-логика (VPN, XUI API)
│   └── utils/         # Утилиты
├── scripts/           # Скрипты деплоя
│   └── deploy-env.sh  # Обновление .env на сервере
├── .env.example       # Пример конфигурации (без секретов)
├── requirements.txt   # Зависимости
└── README.md
```

**Документация:** Хранится на сервере в `/home/ubuntu/VPN4Friends/docs/` (не коммитить в git)

## 🛠️ Технологии

- [aiogram 3](https://docs.aiogram.dev/) — Telegram Bot API
- [SQLAlchemy 2](https://www.sqlalchemy.org/) — ORM
- [aiosqlite](https://github.com/omnilib/aiosqlite) — Async SQLite
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — Конфигурация
- [Docker](https://www.docker.com/) — Контейнеризация
- [GitHub Actions](https://github.com/features/actions) — CI/CD

## 📱 Приложения для подключения

| Платформа | Приложение | Для чего |
|-----------|------------|----------|
| iOS | [V2RayTun](https://apps.apple.com/app/v2raytun/id6476628951) | VLESS/gRPC |
| Android | [V2RayNG](https://github.com/2dust/v2rayNG) | VLESS/gRPC |
| Windows/Mac | [Hiddify](https://github.com/hiddify/hiddify-app) | VLESS/gRPC |
| Telegram | Встроенный прокси | MTProto |

## 📚 Документация

**Вся документация хранится на сервере** (не коммитится в git для безопасности):

- `/home/ubuntu/VPN4Friends/docs/DEPLOY-INSTRUCTIONS.md` — Инструкция по деплою
- `/home/ubuntu/VPN4Friends/docs/VPN-SETUP-FINAL.md` — Архитектура и настройка
- `/home/ubuntu/VPN4Friends/docs/QUICK-REFERENCE.md` — Шпаргалка

**Почему не в git?** Документация содержит IP-адреса серверов и конфигурационные данные которые не должны быть публичными.

## 📄 Лицензия

MIT
