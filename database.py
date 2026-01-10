import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Импорты
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON  # Fallback для SQLite
from pgvector.sqlalchemy import Vector  # 🔥 Поддержка векторов

# Получаем URL базы
DB_URL = os.getenv("DATABASE_URL", "sqlite:///trendscout.db")

# Фикс для Supabase (они дают postgres://, а нужно postgresql://)
if DB_URL and DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

Base = declarative_base()

class Trend(Base):
    __tablename__ = "trends"

    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, index=True)  # ID запуска, чтобы группировать результаты
    vertical = Column(String)            # Тема (например, "flowers")
    platform = Column(String)
    url = Column(String, unique=True, index=True) # Ссылка на видео
    description = Column(Text)
    
    # Статистика (лайки, просмотры, репосты...)
    # Если Postgres - используем быстрый JSONB, иначе обычный JSON
    stats = Column(JSONB if "postgresql" in DB_URL else JSON)
    
    # 🔥 НОВЫЕ ПОЛЯ ДЛЯ МАТЕМАТИКИ ARISTOTLE (UTS)
    followers = Column(Integer, default=0)         # Подписчики автора (для R)
    normalized_reach = Column(Float, default=0.0)  # R: Log(Views)/Log(Followers)
    similarity = Column(Float, default=0.0)        # S: Косинусное сходство с бизнесом
    transfer_score = Column(Float, default=0.0)    # T: Финальный умный скор
    
    # Оставляем старое поле для совместимости, но главным будет transfer_score
    uts_score = Column(Float, default=0.0)

    ai_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 🧠 ВЕКТОР (размер 512 для модели clip-vit-base)
    # Это поле позволяет искать "по смыслу", а не по словам
    embedding = Column(Vector(512))

def get_db_session():
    """Создает подключение к базе и активирует расширения."""
    engine = create_engine(DB_URL, echo=False)
    
    # 🔥 ВАЖНО: Включаем поддержку векторов в базе (если это Postgres)
    if "postgresql" in DB_URL:
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
        except Exception as e:
            print(f"⚠️ Warning: Не удалось проверить расширение vector: {e}")

    # Создаем таблицы, если их нет
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()