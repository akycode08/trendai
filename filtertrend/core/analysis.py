import sys
import os
import time
import base64
import re
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv
from anthropic import Anthropic
import numpy as np
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import requests
import torch

from filtertrend.core import Trend, ProfileData, get_db_session
from filtertrend.core.graph import get_graph
from filtertrend.services import TikTokCollector, ViralContentFilter, TrendScorer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# --- AI SETUP ---
api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    claude_client = Anthropic(api_key=api_key)
else:
    claude_client = None

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

def get_anchor_vector_from_profile(profile_username):
    """
    Создает anchor-вектор из профиля аккаунта.
    Берет все обложки видео из профиля, создает векторы и усредняет их.
    
    Args:
        profile_username: username профиля (будет нормализован)
    
    Returns:
        Усредненный вектор из всех обложек видео профиля, или None если профиль не найден
    """
    if not profile_username:
        return None
    
    try:
        db = get_db_session()
        # Нормализуем username
        clean_username = normalize_username(profile_username)
        
        # Получаем профиль из БД
        profile = db.query(ProfileData).filter(ProfileData.username == clean_username).first()
        db.close()
        
        if not profile or not profile.raw_data:
            print(f"⚠️ Профиль {clean_username} не найден в БД или нет видео")
            return None
        
        raw_data = profile.raw_data if isinstance(profile.raw_data, list) else []
        if not raw_data:
            print(f"⚠️ Профиль {clean_username} не содержит видео")
            return None
        
        # Собираем все обложки видео
        cover_urls = []
        for video in raw_data:
            # Формат Apify: video.videoMeta.cover
            cover_url = None
            if isinstance(video, dict):
                # Пробуем разные форматы
                if "video" in video and isinstance(video["video"], dict):
                    cover_url = video["video"].get("cover") or video["video"].get("thumbnail")
                elif "videoMeta" in video and isinstance(video["videoMeta"], dict):
                    cover_url = video["videoMeta"].get("cover")
                elif "cover" in video:
                    cover_url = video["cover"]
                elif "coverUrl" in video:
                    cover_url = video["coverUrl"]
            
            if cover_url and isinstance(cover_url, str) and cover_url.strip():
                cover_urls.append(cover_url.strip())
        
        if not cover_urls:
            print(f"⚠️ В профиле {clean_username} нет обложек видео")
            return None
        
        print(f"📸 Создаю anchor из {len(cover_urls)} обложек профиля {clean_username}...")
        
        # Создаем векторы для каждой обложки
        vectors = []
        for cover_url in cover_urls[:20]:  # Ограничиваем 20 обложками для скорости
            vec = get_image_embedding(cover_url)
            if vec:
                vectors.append(np.array(vec))
        
        if not vectors:
            print(f"⚠️ Не удалось создать векторы из обложек профиля {clean_username}")
            return None
        
        # Усредняем все векторы (среднее арифметическое)
        avg_vector = np.mean(vectors, axis=0)
        anchor_vector = avg_vector.tolist()
        
        print(f"✅ Anchor-вектор создан из {len(vectors)} обложек")
        return anchor_vector
        
    except Exception as e:
        print(f"⚠️ Ошибка создания anchor из профиля {profile_username}: {e}")
        return None

def normalize_username(username_or_url):
    """Извлекает username из URL или возвращает username как есть"""
    if not username_or_url:
        return ""
    username_or_url = username_or_url.strip()
    
    # Если это URL - извлекаем username из @username
    match = re.search(r'@([^?/_]+)', username_or_url)
    if match:
        return match.group(1).lower()
    
    # Если это уже username - убираем @ и возвращаем
    username = username_or_url.replace("@", "").split('?')[0].split('/')[-1]
    return username.lower()

def find_image_url(item):
    if "videoMeta" in item and item["videoMeta"].get("coverUrl"):
        return item["videoMeta"]["coverUrl"]
    if "cover" in item: return item["cover"]
    if "thumbnail" in item: return item["thumbnail"]
    return None

