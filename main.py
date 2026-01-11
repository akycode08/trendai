import sys
import os
import time
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import requests
import torch

from database import Trend, get_db_session
from src.collector import TikTokCollector
from src.filter import ViralContentFilter
from src.scorer import TrendScorer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# --- AI SETUP ---
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model_gemini = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    model_gemini = None

clip_model = None
clip_processor = None

def load_clip():
    global clip_model, clip_processor
    if clip_model is None:
        print("🧠 Загрузка CLIP...")
        try:
            clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            print("✅ CLIP готов.")
        except Exception as e:
            print(f"⚠️ Ошибка CLIP: {e}")

def get_text_embedding(text: str):
    load_clip()
    if not clip_model or not text: return None
    try:
        inputs = clip_processor(text=[text], return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = clip_model.get_text_features(**inputs)
        return outputs.squeeze().numpy().tolist()
    except: return None

def get_image_embedding(image_url):
    load_clip()
    if not clip_model or not image_url: return None
    try:
        resp = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=5)
        if resp.status_code != 200: return None
        image = Image.open(resp.raw)
        inputs = clip_processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = clip_model.get_image_features(**inputs)
        return outputs.squeeze().numpy().tolist()
    except: return None

def find_image_url(item):
    if "videoMeta" in item and item["videoMeta"].get("coverUrl"):
        return item["videoMeta"]["coverUrl"]
    if "cover" in item: return item["cover"]
    if "thumbnail" in item: return item["thumbnail"]
    return None

def download_image_for_gemini(url):
    if not url: return None
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=10)
        if resp.status_code == 200:
            return Image.open(BytesIO(resp.content))
    except: return None
    return None

# --- ГЛАВНАЯ ЛОГИКА ---
def run_analysis(keywords, business_desc="", mode="search"):
    run_id = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not keywords: return []

    print(f"\n🚀 ЗАПУСК (Mode: {mode}): {keywords}")
    scorer = TrendScorer()
    
    # Вектор бизнеса (ТОЛЬКО ДЛЯ ПОИСКА)
    anchor_vector = None
    if mode == "search" and business_desc:
        anchor_vector = get_text_embedding(business_desc)
    
    # 1. СКАЧИВАЕМ (Лимит 30)
    collector = TikTokCollector()
    raw_items = collector.collect(keywords, limit=30, mode=mode)
    
    if not raw_items:
        print("⚠️ Пусто.")
        return []

    # 2. ФИЛЬТРУЕМ (Твои алгоритмы)
    is_profile = (mode == "profile")
    filter_logic = ViralContentFilter(business_keywords=keywords, is_profile_mode=is_profile)
    clean_items = filter_logic.filter_content(raw_items)
    
    # Baseline
    all_reaches = []
    for item in clean_items:
        views = int(item.get("playCount", 0))
        followers = int(item.get("authorMeta", {}).get("fans", 100))
        if followers < 100: followers = 100
        all_reaches.append(scorer.calculate_normalized_reach(views, followers))
    baseline = float(np.mean(all_reaches)) if all_reaches else 1.0
    
    # --- РАЗВИЛКА ---

    # А. ПРОФИЛЬ (Линейно, без БД)
    if mode == "profile":
        print("\n👤 Анализ профиля (без БД)...")
        results = []
        for i, item in enumerate(clean_items):
            stats = item.get("stats", {})
            views = int(stats.get("playCount", 0))
            likes = int(stats.get("diggCount", 0))
            cover_url = find_image_url(item)
            text_desc = item.get("text", "")
            url = item.get("webVideoUrl")
            
            # AI (Топ-5)
            ai_summary = "Pending"
            if i < 5 and model_gemini:
                try:
                    img = download_image_for_gemini(cover_url)
                    prompt = f"Конкурент. Текст: {text_desc}. Views: {views}. Суть? (1 фраза)"
                    inputs = [prompt, img] if img else [prompt]
                    resp = model_gemini.generate_content(inputs)
                    if resp.text: ai_summary = resp.text.strip()
                    time.sleep(1)
                except: ai_summary = "Limit"
            
            results.append({
                "url": url,
                "cover_url": cover_url,
                "description": text_desc,
                "stats": {"views": views, "likes": likes},
                "ai_summary": ai_summary
            })
            print(f"👀 Processed: {views}")
        return results

    # Б. ПОИСК (Сохраняем в Базу с Формулами)
    else:
        print("\n🌍 Анализ поиска (в БАЗУ)...")
        try:
            db = get_db_session()
        except:
            return []
            
        processed_trends = []
        for item in clean_items:
            url = item.get("webVideoUrl")
            
            existing = db.query(Trend).filter(Trend.url == url).first()
            if existing:
                existing.run_id = run_id
                continue

            stats = item.get("stats", {})
            views = int(stats.get("playCount", 0))
            likes = int(stats.get("diggCount", 0))
            followers = int(item.get("authorMeta", {}).get("fans", 0))
            cover_url = find_image_url(item)
            text_desc = item.get("text", "")
            
            # === ТВОИ ФОРМУЛЫ ===
            reach_score = scorer.calculate_normalized_reach(views, followers)
            
            video_vector = None
            sim_score = 0.0
            if cover_url and anchor_vector:
                video_vector = get_image_embedding(cover_url)
                if video_vector:
                    sim_score = float(scorer.calculate_similarity(anchor_vector, video_vector))
            
            uplift = reach_score - baseline
            # Финальный балл (UTS)
            transfer_score = float(scorer.calculate_transfer_score(sim_score, uplift, reach_score))
            # ====================

            ai_summary = "Pending"
            if model_gemini:
                try:
                    img = download_image_for_gemini(cover_url)
                    prompt = f"Тренд. Текст: {text_desc}. Views: {views}. Суть? (1 фраза)"
                    inputs = [prompt, img] if img else [prompt]
                    resp = model_gemini.generate_content(inputs)
                    if resp.text: ai_summary = resp.text.strip()
                    time.sleep(1)
                except: ai_summary = "Limit"

            # СОХРАНЯЕМ В БД (Включая картинку и баллы!)
            new_trend = Trend(
                run_id=run_id, 
                vertical=keywords[0], 
                platform="tiktok", 
                url=url,
                cover_url=cover_url, # <--- РАСКОММЕНТИРОВАЛИ!
                description=text_desc, 
                stats={"views": views, "likes": likes}, 
                followers=followers,
                normalized_reach=float(reach_score),
                similarity=float(sim_score),
                transfer_score=transfer_score,
                uts_score=transfer_score, # Сохраняем UTS
                ai_summary=ai_summary, 
                embedding=video_vector 
            )
            db.add(new_trend)
            processed_trends.append(new_trend)
            print(f"✅ Saved DB: {views} | UTS: {transfer_score:.2f}")

        db.commit()
        db.close()
        return processed_trends