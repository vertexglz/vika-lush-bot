import asyncio
import datetime
from models import SessionLocal, Booking, ScheduleSlot
from sqlalchemy import select, delete, and_

async def cleanup_old_records():
    today = datetime.date.today()
    threshold = today - datetime.timedelta(days=7)
    async with SessionLocal() as session:
        # Удаляем старые бронирования
        old_bookings = await session.execute(
            select(Booking).join(ScheduleSlot, Booking.slot_id == ScheduleSlot.id)
            .where(ScheduleSlot.date < threshold)
        )
        bookings_to_delete = old_bookings.scalars().all()
        for booking in bookings_to_delete:
            await session.delete(booking)
        # Удаляем старые слоты
        old_slots = await session.execute(
            select(ScheduleSlot).where(ScheduleSlot.date < threshold)
        )
        slots_to_delete = old_slots.scalars().all()
        for slot in slots_to_delete:
            await session.delete(slot)
        await session.commit()
    print('Старые записи и слоты удалены!')

if __name__ == '__main__':
    asyncio.run(cleanup_old_records()) 