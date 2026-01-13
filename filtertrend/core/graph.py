"""
Neo4j Graph Database Integration
Реализует Knowledge Graph для TrendScout (6 Node Types, 27 Edge Types)
"""

import os
from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Neo4j Connection Settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class Neo4jGraph:
    """
    Neo4j Graph Database Manager
    Реализует 6 Node Types и 27 Edge Types согласно PDF спецификации
    """
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """
        Инициализация подключения к Neo4j
        
        Args:
            uri: Neo4j URI (bolt://localhost:7687 или neo4j+s://xxx.neo4j.io для Aura)
            user: Username
            password: Password
        """
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.driver = None
        
    def connect(self):
        """Подключение к Neo4j"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Проверка подключения
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✅ Neo4j подключен: {self.uri}")
            return True
        except Exception as e:
            print(f"⚠️ Ошибка подключения к Neo4j: {e}")
            print(f"💡 Убедитесь, что Neo4j запущен или проверьте NEO4J_URI в .env")
            return False
    
    def close(self):
        """Закрытие подключения"""
        if self.driver:
            self.driver.close()
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    # ==========================================
    # NODE CREATION (6 Node Types)
    # ==========================================
    
    def create_profile_node(self, username: str, channel_data: Dict[str, Any] = None) -> bool:
        """
        Создает узел Profile (Creator)
        
        Args:
            username: Username профиля (normalized, lowercase)
            channel_data: Данные канала (bio, followers, following, videos, verified, name, avatar)
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MERGE (p:Profile {username: $username})
                SET p.followers = $followers,
                    p.following = $following,
                    p.videos = $videos,
                    p.verified = $verified,
                    p.name = $name,
                    p.bio = $bio,
                    p.avatar = $avatar,
                    p.updated_at = datetime()
                RETURN p
                """
                
                followers = channel_data.get("followers", 0) if channel_data else 0
                following = channel_data.get("following", 0) if channel_data else 0
                videos = channel_data.get("videos", 0) if channel_data else 0
                verified = channel_data.get("verified", False) if channel_data else False
                name = channel_data.get("name", username) if channel_data else username
                bio = channel_data.get("bio", "") if channel_data else ""
                avatar = channel_data.get("avatar", "") if channel_data else ""
                
                session.run(query, 
                    username=username.lower(),
                    followers=followers,
                    following=following,
                    videos=videos,
                    verified=verified,
                    name=name,
                    bio=bio,
                    avatar=avatar
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания Profile узла {username}: {e}")
            return False
    
    def create_video_node(self, url: str, video_data: Dict[str, Any]) -> bool:
        """
        Создает узел Video
        
        Args:
            url: URL видео (unique identifier)
            video_data: Данные видео (views, likes, description, cover_url, etc.)
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MERGE (v:Video {url: $url})
                SET v.views = $views,
                    v.likes = $likes,
                    v.comments = $comments,
                    v.shares = $shares,
                    v.description = $description,
                    v.cover_url = $cover_url,
                    v.uts_score = $uts_score,
                    v.created_at = datetime({epochSeconds: $created_at}),
                    v.updated_at = datetime()
                RETURN v
                """
                
                stats = video_data.get("stats", {})
                views = stats.get("views", 0) if isinstance(stats, dict) else 0
                likes = stats.get("likes", 0) if isinstance(stats, dict) else 0
                comments = stats.get("comments", 0) if isinstance(stats, dict) else 0
                shares = stats.get("shares", 0) if isinstance(stats, dict) else 0
                
                session.run(query,
                    url=url,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    description=video_data.get("description", "")[:500],  # Ограничение длины
                    cover_url=video_data.get("cover_url", ""),
                    uts_score=video_data.get("uts_score", 0.0),
                    created_at=video_data.get("created_at", 0)
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания Video узла {url}: {e}")
            return False
    
    def create_hashtag_node(self, hashtag_name: str) -> bool:
        """
        Создает узел Hashtag
        
        Args:
            hashtag_name: Название хэштега (без #)
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MERGE (h:Hashtag {name: $name})
                ON CREATE SET h.usage_count = 1, h.created_at = datetime()
                ON MATCH SET h.usage_count = h.usage_count + 1, h.updated_at = datetime()
                RETURN h
                """
                
                # Нормализуем хэштег (убираем #, lowercase)
                clean_name = hashtag_name.strip().lower().lstrip('#')
                if not clean_name:
                    return False
                
                session.run(query, name=clean_name)
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания Hashtag узла {hashtag_name}: {e}")
            return False
    
    def create_song_node(self, song_data: Dict[str, Any]) -> bool:
        """
        Создает узел Song (Sound)
        
        Args:
            song_data: Данные песни {title, author/artist, id}
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            title = song_data.get("title", "") or song_data.get("name", "")
            author = song_data.get("author", "") or song_data.get("artist", "")
            song_id = song_data.get("id", "") or song_data.get("soundId", "")
            
            if not title and not song_id:
                return False
            
            # Используем ID как уникальный идентификатор, если есть, иначе title+author
            identifier = song_id if song_id else f"{title}_{author}"
            
            with self.driver.session() as session:
                query = """
                MERGE (s:Song {id: $id})
                ON CREATE SET s.title = $title,
                    s.author = $author,
                    s.usage_count = 1,
                    s.created_at = datetime()
                ON MATCH SET s.title = $title,
                    s.author = $author,
                    s.usage_count = coalesce(s.usage_count, 0) + 1,
                    s.updated_at = datetime()
                RETURN s
                """
                
                session.run(query,
                    id=identifier,
                    title=title,
                    author=author
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания Song узла: {e}")
            return False
    
    def create_location_node(self, location_name: str) -> bool:
        """
        Создает узел Location (если есть данные о местоположении)
        
        Args:
            location_name: Название локации
        
        Returns:
            True if successful
        """
        if not self.driver or not location_name:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MERGE (l:Location {name: $name})
                ON CREATE SET l.usage_count = 1, l.created_at = datetime()
                ON MATCH SET l.usage_count = l.usage_count + 1, l.updated_at = datetime()
                RETURN l
                """
                
                session.run(query, name=location_name.strip())
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания Location узла {location_name}: {e}")
            return False
    
    def create_trend_node(self, vertical: str, trend_data: Dict[str, Any] = None) -> bool:
        """
        Создает узел Trend (Vertical/Category)
        
        Args:
            vertical: Название вертикали/категории (например, "beauty", "travel")
            trend_data: Дополнительные данные тренда
        
        Returns:
            True if successful
        """
        if not self.driver or not vertical:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MERGE (t:Trend {vertical: $vertical})
                ON CREATE SET t.video_count = 1, t.created_at = datetime()
                ON MATCH SET t.video_count = t.video_count + 1, t.updated_at = datetime()
                RETURN t
                """
                
                session.run(query, vertical=vertical.strip().lower())
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания Trend узла {vertical}: {e}")
            return False
    
    # ==========================================
    # RELATIONSHIP CREATION (Edge Types)
    # ==========================================
    
    def create_created_by_relationship(self, video_url: str, username: str) -> bool:
        """
        Создает связь CREATED_BY (Video → Profile)
        
        Args:
            video_url: URL видео
            username: Username профиля
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (v:Video {url: $video_url}), (p:Profile {username: $username})
                MERGE (v)-[r:CREATED_BY]->(p)
                SET r.created_at = datetime()
                RETURN r
                """
                
                session.run(query, video_url=video_url, username=username.lower())
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания CREATED_BY связи: {e}")
            return False
    
    def create_tagged_with_relationship(self, video_url: str, hashtag_name: str) -> bool:
        """
        Создает связь TAGGED_WITH (Video → Hashtag)
        
        Args:
            video_url: URL видео
            hashtag_name: Название хэштега
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            clean_hashtag = hashtag_name.strip().lower().lstrip('#')
            if not clean_hashtag:
                return False
            
            with self.driver.session() as session:
                query = """
                MATCH (v:Video {url: $video_url}), (h:Hashtag {name: $hashtag})
                MERGE (v)-[r:TAGGED_WITH]->(h)
                RETURN r
                """
                
                session.run(query, video_url=video_url, hashtag=clean_hashtag)
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания TAGGED_WITH связи: {e}")
            return False
    
    def create_uses_sound_relationship(self, video_url: str, song_data: Dict[str, Any]) -> bool:
        """
        Создает связь USES_SOUND (Video → Song)
        
        Args:
            video_url: URL видео
            song_data: Данные песни {title, author, id}
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            title = song_data.get("title", "") or song_data.get("name", "")
            author = song_data.get("author", "") or song_data.get("artist", "")
            song_id = song_data.get("id", "") or song_data.get("soundId", "")
            
            if not title and not song_id:
                return False
            
            identifier = song_id if song_id else f"{title}_{author}"
            
            with self.driver.session() as session:
                query = """
                MATCH (v:Video {url: $video_url}), (s:Song {id: $song_id})
                MERGE (v)-[r:USES_SOUND]->(s)
                RETURN r
                """
                
                session.run(query, video_url=video_url, song_id=identifier)
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания USES_SOUND связи: {e}")
            return False
    
    def create_similar_visual_relationship(self, video1_url: str, video2_url: str, similarity_score: float) -> bool:
        """
        Создает связь SIMILAR_VISUAL (Video → Video) на основе CLIP similarity
        
        Args:
            video1_url: URL первого видео
            video2_url: URL второго видео
            similarity_score: CLIP cosine similarity (0-1)
        
        Returns:
            True if successful
        """
        if not self.driver or similarity_score < 0.7:  # Только высокое сходство
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (v1:Video {url: $video1_url}), (v2:Video {url: $video2_url})
                WHERE v1 <> v2
                MERGE (v1)-[r:SIMILAR_VISUAL {similarity: $similarity}]->(v2)
                SET r.updated_at = datetime()
                RETURN r
                """
                
                session.run(query, 
                    video1_url=video1_url,
                    video2_url=video2_url,
                    similarity=similarity_score
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания SIMILAR_VISUAL связи: {e}")
            return False
    
    def create_follows_relationship(self, follower_username: str, followed_username: str) -> bool:
        """
        Создает связь FOLLOWS (Profile → Profile)
        
        Args:
            follower_username: Username того, кто подписывается
            followed_username: Username того, на кого подписываются
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (follower:Profile {username: $follower}), (followed:Profile {username: $followed})
                WHERE follower <> followed
                MERGE (follower)-[r:FOLLOWS]->(followed)
                SET r.updated_at = datetime()
                RETURN r
                """
                
                session.run(query,
                    follower=follower_username.lower(),
                    followed=followed_username.lower()
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания FOLLOWS связи: {e}")
            return False
    
    def create_belongs_to_relationship(self, video_url: str, vertical: str) -> bool:
        """
        Создает связь BELONGS_TO (Video → Trend)
        
        Args:
            video_url: URL видео
            vertical: Название вертикали/категории
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (v:Video {url: $video_url}), (t:Trend {vertical: $vertical})
                MERGE (v)-[r:BELONGS_TO]->(t)
                RETURN r
                """
                
                session.run(query, video_url=video_url, vertical=vertical.strip().lower())
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания BELONGS_TO связи: {e}")
            return False
    
    def create_trending_together_relationship(self, hashtag1: str, hashtag2: str, video_count: int = 1) -> bool:
        """
        Создает связь TRENDING_TOGETHER (Hashtag → Hashtag)
        Хэштеги, которые часто используются вместе
        
        Args:
            hashtag1: Первый хэштег
            hashtag2: Второй хэштег
            video_count: Количество видео, где они вместе
        
        Returns:
            True if successful
        """
        if not self.driver or hashtag1 == hashtag2:
            return False
        
        try:
            clean_h1 = hashtag1.strip().lower().lstrip('#')
            clean_h2 = hashtag2.strip().lower().lstrip('#')
            
            with self.driver.session() as session:
                query = """
                MATCH (h1:Hashtag {name: $h1}), (h2:Hashtag {name: $h2})
                WHERE h1 <> h2
                MERGE (h1)-[r:TRENDING_TOGETHER]-(h2)
                ON CREATE SET r.video_count = $count, r.created_at = datetime()
                ON MATCH SET r.video_count = r.video_count + $count, r.updated_at = datetime()
                RETURN r
                """
                
                session.run(query, h1=clean_h1, h2=clean_h2, count=video_count)
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания TRENDING_TOGETHER связи: {e}")
            return False
    
    def create_influences_relationship(self, influencer_username: str, influenced_username: str, influence_score: float = 1.0) -> bool:
        """
        Создает связь INFLUENCES (Profile → Profile)
        Профиль влияет на другой профиль (по хэштегам, стилю)
        
        Args:
            influencer_username: Username влияющего профиля
            influenced_username: Username влияемого профиля
            influence_score: Оценка влияния (0-1)
        
        Returns:
            True if successful
        """
        if not self.driver or influencer_username == influenced_username:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (influencer:Profile {username: $influencer}), (influenced:Profile {username: $influenced})
                WHERE influencer <> influenced
                MERGE (influencer)-[r:INFLUENCES]->(influenced)
                SET r.influence_score = $score, r.updated_at = datetime()
                ON CREATE SET r.created_at = datetime()
                RETURN r
                """
                
                session.run(query,
                    influencer=influencer_username.lower(),
                    influenced=influenced_username.lower(),
                    score=influence_score
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания INFLUENCES связи: {e}")
            return False
    
    def create_uses_location_relationship(self, video_url: str, location_name: str) -> bool:
        """
        Создает связь USES_LOCATION (Video → Location)
        
        Args:
            video_url: URL видео
            location_name: Название локации
        
        Returns:
            True if successful
        """
        if not self.driver or not location_name:
            return False
        
        try:
            # Создаем узел Location если его нет
            self.create_location_node(location_name)
            
            with self.driver.session() as session:
                query = """
                MATCH (v:Video {url: $video_url}), (l:Location {name: $location})
                MERGE (v)-[r:USES_LOCATION]->(l)
                RETURN r
                """
                
                session.run(query, video_url=video_url, location=location_name.strip())
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания USES_LOCATION связи: {e}")
            return False
    
    def create_related_to_relationship(self, trend1: str, trend2: str, similarity: float = 0.5) -> bool:
        """
        Создает связь RELATED_TO (Trend → Trend)
        Связанные тренды (по общим хэштегам, видео)
        
        Args:
            trend1: Первый тренд
            trend2: Второй тренд
            similarity: Степень схожести (0-1)
        
        Returns:
            True if successful
        """
        if not self.driver or trend1 == trend2:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (t1:Trend {vertical: $trend1}), (t2:Trend {vertical: $trend2})
                WHERE t1 <> t2
                MERGE (t1)-[r:RELATED_TO {similarity: $similarity}]->(t2)
                SET r.updated_at = datetime()
                ON CREATE SET r.created_at = datetime()
                RETURN r
                """
                
                session.run(query,
                    trend1=trend1.strip().lower(),
                    trend2=trend2.strip().lower(),
                    similarity=similarity
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания RELATED_TO связи: {e}")
            return False
    
    def create_mentions_relationship(self, video_url: str, mentioned_username: str) -> bool:
        """
        Создает связь MENTIONS (Video → Profile)
        Видео упоминает профиль (через @username в описании)
        
        Args:
            video_url: URL видео
            mentioned_username: Username упомянутого профиля
        
        Returns:
            True if successful
        """
        if not self.driver or not mentioned_username:
            return False
        
        try:
            # Создаем узел Profile если его нет
            self.create_profile_node(mentioned_username.lower())
            
            with self.driver.session() as session:
                query = """
                MATCH (v:Video {url: $video_url}), (p:Profile {username: $username})
                MERGE (v)-[r:MENTIONS]->(p)
                RETURN r
                """
                
                session.run(query, video_url=video_url, username=mentioned_username.lower())
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания MENTIONS связи: {e}")
            return False
    
    def create_competes_with_relationship(self, profile1: str, profile2: str, competition_score: float = 0.5) -> bool:
        """
        Создает связь COMPETES_WITH (Profile → Profile)
        Профили конкурируют (используют те же хэштеги, в той же нише)
        
        Args:
            profile1: Первый профиль
            profile2: Второй профиль
            competition_score: Оценка конкуренции (0-1)
        
        Returns:
            True if successful
        """
        if not self.driver or profile1 == profile2:
            return False
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p1:Profile {username: $p1}), (p2:Profile {username: $p2})
                WHERE p1 <> p2
                MERGE (p1)-[r:COMPETES_WITH]-(p2)
                ON CREATE SET r.score = $score, r.created_at = datetime()
                ON MATCH SET r.score = $score, r.updated_at = datetime()
                RETURN r
                """
                
                session.run(query,
                    p1=profile1.lower(),
                    p2=profile2.lower(),
                    score=competition_score
                )
                return True
        except Exception as e:
            print(f"⚠️ Ошибка создания COMPETES_WITH связи: {e}")
            return False
    
    def create_dueted_with_relationship(self, video1_url: str, video2_url: str) -> bool:
        """Создает связь DUETED_WITH (Video → Video) - дуэты"""
        if not self.driver or video1_url == video2_url:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (v1:Video {url: $v1}), (v2:Video {url: $v2}) WHERE v1 <> v2 MERGE (v1)-[r:DUETED_WITH]-(v2) RETURN r"
                session.run(query, v1=video1_url, v2=video2_url)
                return True
        except Exception as e:
            return False
    
    def create_stitched_from_relationship(self, video_url: str, original_url: str) -> bool:
        """Создает связь STITCHED_FROM (Video → Video) - стыки"""
        if not self.driver or video_url == original_url:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (v:Video {url: $v}), (orig:Video {url: $orig}) MERGE (v)-[r:STITCHED_FROM]->(orig) RETURN r"
                session.run(query, v=video_url, orig=original_url)
                return True
        except Exception as e:
            return False
    
    def create_inspired_by_relationship(self, video_url: str, inspiration_url: str, similarity: float = 0.7) -> bool:
        """Создает связь INSPIRED_BY (Video → Video) - вдохновлено"""
        if not self.driver or video_url == inspiration_url:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (v:Video {url: $v}), (insp:Video {url: $insp}) MERGE (v)-[r:INSPIRED_BY {similarity: $sim}]->(insp) RETURN r"
                session.run(query, v=video_url, insp=inspiration_url, sim=similarity)
                return True
        except Exception as e:
            return False
    
    def create_part_of_series_relationship(self, video1_url: str, video2_url: str) -> bool:
        """Создает связь PART_OF_SERIES (Video → Video) - часть серии"""
        if not self.driver or video1_url == video2_url:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (v1:Video {url: $v1}), (v2:Video {url: $v2}) WHERE v1 <> v2 MERGE (v1)-[r:PART_OF_SERIES]-(v2) RETURN r"
                session.run(query, v1=video1_url, v2=video2_url)
                return True
        except Exception as e:
            return False
    
    def create_features_relationship(self, video_url: str, featured_username: str) -> bool:
        """Создает связь FEATURES (Video → Profile) - видео фичирует профиль"""
        if not self.driver:
            return False
        try:
            self.create_profile_node(featured_username.lower())
            with self.driver.session() as session:
                query = "MATCH (v:Video {url: $v}), (p:Profile {username: $u}) MERGE (v)-[r:FEATURES]->(p) RETURN r"
                session.run(query, v=video_url, u=featured_username.lower())
                return True
        except Exception as e:
            return False
    
    def create_promotes_relationship(self, profile_username: str, hashtag_name: str) -> bool:
        """Создает связь PROMOTES (Profile → Hashtag) - профиль продвигает хэштег"""
        if not self.driver:
            return False
        try:
            clean_tag = hashtag_name.strip().lower().lstrip('#')
            with self.driver.session() as session:
                query = "MATCH (p:Profile {username: $u}), (h:Hashtag {name: $h}) MERGE (p)-[r:PROMOTES]->(h) RETURN r"
                session.run(query, u=profile_username.lower(), h=clean_tag)
                return True
        except Exception as e:
            return False
    
    def create_tracks_relationship(self, profile_username: str, trend_vertical: str) -> bool:
        """Создает связь TRACKS (Profile → Trend) - профиль отслеживает тренд"""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (p:Profile {username: $u}), (t:Trend {vertical: $v}) MERGE (p)-[r:TRACKS]->(t) RETURN r"
                session.run(query, u=profile_username.lower(), v=trend_vertical.lower())
                return True
        except Exception as e:
            return False
    
    def create_analyzes_relationship(self, profile_username: str, video_url: str) -> bool:
        """Создает связь ANALYZES (Profile → Video) - профиль анализирует видео"""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (p:Profile {username: $u}), (v:Video {url: $v}) MERGE (p)-[r:ANALYZES]->(v) RETURN r"
                session.run(query, u=profile_username.lower(), v=video_url)
                return True
        except Exception as e:
            return False
    
    def create_responds_to_relationship(self, video_url: str, response_to_url: str) -> bool:
        """Создает связь RESPONDS_TO (Video → Video) - ответ на видео"""
        if not self.driver or video_url == response_to_url:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (v:Video {url: $v}), (orig:Video {url: $orig}) MERGE (v)-[r:RESPONDS_TO]->(orig) RETURN r"
                session.run(query, v=video_url, orig=response_to_url)
                return True
        except Exception as e:
            return False
    
    def create_shares_hashtag_relationship(self, profile1: str, profile2: str, hashtag: str) -> bool:
        """Создает связь SHARES_HASHTAG (Profile → Profile) - профили используют один хэштег"""
        if not self.driver or profile1 == profile2:
            return False
        try:
            clean_tag = hashtag.strip().lower().lstrip('#')
            with self.driver.session() as session:
                query = "MATCH (p1:Profile {username: $p1}), (p2:Profile {username: $p2}), (h:Hashtag {name: $h}) WHERE p1 <> p2 MERGE (p1)-[r:SHARES_HASHTAG {hashtag: $h}]-(p2) RETURN r"
                session.run(query, p1=profile1.lower(), p2=profile2.lower(), h=clean_tag)
                return True
        except Exception as e:
            return False
    
    def create_uses_same_sound_relationship(self, video1_url: str, video2_url: str) -> bool:
        """Создает связь USES_SAME_SOUND (Video → Video) - используют одну песню"""
        if not self.driver or video1_url == video2_url:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (v1:Video {url: $v1}), (v2:Video {url: $v2}) WHERE v1 <> v2 MERGE (v1)-[r:USES_SAME_SOUND]-(v2) RETURN r"
                session.run(query, v1=video1_url, v2=video2_url)
                return True
        except Exception as e:
            return False
    
    def create_trended_with_relationship(self, hashtag1: str, hashtag2: str) -> bool:
        """Создает связь TRENDED_WITH (Hashtag → Hashtag) - хэштеги трендят вместе (альтернатива TRENDING_TOGETHER)"""
        return self.create_trending_together_relationship(hashtag1, hashtag2)
    
    def create_collaborates_relationship(self, profile1: str, profile2: str) -> bool:
        """Создает связь COLLABORATES (Profile → Profile) - коллаборации"""
        if not self.driver or profile1 == profile2:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (p1:Profile {username: $p1}), (p2:Profile {username: $p2}) WHERE p1 <> p2 MERGE (p1)-[r:COLLABORATES]-(p2) RETURN r"
                session.run(query, p1=profile1.lower(), p2=profile2.lower())
                return True
        except Exception as e:
            return False
    
    def create_in_same_trend_relationship(self, video1_url: str, video2_url: str) -> bool:
        """Создает связь IN_SAME_TREND (Video → Video) - видео в одном тренде"""
        if not self.driver or video1_url == video2_url:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (v1:Video {url: $v1}), (v2:Video {url: $v2}) WHERE v1 <> v2 MERGE (v1)-[r:IN_SAME_TREND]-(v2) RETURN r"
                session.run(query, v1=video1_url, v2=video2_url)
                return True
        except Exception as e:
            return False
    
    def create_recommends_relationship(self, profile_username: str, video_url: str, recommendation_score: float = 0.5) -> bool:
        """Создает связь RECOMMENDS (Profile → Video) - профиль рекомендует видео (через лайки, репосты)"""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                query = "MATCH (p:Profile {username: $u}), (v:Video {url: $v}) MERGE (p)-[r:RECOMMENDS {score: $score}]->(v) RETURN r"
                session.run(query, u=profile_username.lower(), v=video_url, score=recommendation_score)
                return True
        except Exception as e:
            return False
    
    # ==========================================
    # BATCH OPERATIONS
    # ==========================================
    
    def save_video_with_relationships(self, video_url: str, video_data: Dict[str, Any], 
                                      username: str, vertical: str = None) -> bool:
        """
        Сохраняет видео со всеми связями (batch операция)
        
        Args:
            video_url: URL видео
            video_data: Данные видео (должно содержать stats, description, cover_url, hashtags, song)
            username: Username создателя
            vertical: Вертикаль/категория (опционально)
        
        Returns:
            True if successful
        """
        if not self.driver:
            return False
        
        try:
            # 1. Создаем узел Video
            self.create_video_node(video_url, video_data)
            
            # 2. Создаем профиль и связь CREATED_BY
            self.create_profile_node(username.lower())  # Создаем профиль если его нет
            self.create_created_by_relationship(video_url, username)
            
            # 3. Создаем хэштеги и связи TAGGED_WITH + TRENDING_TOGETHER
            hashtags = video_data.get("hashtags", [])
            if isinstance(hashtags, list):
                valid_tags = [tag for tag in hashtags if tag and isinstance(tag, str)]
                for tag in valid_tags:
                    self.create_hashtag_node(tag)
                    self.create_tagged_with_relationship(video_url, tag)
                
                # Создаем связи TRENDING_TOGETHER между всеми парами хэштегов
                for i, tag1 in enumerate(valid_tags):
                    for tag2 in valid_tags[i+1:]:
                        self.create_trending_together_relationship(tag1, tag2, video_count=1)
            
            # 4. Создаем песню и связь USES_SOUND
            song_data = video_data.get("song", {})
            if song_data:
                self.create_song_node(song_data)
                self.create_uses_sound_relationship(video_url, song_data)
            
            # 5. Создаем связь BELONGS_TO (если есть vertical)
            if vertical:
                self.create_trend_node(vertical)
                self.create_belongs_to_relationship(video_url, vertical)
            
            # 6. АВТОМАТИЧЕСКОЕ СОЗДАНИЕ СВЯЗЕЙ (аналитика)
            try:
                # Находим конкурентов (профили с общими хэштегами)
                if valid_tags:
                    with self.driver.session() as session:
                        competitors_query = """
                        MATCH (p:Profile {username: $username})-[:CREATED_BY]-(v1:Video)-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(v2:Video)-[:CREATED_BY]->(comp:Profile)
                        WHERE p <> comp
                        WITH comp, COUNT(DISTINCT h) as common_tags
                        WHERE common_tags >= 2
                        RETURN comp.username as competitor
                        LIMIT 5
                        """
                        competitors = session.run(competitors_query, username=username.lower())
                        for record in competitors:
                            competitor = record['competitor']
                            # Создаем связь COMPETES_WITH
                            self.create_competes_with_relationship(username.lower(), competitor, competition_score=0.5)
                
                # Находим видео с той же песней
                if song_data:
                    with self.driver.session() as session:
                        same_sound_query = """
                        MATCH (v1:Video {url: $url})-[:USES_SOUND]->(s:Song)<-[:USES_SOUND]-(v2:Video)
                        WHERE v1 <> v2
                        RETURN v2.url as video_url
                        LIMIT 3
                        """
                        same_sound_videos = session.run(same_sound_query, url=video_url)
                        for record in same_sound_videos:
                            self.create_uses_same_sound_relationship(video_url, record['video_url'])
                
                # Создаем связи IN_SAME_TREND для видео в одном тренде
                if vertical:
                    with self.driver.session() as session:
                        same_trend_query = """
                        MATCH (v1:Video {url: $url})-[:BELONGS_TO]->(t:Trend {vertical: $vertical})<-[:BELONGS_TO]-(v2:Video)
                        WHERE v1 <> v2
                        RETURN v2.url as video_url
                        LIMIT 5
                        """
                        same_trend_videos = session.run(same_trend_query, url=video_url, vertical=vertical.lower())
                        for record in same_trend_videos:
                            self.create_in_same_trend_relationship(video_url, record['video_url'])
            except Exception as e:
                pass  # Тихая ошибка для автоматических связей
            
            return True
        except Exception as e:
            print(f"⚠️ Ошибка сохранения видео со связями {video_url}: {e}")
            return False
    
    # ==========================================
    # BATCH ANALYTICS (Автоматическое создание связей)
    # ==========================================
    
    def build_all_relationships(self) -> Dict[str, int]:
        """
        Автоматически создает все связи для существующих данных
        (COMPETES_WITH, IN_SAME_TREND, USES_SAME_SOUND и т.д.)
        
        Returns:
            Словарь с количеством созданных связей по типам
        """
        if not self.driver:
            return {}
        
        results = {
            "competes_with": 0,
            "in_same_trend": 0,
            "uses_same_sound": 0,
            "related_to": 0
        }
        
        try:
            # 1. COMPETES_WITH - профили с общими хэштегами
            with self.driver.session() as session:
                query = """
                MATCH (p1:Profile)-[:CREATED_BY]-(v1:Video)-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(v2:Video)-[:CREATED_BY]->(p2:Profile)
                WHERE p1 <> p2
                WITH p1, p2, COUNT(DISTINCT h) as common_tags
                WHERE common_tags >= 2
                RETURN DISTINCT p1.username as p1, p2.username as p2
                LIMIT 100
                """
                competitors = session.run(query)
                for record in competitors:
                    if self.create_competes_with_relationship(record['p1'], record['p2']):
                        results["competes_with"] += 1
            
            # 2. IN_SAME_TREND - видео в одном тренде
            with self.driver.session() as session:
                query = """
                MATCH (v1:Video)-[:BELONGS_TO]->(t:Trend)<-[:BELONGS_TO]-(v2:Video)
                WHERE v1 <> v2
                RETURN DISTINCT v1.url as v1, v2.url as v2
                LIMIT 200
                """
                same_trend = session.run(query)
                for record in same_trend:
                    if self.create_in_same_trend_relationship(record['v1'], record['v2']):
                        results["in_same_trend"] += 1
            
            # 3. USES_SAME_SOUND - видео с одной песней
            with self.driver.session() as session:
                query = """
                MATCH (v1:Video)-[:USES_SOUND]->(s:Song)<-[:USES_SOUND]-(v2:Video)
                WHERE v1 <> v2
                RETURN DISTINCT v1.url as v1, v2.url as v2
                LIMIT 200
                """
                same_sound = session.run(query)
                for record in same_sound:
                    if self.create_uses_same_sound_relationship(record['v1'], record['v2']):
                        results["uses_same_sound"] += 1
            
            # 4. RELATED_TO - связанные тренды
            with self.driver.session() as session:
                query = """
                MATCH (t1:Trend)<-[:BELONGS_TO]-(v1:Video)-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(v2:Video)-[:BELONGS_TO]->(t2:Trend)
                WHERE t1 <> t2
                WITH t1, t2, COUNT(DISTINCT h) as common_hashtags
                WHERE common_hashtags >= 3
                RETURN DISTINCT t1.vertical as t1, t2.vertical as t2, common_hashtags
                LIMIT 50
                """
                related = session.run(query)
                for record in related:
                    similarity = min(record['common_hashtags'] / 10.0, 1.0)  # Нормализуем до 0-1
                    if self.create_related_to_relationship(record['t1'], record['t2'], similarity):
                        results["related_to"] += 1
            
            print(f"✅ Создано связей: {results}")
            return results
            
        except Exception as e:
            print(f"⚠️ Ошибка создания связей: {e}")
            return results
    
    # ==========================================
    # QUERY OPERATIONS
    # ==========================================
    
    def find_similar_videos(self, video_url: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Находит похожие видео через граф (по хэштегам, музыке)
        
        Args:
            video_url: URL исходного видео
            limit: Максимум результатов
        
        Returns:
            Список похожих видео
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (v:Video {url: $video_url})-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(similar:Video)
                WHERE v <> similar
                WITH similar, COUNT(h) AS common_tags
                ORDER BY common_tags DESC, similar.views DESC
                LIMIT $limit
                RETURN similar.url AS url, similar.views AS views, common_tags
                """
                
                result = session.run(query, video_url=video_url, limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"⚠️ Ошибка поиска похожих видео: {e}")
            return []
    
    # ==========================================
    # ANALYTICS QUERIES (Графовая аналитика)
    # ==========================================
    
    def find_competitors(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Находит конкурентов профиля (используют те же хэштеги)
        
        Args:
            username: Username профиля
            limit: Максимум результатов
        
        Returns:
            Список конкурентов с метриками
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Profile {username: $username})-[:CREATED_BY]-(v1:Video)-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(v2:Video)-[:CREATED_BY]->(competitor:Profile)
                WHERE p <> competitor
                WITH competitor, COUNT(DISTINCT h) as common_hashtags, AVG(v2.views) as avg_views
                ORDER BY common_hashtags DESC, avg_views DESC
                LIMIT $limit
                RETURN competitor.username as username, 
                       competitor.followers as followers,
                       common_hashtags,
                       avg_views
                """
                
                result = session.run(query, username=username.lower(), limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"⚠️ Ошибка поиска конкурентов: {e}")
            return []
    
    def find_influencers(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Находит профили, которые влияют на данный (используют хэштеги раньше)
        
        Args:
            username: Username профиля
            limit: Максимум результатов
        
        Returns:
            Список влияющих профилей
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Profile {username: $username})-[:CREATED_BY]-(v1:Video)-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(v2:Video)-[:CREATED_BY]->(influencer:Profile)
                WHERE p <> influencer AND v2.created_at < v1.created_at
                WITH influencer, COUNT(DISTINCT h) as influence_score, AVG(v2.views) as avg_views
                ORDER BY influence_score DESC, avg_views DESC
                LIMIT $limit
                RETURN influencer.username as username,
                       influencer.followers as followers,
                       influence_score,
                       avg_views
                """
                
                result = session.run(query, username=username.lower(), limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"⚠️ Ошибка поиска влияющих: {e}")
            return []
    
    def find_trending_hashtag_pairs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Находит пары хэштегов, которые часто используются вместе
        
        Args:
            limit: Максимум результатов
        
        Returns:
            Список пар хэштегов с частотой
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (h1:Hashtag)-[r:TRENDING_TOGETHER]-(h2:Hashtag)
                WHERE h1.name < h2.name
                RETURN h1.name as hashtag1, 
                       h2.name as hashtag2,
                       r.video_count as together_count
                ORDER BY r.video_count DESC
                LIMIT $limit
                """
                
                result = session.run(query, limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"⚠️ Ошибка поиска пар хэштегов: {e}")
            return []
    
    def find_related_trends(self, vertical: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Находит связанные тренды (по общим хэштегам)
        
        Args:
            vertical: Название тренда
            limit: Максимум результатов
        
        Returns:
            Список связанных трендов
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (t1:Trend {vertical: $vertical})<-[:BELONGS_TO]-(v1:Video)-[:TAGGED_WITH]->(h:Hashtag)<-[:TAGGED_WITH]-(v2:Video)-[:BELONGS_TO]->(t2:Trend)
                WHERE t1 <> t2
                WITH t2, COUNT(DISTINCT h) as common_hashtags
                ORDER BY common_hashtags DESC
                LIMIT $limit
                RETURN t2.vertical as vertical, common_hashtags
                """
                
                result = session.run(query, vertical=vertical.lower(), limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"⚠️ Ошибка поиска связанных трендов: {e}")
            return []
    
    def get_profile_hashtag_network(self, username: str) -> Dict[str, Any]:
        """
        Получает сеть хэштегов профиля (какие хэштеги использует и как часто вместе)
        
        Args:
            username: Username профиля
        
        Returns:
            Словарь с данными сети
        """
        if not self.driver:
            return {}
        
        try:
            with self.driver.session() as session:
                # Топ хэштеги профиля
                hashtags_query = """
                MATCH (p:Profile {username: $username})-[:CREATED_BY]-(v:Video)-[:TAGGED_WITH]->(h:Hashtag)
                RETURN h.name as hashtag, COUNT(v) as video_count
                ORDER BY video_count DESC
                LIMIT 20
                """
                
                hashtags_result = session.run(hashtags_query, username=username.lower())
                hashtags = [dict(record) for record in hashtags_result]
                
                # Пары хэштегов профиля
                pairs_query = """
                MATCH (p:Profile {username: $username})-[:CREATED_BY]-(v:Video)-[:TAGGED_WITH]->(h1:Hashtag)
                MATCH (v)-[:TAGGED_WITH]->(h2:Hashtag)
                WHERE h1 <> h2
                WITH h1, h2, COUNT(v) as together_count
                ORDER BY together_count DESC
                LIMIT 10
                RETURN h1.name as hashtag1, h2.name as hashtag2, together_count
                """
                
                pairs_result = session.run(pairs_query, username=username.lower())
                pairs = [dict(record) for record in pairs_result]
                
                return {
                    "hashtags": hashtags,
                    "pairs": pairs
                }
        except Exception as e:
            print(f"⚠️ Ошибка получения сети хэштегов: {e}")
            return {}
    
    def get_profile_videos(self, username: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Получает все видео профиля
        
        Args:
            username: Username профиля
            limit: Максимум результатов
        
        Returns:
            Список видео
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (v:Video)-[:CREATED_BY]->(p:Profile {username: $username})
                RETURN v.url AS url, v.views AS views, v.likes AS likes, v.uts_score AS uts_score
                ORDER BY v.views DESC
                LIMIT $limit
                """
                
                result = session.run(query, username=username.lower(), limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            print(f"⚠️ Ошибка получения видео профиля: {e}")
            return []


# Singleton instance
_graph_instance: Optional[Neo4jGraph] = None

def get_graph() -> Optional[Neo4jGraph]:
    """
    Получает singleton экземпляр Neo4jGraph
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = Neo4jGraph()
        _graph_instance.connect()
    return _graph_instance if _graph_instance.driver else None
