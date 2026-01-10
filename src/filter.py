import time
from datetime import datetime, timezone
from typing import List

class ViralContentFilter:
    def __init__(self, business_keywords: List[str] = None):
        self.business_keywords = set(k.lower() for k in (business_keywords or []))
        
        # Настройки фильтрации
        self.min_views_fresh = 1000       # Для свежих (<48ч)
        self.min_likes_recent = 1000      # Для видео за 2 месяца (снизил до 1000, чтобы не терять микро-тренды)
        self.min_views_timeless = 500000  # Миллионники (от 500к)
        
        # Векторный порог (оставляем мягким, чтобы не выкинуть лишнее)
        self.min_similarity = 0.2

    def filter_content(self, raw_items: List[dict]) -> List[dict]:
        """Этап 1: Фильтрация по дате и просмотрам (Hard Filters)"""
        filtered = []
        current_dt = datetime.now(timezone.utc)
        
        print(f"🧹 Filter: Анализ {len(raw_items)} видео...")

        for item in raw_items:
            # 1. ПАРСИНГ ДАТЫ
            created_at = None
            iso_date = item.get("createTimeISO")
            if iso_date:
                try:
                    created_at = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
                except ValueError:
                    pass
            
            if not created_at:
                ts = item.get("createTime")
                if ts:
                    if ts > 10000000000: ts = ts / 1000
                    created_at = datetime.fromtimestamp(ts, timezone.utc)

            if not created_at: continue

            # Считаем возраст
            age_days = (current_dt - created_at).days
            age_hours = (current_dt - created_at).total_seconds() / 3600

            # 2. ПОЛУЧЕНИЕ ДАННЫХ
            stats = item.get("stats", {})
            views = int(item.get("playCount") or stats.get("playCount", 0))
            likes = int(item.get("diggCount") or stats.get("diggCount", 0))

            # --- 3. НОВАЯ ЛОГИКА (БЕЗ ДИНОЗАВРОВ) ---
            is_good = False
            
            # ПРАВИЛО 1: "Хит Года" (Было: Бессмертный)
            # Теперь берем миллионники, только если они вышли в течение ГОДА (365 дней)
            if views >= self.min_views_timeless and age_days <= 365:
                is_good = True

            # ПРАВИЛО 2: "Актуальный тренд" (2 месяца)
            # Видео средней популярности, но свежее
            elif age_days <= 60 and likes >= self.min_likes_recent:
                is_good = True

            # ПРАВИЛО 3: "Свежая ракета" (48 часов)
            # Совсем новые видео, которые только начали расти
            elif age_hours <= 48 and views >= self.min_views_fresh:
                is_good = True

            if is_good:
                filtered.append(item)
            
        print(f"🧹 Filter: Оставлено {len(filtered)} видео.")
        return filtered

    def check_similarity(self, similarity_score: float) -> bool:
        """Этап 2: Проверка на релевантность бизнесу"""
        return similarity_score >= self.min_similarity