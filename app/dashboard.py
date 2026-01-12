import sys
import os
import importlib
# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import datetime as dt

# Принудительная перезагрузка модулей для обновления функции run_analysis
if 'filtertrend.core.analysis' in sys.modules:
    importlib.reload(sys.modules['filtertrend.core.analysis'])
if 'filtertrend.core' in sys.modules:
    importlib.reload(sys.modules['filtertrend.core'])
from filtertrend.core import get_db_session, Trend, ProfileData, run_analysis
import urllib.parse
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

st.set_page_config(page_title="TrendScout", layout="wide", page_icon="🔥")

st.markdown("""
<style>
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        border-radius: 15px; padding: 10px;
    }
    .stButton>button {width: 100%; border-radius: 8px;}
    
    /* Стили для изображений */
    div[data-testid="stImage"] img { 
        border-radius: 12px; object-fit: cover; 
    }
    a { text-decoration: none; color: inherit; }
    
    /* Engagement Metrics Styles */
    .engagement-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin-bottom: 20px;
    }
    .engagement-card {
        background: #0e1117;
        border-radius: 16px;
        padding: 25px;
        border: 1px solid #2a2d3a;
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }
    .card-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 16px;
        font-weight: 600;
        color: #fff;
    }
    .card-value {
        font-size: 28px;
        font-weight: 700;
    }
    .card-value.pink { color: #ff0050; }
    .card-value.cyan { color: #00f2ea; }
    .card-value.green { color: #00d26a; }
    .card-value.orange { color: #f97316; }
    .card-explanation {
        font-size: 14px;
        color: #888;
        margin-bottom: 18px;
    }
    .progress-container {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .progress-bar {
        flex: 1;
        height: 8px;
        background: #2a2d3a;
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    .progress-fill.pink { background: linear-gradient(90deg, #ff0050, #ff3366); }
    .progress-fill.cyan { background: linear-gradient(90deg, #00f2ea, #00d4aa); }
    .progress-fill.green { background: linear-gradient(90deg, #00d26a, #00f2a0); }
    .progress-fill.orange { background: linear-gradient(90deg, #f97316, #fb923c); }
    .status-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        white-space: nowrap;
    }
    .badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge.excellent {
        background: rgba(0, 210, 106, 0.2);
        color: #00d26a;
    }
    .badge.normal {
        background: rgba(0, 242, 234, 0.2);
        color: #00f2ea;
    }
    .badge.low {
        background: rgba(249, 115, 22, 0.2);
        color: #f97316;
    }
    .benchmark {
        font-size: 11px;
        color: #666;
    }
    
    /* Hashtags Section Styles */
    .hashtags-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-bottom: 30px;
    }
    .hashtag-row {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr;
        align-items: center;
        background: #0e1117;
        border-radius: 12px;
        padding: 18px 25px;
        border: 1px solid #2a2d3a;
        transition: border-color 0.2s;
    }
    .hashtag-row:hover {
        border-color: #ff0050;
    }
    .hashtag-row .name {
        font-size: 16px;
        font-weight: 600;
        color: #ff0050;
    }
    .hashtag-row .count {
        text-align: center;
    }
    .hashtag-row .count .value {
        font-size: 20px;
        font-weight: 700;
        color: #fff;
    }
    .hashtag-row .count .label {
        font-size: 11px;
        color: #888;
        margin-top: 2px;
    }
    .hashtag-row .views {
        text-align: right;
    }
    .hashtag-row .views .value {
        font-size: 20px;
        font-weight: 700;
        color: #00f2ea;
    }
    .hashtag-row .views .label {
        font-size: 11px;
        color: #888;
        margin-top: 2px;
    }
    
    /* Sounds Section Styles */
    .sound-item {
        display: grid;
        grid-template-columns: 50px 1fr 100px 120px;
        align-items: center;
        gap: 20px;
        padding: 20px 0;
        border-bottom: 1px solid #2a2d3a;
    }
    .sound-item:last-child {
        border-bottom: none;
    }
    .sound-rank {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #ff0050, #ff3366);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 16px;
        color: #fff;
    }
    .sound-info .title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 4px;
        color: #fff;
    }
    .sound-info .artist {
        font-size: 13px;
        color: #888;
    }
    .sound-uses {
        text-align: center;
    }
    .sound-uses .value {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
    }
    .sound-uses .label {
        font-size: 11px;
        color: #888;
        margin-top: 2px;
    }
    .sound-views {
        text-align: right;
    }
    .sound-views .value {
        font-size: 18px;
        font-weight: 700;
        color: #00f2ea;
    }
    .sound-views .label {
        font-size: 11px;
        color: #888;
        margin-top: 2px;
    }
    
    /* Charts Section Styles */
    .charts-section {
        display: flex;
        flex-direction: column;
        gap: 25px;
        margin-bottom: 40px;
    }
    .chart-card {
        background: linear-gradient(135deg, #1a1d29 0%, #1e2130 100%);
        border-radius: 20px;
        padding: 25px 30px;
        border: 1px solid #2a2d3a;
    }
    .chart-title {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 20px;
        color: #fff;
    }
</style>
""", unsafe_allow_html=True)

