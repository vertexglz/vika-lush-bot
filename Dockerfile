# Используем официальный Python-образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Указываем переменные окружения (можно переопределить через docker run -e ...)
ENV BOT_TOKEN="your_bot_token_here"
ENV DATABASE_URL="your_database_url_here"

# Открываем порт (если вдруг понадобится для webhook)
EXPOSE 8080

# Команда запуска бота
CMD ["python", "bot.py"] 