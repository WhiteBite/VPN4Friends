# 🛠️ Development Guide

## 🚀 Быстрый старт для разработки

### 1. Установка

```bash
# Клонировать репо
git clone https://github.com/WhiteBite/VPN4Friends.git
cd VPN4Friends

# Установить зависимости
pip install -r requirements.txt
pip install -r requirements-test.txt

# Установить pre-commit хуки
pre-commit install
```

### 2. Настройка окружения

```bash
# Скопировать пример
cp .env.example .env

# Отредактировать .env своими данными
# (бот токен, админ ID, и т.д.)
```

### 3. База данных и Миграции

Проект использует **Alembic** для управления схемой базы данных. Это гарантирует, что у всех разработчиков одинаковые таблицы и колонки.

```bash
# Применить все миграции (создать/обновить таблицы)
python -m alembic upgrade head

# Создать новую миграцию (если изменили models.py)
python -m alembic revision --autogenerate -m "описание изменений"
```

> [!IMPORTANT]
> Всегда запускайте `alembic upgrade head` после обновления кода из репозитория!

### 4. Запуск бота локально

```bash
# Запустить бота
python -m src.bot.app

# Бот запущен! Тестируй в Telegram
```

**Логи будут в консоли** — видишь ошибки сразу, не на проде!

---

## 🧪 Тестирование

### Запустить все тесты

```bash
pytest
```

### Запустить конкретный тест

```bash
pytest tests/unit/test_repositories.py -v
pytest tests/integration/test_api_endpoints.py -v
```

### Запустить с покрытием

```bash
pytest --cov=src --cov-report=html
# Отчёт: htmlcov/index.html
```

### Pre-commit хуки

**Автоматически запускаются перед каждым коммитом:**

```bash
# Ruff linting
ruff check src/

# Ruff formatting
ruff format src/

# Pytest (только unit и API тесты)
pytest tests/unit/ tests/integration/test_api_endpoints.py
```

**Если тесты падают — коммит блокируется!**

---

## 🔄 CI/CD Pipeline

### Что происходит при `git push`:

1. **Ruff linting** — проверка кода
2. **Ruff format** — проверка форматирования
3. **Pytest** — запуск тестов (17 тестов)
4. **Deploy** — если всё прошло → деплой на сервер

### Файлы:

- `.github/workflows/ci.yml` — CI/CD конфигурация
- `.pre-commit-config.yaml` — pre-commit хуки

---

## 🐛 Отладка

### Логирование

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Info message")
logger.error("Error message")
```

**Логи видны:**
- Локально: в консоли
- На сервере: `docker logs vpn4friends`

### Debug режим

```bash
# Запустить с дебаг логами
PYTHONPATH=. python -m src.bot.app --log-level=DEBUG
```

---

## 📁 Структура проекта

```
VPN4Friends/
├── src/
│   ├── bot/              # Bot app
│   ├── api/              # FastAPI backend
│   ├── handlers/         # Bot handlers
│   ├── services/         # Business logic
│   ├── database/         # Models & repositories
│   └── keyboards/        # Keyboards
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
└── requirements*.txt
```

---

## ✅ Чеклист перед коммитом

- [ ] Тесты проходят: `pytest`
- [ ] Linting проходит: `ruff check src/`
- [ ] Форматирование: `ruff format src/`
- [ ] Pre-commit хуки установлены: `pre-commit install`

**Если всё зелёное — коммить!**

---

## 🆘 Troubleshooting

### "ModuleNotFoundError: No module named 'aiogram'"

```bash
pip install -r requirements.txt
```

### "Pre-commit failed"

```bash
# Запустить вручную
pre-commit run --all-files

# Исправить ошибки
# Закоммитить снова
```

### "Tests failed on GitHub but pass locally"

```bash
# Запустить в чистом окружении
docker run --rm -v $(pwd):/app -w /app python:3.11 \
  bash -c "pip install -r requirements.txt -r requirements-test.txt && pytest"
```

---

## 📚 Resources

- [Aiogram docs](https://docs.aiogram.dev/)
- [FastAPI docs](https://fastapi.tiangolo.com/)
- [Pytest docs](https://docs.pytest.org/)
- [Pre-commit docs](https://pre-commit.com/)
