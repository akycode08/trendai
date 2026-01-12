#!/usr/bin/env python3
"""
Скрипт для получения сырого JSON ответа от Apify API
Показывает ВСЕ поля, которые возвращает актер apidojo/tiktok-scraper
"""

import os
import json
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

def get_raw_apify_response():
    """Получает сырой JSON ответ от Apify API"""
    
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("❌ APIFY_API_TOKEN не найден в .env")
        return None
    
    client = ApifyClient(token)
    actor_id = "apidojo/tiktok-scraper"
    
    # Тестовый профиль для проверки
    test_profile = "diazharass"  # Можно изменить
    
    print(f"📡 Запрашиваю данные профиля: @{test_profile}")
    print(f"🔗 Актор: {actor_id}")
    print("⏳ Это может занять 10-30 секунд...")
    print()
    
    run_input = {
        "maxItems": 5,  # Берем только 5 видео для примера
        "resultsPerPage": 5,
        "startUrls": [f"https://www.tiktok.com/@{test_profile}"]
    }
    
    try:
        # Запускаем актера
        run = client.actor(actor_id).call(run_input=run_input)
        
        if not run:
            print("❌ Apify вернул пустой run")
            return None
        
        print(f"✅ Запрос выполнен, dataset ID: {run['defaultDatasetId']}")
        
        # Получаем сырые данные
        dataset = client.dataset(run["defaultDatasetId"])
        raw_items = list(dataset.iterate_items())
        
        print(f"📦 Получено {len(raw_items)} записей")
        print()
        
        if raw_items:
            # Берем первую запись для примера
            first_item = raw_items[0]
            
            print("=" * 80)
            print("📋 СЫРОЙ JSON ОТВЕТ ОТ APIFY (первая запись):")
            print("=" * 80)
            print()
            
            # Форматируем JSON с отступами
            json_output = json.dumps(first_item, indent=2, ensure_ascii=False)
            print(json_output)
            
            print()
            print("=" * 80)
            print(f"📊 Всего полей в ответе: {len(first_item.keys())}")
            print("=" * 80)
            print()
            
            # Показываем список всех ключей
            print("🔑 Все ключи в ответе:")
            for key in sorted(first_item.keys()):
                value = first_item[key]
                value_type = type(value).__name__
                value_preview = str(value)[:100] if value else "None"
                print(f"  - {key}: {value_type} = {value_preview}")
            
            # Сохраняем в файл
            output_file = "apify_raw_response.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(raw_items, f, indent=2, ensure_ascii=False)
            
            print()
            print(f"💾 Полный ответ сохранен в файл: {output_file}")
            print(f"   Всего записей в файле: {len(raw_items)}")
            
            return raw_items
        else:
            print("⚠️ Нет данных в ответе")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    get_raw_apify_response()