# === ПОМОЩНИК: Рендер картинки (С ФИКСОМ HEIC -> JPEG) ===
def render_safe_image(url, height=None):
    if not url:
        st.markdown("⬛ *Нет фото*")
        return

    # Мы используем сервис wsrv.nl.
    # Он скачивает картинку с серверов TikTok (обходит защиту 403)
    # И конвертирует HEIC/WEBP в обычный JPG на лету.
    try:
        # 1. Кодируем ссылку, чтобы спецсимволы не сломали запрос
        encoded_url = urllib.parse.quote(url, safe='')
        
        # 2. Формируем ссылку через прокси
        # output=jpg -> превратить в JPG
        # q=80 -> качество 80% для скорости
        final_src = f"https://wsrv.nl/?url={encoded_url}&output=jpg&q=80"
    except:
        final_src = url # Если вдруг ошибка, пробуем оригинал

    # Настройка высоты (если передана)
    style_height = f"height: {height}px;" if height else ""
    
    # 3. Рисуем через HTML
    html_code = f'<img src="{final_src}" style="{style_height} width: 100%; border-radius: 12px; object-fit: cover;" loading="lazy">'
    st.markdown(html_code, unsafe_allow_html=True)

# === ПОМОЩНИК: Грид карточек ===
def render_grid(items):
    if not items:
        st.info("Нет данных для отображения.")
        return
    
    cols = st.columns(3)
    for idx, item in enumerate(items):
        col = cols[idx % 3]
        with col:
            stats = item.get("stats", {})
            views = stats.get("views", 0)
            likes = stats.get("likes", 0)
            desc = item.get("description", "")[:100]
            url = item.get("url", "")
            cover = item.get("cover_url", "")
            
            render_safe_image(cover, height=200)
            st.markdown(f"**{desc[:80]}...**" if len(desc) > 80 else f"**{desc}**")
            st.markdown(f"👁 {views:,} | ❤️ {likes:,}")
            if url:
                st.link_button("📺 Смотреть", url)

# === ПОМОЩНИК: Топ карточка ===
def render_top_card(item, rank):
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            cover = item.get("cover_url", "")
            render_safe_image(cover, height=300)
        
        with col2:
            stats = item.get("stats", {})
            views = stats.get("views", 0)
            likes = stats.get("likes", 0)
            desc = item.get("description", "")
            url = item.get("url", "")
            ai = item.get("ai_summary", "")
            
            st.markdown(f"## 🥇 #{rank}")
            st.markdown(f"## 👁 {views:,}")
            st.markdown(f"**Лайки:** {likes:,}")
            
            if ai and len(str(ai)) > 5 and ai != "Pending":
                st.info(f"🤖 **AI Инсайт:** {ai}")
            else:
                st.markdown(f"**Описание:** {desc[:150]}...")
            
            st.link_button("🔥 Смотреть Вирусное Видео", url, type="primary")

# === ФУНКЦИЯ: Нормализация username ===
def normalize_username(username_input):
    """Извлекает чистый username из URL или текста"""
    if not username_input:
        return ""
    # Убираем @ в начале
    username = username_input.strip().lstrip("@")
    # Если это URL, извлекаем username
    if "tiktok.com" in username:
        parts = username.split("@")
        if len(parts) > 1:
            username = parts[-1].split("/")[0].split("?")[0]
    return username.strip().lower()

# === ФУНКЦИЯ: Получение channel данных из БД ===
def get_channel_data_from_db(username):
    """Получает channel данные из БД (реконструирует из первого видео)"""
    try:
        db = get_db_session()
        from sqlalchemy import or_
        
        profile_username = normalize_username(username)
        
        # Ищем видео профиля
        cached_trends = db.query(Trend).filter(
            or_(
                Trend.author_username.ilike(f"%{profile_username}%"),
                Trend.vertical.ilike(f"%{profile_username}%")
            )
        ).order_by(Trend.created_at.desc()).limit(1).all()
        
        db.close()
        
        if cached_trends and len(cached_trends) > 0:
            # Реконструируем channel данные из БД
            first_trend = cached_trends[0]
            stats = first_trend.stats if isinstance(first_trend.stats, dict) else {}
            
            # Базовые channel данные (реконструированные)
            channel_data = {
                "username": profile_username,
                "followers": first_trend.followers or 0,
                "name": profile_username,  # Можно улучшить, сохраняя отдельно
                "verified": False,  # Нужно сохранять отдельно
                "bio": "",  # Нужно сохранять отдельно
                "avatar": first_trend.cover_url or "",  # Примерно
                "following": 0,  # Нужно сохранять отдельно
                "videos": 0  # Нужно сохранять отдельно
            }
            return channel_data
    except Exception as e:
        print(f"⚠️ Ошибка получения channel данных из БД: {e}")
    return None

