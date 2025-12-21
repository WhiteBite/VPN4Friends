---
inclusion: always
---

# Commit Workflow

## Перед каждым коммитом ОБЯЗАТЕЛЬНО:

1. **Форматирование**: `ruff format src/`
2. **Линтинг**: `ruff check src/ --fix`
3. **Проверка**: `ruff format --check src/ && ruff check src/`

## Порядок действий:

```bash
# 1. Форматируем
ruff format src/

# 2. Исправляем линт-ошибки
ruff check src/ --fix

# 3. Проверяем что всё ок
ruff format --check src/
ruff check src/

# 4. Только после успешных проверок — коммит
git add .
git commit -m "..."
git push
```

## НЕ коммитить если:
- `ruff format --check` выдаёт ошибки
- `ruff check` выдаёт ошибки

## Деплой:
**Деплой происходит АВТОМАТИЧЕСКИ через GitHub Actions при пуше в master.**

НЕ деплоить вручную через SSH! Только через git push.

Проверить статус деплоя: https://github.com/WhiteBite/VPN4Friends/actions
