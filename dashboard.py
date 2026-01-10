import pandas as pd
import streamlit as st
import time
import plotly.express as px
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

from database import Trend, get_db_session
from main import run_analysis 

# --- ФУНКЦИИ ---
def load_runs(session):
    rows = session.query(Trend.run_id).distinct().order_by(Trend.run_id.desc()).all()
    return [r[0] for r in rows]

def fetch_data(session, selected_run):
    query = session.query(Trend)
    if selected_run:
        query = query.filter(Trend.run_id == selected_run)
    return query.all()

def prepare_df(data):
    if not data: return pd.DataFrame()
    return pd.DataFrame([
        {
            "UTS": round(t.transfer_score, 2),
            "S (Схожесть)": round(t.similarity, 2),
            "R (Охват)": round(t.normalized_reach, 2),
            "Просмотры": (t.stats or {}).get('views', 0),
            "Подписчики": t.followers,
            "AI Суть": t.ai_summary if t.ai_summary != "AI Error" else t.description[:50],
            "Ссылка": t.url,
            "created_at": t.created_at # Важно для разделения!
        }
        for t in data
    ])

# --- ИНТЕРФЕЙС ---
def render_dashboard():
    st.set_page_config(page_title="TrendScout UTS", page_icon="🎯", layout="wide")
    st.markdown("""
        <style>
        .block-container {padding-top: 1rem;}
        h3 {color: #FF4B4B;} 
        </style>
    """, unsafe_allow_html=True)

    st.title("🎯 TrendScout — Double View")

    session = get_db_session()
    
    # === SIDEBAR ===
    with st.sidebar:
        st.header("🔍 Новый поиск")
        with st.form("search_form"):
            keywords_input = st.text_area("Темы:", value="Спортивное питание", height=70)
            business_desc = st.text_area("Визуальное описание бизнеса:", value="Aesthetic gym, protein shaker, workout", height=100)
            if st.form_submit_button("🚀 ЗАПУСК (Гибрид)", type="primary"):
                keywords = [k.strip() for k in keywords_input.splitlines() if k.strip()]
                if keywords:
                    st.info("Этап 1: Ищем в базе... Этап 2: Идем в Apify...")
                    run_analysis(keywords, business_desc=business_desc)
                    st.success("Готово!")
                    time.sleep(0.5)
                    st.rerun()

        st.divider()
        all_runs = load_runs(session)
        selected_run = st.selectbox("История:", all_runs, index=0 if all_runs else None)
        
        if st.button("🗑️ Очистить базу"):
            session.query(Trend).delete()
            session.commit()
            st.rerun()

    if not selected_run:
        st.info("База пуста.")
        return

    # === РАЗДЕЛЕНИЕ ДАННЫХ ===
    data = fetch_data(session, selected_run)
    df = prepare_df(data)
    
    if df.empty:
        st.warning("Нет данных.")
        return

    # Логика разделения: "Новые" - это те, что созданы в последние 10 минут от времени запуска
    # Но так как run_id - это строка, возьмем просто max(created_at) как точку отсчета
    latest_time = df['created_at'].max()
    time_threshold = latest_time - timedelta(minutes=10)

    # Две таблицы
    df_fresh = df[df['created_at'] > time_threshold]
    df_archive = df[df['created_at'] <= time_threshold]

    # === МЕТРИКИ ОБЩИЕ ===
    c1, c2, c3 = st.columns(3)
    c1.metric("Всего найдено", len(df))
    c2.metric("🆕 Свежих (Apify)", len(df_fresh))
    c3.metric("🗄️ Из Архива (DB)", len(df_archive))

    # === ТАБЛИЦА 1: СВЕЖИЕ ===
    st.subheader("🔥 Свежие находки (Только что скачали)")
    if not df_fresh.empty:
        st.dataframe(
            df_fresh.drop(columns=["created_at"]),
            use_container_width=True,
            hide_index=True,
            column_config={"Ссылка": st.column_config.LinkColumn("TikTok", display_text="Link"), "UTS": st.column_config.ProgressColumn("UTS", format="%.2f")}
        )
    else:
        st.info("Скрепер не нашел ничего нового (или всё отфильтровал).")

    # === ТАБЛИЦА 2: АРХИВ ===
    st.subheader("🗄️ Найдено в вашей Базе (Экономия токенов)")
    if not df_archive.empty:
        st.dataframe(
            df_archive.drop(columns=["created_at"]),
            use_container_width=True,
            hide_index=True,
            column_config={"Ссылка": st.column_config.LinkColumn("TikTok", display_text="Link"), "UTS": st.column_config.ProgressColumn("UTS", format="%.2f")}
        )
    else:
        st.info("В базе не нашлось подходящих старых видео.")

if __name__ == "__main__":
    render_dashboard()