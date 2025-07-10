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

# Оставляем только имена переменных, значения задаются при запуске контейнера!
ENV BOT_TOKEN=""
ENV DB_HOST=""
ENV DB_PORT=""
ENV DB_NAME=""
ENV DB_USER=""
ENV DB_PASS=""

# Открываем порт (если вдруг понадобится для webhook)
EXPOSE 8080

# Команда запуска (замени main.py на свой файл, если нужно)
CMD ["python", "bot.py"] 