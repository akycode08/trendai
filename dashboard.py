import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_db_session, Trend
from main import run_analysis
import urllib.parse

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

# === 1. ФУНКЦИЯ ДЛЯ ОБЫЧНОЙ СЕТКИ (Остальные видео) ===
def render_grid(items):
    cols = st.columns(3)
    for i, item in enumerate(items):
        with cols[i % 3]:
            with st.container(border=True):
                # Логика извлечения данных
                if isinstance(item, dict):
                    cover = item.get("cover_url")
                    views = item["stats"].get("views", 0)
                    likes = item["stats"].get("likes", 0)
                    desc = item.get("description", "")
                    url = item.get("url")
                    score = None
                else:
                    cover = item.cover_url 
                    views = item.stats.get("views", 0)
                    likes = item.stats.get("likes", 0)
                    desc = item.description
                    url = item.url
                    score = item.uts_score

                # 🔥 ИСПОЛЬЗУЕМ БЕЗОПАСНЫЙ РЕНДЕР
                render_safe_image(cover, height=200)
                
                # Метрики
                c1, c2 = st.columns(2)
                c1.markdown(f"👁 **{views:,}**")
                c2.markdown(f"❤️ **{likes:,}**")
                
                if score: st.caption(f"📈 Score: {score:.2f}")
                
                # Кнопка
                st.link_button("▶️ Смотреть", url)

# === 2. НОВАЯ ФУНКЦИЯ ДЛЯ ТОП-3 (ВИРАЛЬНЫЙ ВИД) ===
def render_top_card(item, rank):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    medal = medals.get(rank, "🏅")
    
    # Извлечение данных
    if isinstance(item, dict):
        cover = item.get("cover_url")
        views = item["stats"].get("views", 0)
        likes = item["stats"].get("likes", 0)
        ai = item.get("ai_summary")
        desc = item.get("description", "")
        url = item.get("url")
    else:
        cover = item.cover_url
        views = item.stats.get("views", 0)
        likes = item.stats.get("likes", 0)
        ai = item.ai_summary
        desc = item.description
        url = item.url

    # Отрисовка КРУПНОЙ карточки
    with st.container(border=True):
        st.markdown(f"### {medal} Место #{rank}")
        
        c1, c2 = st.columns([1, 2]) # Картинка слева, текст справа
        
        with c1:
            # 🔥 И ЗДЕСЬ ТОЖЕ БЕЗОПАСНЫЙ РЕНДЕР
            render_safe_image(cover)
        
        with c2:
            st.markdown(f"## 👁 {views:,}")
            st.markdown(f"**Лайки:** {likes:,}")
            
            if ai and len(str(ai)) > 5 and ai != "Pending":
                st.info(f"🤖 **AI Инсайт:** {ai}")
            else:
                st.markdown(f"**Описание:** {desc[:150]}...")
            
            st.link_button("🔥 Смотреть Вирусное Видео", url, type="primary")

# === ЛОГИКА СЕССИИ ===
if 'profile_results' not in st.session_state:
    st.session_state.profile_results = []
if 'profile_nick' not in st.session_state:
    st.session_state.profile_nick = ""

# === САЙДБАР ===
with st.sidebar:
    st.title("🚀 TrendScout")
    page = st.radio("Раздел", ["👤 Анализ Конкурента", "🌍 Поиск Трендов"])

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
        tab1, tab2 = st.tabs(["🏆 Топ-3 Хита (Год)", "🆕 Лента (Последние 30)"])
        
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

    else:
        st.info("Введите никнейм выше, чтобы начать.")

# ==========================================
# 🌍 СТРАНИЦА: ПОИСК ТРЕНДОВ
# ==========================================
elif page == "🌍 Поиск Трендов":
    st.title("🌍 Глобальный Поиск")
    
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        k = c1.text_input("Тема (на англ):", "Travel")
        d = c2.text_input("Контекст (для AI):", "Tours")
        if st.button("🚀 Найти", type="primary"):
            with st.spinner("Ищу, фильтрую и сохраняю..."):
                run_analysis([k], business_desc=d, mode="search")
                st.rerun()

    db = get_db_session()
    trends = db.query(Trend).filter(Trend.vertical == k).order_by(Trend.uts_score.desc()).limit(30).all()
    db.close()

    if trends:
        st.subheader(f"Результаты по теме: {k}")
        render_grid(trends)
    else:
        st.info("Введите тему для поиска.")