# === ФУНКЦИЯ: Получение сырых данных из БД ===
def get_raw_data_from_db(username):
    """Получает сырые данные (в формате Apify) из БД"""
    try:
        db = get_db_session()
        from sqlalchemy import or_
        
        profile_username = normalize_username(username)
        
        # Ищем видео профиля
        cached_trends = db.query(Trend).filter(
            or_(
                Trend.author_username.ilike(f"%{profile_username}%"),
                Trend.vertical.ilike(f"%{profile_username}%")
            )
        ).order_by(Trend.created_at.desc()).limit(30).all()
        
        db.close()
        
        if cached_trends:
            # Конвертируем данные из БД в формат Apify
            raw_data = []
            for trend in cached_trends:
                stats = trend.stats if isinstance(trend.stats, dict) else {}
                
                # Реконструируем формат Apify
                raw_item = {
                    "views": stats.get("views", 0),
                    "likes": stats.get("likes", 0),
                    "comments": stats.get("commentCount", 0),
                    "shares": stats.get("shareCount", 0),
                    "bookmarks": stats.get("bookmarks", 0),
                    "hashtags": stats.get("hashtags", []),
                    "title": trend.description or "",
                    "video": {
                        "duration": stats.get("duration", None),
                        "cover": trend.cover_url or "",
                        "thumbnail": trend.cover_url or ""
                    },
                    "uploadedAt": int(trend.created_at.timestamp()) if trend.created_at else 0,
                    "uploadedAtFormatted": trend.created_at.isoformat() if trend.created_at else "",
                    "song": stats.get("song", {}),
                    "channel": {
                        "username": trend.author_username or profile_username,
                        "followers": trend.followers or 0,
                        "name": trend.author_username or profile_username,
                        "verified": False,
                        "bio": "",
                        "following": 0,
                        "videos": 0
                    }
                }
                raw_data.append(raw_item)
            
            return raw_data
    except Exception as e:
        print(f"⚠️ Ошибка получения сырых данных из БД: {e}")
    return []

# === ФУНКЦИЯ: Сохранение данных профиля в БД ===
def save_profile_data_to_db(username, channel_data, raw_data):
    """Сохраняет полные данные профиля в БД (channel_data + raw_data)"""
    try:
        db = get_db_session()
        profile_username = normalize_username(username)
        
        # Проверяем, есть ли уже данные для этого профиля
        existing = db.query(ProfileData).filter(ProfileData.username == profile_username).first()
        
        if existing:
            # Обновляем существующие данные
            existing.channel_data = channel_data
            existing.raw_data = raw_data
            existing.updated_at = dt.datetime.utcnow()
        else:
            # Создаем новую запись
            new_profile = ProfileData(
                username=profile_username,
                channel_data=channel_data,
                raw_data=raw_data
            )
            db.add(new_profile)
        
        db.commit()
        db.close()
        print(f"✅ Профиль {profile_username} сохранен в БД")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка сохранения профиля в БД: {e}")
        if db:
            db.rollback()
            db.close()
        return False

# === ФУНКЦИЯ: Получение данных профиля из БД ===
def get_profile_data_from_db(username):
    """Получает полные данные профиля из БД (channel_data + raw_data)"""
    try:
        db = get_db_session()
        profile_username = normalize_username(username)
        
        profile = db.query(ProfileData).filter(ProfileData.username == profile_username).first()
        db.close()
        
        if profile:
            return {
                "channel_data": profile.channel_data if profile.channel_data else None,
                "raw_data": profile.raw_data if profile.raw_data else []
            }
    except Exception as e:
        print(f"⚠️ Ошибка получения профиля из БД: {e}")
    return None

# === ФУНКЦИЯ: Получение channel данных из Apify ===
def get_channel_data_from_apify(username):
    """Получает channel данные из сырого ответа Apify"""
    try:
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            return None
        
        client = ApifyClient(token)
        actor_id = "apidojo/tiktok-scraper"
        
        # Формируем URL
        clean_nick = username.strip().replace("@", "").replace("https://www.tiktok.com/", "").strip("/")
        profile_url = f"https://www.tiktok.com/@{clean_nick}"
        
        run_input = {
            "maxItems": 1,  # Нужен только один элемент для channel данных
            "resultsPerPage": 1,
            "startUrls": [profile_url]
        }
        
        # Запускаем актера
        run = client.actor(actor_id).call(run_input=run_input)
        if not run:
            return None
        
        # Получаем сырые данные
        dataset = client.dataset(run["defaultDatasetId"])
        raw_items = list(dataset.iterate_items())
        
        if raw_items and len(raw_items) > 0:
            first_item = raw_items[0]
            channel = first_item.get("channel", {})
            if channel:
                return channel
    except Exception as e:
        st.error(f"Ошибка получения channel данных: {e}")
    return None

