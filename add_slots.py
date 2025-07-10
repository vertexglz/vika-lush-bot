import asyncio
import datetime
from models import SessionLocal, ScheduleSlot

async def add_week_slots():
    today = datetime.date.today()
    times = ["17:00", "18:30", "20:00"]
    async with SessionLocal() as session:
        for i in range(7):
            date = today + datetime.timedelta(days=i)
            for t in times:
                exists = await session.scalar(
                    ScheduleSlot.__table__.select().where(
                        (ScheduleSlot.date == date) & (ScheduleSlot.time == t)
                    )
                )
                if not exists:
                    slot = ScheduleSlot(date=date, time=t, is_booked=False)
                    session.add(slot)
        await session.commit()
    print('Слоты добавлены!')

if __name__ == '__main__':
    asyncio.run(add_week_slots()) 