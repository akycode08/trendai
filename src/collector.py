import os
from typing import List
from apify_client import ApifyClient

class TikTokCollector:
    def __init__(self):
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            print("⚠️ WARNING: APIFY_API_TOKEN not found in .env")
            self.client = None
        else:
            self.client = ApifyClient(token)

    def collect(self, keywords: List[str], limit_per_keyword: int = 30):
        if not self.client or not keywords:
            return []

        # Общий лимит
        total_max_items = len(keywords) * limit_per_keyword
        
        print(f"📡 Collector: Запрос Apify. Слов: {len(keywords)}. Лимит: {total_max_items}")

        run_input = {
            "searchQueries": keywords,
            "resultsPerPage": limit_per_keyword, 
            "maxItems": total_max_items,
            "sortType": 0,  # 0 = Relevance (лучший баланс свежести и качества)
            "scrapeComments": False,
            "scrapeDescriptions": True,
            # Нам критически важно получить данные автора (подписчики)
        }

        try:
            actor = self.client.actor("clockworks/tiktok-scraper")
            run = actor.call(run_input=run_input)
            
            if not run: return []

            dataset = self.client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())
            
            print(f"✅ Collector: Скачано {len(items)} сырых видео.")
            return items

        except Exception as exc:
            print(f"⚠️ Ошибка Apify: {exc}")
            return []