# Используем официальный Python образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы приложения
COPY . .

# Создаем директорию для загрузок и устанавливаем права доступа
RUN mkdir -p uploads && \
    chmod -R 777 /app

# Открываем порт 5000 для вебхука
EXPOSE 5000

# Устанавливаем переменные окружения по умолчанию
ENV SERVER_PORT=5000
ENV SERVER_HOST=0.0.0.0
ENV UPLOAD_FOLDER=uploads

# Запускаем приложение
CMD ["python", "server.py"]

