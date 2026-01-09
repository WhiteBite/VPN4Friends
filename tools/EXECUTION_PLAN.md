# Reality Keys Fix - Execution Plan

## Текущая ситуация

✅ **Проблема идентифицирована**: Оригинальный приватный ключ утерян  
✅ **Решение готово**: Новая валидная пара ключей сгенерирована  
✅ **Скрипт создан**: `restore_reality_keys.py`  

## Что нужно сделать

### Шаг 1: Загрузить скрипт на сервер

```bash
# На локальной машине
scp tools/restore_reality_keys.py root@185.232.205.172:/root/VPN4Friends/tools/

# Или через git
cd /root/VPN4Friends
git pull
```

### Шаг 2: Выполнить скрипт

```bash
ssh root@185.232.205.172
cd /root/VPN4Friends/tools
chmod +x restore_reality_keys.py
python3 restore_reality_keys.py
```

Скрипт спросит подтверждение перед выполнением.

### Шаг 3: Перезапустить 3x-ui

```bash
docker restart 3x-ui
sleep 10
docker ps | grep 3x-ui  # Проверить что запустился
```

### Шаг 4: Проверить что ключи обновились

```bash
# Проверить базу данных
sqlite3 /opt/3x-ui/db/x-ui.db "SELECT stream_settings FROM inbounds WHERE port = 443" | python3 -c "import sys, json; data = json.loads(sys.stdin.read()); r = data['realitySettings']; print(f'Private: {r[\"privateKey\"]}\nPublic: {r[\"publicKey\"]}')"

# Проверить что ключи валидны
docker exec 3x-ui /app/bin/xray-linux-amd64 x25519 -i AAZI_hbzcWQsfvmlYh9iP8De0nbTbxq5CqGRgmtqWEI
```

Должно показать:
```
Private: AAZI_hbzcWQsfvmlYh9iP8De0nbTbxq5CqGRgmtqWEI
Public: bxOgD6CIWGhrRZOXx9v0-JcfAsoXjWntB_Sz-yjZ0Wg
Password: bxOgD6CIWGhrRZOXx9v0-JcfAsoXjWntB_Sz-yjZ0Wg
```

### Шаг 5: Обновить .env файл

```bash
cd /root/VPN4Friends
nano .env
```

Изменить строку:
```
REALITY_PUBLIC_KEY=bxOgD6CIWGhrRZOXx9v0-JcfAsoXjWntB_Sz-yjZ0Wg
```

Сохранить (Ctrl+O, Enter, Ctrl+X).

### Шаг 6: Создать тестового клиента

1. Открыть панель: http://185.232.205.172:2053
2. Логин: admin / admin123
3. Inbounds → Inbound на порту 443 → Clients
4. Добавить нового клиента (например, "test-new-keys")
5. Скопировать VLESS ссылку

### Шаг 7: Протестировать подключение

Подключиться с новым конфигом через Throne или другой клиент.

Если работает - переходим к шагу 8.

### Шаг 8: Обновить конфиги для всех пользователей

Для каждого существующего пользователя:
1. Открыть его клиента в панели 3X-UI
2. Скопировать новую VLESS ссылку
3. Отправить пользователю через бота или вручную

## Новые параметры Reality

```
Public Key: bxOgD6CIWGhrRZOXx9v0-JcfAsoXjWntB_Sz-yjZ0Wg
SNI: google.com
Short ID: 33189997caa12349
Fingerprint: chrome
Spider X: /
```

## Пример новой VLESS ссылки

```
vless://[UUID]@185.232.205.172:443?type=tcp&security=reality&pbk=bxOgD6CIWGhrRZOXx9v0-JcfAsoXjWntB_Sz-yjZ0Wg&fp=chrome&sni=google.com&sid=33189997caa12349&spx=%2F&flow=xtls-rprx-vision#[ClientName]
```

## ⚠️ Критически важно

- **НЕ пропускать** шаг с обновлением .env файла
- **ВСЕ пользователи** должны получить новые конфиги
- **Старые конфиги перестанут работать** после перезапуска 3x-ui

## Откат (если что-то пошло не так)

Скрипт создает бэкапы:
- `/root/x-ui.db.backup_YYYYMMDD_HHMMSS`
- `/root/config.json.backup_YYYYMMDD_HHMMSS`

Для отката:
```bash
# Остановить 3x-ui
docker stop 3x-ui

# Восстановить базу
cp /root/x-ui.db.backup_YYYYMMDD_HHMMSS /opt/3x-ui/db/x-ui.db

# Запустить 3x-ui
docker start 3x-ui
```

## Вопросы?

Читай `REALITY_KEYS_SOLUTION.md` для подробного объяснения проблемы.
