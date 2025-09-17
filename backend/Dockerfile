FROM python:3.10-slim

# Установка зависимостей для aiosqlite
RUN apt-get update && apt-get install -y libsqlite3-dev

WORKDIR /app

# Установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY ./app ./app
COPY ./migrations ./migrations

# Точка входа
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-reload"]