# === ФУНКЦИЯ: Форматирование чисел ===
def format_number(num):
    """Форматирует числа: 101547 -> 101.5K"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)

def get_engagement_status(rate, benchmark_min, benchmark_max):
    """Определяет статус engagement метрики: excellent/normal/low"""
    if rate >= benchmark_max * 1.5:  # Намного выше нормы = отлично
        return "excellent", "Отлично!"
    elif rate >= benchmark_min:  # Выше или в норме = норма
        return "normal", "Норма"
    else:  # Ниже нормы = низкий
        return "low", "Низкий"

def render_engagement_metric(icon, title, rate, color_class, explanation, benchmark_min, benchmark_max, benchmark_text):
    """Рендерит одну карточку engagement метрики с progress bar"""
    status_class, status_text = get_engagement_status(rate, benchmark_min, benchmark_max)
    
    # Расчет ширины progress bar (максимум 100%)
    max_rate = benchmark_max * 2  # Максимум для визуализации (2x от нормы)
    progress_width = min((rate / max_rate * 100), 100)
    
    html = f"""
    <div class="engagement-card">
        <div class="card-header">
            <div class="card-title">
                <span>{icon}</span>
                {title}
            </div>
            <div class="card-value {color_class}">{rate:.2f}%</div>
        </div>
        <div class="card-explanation">{explanation}</div>
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill {color_class}" style="width: {progress_width}%"></div>
            </div>
            <div class="status-badge">
                <span class="badge {status_class}">{status_text}</span>
                <span class="benchmark">({benchmark_text})</span>
            </div>
        </div>
    </div>
    """
    return html

# === ЛОГИКА СЕССИИ ===
if 'profile_results' not in st.session_state:
    st.session_state.profile_results = []
if 'profile_nick' not in st.session_state:
    st.session_state.profile_nick = ""
if 'profile_channel_data' not in st.session_state:
    st.session_state.profile_channel_data = None
if 'profile_raw_data' not in st.session_state:
    st.session_state.profile_raw_data = []

# === САЙДБАР ===
with st.sidebar:
    st.title("🚀 TrendScout")
    page = st.radio("Раздел", ["👤 Анализ Конкурента", "👤 Профиль Аккаунта", "🌍 Поиск Трендов"])

# ==========================================
# 👤 СТРАНИЦА: АНАЛИЗ КОНКУРЕНТА
# ==========================================
if page == "👤 Анализ Конкурента":
    st.title("👤 Разбор Конкурента")
    
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        nick = c1.text_input("Никнейм (без @):", "diazharass")
        if c2.button("🔥 Сканировать", type="primary"):
            with st.spinner("Сканирую профиль..."):
                results = run_analysis([nick], mode="profile")
                if results:
                    st.session_state.profile_results = results
                    st.session_state.profile_nick = nick
                    st.rerun()
                else:
                    st.error("Ничего не найдено или профиль закрыт.")

    # ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
    if st.session_state.profile_results:
        results = st.session_state.profile_results
        
        # 1. СОРТИРОВКА
        now = datetime.now()
        year_ago = now - timedelta(days=365)
        
        year_videos = [
            v for v in results 
            if v.get('create_time') and datetime.fromtimestamp(v['create_time']) > year_ago
        ]
        if not year_videos: year_videos = results
        
        top_3_year = sorted(year_videos, key=lambda x: x["stats"]["views"], reverse=True)[:3]
        
        latest_30 = sorted(results, key=lambda x: x.get("create_time", 0), reverse=True)[:30]

        # 2. ВКЛАДКИ
        st.divider()
        tab1, tab2, tab3 = st.tabs(["🏆 Топ-3 Хита (Год)", "🆕 Лента (Последние 30)", "📊 Таблица данных"])
        
        with tab1:
            st.subheader(f"🥇 Золотой фонд @{st.session_state.profile_nick}")
            if top_3_year:
                for i, video in enumerate(top_3_year):
                    render_top_card(video, rank=i+1)
            else:
                st.info("Нет данных за последний год.")
                
        with tab2:
            st.subheader("📅 Хронология публикаций")
            render_grid(latest_30)
        
        with tab3:
            st.subheader("📊 Все данные в таблице")
            # Создаем таблицу из результатов
            table_data = []
            for video in results:
                stats = video.get("stats", {})
                views = stats.get("views", 0)
                likes = stats.get("likes", 0)
                desc = video.get("description", "")[:100]  # Первые 100 символов
                url = video.get("url", "")
                cover = video.get("cover_url", "")
                ai_summary = video.get("ai_summary", "Pending")
                
                # Дата
                create_time = video.get("create_time", 0)
                if create_time:
                    date_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = "N/A"
                
                table_data.append({
                    "Обложка": cover[:50] + "..." if len(cover) > 50 else cover,
                    "Описание": desc,
                    "Просмотры": f"{views:,}",
                    "Лайки": f"{likes:,}",
                    "AI Инсайт": ai_summary[:50] + "..." if len(ai_summary) > 50 else ai_summary,
                    "Дата": date_str,
                    "URL": url[:50] + "..." if len(url) > 50 else url
                })
            
            if table_data:
                df = pd.DataFrame(table_data)
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Обложка": st.column_config.TextColumn("Обложка", width="medium"),
                        "Описание": st.column_config.TextColumn("Описание", width="large"),
                        "Просмотры": st.column_config.TextColumn("Просмотры", width="small"),
                        "Лайки": st.column_config.TextColumn("Лайки", width="small"),
                        "AI Инсайт": st.column_config.TextColumn("AI Инсайт", width="medium"),
                        "Дата": st.column_config.TextColumn("Дата", width="small"),
                        "URL": st.column_config.LinkColumn("URL", width="large")
                    }
                )
                st.caption(f"Всего записей: {len(table_data)}")
            else:
                st.info("Нет данных для отображения.")

    else:
        st.info("Введите никнейм выше, чтобы начать.")

# ==========================================
# 👤 СТРАНИЦА: ПРОФИЛЬ АККАУНТА
# ==========================================
elif page == "👤 Профиль Аккаунта":
    st.title("👤 Профиль Аккаунта")
    
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        nick = c1.text_input("Никнейм (без @):", "diazharass", key="profile_username_input")
        if c2.button("🔥 Загрузить", type="primary", key="profile_load_btn"):
            with st.spinner("Загружаю данные профиля..."):
                profile_username = normalize_username(nick)
                
                # ВСЕГДА сначала запрашиваем Apify, затем сохраняем в БД
                channel_data = None
                raw_data = []
                
                try:
                    st.info("📡 Запрашиваем Apify и сохраняем в БД...")
                    # Сначала проверяем БД
                    cached_profile = get_profile_data_from_db(nick)
                    
                    if cached_profile and cached_profile.get("channel_data") and cached_profile.get("raw_data"):
                        st.success(f"✅ Данные найдены в БД, используем кеш")
                        channel_data = cached_profile["channel_data"]
                        raw_data = cached_profile["raw_data"]
                    else:
                        # Если нет в БД, запрашиваем из Apify
                        st.info("📡 Данных нет в БД, запрашиваем Apify...")
                        # Используем run_analysis для запроса Apify и сохранения видео в БД
                        results = run_analysis([nick], mode="profile")
                        if results:
                            st.success(f"✅ Загружено {len(results)} видео из Apify...")
                            # Получаем channel данные из Apify
                            channel_data = get_channel_data_from_apify(nick)
                            # Получаем raw_data из Apify напрямую (с hashtags и song)
                            raw_data = []
                            try:
                                token = os.getenv("APIFY_API_TOKEN")
                                if token:
                                    client = ApifyClient(token)
                                    actor_id = "apidojo/tiktok-scraper"
                                    clean_nick = nick.strip().replace("@", "").replace("https://www.tiktok.com/", "").strip("/")
                                    profile_url = f"https://www.tiktok.com/@{clean_nick}"
                                    
                                    run_input = {
                                        "maxItems": 30,
                                        "resultsPerPage": 30,
                                        "startUrls": [profile_url]
                                    }
                                    
                                    run = client.actor(actor_id).call(run_input=run_input)
                                    if run:
                                        dataset = client.dataset(run["defaultDatasetId"])
                                        raw_items = list(dataset.iterate_items())
                                        raw_data = raw_items
                                        st.success(f"✅ Получено {len(raw_data)} видео с полными данными (hashtags, song)")
                            except Exception as e2:
                                st.warning(f"⚠️ Не удалось загрузить сырые данные из Apify: {e2}")
                            
                            # Сохраняем в таблицу профилей
                            if channel_data and raw_data:
                                save_profile_data_to_db(nick, channel_data, raw_data)
                                st.success(f"✅ Данные профиля сохранены в БД")
                            else:
                                st.warning("⚠️ Не все данные получены (channel_data или raw_data)")
                        else:
                            st.error("Не удалось загрузить данные профиля из Apify.")
                            channel_data = None
                            raw_data = []
                except Exception as e:
                    st.error(f"Ошибка загрузки: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    channel_data = None
                    raw_data = []
                
                # Сохраняем в session_state
                if channel_data:
                    st.session_state.profile_channel_data = channel_data
                    st.session_state.profile_nick = nick
                    st.session_state.profile_raw_data = raw_data
                    st.rerun()
                else:
                    st.error("Не удалось загрузить данные профиля.")
    
    # ОТОБРАЖЕНИЕ ДАННЫХ ПРОФИЛЯ
    if st.session_state.profile_channel_data:
        channel = st.session_state.profile_channel_data
        raw_data = st.session_state.profile_raw_data
        
        # === СЕКЦИЯ 1: ПРОФИЛЬ ===
        st.divider()
        st.subheader("👤 Профиль")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            avatar_url = channel.get("avatar", "")
            render_safe_image(avatar_url, height=150)
        
        with col2:
            name = channel.get("name", "")
            username = channel.get("username", "")
            verified = channel.get("verified", False)
            bio = channel.get("bio", "")
            
            verified_badge = "✅" if verified else ""
            st.markdown(f"## {name} {verified_badge}")
            st.markdown(f"**@{username}**")
            if bio:
                st.markdown(f"**Био:** {bio}")
        
        # === СЕКЦИЯ 2: СТАТИСТИКА ПРОФИЛЯ ===
        st.divider()
        st.subheader("📊 Статистика профиля")
        
        followers = channel.get("followers", 0)
        following = channel.get("following", 0)
        videos_count = channel.get("videos", 0)
        
        # Рассчитываем статистику из сырых данных
        total_views = sum(item.get("views", 0) for item in raw_data)
        total_likes = sum(item.get("likes", 0) for item in raw_data)
        total_comments = sum(item.get("comments", 0) for item in raw_data)
        total_shares = sum(item.get("shares", 0) for item in raw_data)
        total_bookmarks = sum(item.get("bookmarks", 0) for item in raw_data)
        
        avg_views = total_views / len(raw_data) if raw_data else 0
        avg_likes = total_likes / len(raw_data) if raw_data else 0
        engagement_rate = ((total_likes + total_comments + total_shares) / total_views * 100) if total_views > 0 else 0
        
        # 4 карточки базовой статистики
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Подписчики", format_number(followers))
        with col2:
            st.metric("Подписки", format_number(following))
        with col3:
            st.metric("Видео", format_number(videos_count))
        with col4:
            st.metric("Всего просмотров", format_number(total_views))
        
        # 4 карточки расчетной статистики
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего лайков", format_number(total_likes))
        with col2:
            st.metric("Средние просмотры", format_number(int(avg_views)))
        with col3:
            st.metric("Средние лайки", format_number(int(avg_likes)))
        with col4:
            st.metric("Engagement Rate", f"{engagement_rate:.2f}%")
        
        # === СЕКЦИЯ 3: ENGAGEMENT МЕТРИКИ ===
        st.divider()
        st.subheader("📈 Engagement метрики")
        
        like_rate = (total_likes / total_views * 100) if total_views > 0 else 0
        comment_rate = (total_comments / total_views * 100) if total_views > 0 else 0
        share_rate = (total_shares / total_views * 100) if total_views > 0 else 0
        save_rate = (total_bookmarks / total_views * 100) if total_views > 0 else 0
        
        # Генерируем HTML для engagement метрик
        like_html = render_engagement_metric(
            "❤️", "Like Rate", like_rate, "pink",
            "Из 100 зрителей " + str(int(like_rate)) + " ставят лайк",
            3.0, 5.0, "норма 3-5%"
        )
        comment_html = render_engagement_metric(
            "💬", "Comment Rate", comment_rate, "orange",
            "Из 10,000 зрителей " + str(int(comment_rate * 100)) + " пишут комментарий",
            0.5, 1.0, "норма 0.5-1%"
        )
        share_html = render_engagement_metric(
            "🔄", "Share Rate", share_rate, "cyan",
            "Из 1,000 зрителей " + str(int(share_rate * 10)) + " делятся видео",
            0.3, 0.5, "норма 0.3-0.5%"
        )
        save_html = render_engagement_metric(
            "🔖", "Save Rate", save_rate, "green",
            "Из 100 зрителей " + str(int(save_rate)) + " сохраняют видео",
            0.5, 1.0, "норма 0.5-1%"
        )
        
        # Отображаем в 2x2 grid
        engagement_html = f"""
        <div class="engagement-grid">
            {like_html}
            {comment_html}
            {share_html}
            {save_html}
        </div>
        """
        st.markdown(engagement_html, unsafe_allow_html=True)
        
        # === СЕКЦИЯ 4: КОНТЕНТ АНАЛИЗ ===
        st.divider()
        st.subheader("📹 Анализ контента")
        
        # Вертикальный layout (без колонок)
        charts_html = '<div class="charts-section">'
        
        # График 1: Duration vs Views
        durations = [item.get("video", {}).get("duration", 0) for item in raw_data if item.get("video", {}).get("duration")]
        views_list = [item.get("views", 0) for item in raw_data if item.get("video", {}).get("duration")]
        
        if durations and views_list:
            charts_html += '<div class="chart-card">'
            charts_html += '<div class="chart-title">Duration vs Views</div>'
            charts_html += '</div>'
            st.markdown(charts_html, unsafe_allow_html=True)
            
            fig_scatter = px.scatter(
                x=durations,
                y=views_list,
                labels={'x': 'Длительность (сек)', 'y': 'Просмотры'},
                color=views_list,
                color_continuous_scale='viridis'
            )
            fig_scatter.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            charts_html += '<div class="chart-card">'
            charts_html += '<div class="chart-title">Duration vs Views</div>'
            charts_html += '<div style="padding: 20px; color: #888;">Нет данных о длительности видео</div>'
            charts_html += '</div>'
            st.markdown(charts_html, unsafe_allow_html=True)
        
        # График 2: Время постинга (Heatmap)
        charts_html2 = '<div class="chart-card">'
        charts_html2 += '<div class="chart-title">Время постинга (Heatmap)</div>'
        charts_html2 += '</div>'
        st.markdown(charts_html2, unsafe_allow_html=True)
        
        if raw_data:
            posting_data = []
            for item in raw_data:
                uploaded_str = item.get("uploadedAtFormatted", "")
                if uploaded_str:
                    try:
                        dt = datetime.fromisoformat(uploaded_str.replace('Z', '+00:00'))
                        posting_data.append({
                            'day_of_week': dt.strftime('%A'),
                            'hour': dt.hour,
                            'views': item.get("views", 0)
                        })
                    except:
                        pass
            
            if posting_data:
                df_posting = pd.DataFrame(posting_data)
                pivot = df_posting.groupby(['day_of_week', 'hour'])['views'].mean().reset_index()
                pivot_pivot = pivot.pivot(index='day_of_week', columns='hour', values='views')
                
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                pivot_pivot = pivot_pivot.reindex([d for d in days_order if d in pivot_pivot.index])
                
                fig_heatmap = px.imshow(
                    pivot_pivot,
                    labels=dict(x="Час", y="День недели", color="Средние просмотры"),
                    aspect="auto",
                    color_continuous_scale='viridis'
                )
                fig_heatmap.update_layout(height=400, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_heatmap, use_container_width=True)
            else:
                st.info("Нет данных о времени постинга")
        else:
            st.info("Нет данных")
        
        # === СЕКЦИЯ 5: TOP HASHTAGS ===
        st.divider()
        st.subheader("🏷️ Топ хэштеги")
        
        # Собираем все хэштеги
        hashtag_stats = {}
        for item in raw_data:
            hashtags = item.get("hashtags", [])
            views = item.get("views", 0)
            for tag in hashtags:
                if tag and isinstance(tag, str) and tag.strip():  # Пропускаем null, пустые строки
                    tag_clean = tag.strip().lower()  # Нормализуем (lowercase)
                    if tag_clean not in hashtag_stats:
                        hashtag_stats[tag_clean] = {'count': 0, 'total_views': 0, 'original': tag}
                    hashtag_stats[tag_clean]['count'] += 1
                    hashtag_stats[tag_clean]['total_views'] += views
        
        # Сортируем по частоте использования
        top_hashtags_by_count = sorted(hashtag_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        
        if top_hashtags_by_count:
            # Создаем HTML для rows
            hashtag_rows_html = '<div class="hashtags-list">'
            for tag, stats in top_hashtags_by_count:
                avg_views_tag = stats['total_views'] / stats['count'] if stats['count'] > 0 else 0
                original_tag = stats.get('original', tag)
                # Экранируем специальные символы для HTML
                original_tag_escaped = original_tag.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                hashtag_rows_html += '<div class="hashtag-row">'
                hashtag_rows_html += f'<div class="name">#{original_tag_escaped}</div>'
                hashtag_rows_html += f'<div class="count"><div class="value">{stats["count"]}</div><div class="label">раз</div></div>'
                hashtag_rows_html += f'<div class="views"><div class="value">{format_number(int(avg_views_tag))}</div><div class="label">Ø просмотры</div></div>'
                hashtag_rows_html += '</div>'
            hashtag_rows_html += '</div>'
            st.markdown(hashtag_rows_html, unsafe_allow_html=True)
            
            # Дополнительно: график топ-10 хэштегов по частоте
            st.markdown("---")
            st.markdown("**Топ-10 хэштегов по частоте использования**")
            
            hashtags_list = [stats['original'] for tag, stats in top_hashtags_by_count]
            counts_list = [stats['count'] for tag, stats in top_hashtags_by_count]
            avg_views_list = [stats['total_views'] / stats['count'] if stats['count'] > 0 else 0 for tag, stats in top_hashtags_by_count]
            
            # Создаем DataFrame для графика
            df_hashtags = pd.DataFrame({
                'Hashtag': hashtags_list,
                'Использований': counts_list,
                'Средние просмотры': avg_views_list
            })
            
            # Столбчатый график
            fig_hashtags = px.bar(
                df_hashtags,
                x='Hashtag',
                y='Использований',
                labels={'Hashtag': 'Хэштег', 'Использований': 'Количество использований'},
                color='Средние просмотры',
                color_continuous_scale='viridis',
                title='Топ-10 хэштегов по частоте использования'
            )
            fig_hashtags.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_hashtags, use_container_width=True)
        else:
            st.info("Хэштеги не найдены в загруженных видео")
        
        # === СЕКЦИЯ 6: TOP SOUNDS ===
        st.divider()
        st.subheader("🎵 Топ треки")
        
        # Собираем все треки (сохраняем title и artist отдельно)
        sound_stats = {}
        for item in raw_data:
            song = item.get("song", {})
            if song:
                title = song.get("title", "")
                artist = song.get("artist", "")
                if title:  # Только если есть title
                    sound_key = f"{title} - {artist}" if artist else title
                    views = item.get("views", 0)
                    
                    if sound_key not in sound_stats:
                        sound_stats[sound_key] = {'count': 0, 'total_views': 0, 'title': title, 'artist': artist}
                    sound_stats[sound_key]['count'] += 1
                    sound_stats[sound_key]['total_views'] += views
        
        # Сортируем по частоте
        top_sounds = sorted(sound_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        
        if top_sounds:
            # Создаем HTML для rows с рангами
            sounds_html = '<div>'
            for rank, (sound_key, stats) in enumerate(top_sounds, 1):
                avg_views_sound = stats['total_views'] / stats['count'] if stats['count'] > 0 else 0
                title = stats.get('title', sound_key)
                artist = stats.get('artist', '')
                # Экранируем специальные символы для HTML
                title_escaped = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                artist_escaped = artist.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                sounds_html += f'<div class="sound-item">'
                sounds_html += f'<div class="sound-rank">{rank}</div>'
                sounds_html += f'<div class="sound-info"><div class="title">{title_escaped}</div><div class="artist">{artist_escaped}</div></div>'
                sounds_html += f'<div class="sound-uses"><div class="value">{stats["count"]}</div><div class="label">раза</div></div>'
                sounds_html += f'<div class="sound-views"><div class="value">{format_number(int(avg_views_sound))}</div><div class="label">Ø просмотры</div></div>'
                sounds_html += '</div>'
            sounds_html += '</div>'
            st.markdown(sounds_html, unsafe_allow_html=True)
        else:
            st.info("Треки не найдены")
    
    else:
        st.info("Введите никнейм выше, чтобы начать анализ профиля.")

# ==========================================
# 🌍 СТРАНИЦА: ПОИСК ТРЕНДОВ
# ==========================================
elif page == "🌍 Поиск Трендов":
    st.title("🌍 Глобальный Поиск")
    
    # Получаем список всех профилей из БД для выбора
    db_profiles = get_db_session()
    all_profiles = db_profiles.query(ProfileData.username).order_by(ProfileData.username).all()
    db_profiles.close()
    profile_options = [""] + [p[0] for p in all_profiles]  # Первый вариант - пустой (не использовать профиль)
    
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        k = c1.text_input("Тема (на англ):", "Travel")
        
        # Выбор профиля для anchor
        selected_profile = c2.selectbox(
            "👤 Профиль для Anchor (опционально):",
            options=profile_options,
            index=0,
            help="Выберите профиль аккаунта, который будет использоваться как anchor (эталон) для поиска похожих трендов. Если не выбран, можно использовать текстовое описание ниже."
        )
        
        # Текстовое описание (fallback, если профиль не выбран)
        d = st.text_input("Контекст (для AI) - если профиль не выбран:", "Tours", help="Используется только если профиль не выбран")
        
        if st.button("🚀 Найти", type="primary"):
            with st.spinner("Ищу, фильтрую и сохраняю..."):
                # Передаем anchor_profile_username если профиль выбран
                anchor_username = selected_profile if selected_profile else ""
                run_analysis([k], business_desc=d, anchor_profile_username=anchor_username, mode="search")
                st.rerun()

    db = get_db_session()
    trends = db.query(Trend).filter(Trend.vertical == k).order_by(Trend.uts_score.desc()).limit(30).all()
    db.close()

    if trends:
        st.subheader(f"Результаты по теме: {k}")
        # Преобразуем объекты Trend в словари для render_grid
        trends_dicts = []
        for trend in trends:
            stats = trend.stats if isinstance(trend.stats, dict) else {}
            trend_dict = {
                "stats": stats,
                "description": trend.description or "",
                "url": trend.url or "",
                "cover_url": trend.cover_url or "",
                "ai_summary": trend.ai_summary or ""
            }
            trends_dicts.append(trend_dict)
        render_grid(trends_dicts)
    else:
        st.info("Введите тему для поиска.")
