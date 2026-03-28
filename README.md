# 🔐 VPN4Friends

**Telegram-бот и Mini App для управления личным VPN-сервисом.**

Современное решение для раздачи VPN (VLESS, Reality, gRPC, Shadowsocks, Telegram Proxies) друзьям и близким. Включает удобное управление через инлайн-меню и потрясающий интерфейс Telegram Mini App (Glassmorphism, плавная анимация, динамические конфиги).

---

## ✨ Ключевые возможности

### 📱 Для пользователей (Mini App)
- 🚀 **Красивый дашборд** — управление своим профилем внутри приложения Telegram.
- 🔗 **Поддержка любых протоколов** — генерация ссылок для VLESS, xHTTP/TCP, gRPC, Shadowsocks и нативных Telegram-прокси (MTProto / SOCKS5).
- 🌍 **Динамический список локаций** — удобная группировка серверов по странам с подсказками по протоколам (какой протокол для чего нужен).
- 📊 **Мониторинг трафика** — просмотр своей статистики в реальном времени.

### 🛡️ Для администратора
- ✅ **Ручное одобрение заявок** — новые пользователи запрашивают доступ прямо через бота (или Mini App), а админ решает, одобрять их или нет.
- ⚙️ **Безопасная конфигурация** — все серверы и секреты вынесены в **один JSON-объект**, который легко хранится в GitHub Secrets и раскатывается через CI/CD (никакого хардкода).
- 📢 **Броадкасты и обратная связь** — встроенные рассылки и функции общения поддержки.
- 🔄 **Интеграция с X-UI** — автоматическое создание клиентов в [3X-UI](https://github.com/MHSanaei/3x-ui) при получении доступа. Поддержка каскадных серверов (Relay) для обхода DPI.

---

## 🌍 Архитектура и Динамические конфиги

Проект спроектирован так, чтобы вы могли добавлять неограниченное количество серверов, локаций и маршрутов **без изменения исходного кода фронтенда или бэкенда**. Вся конфигурация пробрасывается через JSON в переменную окружения `ENDPOINTS_CONFIG`.

### Пример добавления новой локации (через JSON):
```json
[
  {
    "name": "germany_direct",
    "label": "🇩🇪 Германия (Direct)",
    "category": "vpn",
    "country": "Германия",
    "host": "de.example.com",
    "port": 443,
    "protocol": "vless",
    "transport": "reality"
  },
  {
    "name": "finland_tg_socks",
    "label": "FI SOCKS5 Proxy",
    "category": "telegram",
    "country": "Финляндия",
    "host": "fi.example.com",
    "port": 1080,
    "protocol": "socks",
    "transport": "socks",
    "panel_config": {
      "user": "telegram",
      "pass": "your_secure_password"
    }
  }
]
```
*Выше описанные данные автоматически парсятся приложением: бэкенд включает их в API, а UI группирует их во вкладках (VPN / Telegram) и по странам.*

---

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- Node.js 18+ (для сборки Mini App по желанию)
- Поднятая панель [3X-UI](https://github.com/MHSanaei/3x-ui)
- Токен Telegram бота от [@BotFather](https://t.me/BotFather)

### Установка (локально)

```bash
# Клонируйте репозиторий
git clone https://github.com/your-username/VPN4Friends.git
cd VPN4Friends

# Создайте и активируйте виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Для Linux/Mac
# .venv\Scripts\activate   # Для Windows

# Установите зависимости
pip install -r requirements.txt

# Скопируйте пример конфига
cp vpn-config.example.json vpn-config.json
# Заполните vpn-config.json вашими реальными серверами, ключами и настройками X-UI.

# Запустите скрипт трансформации (или используйте jq на сервере), 
# чтобы перевести JSON в переменные среды .env
# Запустите бота:
python -m src.bot.app
```

---

## 📦 Деплой через GitHub Actions (CI/CD)

Этот проект настроен для автоматического деплоя на ваш VPS без хранения приватных ключей в самом репозитории.

1. Убедитесь, что ваш файл с секретами (`vpn-config.json`) добавлен в `.gitignore`!
2. Перейдите в настройки вашего форка в GitHub: **Settings -> Secrets and variables -> Actions**
3. Создайте следующие секреты:
   - `SERVER_HOST` — IP-адрес вашего сервера для бота.
   - `SERVER_USER` — Имя пользователя (например, `ubuntu`).
   - `SSH_KEY` — Ваш приватный SSH ключ для доступа.
   - `VPN_CONFIG` — Полное содержимое предварительно заполненного файла `vpn-config.json` (весь текст!).
4. При каждом пуше в ветку `master` GitHub Actions автоматически:
   - Соберёт и проверит код (линтеры + тесты).
   - Зайдет на сервер по SSH.
   - С помощью `jq` перегонит `VPN_CONFIG` из JSON в файл `.env`.
   - Перезапустит сервисы приложения.

---

## 📱 Рекомендуемые клиенты для подключения
Боту уже известны и понятны все современные VPN-клиенты. Сгенерированные ссылки (VLESS / Shadowsocks) безопасны к импорту и автоматически декодируют красивые имена:

| Платформа | Приложение |
|-----------|------------|
| iOS | [V2RayTun](https://apps.apple.com/app/v2raytun/id6476628951), [Streisand](https://apps.apple.com/app/streisand/id6450534064) |
| Android | [v2rayNG](https://github.com/2dust/v2rayNG/releases), [Hiddify](https://github.com/hiddify/hiddify-app) |
| Windows/Mac | [Hiddify](https://github.com/hiddify/hiddify-app), [v2rayN](https://github.com/2dust/v2rayN) |

---

## 📄 Лицензия

MIT License
