"""
Migration utilities: PostgreSQL → Neo4j
Миграция данных из PostgreSQL в Neo4j граф
"""

from typing import Optional, List, Dict, Any
from .models import get_db_session, Trend, ProfileData
from .graph import Neo4jGraph, get_graph
from datetime import datetime

def extract_hashtags_from_raw_data(raw_data: Dict[str, Any]) -> List[str]:
    """
    Извлекает хэштеги из raw Apify данных
    
    Args:
        raw_data: Сырые данные от Apify (может быть в разных форматах)
    
    Returns:
        Список хэштегов (строки)
    """
    hashtags = []
    
    # Формат 1: прямое поле hashtags
    if "hashtags" in raw_data:
        tags = raw_data["hashtags"]
        if isinstance(tags, list):
            hashtags.extend([tag for tag in tags if tag and isinstance(tag, str)])
    
    # Формат 2: вложенный формат
    if "channel" in raw_data and isinstance(raw_data["channel"], dict):
        channel_tags = raw_data["channel"].get("hashtags", [])
        if isinstance(channel_tags, list):
            hashtags.extend([tag for tag in channel_tags if tag and isinstance(tag, str)])
    
    return list(set(hashtags))  # Убираем дубликаты

def extract_song_from_raw_data(raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Извлекает данные песни из raw Apify данных
    
    Args:
        raw_data: Сырые данные от Apify
    
    Returns:
        Словарь с данными песни {title, author/artist, id} или None
    """
    # Формат 1: прямое поле song
    if "song" in raw_data:
        song = raw_data["song"]
        if isinstance(song, dict) and (song.get("title") or song.get("id")):
            return song
    
    # Формат 2: music field
    if "music" in raw_data:
        music = raw_data["music"]
        if isinstance(music, dict):
            return {
                "title": music.get("title", ""),
                "author": music.get("author", "") or music.get("artist", ""),
                "id": music.get("id", "")
            }
    
    return None

def migrate_trend_to_graph(trend: Trend, graph: Neo4jGraph, raw_apify_data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Мигрирует один Trend из PostgreSQL в Neo4j
    
    Args:
        trend: Объект Trend из PostgreSQL
        graph: Экземпляр Neo4jGraph
        raw_apify_data: Сырые данные от Apify (для хэштегов и музыки)
    
    Returns:
        True if successful
    """
    if not trend.url:
        return False
    
    try:
        # Подготовка данных видео
        stats = trend.stats if isinstance(trend.stats, dict) else {}
        video_data = {
            "url": trend.url,
            "description": trend.description or "",
            "cover_url": trend.cover_url or "",
            "views": stats.get("views", 0),
            "likes": stats.get("likes", 0),
            "comments": stats.get("comments", 0) or stats.get("commentCount", 0),
            "shares": stats.get("shares", 0) or stats.get("shareCount", 0),
            "uts_score": trend.uts_score or 0.0,
            "created_at": int(trend.created_at.timestamp()) if trend.created_at else 0,
            "stats": stats
        }
        
        # Добавляем хэштеги и музыку из raw_data, если есть
        if raw_apify_data:
            hashtags = extract_hashtags_from_raw_data(raw_apify_data)
            video_data["hashtags"] = hashtags
            
            song = extract_song_from_raw_data(raw_apify_data)
            if song:
                video_data["song"] = song
        
        # Создаем профиль, если есть username
        username = trend.author_username
        if username:
            # Пытаемся получить channel_data из ProfileData
            db = get_db_session()
            profile_data = db.query(ProfileData).filter(ProfileData.username == username.lower()).first()
            db.close()
            
            channel_data = None
            if profile_data and profile_data.channel_data:
                channel_data = profile_data.channel_data if isinstance(profile_data.channel_data, dict) else {}
            
            if not channel_data:
                # Создаем минимальный channel_data из Trend
                channel_data = {
                    "followers": trend.followers or 0,
                    "following": 0,
                    "videos": 0,
                    "verified": False,
                    "name": username,
                    "bio": "",
                    "avatar": ""
                }
            
            graph.create_profile_node(username, channel_data)
        
        # Сохраняем видео со всеми связями
        vertical = trend.vertical if trend.vertical else None
        success = graph.save_video_with_relationships(
            trend.url,
            video_data,
            username if username else "",
            vertical
        )
        
        return success
    except Exception as e:
        print(f"⚠️ Ошибка миграции Trend {trend.url}: {e}")
        return False

def migrate_profile_to_graph(username: str, graph: Neo4jGraph) -> int:
    """
    Мигрирует профиль и все его видео из PostgreSQL в Neo4j
    
    Args:
        username: Username профиля (normalized, lowercase)
        graph: Экземпляр Neo4jGraph
    
    Returns:
        Количество успешно мигрированных видео
    """
    db = get_db_session()
    
    try:
        # Получаем ProfileData
        profile_data = db.query(ProfileData).filter(ProfileData.username == username.lower()).first()
        
        if not profile_data:
            print(f"⚠️ Профиль {username} не найден в PostgreSQL")
            return 0
        
        # Создаем узел Profile
        channel_data = profile_data.channel_data if isinstance(profile_data.channel_data, dict) else {}
        graph.create_profile_node(username.lower(), channel_data)
        
        # Получаем все видео профиля из Trend таблицы
        trends = db.query(Trend).filter(Trend.author_username == username.lower()).all()
        
        migrated_count = 0
        raw_data_list = profile_data.raw_data if isinstance(profile_data.raw_data, list) else []
        
        # Создаем словарь raw_data по URL для быстрого доступа
        raw_data_map = {}
        for raw_item in raw_data_list:
            if isinstance(raw_item, dict):
                url = raw_item.get("postPage") or raw_item.get("video", {}).get("url") or raw_item.get("url")
                if url:
                    raw_data_map[url] = raw_item
        
        # Мигрируем каждое видео
        for trend in trends:
            raw_data = raw_data_map.get(trend.url) if trend.url in raw_data_map else None
            if migrate_trend_to_graph(trend, graph, raw_data):
                migrated_count += 1
        
        print(f"✅ Мигрировано {migrated_count}/{len(trends)} видео профиля {username}")
        return migrated_count
        
    except Exception as e:
        print(f"⚠️ Ошибка миграции профиля {username}: {e}")
        return 0
    finally:
        db.close()

def migrate_all_profiles_to_graph(graph: Optional[Neo4jGraph] = None) -> Dict[str, int]:
    """
    Мигрирует все профили из PostgreSQL в Neo4j
    
    Args:
        graph: Экземпляр Neo4jGraph (если None, создается новый)
    
    Returns:
        Словарь {username: migrated_count}
    """
    if graph is None:
        graph = get_graph()
        if not graph:
            print("⚠️ Не удалось подключиться к Neo4j")
            return {}
    
    db = get_db_session()
    
    try:
        # Получаем все профили
        profiles = db.query(ProfileData).all()
        
        results = {}
        for profile in profiles:
            username = profile.username
            count = migrate_profile_to_graph(username, graph)
            results[username] = count
        
        total = sum(results.values())
        print(f"✅ Миграция завершена: {total} видео из {len(profiles)} профилей")
        return results
        
    except Exception as e:
        print(f"⚠️ Ошибка миграции всех профилей: {e}")
        return {}
    finally:
        db.close()

def migrate_all_trends_to_graph(graph: Optional[Neo4jGraph] = None, limit: Optional[int] = None) -> int:
    """
    Мигрирует все тренды из PostgreSQL в Neo4j
    
    Args:
        graph: Экземпляр Neo4jGraph (если None, создается новый)
        limit: Максимальное количество трендов для миграции (None = все)
    
    Returns:
        Количество успешно мигрированных трендов
    """
    if graph is None:
        graph = get_graph()
        if not graph:
            print("⚠️ Не удалось подключиться к Neo4j")
            return 0
    
    db = get_db_session()
    
    try:
        query = db.query(Trend)
        if limit:
            query = query.limit(limit)
        trends = query.all()
        
        migrated_count = 0
        for trend in trends:
            if migrate_trend_to_graph(trend, graph):
                migrated_count += 1
        
        print(f"✅ Мигрировано {migrated_count}/{len(trends)} трендов")
        return migrated_count
        
    except Exception as e:
        print(f"⚠️ Ошибка миграции всех трендов: {e}")
        return 0
    finally:
        db.close()
