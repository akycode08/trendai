from datetime import datetime, timedelta
import re
from typing import List

class ViralContentFilter:
    def __init__(self, business_keywords: List[str] = None, is_profile_mode: bool = False):
        """
        is_profile_mode: Если True, отключаем жесткие фильтры по просмотрам
        """
        self.business_keywords = set(k.lower() for k in (business_keywords or []))
        self.is_profile_mode = is_profile_mode 
        
        # Настройки фильтрации (Работают только в режиме поиска)
        self.min_views_fresh = 1000       # Для свежих (<48ч)
        self.min_likes_recent = 1000      # Для видео за 2 месяца
        self.min_views_timeless = 100000  # Миллионники
        
    def filter_content(self, raw_items: List[dict]) -> List[dict]:
        filtered = []
        now = datetime.now()
        print(f"🧹 Filter: Анализ {len(raw_items)} видео (Profile Mode: {self.is_profile_mode})...")

        for item in raw_items:
            # 1. Проверка структуры (обязательно должна быть ссылка и автор)
            if not item.get("webVideoUrl"):
                continue

            # --- ЕСЛИ ЭТО ПРОФИЛЬ КОНКУРЕНТА - БЕРЕМ ПОЧТИ ВСЁ ---
            if self.is_profile_mode:
                # Можно добавить минимальный порог, чтобы совсем мусор не брать (например, 100 просмотров)
                if item.get("playCount", 0) > 0:
                    filtered.append(item)
                continue
            # -----------------------------------------------------

            # ДАЛЕЕ ИДЕТ СТАНДАРТНАЯ ЛОГИКА ДЛЯ ПОИСКА ТРЕНДОВ
            views = item.get("playCount", 0)
            likes = item.get("diggCount", 0)
            create_time = item.get("createTime", 0)
            
            # Дата создания
            try:
                created_at = datetime.fromtimestamp(create_time)
                age = now - created_at
            except:
                age = timedelta(days=365) # Если даты нет, считаем старым

            # Логика виральности
            is_viral = False
            
            # A. Свежий вирус (до 48 часов)
            if age <= timedelta(hours=48):
                if views >= self.min_views_fresh:
                    is_viral = True
            
            # B. Недавний тренд (до 60 дней)
            elif age <= timedelta(days=60):
                if likes >= self.min_likes_recent:
                    is_viral = True
                    
            # C. Вечная классика (любая дата)
            else:
                if views >= self.min_views_timeless:
                    is_viral = True

            if is_viral:
                filtered.append(item)

        print(f"🧹 Filter: Оставлено {len(filtered)} видео.")
        return filtered