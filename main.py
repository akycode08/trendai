import sys
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np

# --- VISION IMPORTS ---
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import requests
import torch

# --- НАШИ МОДУЛИ ---
from database import Trend, get_db_session
from src.collector import TikTokCollector
from src.filter import ViralContentFilter
from src.scorer import TrendScorer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# --- 1. НАСТРОЙКА AI ---
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
else:
    model_gemini = None

print("🧠 Загрузка CLIP...")
try:
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    print("✅ CLIP готов.")
except Exception as e:
    print(f"⚠️ Ошибка CLIP: {e}")
    clip_model = None

# --- 2. ФУНКЦИИ ВЕКТОРИЗАЦИИ ---
def get_text_embedding(text: str):
    if not clip_model or not text: return None
    try:
        inputs = clip_processor(text=[text], return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = clip_model.get_text_features(**inputs)
        return outputs.squeeze().numpy().tolist()
    except Exception as e:
        print(f"⚠️ Ошибка Text Embedding: {e}")
        return None

def get_image_embedding(image_url):
    if not clip_model or not image_url: return None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/"
    }
    try:
        resp = requests.get(image_url, headers=headers, stream=True, timeout=5)
        if resp.status_code != 200: return None
        image = Image.open(resp.raw)
        inputs = clip_processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = clip_model.get_image_features(**inputs)
        return outputs.squeeze().numpy().tolist()
    except Exception:
        return None

def find_image_url(item):
    if "videoMeta" in item and isinstance(item["videoMeta"], dict):
        cover = item["videoMeta"].get("coverUrl") or item["videoMeta"].get("originalCoverUrl")
        if cover: return cover
    if "video" in item and isinstance(item["video"], dict):
        cover = item["video"].get("cover") or item["video"].get("originCover")
        if cover: return cover
    if "authorMeta" in item and isinstance(item["authorMeta"], dict):
        avatar = item["authorMeta"].get("avatar") or item["authorMeta"].get("originalAvatarUrl")
        if avatar: return avatar
    return None

# --- 3. ГЛАВНАЯ ЛОГИКА ---
def run_analysis(keywords, business_desc=""):
    run_id = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not keywords: return

    print(f"🚀 UTS Анализ: {keywords}")
    print(f"🏢 Бизнес: {business_desc}")

    scorer = TrendScorer()
    anchor_vector = get_text_embedding(business_desc) if business_desc else None
    
    try:
        db = get_db_session()
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return

    # === ЭТАП 1: SMART CACHE (ИЩЕМ В БАЗЕ) ===
    cache_count = 0
    if anchor_vector:
        print("🔍 Проверка Smart Cache (ищем старые запасы)...")
        try:
            cached_trends = db.query(Trend).order_by(
                Trend.embedding.cosine_distance(anchor_vector)
            ).limit(15).all()

            for t in cached_trends:
                # Не обновляем, если это УЖЕ текущий запуск
                if t.run_id == run_id: continue
                
                if t.embedding is not None:
                    sim = scorer.calculate_similarity(anchor_vector, t.embedding)
                    
                    # Если похоже на новый запрос - "поднимаем" в отчет
                    if sim > 0.60: 
                        print(f"   🔄 Кэш: обновляем дату для {t.id} (Sim: {sim:.2f})")
                        t.run_id = run_id        # Ставим текущую дату
                        t.vertical = keywords[0] # Обновляем тему
                        # Пересчитываем схожесть под новый бизнес-вектор
                        t.similarity = sim 
                        t.transfer_score = float(scorer.calculate_transfer_score(
                            sim, t.normalized_reach - 1.0, t.normalized_reach
                        ))
                        cache_count += 1
            
            db.commit()
            print(f"🎉 Из базы поднято: {cache_count} видео.")

        except Exception as e:
            print(f"⚠️ Ошибка Smart Cache: {e}")

    # === ЭТАП 2: ЗАПУСК СКРЕПЕРА (ВСЕГДА) ===
    print("📡 Запускаем Apify за свежим контентом...")
    
    collector = TikTokCollector()
    filter_logic = ViralContentFilter(business_keywords=keywords)

    raw_items = collector.collect(keywords, limit_per_keyword=30)
    
    if not raw_items:
        print("⚠️ Apify ничего не нашел.")
        db.close()
        return

    clean_items = filter_logic.filter_content(raw_items)
    print(f"💎 На векторизацию: {len(clean_items)} видео.")
    
    saved_count = 0
    
    # Baseline
    all_reaches = []
    for item in clean_items:
        views = int(item.get("playCount") or item.get("stats", {}).get("playCount", 0))
        author_meta = item.get("authorMeta") or {}
        followers = int(author_meta.get("fans") or author_meta.get("followers") or 0)
        r = scorer.calculate_normalized_reach(views, followers)
        all_reaches.append(r)
    
    baseline_reach = float(np.mean(all_reaches)) if all_reaches else 1.0
    
    for item in clean_items:
        url = item.get("webVideoUrl") or item.get("video", {}).get("playAddr", "")
        
        # 🔥 ПРОВЕРКА НА ДУБЛИКАТЫ ИЗ СКРЕПЕРА
        existing = db.query(Trend).filter(Trend.url == url).first()
        if existing:
            # Если скрепер нашел то, что уже есть - просто обновляем run_id
            # (Если мы это видео еще не обновили на этапе кэша)
            if existing.run_id != run_id:
                print(f"   🔄 Скрепер нашел дубль из базы: {existing.id}")
                existing.run_id = run_id
                saved_count += 1
            continue

        # --- ОБРАБОТКА НОВОГО ---
        stats = item.get("stats", {})
        views = int(item.get("playCount") or stats.get("playCount", 0))
        likes = int(item.get("diggCount") or stats.get("diggCount", 0))
        
        author_meta = item.get("authorMeta") or {}
        followers = int(author_meta.get("fans") or author_meta.get("followers") or 0)

        reach_score = scorer.calculate_normalized_reach(views, followers)
        
        cover_url = find_image_url(item)
        video_vector = None
        similarity_score = 0.0
        
        if cover_url:
            video_vector = get_image_embedding(cover_url)
            if video_vector and anchor_vector:
                similarity_score = scorer.calculate_similarity(anchor_vector, video_vector)
        
        uplift_score = reach_score - baseline_reach
        transfer_score = float(scorer.calculate_transfer_score(similarity_score, uplift_score, reach_score))

        text_desc = item.get("text") or item.get("desc", "")
        summary = "No Key"
        if model_gemini:
            try:
                time.sleep(1.5)
                prompt = f"О чем видео (5 слов, рус): '{text_desc}'"
                resp = model_gemini.generate_content(prompt)
                if resp.text: summary = resp.text.strip()
            except:
                summary = "AI Error"

        new_trend = Trend(
            run_id=run_id, 
            vertical=keywords[0], 
            platform="tiktok", 
            url=url,
            description=text_desc, 
            stats={"views": views, "likes": likes}, 
            followers=followers,
            normalized_reach=float(reach_score),
            similarity=float(similarity_score),
            transfer_score=transfer_score,
            uts_score=transfer_score,
            ai_summary=summary, 
            embedding=video_vector 
        )
        db.add(new_trend)
        saved_count += 1
        print(f"✅ NEW: {transfer_score:.2f} (S:{similarity_score:.2f}) | {summary[:10]}...")

    db.commit()
    db.close()
    print(f"\n🏁 Готово! Старых: {cache_count}, Новых: {saved_count}")

if __name__ == "__main__":
    pass