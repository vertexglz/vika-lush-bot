import asyncio
import datetime
import logging
from aiogram import Bot
from sqlalchemy import select, and_
from models import SessionLocal, Booking, User, ScheduleSlot
from config import BOT_TOKEN

bot = Bot(token=str(BOT_TOKEN))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

async def send_reminders():
    now = datetime.datetime.now()
    async with SessionLocal() as session:
        try:
            bookings = await session.execute(
                select(Booking, User, ScheduleSlot)
                .join(User, Booking.user_id == User.id)
                .join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
                .where(ScheduleSlot.is_booked == True)
            )
            rows = bookings.all()
            for booking, user, slot in rows:
                slot_dt = datetime.datetime.combine(slot.date, datetime.datetime.strptime(slot.time, "%H:%M").time())
                delta = slot_dt - now
                if 11.5*3600 < delta.total_seconds() < 12.5*3600:
                    name = getattr(booking, 'name', None) or 'Клиент'
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            f"👋 {name}, напоминаем о вашей записи к мастеру Виктории на {slot_dt.strftime('%d.%m.%Y в %H:%M')}\n"
                            f"Если вы не сможете прийти — пожалуйста, заранее отмените запись или напишите мастеру!"
                        )
                        logging.info(f"Напоминание отправлено {user.telegram_id} на {slot_dt}")
                    except Exception as e:
                        logging.error(f"Ошибка отправки {user.telegram_id}: {e}")
        except Exception as e:
            logging.exception("Ошибка при отправке напоминаний")

if __name__ == '__main__':
    asyncio.run(send_reminders()) 