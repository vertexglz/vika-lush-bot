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
ENV BOT_TOKEN="your_token_here"
ENV DB_HOST="localhost"
ENV DB_PORT="5432"
ENV DB_NAME="chatbot_vika"
ENV DB_USER="pavelveretennikov"
ENV DB_PASS="your_password_here"

# Открываем порт (если вдруг понадобится для webhook)
EXPOSE 8080

# Команда запуска (замени main.py на свой файл, если нужно)
CMD ["python", "main.py"] 