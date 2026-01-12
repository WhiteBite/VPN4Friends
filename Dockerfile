FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY src/ ./src/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Создание директории для данных
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy the start script and make it executable
COPY start.sh .
RUN chmod +x start.sh

# Set the command to run the start script
CMD ["./start.sh"]
