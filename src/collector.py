import os
from typing import List
from apify_client import ApifyClient
from src.adapter import adapt_apidojo_to_standard

class TikTokCollector:
    def __init__(self):
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            print("⚠️ WARNING: APIFY_API_TOKEN not found in .env")
            self.client = None
        else:
            self.client = ApifyClient(token)
            
        # Используем Apidojo
        self.actor_id = "apidojo/tiktok-scraper"

    def collect(self, targets: List[str], limit: int = 20, mode: str = "search"):
        """
        targets: список слов (для поиска) или никнеймов (для профиля)
        mode: "search" или "profile"
        """
        if not self.client or not targets:
            return []

        print(f"📡 Collector: Режим '{mode}' для {targets}. Лимит: {limit}")

        run_input = {
            "maxItems": limit,
            # Доп. настройки для стабильности
            "resultsPerPage": limit, 
        }

        # --- ЛОГИКА ПЕРЕКЛЮЧЕНИЯ ---
        if mode == "profile":
            # ВАРИАНТ 3 (ПОБЕДНЫЙ): startUrls как список СТРОК
            urls = []
            for t in targets:
                # 1. Чистим никнейм
                clean_nick = t.strip().replace("@", "").replace("https://www.tiktok.com/", "").strip("/")
                # 2. Формируем полную ссылку
                full_url = f"https://www.tiktok.com/@{clean_nick}"
                # 3. Добавляем СТРОКУ (не словарь!)
                urls.append(full_url)
            
            # Кладем в startUrls (это проходит валидацию)
            run_input["startUrls"] = urls
            
        else:
            # РЕЖИМ ПОИСКА
            run_input["keywords"] = targets
            run_input["searchSection"] = "top"
            run_input["startUrls"] = []

        try:
            # Запускаем актера
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            
            if not run: 
                print("⚠️ Apify вернул пустой run.")
                return []

            dataset = self.client.dataset(run["defaultDatasetId"])
            
            # Получаем сырые данные
            raw_items = list(dataset.iterate_items())
            print(f"📦 Apidojo вернул {len(raw_items)} сырых записей.")
            
            final_items = []
            for item in raw_items:
                # Прогоняем через адаптер
                std_item = adapt_apidojo_to_standard(item)
                if std_item:
                    final_items.append(std_item)
            
            print(f"✅ Адаптировано {len(final_items)} видео.")
            return final_items

        except Exception as exc:
            print(f"⚠️ Ошибка Apify: {exc}")
            return []