import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = "7680781537:AAFyxeFSYngQvyGC4Lw1fbgBsSIWZjuBP_I"
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chatbot_vika')
DB_USER = os.getenv('DB_USER', 'pavelveretennikov')
DB_PASS = os.getenv('DB_PASS', '')

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 