# Файл: src/adapter.py

def adapt_apidojo_to_standard(item):
    """
    Универсальный адаптер. 
    Понимает:
    1. Плоский формат (video.cover) - ТВОЙ СЛУЧАЙ
    2. Вложенный формат (video: {cover: ...})
    3. Старый формат (author, videoUrl)
    """
    try:
        # --- ВАРИАНТ 0: ПЛОСКИЙ ФОРМАТ (Flattened JSON) ---
        # Проверяем наличие ключей с точками, как в твоем примере
        if "video.cover" in item or "channel.username" in item:
            
            stats = {
                "playCount": item.get("views", 0),
                "diggCount": item.get("likes", 0),
                "commentCount": item.get("comments", 0),
                "shareCount": item.get("shares", 0)
            }
            
            # Извлекаем картинку из плоских ключей
            cover_url = item.get("video.cover") or item.get("video.thumbnail")
            
            return {
                "id": item.get("id"),
                "webVideoUrl": item.get("postPage") or item.get("video.url"),
                "text": item.get("title", ""),
                "createTime": item.get("uploadedAt", 0), # Таймштамп для сортировки
                "authorMeta": {
                    "id": item.get("channel.id"),
                    "name": item.get("channel.username"), # diazharass
                    "nickName": item.get("channel.name"), # 214AMG
                    "fans": item.get("channel.followers", 0),
                    "avatar": item.get("channel.avatar")
                },
                "videoMeta": {
                    "coverUrl": cover_url, # <--- ВОТ ОНА!
                    "duration": item.get("video.duration", 0),
                    "downloadAddr": item.get("video.url")
                },
                "stats": stats,
                "playCount": stats["playCount"],
                "diggCount": stats["diggCount"]
            }

        # --- ВАРИАНТ 1: Новый формат (Вложенные словари) ---
        elif "channel" in item and isinstance(item["channel"], dict):
            channel = item.get("channel", {})
            video_data = item.get("video", {})
            
            stats = {
                "playCount": item.get("views", 0),
                "diggCount": item.get("likes", 0),
                "commentCount": item.get("comments", 0),
                "shareCount": item.get("shares", 0)
            }

            return {
                "id": item.get("id"),
                "webVideoUrl": item.get("postPage") or video_data.get("url"),
                "text": item.get("title", ""),
                "createTime": item.get("uploadedAt", 0),
                "authorMeta": {
                    "id": channel.get("id"),
                    "name": channel.get("username"),
                    "nickName": channel.get("name"),
                    "fans": channel.get("followers", 0),
                    "avatar": channel.get("avatar")
                },
                "videoMeta": {
                    "coverUrl": video_data.get("cover") or video_data.get("thumbnail"),
                    "duration": video_data.get("duration", 0),
                    "downloadAddr": video_data.get("url")
                },
                "stats": stats,
                "playCount": stats["playCount"],
                "diggCount": stats["diggCount"]
            }

        # --- ВАРИАНТ 2: Старый формат (Legacy) ---
        else:
            author = item.get("author", {})
            stats = item.get("stats", {})
            if not stats:
                stats = {
                    "playCount": item.get("playCount", 0),
                    "diggCount": item.get("diggCount", 0),
                    "commentCount": item.get("commentCount", 0),
                    "shareCount": item.get("shareCount", 0)
                }
            
            return {
                "id": item.get("id"),
                "webVideoUrl": item.get("videoUrl") or item.get("webVideoUrl"),
                "text": item.get("desc", "") or item.get("text", ""),
                "createTime": item.get("createTime", 0),
                "authorMeta": {
                    "id": author.get("id"),
                    "name": author.get("uniqueId"),
                    "nickName": author.get("nickname"),
                    "fans": author.get("fans", 0),
                    "avatar": author.get("avatarThumb") or author.get("avatar")
                },
                "videoMeta": {
                    "coverUrl": item.get("video", {}).get("cover") or item.get("cover"),
                    "duration": item.get("video", {}).get("duration", 0),
                    "downloadAddr": item.get("video", {}).get("downloadAddr")
                },
                "stats": stats,
                "playCount": stats["playCount"],
                "diggCount": stats["diggCount"]
            }

    except Exception as e:
        print(f"⚠️ Ошибка адаптации элемента: {e}")
        return None