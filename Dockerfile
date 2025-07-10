# Используем официальный Python-образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Указываем переменные окружения (опционально, можно задать через fly.io)
# ENV BOT_TOKEN=... DATABASE_URL=...

# Команда запуска бота
CMD ["python", "bot.py"] 