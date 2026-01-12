import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from pgvector.sqlalchemy import Vector

DB_URL = os.getenv("DATABASE_URL", "sqlite:///trendscout.db")
if DB_URL and DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

Base = declarative_base()

class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, index=True)
    vertical = Column(String)
    platform = Column(String)
    url = Column(String, unique=True, index=True)
    author_username = Column(String, index=True)  # Для кеширования профилей
    
    # --- 🔥 ВЕРНУЛИ ПОЛЕ, ЧТОБЫ БЫЛИ КАРТИНКИ В ПОИСКЕ ---
    cover_url = Column(String)
    # -----------------------------------------------------

    description = Column(Text)
    stats = Column(JSONB if "postgresql" in DB_URL else JSON)
    
    followers = Column(Integer, default=0)
    
    # --- ТВОИ ФОРМУЛЫ (UTS, REACH, SIMILARITY) ---
    normalized_reach = Column(Float, default=0.0)
    similarity = Column(Float, default=0.0)
    transfer_score = Column(Float, default=0.0)
    uts_score = Column(Float, default=0.0)
    # ---------------------------------------------

    ai_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(Vector(512))

class ProfileData(Base):
    """Таблица для хранения полных данных профиля (channel + raw_data с hashtags и song)"""
    __tablename__ = "profile_data"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)  # Нормализованный username (lowercase)
    channel_data = Column(JSONB if "postgresql" in DB_URL else JSON)  # Полные данные channel (bio, followers, following, videos, verified, name, avatar)
    raw_data = Column(JSONB if "postgresql" in DB_URL else JSON)  # Массив всех видео с полными данными (hashtags, song, views, likes, и т.д.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_db_session():
    engine = create_engine(DB_URL, echo=False)
    if "postgresql" in DB_URL:
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
        except Exception as e:
            print(f"⚠️ Warning: {e}")
            
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()