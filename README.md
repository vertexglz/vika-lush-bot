# Чат-бот для записи на ресницы

## Запуск бота

1. Установите зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Создайте файл `.env` в корне проекта (см. пример в example.env).
3. Инициализируйте базу данных:
   ```bash
   python db_init.py
   python add_slots.py
   ```
4. Запустите бота:
   ```bash
   python bot.py
   ```

## Автоматические напоминания

Скрипт `reminder.py` отправляет напоминания пользователям за 12 часов до записи. Для автоматизации используйте cron или systemd.

### Cron (раз в час)

1. Откройте crontab:
   ```bash
   crontab -e
   ```
2. Добавьте строку (замените путь на свой):
   ```
   0 * * * * cd /Users/pavelveretennikov/Documents/programming/chatbot\ for\ Vika && /Users/pavelveretennikov/Documents/programming/chatbot\ for\ Vika/venv/bin/python reminder.py
   ```

### Systemd (Linux)

Создайте файл `reminder.service`:
```ini
[Unit]
Description=Telegram Reminder Service

[Service]
WorkingDirectory=/path/to/project
ExecStart=/path/to/project/venv/bin/python reminder.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Создайте файл `reminder.timer`:
```ini
[Unit]
Description=Run reminder every hour

[Timer]
OnCalendar=hourly

[Install]
WantedBy=timers.target
```

Активируйте:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now reminder.timer
```

## Автоматическая очистка базы

Для удаления старых записей и слотов (старше 7 дней) используйте скрипт `cleanup_db.py`. Для автоматизации добавьте в cron:

1. Откройте crontab:
   ```bash
   crontab -e
   ```
2. Добавьте строку (замените путь на свой):
   ```
   0 0 * * * cd /Users/pavelveretennikov/Documents/programming/chatbot\ for\ Vika && /Users/pavelveretennikov/Documents/programming/chatbot\ for\ Vika/venv/bin/python cleanup_db.py
   ```

Теперь очистка будет выполняться ежедневно в 00:00.

## Запуск 24/7

Для постоянной работы бота используйте screen/tmux или systemd:
```bash
screen -S bot
python bot.py
# Для выхода из screen: Ctrl+A, затем D
```

Или создайте systemd unit для bot.py по аналогии с reminder.service.

---

## Контакты и поддержка
- Вопросы: Telegram @ваш_ник 