def download_image_for_claude(url):
    """Загружает изображение и конвертирует в base64 для Claude API"""
    if not url: return None
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=5)
        if resp.status_code == 200:
            img_bytes = resp.content
            # Ограничение размера: Claude API имеет лимит ~5MB на изображение
            if len(img_bytes) > 5 * 1024 * 1024:  # 5MB
                return None
            
            # Определяем тип изображения по MIME типу или расширению
            img_format = "jpeg"
            content_type = resp.headers.get('content-type', '').lower()
            if 'png' in content_type or url.lower().endswith('.png'): 
                img_format = "png"
            elif 'webp' in content_type or url.lower().endswith('.webp'): 
                img_format = "webp"
            elif 'gif' in content_type or url.lower().endswith('.gif'): 
                img_format = "gif"
            elif 'jpeg' in content_type or 'jpg' in content_type:
                img_format = "jpeg"
            
            # Конвертируем в base64
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": f"image/{img_format}",
                    "data": img_base64
                }
            }
    except Exception as e:
        # Тихая ошибка - просто не используем изображение
        return None
    return None

# --- ГЛАВНАЯ ЛОГИКА ---
def run_analysis(keywords, business_desc="", anchor_profile_username="", mode="search"):
    run_id = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not keywords: return []

    print(f"\n🚀 ЗАПУСК (Mode: {mode}): {keywords}")
    scorer = TrendScorer()
    
    # Вектор бизнеса (anchor) - ТОЛЬКО ДЛЯ ПОИСКА
    anchor_vector = None
    if mode == "search":
        # Приоритет: профиль аккаунта > текстовое описание
        if anchor_profile_username:
            anchor_vector = get_anchor_vector_from_profile(anchor_profile_username)
            if anchor_vector:
                print(f"✅ Используем anchor из профиля: {anchor_profile_username}")
            else:
                print(f"⚠️ Не удалось создать anchor из профиля {anchor_profile_username}, пробуем текстовое описание...")
                if business_desc:
                    anchor_vector = get_text_embedding(business_desc)
        elif business_desc:
            # Fallback: текстовое описание (старый способ)
            anchor_vector = get_text_embedding(business_desc)
    
    # 1. СКАЧИВАЕМ (Лимит 30)
    raw_items = []
    
    if mode == "profile":
        # ВСЕГДА сначала запрашиваем Apify, затем сохраняем в БД
        profile_input = keywords[0] if keywords else ""
        profile_username = normalize_username(profile_input)
        print(f"📡 Запрашиваем Apify для профиля {profile_username}...")
        collector = TikTokCollector()
        raw_items = collector.collect(keywords, limit=30, mode=mode)
    else:
        # Для search режима - всегда запрашиваем Apify
        collector = TikTokCollector()
        raw_items = collector.collect(keywords, limit=30, mode=mode)
    
    if not raw_items and mode != "profile":
        print("⚠️ Пусто.")
        return []

    # 2. ФИЛЬТРУЕМ (Твои алгоритмы)
    is_profile = (mode == "profile")
    filter_logic = ViralContentFilter(business_keywords=keywords, is_profile_mode=is_profile)
    clean_items = filter_logic.filter_content(raw_items) if raw_items else []
    
    # Baseline
    all_reaches = []
    for item in clean_items:
        views = int(item.get("playCount", 0))
        followers = int(item.get("authorMeta", {}).get("fans", 100))
        if followers < 100: followers = 100
        all_reaches.append(scorer.calculate_normalized_reach(views, followers))
    baseline = float(np.mean(all_reaches)) if all_reaches else 1.0
    
    # --- РАЗВИЛКА ---

    # А. ПРОФИЛЬ (Запрашиваем Apify, сохраняем в БД)
    if mode == "profile":
        print("\n👤 Анализ профиля (запрос Apify, сохранение в БД)...")
        try:
            db = get_db_session()
        except:
            db = None
            print("⚠️ БД недоступна, работаем без сохранения")
        
        profile_input = keywords[0] if keywords else ""
        profile_username = normalize_username(profile_input)
        results = []
        cached_count = 0
        new_count = 0
        
        # ВСЕГДА обрабатываем данные из Apify и сохраняем в БД
        for i, item in enumerate(clean_items):
            stats = item.get("stats", {})
            views = int(stats.get("playCount", 0))
            likes = int(stats.get("diggCount", 0))
            cover_url = find_image_url(item)
            text_desc = item.get("text", "")
            url = item.get("webVideoUrl")
            
            # Проверяем кеш в БД (чтобы не дублировать)
            cached_item = None
            if db and url:
                cached_item = db.query(Trend).filter(Trend.url == url).first()
            
            if cached_item:
                # Используем данные из кеша (но всё равно возвращаем в результатах)
                cached_count += 1
                ai_summary = cached_item.ai_summary or "Pending"
                results.append({
                    "url": cached_item.url,
                    "cover_url": cached_item.cover_url,
                    "description": cached_item.description,
                    "stats": cached_item.stats if isinstance(cached_item.stats, dict) else {"views": views, "likes": likes},
                    "ai_summary": ai_summary,
                    "create_time": cached_item.created_at.timestamp() if cached_item.created_at else 0
                })
                print(f"💾 Кеш: {views} views")
            else:
                # Новое видео - обрабатываем и сохраняем
                new_count += 1
                ai_summary = "Pending"
                if i < 5 and claude_client:
                    try:
                        img_data = download_image_for_claude(cover_url)
                        prompt = f"Конкурент. Текст: {text_desc}. Views: {views}. Суть? (1 фраза)"
                        
                        # Формируем сообщение: пробуем с изображением, если не получается - только текст
                        if img_data:
                            messages = [{
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    img_data
                                ]
                            }]
                        else:
                            messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                        
                        # Используем более дешевую модель для экономии
                        resp = claude_client.messages.create(
                            model="claude-3-5-haiku-20241022",
                            max_tokens=50,
                            messages=messages
                        )
                        if resp.content and len(resp.content) > 0:
                            ai_summary = resp.content[0].text.strip()
                        time.sleep(0.5)
                    except Exception as e:
                        # При ошибке пробуем только текст
                        try:
                            resp = claude_client.messages.create(
                                model="claude-3-5-haiku-20241022",
                                max_tokens=50,
                                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                            )
                            if resp.content and len(resp.content) > 0:
                                ai_summary = resp.content[0].text.strip()
                        except:
                            ai_summary = "Ошибка API"
                
                # Сохраняем в БД для кеширования
                if db and url:
                    try:
                        followers = int(item.get("authorMeta", {}).get("fans", 0))
                        # Нормализуем username для сохранения
                        saved_username = normalize_username(profile_input) if profile_input else profile_username
                        new_trend = Trend(
                            run_id=run_id,
                            vertical=saved_username,  # Сохраняем нормализованный username
                            platform="tiktok",
                            url=url,
                            cover_url=cover_url,
                            description=text_desc,
                            stats={"views": views, "likes": likes},
                            followers=followers,
                            author_username=saved_username,  # Для поиска по профилю
                            ai_summary=ai_summary,
                            normalized_reach=0.0,  # Для профилей не считаем
                            similarity=0.0,
                            transfer_score=0.0,
                            uts_score=0.0
                        )
                        db.add(new_trend)
                    except Exception as e:
                        print(f"⚠️ Ошибка сохранения в БД: {e}")
                
                # === NEO4J ИНТЕГРАЦИЯ (опционально, не блокирует) ===
                try:
                    graph = get_graph()
                    if graph and graph.driver:
                        username = item.get("authorMeta", {}).get("name", "")
                        if username:
                            # Адаптируем stats для Neo4j (views, likes, comments, shares)
                            stats_for_graph = {
                                "views": views,
                                "likes": likes,
                                "comments": int(stats.get("commentCount", 0)),
                                "shares": int(stats.get("shareCount", 0))
                            }
                            
                            video_data_for_graph = {
                                "stats": stats_for_graph,
                                "description": text_desc,
                                "cover_url": cover_url,
                                "hashtags": item.get("hashtags", []),  # Из адаптированных данных
                                "song": item.get("song"),  # Из адаптированных данных
                                "uts_score": 0.0,  # Для профилей не считаем
                                "created_at": item.get("createTime", 0)  # Таймштамп
                            }
                            
                            # Сохраняем в Neo4j со всеми связями
                            graph.save_video_with_relationships(
                                video_url=url,
                                video_data=video_data_for_graph,
                                username=username.lower(),
                                vertical=None  # Для профилей vertical не используется
                            )
                except Exception as e:
                    # Neo4j ошибки не блокируют основной процесс
                    pass  # Тихая ошибка для профилей
                
                results.append({
                    "url": url,
                    "cover_url": cover_url,
                    "description": text_desc,
                    "stats": {"views": views, "likes": likes},
                    "ai_summary": ai_summary,
                    "create_time": item.get("createTime", 0)
                })
                print(f"🆕 Новое: {views} views")
        
        if db:
            try:
                db.commit()
                print(f"✅ Кеш: {cached_count} из БД, {new_count} новых сохранено")
            except:
                pass
            finally:
                db.close()
        
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
            # Ограничение: AI анализ только для первых 10 видео (защита от больших расходов)
            if claude_client and len(processed_trends) < 10:
                try:
                    img_data = download_image_for_claude(cover_url)
                    prompt = f"Тренд. Текст: {text_desc}. Views: {views}. Суть? (1 фраза)"
                    
                    # Формируем сообщение: пробуем с изображением, если не получается - только текст
                    if img_data:
                        messages = [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                img_data
                            ]
                        }]
                    else:
                        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                    
                    # Используем более дешевую модель для экономии
                    resp = claude_client.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=50,
                        messages=messages
                    )
                    if resp.content and len(resp.content) > 0:
                        ai_summary = resp.content[0].text.strip()
                    time.sleep(0.5)
                except Exception as e:
                    # При ошибке пробуем только текст
                    try:
                        resp = claude_client.messages.create(
                            model="claude-3-5-haiku-20241022",
                            max_tokens=50,
                            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                        )
                        if resp.content and len(resp.content) > 0:
                            ai_summary = resp.content[0].text.strip()
                    except:
                        ai_summary = "Ошибка API"

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
            
            # === NEO4J ИНТЕГРАЦИЯ (опционально, не блокирует) ===
            try:
                graph = get_graph()
                if graph and graph.driver:
                    # Подготавливаем данные для Neo4j
                    username = item.get("authorMeta", {}).get("name", "")
                    if username:
                        # Адаптируем stats для Neo4j (views, likes, comments, shares)
                        stats_for_graph = {
                            "views": views,
                            "likes": likes,
                            "comments": int(stats.get("commentCount", 0)),
                            "shares": int(stats.get("shareCount", 0))
                        }
                        
                        video_data_for_graph = {
                            "stats": stats_for_graph,
                            "description": text_desc,
                            "cover_url": cover_url,
                            "hashtags": item.get("hashtags", []),  # Из адаптированных данных
                            "song": item.get("song"),  # Из адаптированных данных
                            "uts_score": transfer_score,  # UTS для поиска
                            "created_at": item.get("createTime", 0)  # Таймштамп
                        }
                        
                        # Сохраняем в Neo4j со всеми связями
                        graph.save_video_with_relationships(
                            video_url=url,
                            video_data=video_data_for_graph,
                            username=username.lower(),
                            vertical=keywords[0] if keywords else None
                        )
                        print(f"  📊 Neo4j: сохранено")
            except Exception as e:
                # Neo4j ошибки не блокируют основной процесс
                print(f"  ⚠️ Neo4j: {e}")

        db.commit()
        
        # Преобразуем объекты в словари перед закрытием сессии
        trends_dicts = []
        for trend in processed_trends:
            stats = trend.stats if isinstance(trend.stats, dict) else {}
            trends_dicts.append({
                "url": trend.url,
                "cover_url": trend.cover_url,
                "description": trend.description,
                "stats": stats,
                "uts_score": trend.uts_score,
                "ai_summary": trend.ai_summary
            })
        
        db.close()
        return trends_dicts