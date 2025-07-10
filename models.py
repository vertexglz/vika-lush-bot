from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean
import datetime
from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    bookings = relationship('Booking', back_populates='user')

class ScheduleSlot(Base):
    __tablename__ = 'schedule_slots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime.date] = mapped_column(DateTime, nullable=False)
    time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False)
    booking = relationship('Booking', back_populates='slot', uselist=False)

class Booking(Base):
    __tablename__ = 'bookings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    slot_id: Mapped[int] = mapped_column(Integer, ForeignKey('schedule_slots.id'))
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    user = relationship('User', back_populates='bookings')
    slot = relationship('ScheduleSlot', back_populates='booking') 