import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import calendar
from datetime import datetime, date, timedelta
import requests
import os

# --- 📱 レイアウト設定 ---
st.set_page_config(page_title="天気日記", page_icon="☀️", layout="centered")

# ローカル環境で「Deploy」ボタンを非表示にする設定
try:
    st.set_option("client.toolbarMode", "viewer")
except Exception:
    pass

st.markdown("""
<style>
    /* 全体の縦スクロールを確実にする設定 */
    html, body, [data-testid="stAppViewContainer"] {
        overflow-y: auto !important;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 600px;
    }

    /* スマホなどでプルダウンを綺麗に横並びにする設定 */
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            flex: 1 1 auto !important;
            min-width: 0 !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- 🔄 自動データ取得・更新ロジック（スマート自動更新版） ---
def check_and_update():
    daily_path = "weather_daily.parquet"
    hourly_path = "weather_hourly.parquet"
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if not os.path.exists(daily_path) or not os.path.exists(hourly_path):
        st.info("🔄 気象データファイルが見つかりません。自動でデータを取得しています...")
        fetch_and_save_data("2015-01-01", today_str, daily_path, hourly_path, is_init=True)
    else:
        try:
            df_daily_check = pd.read_parquet(daily_path)
            last_date_str = str(pd.to_datetime(df_daily_check["time"].max()).strftime("%Y-%m-%d"))
            
            if last_date_str < today_str:
                st.info("🔄 最新の気象データを更新しています...")
                fetch_and_save_data(last_date_str, today_str, daily_path, hourly_path, is_init=False)
        except Exception:
            fetch_and_save_data("2015-01-01", today_str, daily_path, hourly_path, is_init=True)

def fetch_and_save_data(start_date, end_date, daily_path, hourly_path, is_init=False):
    LAT = 32.826687
    LON = 129.884194
    
    # 正しい風速単位パラメータ（windspeed_unit=ms）を使用
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={LAT}&longitude={LON}&start_date={start_date}&end_date={end_date}&hourly=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto&windspeed_unit=ms"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if "daily" in data:
            new_daily_df = pd.DataFrame({
                "time": pd.to_datetime(data["daily"]["time"]).date,
                "temperature_2m_max": data["daily"]["temperature_2m_max"],
                "temperature_2m_min": data["daily"]["temperature_2m_min"],
                "precipitation_sum": data["daily"].get("precipitation_sum", 0)
            })
            
            if not is_init and os.path.exists(daily_path):
                old_df = pd.read_parquet(daily_path)
                daily_df = pd.concat([old_df, new_daily_df]).drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
            else:
                daily_df = new_daily_df
                
            daily_df.to_parquet(daily_path, index=False)
            
        if "hourly" in data:
            new_hourly_df = pd.DataFrame({
                "time": pd.to_datetime(data["hourly"]["time"]),
                "temperature_2m": data["hourly"]["temperature_2m"],
                "precipitation": data["hourly"]["precipitation"],
                "weather_code": data["hourly"]["weather_code"],
                "wind_speed_10m": data["hourly"].get("wind_speed_10m", 0)
            })
            
            if not is_init and os.path.exists(hourly_path):
                old_df = pd.read_parquet(hourly_path)
                hourly_df = pd.concat([old_df, new_hourly_df]).drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
            else:
                hourly_df = new_hourly_df
                
            hourly_df.to_parquet(hourly_path, index=False)
            
        if is_init:
            st.success("✨ 2015年からの気象データの初期取得が完了しました！")
    except Exception as e:
        st.error(f"⚠️ 気象データの取得に失敗しました: {e}")

check_and_update()

# --- セッション状態の初期化 ---
if "selected_day" not in st.session_state:
    st.session_state["selected_day"] = 1

if "current_year" not in st.session_state:
    st.session_state["current_year"] = datetime.now().year

if "current_month" not in st.session_state:
    st.session_state["current_month"] = datetime.now().month

# URLのクエリパラメータから選択日を取得（カレンダー連動用）
query_params = st.query_params
if "day" in query_params:
    try:
        val = int(query_params["day"])
        if st.session_state["selected_day"] != val:
            st.session_state["selected_day"] = val
    except ValueError:
        pass

# --- 1. タイトル と 年月選択プルダウン（横並び） ---
st.markdown("<h1 style='font-size: 20px; margin-bottom: 5px;'>☀️ 天気日記</h1>", unsafe_allow_html=True)

col_y, col_m = st.columns(2)

with col_y:
    available_years = list(range(datetime.now().year, 2014, -1))
    current_year = st.session_state["current_year"]
    year_index = available_years.index(current_year) if current_year in available_years else 0
    
    selected_year = st.selectbox(
        "年",
        available_years,
        index=year_index,
        format_func=lambda x: f"{x}年",
        label_visibility="collapsed"
    )

with col_m:
    available_months = list(range(1, 13))
    current_month = st.session_state["current_month"]
    month_index = available_months.index(current_month) if current_month in available_months else 0
    
    selected_month = st.selectbox(
        "月",
        available_months,
        index=month_index,
        format_func=lambda x: f"{x}月",
        label_visibility="collapsed"
    )

if selected_year != st.session_state["current_year"] or selected_month != st.session_state["current_month"]:
    st.session_state["current_year"] = selected_year
    st.session_state["current_month"] = selected_month
    st.session_state["selected_day"] = 1
    st.rerun()

year = st.session_state["current_year"]
month = st.session_state["current_month"]

st.write("") 

# ⚡ Parquet形式でデータを読み込み、メモリにキャッシュする
@st.cache_data
def load_weather_data():
    if os.path.exists("weather_daily.parquet"):
        df_daily = pd.read_parquet("weather_daily.parquet")
    else:
        df_daily = pd.DataFrame()
        
    if os.path.exists("weather_hourly.parquet"):
        df_hourly = pd.read_parquet("weather_hourly.parquet")
    else:
        df_hourly = pd.DataFrame()
        
    return df_daily, df_hourly

try:
    df_daily, df_hourly = load_weather_data()
except Exception as e:
    st.error(f"データファイルの読み込みに失敗しました。(エラー詳細: {e})")
    st.stop()

# 天気コードを絵文字に変換する関数
def code_to_emoji(code):
    if pd.isna(code):
        return "☀️"
    code = int(code)
    if code == 0:
        return "☀️"  # 快晴
    elif code in [1, 2]:
        return "⛅"  # 晴れ・一部曇り
    elif code == 3:
        return "☁️"  # 曇り
    elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        return "🌧️"  # 雨
    elif code >= 95:
        return "⚡"  # 雷
    else:
        return "☁️"  # その他

am_dict = {}
pm_dict = {}
max_temp_dict = {}
min_temp_dict = {}

if not df_hourly.empty:
    year_hourly = df_hourly[df_hourly["time"].dt.year == year]

    for date_str, group in year_hourly.groupby(year_hourly["time"].dt.date):
        am_row = group[group["time"].dt.hour == 9]
        am_code = am_row["weather_code"].values[0] if not am_row.empty else 0
        am_dict[date_str] = code_to_emoji(am_code)
        
        pm_row = group[group["time"].dt.hour == 15]
        pm_code = pm_row["weather_code"].values[0] if not pm_row.empty else 0
        pm_dict[date_str] = code_to_emoji(pm_code)

# 日別データから最高気温・最低気温を取得
if not df_daily.empty:
    year_daily = df_daily[pd.to_datetime(df_daily["time"]).dt.year == year]
    for _, row in year_daily.iterrows():
        d_val = row["time"]
        if isinstance(d_val, str):
            d_val = datetime.strptime(d_val, "%Y-%m-%d").date()
        if "temperature_2m_max" in df_daily.columns:
            max_temp_dict[d_val] = row["temperature_2m_max"]
        if "temperature_2m_min" in df_daily.columns:
            min_temp_dict[d_val] = row["temperature_2m_min"]

# --- 2. 横スクロールカレンダーの生成 ---
last_day = calendar.monthrange(year, month)[1]
today = date.today()
current_selected_day = st.session_state["selected_day"]

if current_selected_day > last_day:
    current_selected_day = last_day
    st.session_state["selected_day"] = last_day

calendar_cards_html = ""
days_of_week_jp = ["日", "月", "火", "水", "木", "金", "土"]

for d in range(1, last_day + 1):
    target_date = date(year, month, d)
    wd_index = (target_date.weekday() + 1) % 7
    wd_str = days_of_week_jp[wd_index]
    
    color_style = "color: #333;"
    if wd_index == 0:  # 日曜
        color_style = "color: #d9534f;"
    elif wd_index == 6: # 土曜
        color_style = "color: #0275d8;"

    is_selected = (d == current_selected_day)
    
    border_color = "#ff4b4b" if is_selected else "#ccc"
    bg_color = "#fff0f0" if is_selected else "#ffffff"
    shadow = "box-shadow: 0 2px 5px rgba(255,75,75,0.3);" if is_selected else "box-shadow: 0 1px 3px rgba(0,0,0,0.05);"

    if target_date > today:
        am_mark = "-"
        pm_mark = "-"
        temp_str = ""
    else:
        am_mark = am_dict.get(target_date, "-")
        pm_mark = pm_dict.get(target_date, "-")
        
        max_t = max_temp_dict.get(target_date, "")
        min_t = min_temp_dict.get(target_date, "")
        
        max_str = f"{max_t:.1f}°" if pd.notna(max_t) and max_t != "" else ""
        min_str = f"{min_t:.1f}°" if pd.notna(min_t) and min_t != "" else ""
        
        if max_str and min_str:
            temp_str = f"<span style='color: #d9534f;'>{max_str}</span><br><span style='color: #0275d8;'>{min_str}</span>"
        elif max_str:
            temp_str = f"<span style='color: #d9534f;'>{max_str}</span>"
        elif min_str:
            temp_str = f"<span style='color: #0275d8;'>{min_str}</span>"
        else:
            temp_str = ""

    card_id_attr = "id='selected-card'" if is_selected else ""

    calendar_cards_html += f"""
    <div {card_id_attr} onclick="window.parent.location.href='?day={d}'" 
         style='flex: 0 0 75px; height: 166px; border: 2px solid {border_color}; border-radius: 8px; text-align: center; padding: 3px 2px; background-color: {bg_color}; {shadow} cursor: pointer; font-family: sans-serif; transition: 0.2s;'>
        <div style='font-size: 18px; font-weight: bold; {color_style}'>{wd_str}</div>
        <div style='font-size: 20px; font-weight: bold; color: #111; margin: 1px 0;'>{d}</div>
        <div style='font-size: 30px; line-height: 1.1; margin: 2px 0;'>{am_mark}<br>{pm_mark}</div>
        <div style='font-size: 20px; font-weight: bold; margin-top: 2px; line-height: 1.2;'>{temp_str}</div>
    </div>
    """

cal_scroll_container = f"""
<html>
<head>
<style>
    .cal-scroll {{
        display: flex;
        overflow-x: auto;
        gap: 8px;
        padding: 4px 2px;
        width: 100%;
        white-space: nowrap;
        -webkit-overflow-scrolling: touch;
    }}
    .cal-scroll::-webkit-scrollbar {{
        height: 6px;
    }}
    .cal-scroll::-webkit-scrollbar-track {{
        background: #f1f1f1;
        border-radius: 3px;
    }}
    .cal-scroll::-webkit-scrollbar-thumb {{
        background: #ccc;
        border-radius: 3px;
    }}
</style>
</head>
<body style="margin:0; background-color: transparent;">
    <div class="cal-scroll" id="calendarContainer">
        {calendar_cards_html}
    </div>
    <script>
        window.onload = function() {{
            const selectedCard = document.getElementById('selected-card');
            const container = document.getElementById('calendarContainer');
            if (selectedCard && container) {{
                const scrollLeftPos = selectedCard.offsetLeft - (container.clientWidth / 2) + (selectedCard.clientWidth / 2);
                container.scrollLeft = scrollLeftPos;
            }}
        }};
    </script>
</body>
</html>
"""

components.html(cal_scroll_container, height=180)

st.markdown("<div style='margin: -25px 0 0 0;'></div>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("<div style='margin: -25px 0 0 0;'></div>", unsafe_allow_html=True)

# --- 3. 選択された日の詳細タイムライン ---
col_label_t, col_select = st.columns([2.2, 0.8])
with col_label_t:
    st.markdown("<div style='padding-top: 5px; font-weight: bold; font-size: 16px;'>⏱️ 時間別の詳細:</div>", unsafe_allow_html=True)

with col_select:
    days_list = list(range(1, last_day + 1))
    safe_index = current_selected_day - 1 if current_selected_day <= last_day else last_day - 1
    
    selected_day_from_box = st.selectbox(
        "日付選択",
        days_list,
        index=safe_index,
        format_func=lambda d: f"{d}日",
        label_visibility="collapsed"
    )

if st.session_state["selected_day"] != selected_day_from_box:
    st.session_state["selected_day"] = selected_day_from_box
    st.rerun()

target_date_str = f"{year}-{month:02d}-{selected_day_from_box:02d}"

if not df_hourly.empty:
    day_df = year_hourly[year_hourly["time"].dt.date.astype(str) == target_date_str]
else:
    day_df = pd.DataFrame()

if not day_df.empty:
    cards_html = ""
    for _, row in day_df.iterrows():
        hour_val = row["time"].hour
        hour_str = f"{hour_val}時"
        
        emoji = code_to_emoji(row["weather_code"])
        temp = row["temperature_2m"]
        precip = row["precipitation"]
        wind_speed = row.get("wind_speed_10m", 0)
        if pd.isna(wind_speed):
            wind_speed = 0
        
        # 💧 降水量・風速マーク付き
        cards_html += f"""
        <div style='flex: 0 0 95px; height: 155px; border: 1px solid #ccc; border-radius: 8px; text-align: center; padding: 4px 2px; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.05); font-family: sans-serif;'>
            <div style='font-size: 22px; font-weight: bold; color: #444;'>{hour_str}</div>
            <div style='font-size: 36px; margin: 2px 0;'>{emoji}</div>
            <div style='font-size: 22px; font-weight: bold; color: #d9534f;'>{temp}°C</div>
            <div style='font-size: 18px; color: #0275d8; margin-top: 1px;'>💧{precip}mm</div>
            <div style='font-size: 18px; color: #555; margin-top: 2px; border-top: 1px dashed #eee; padding-top: 2px;'>💨 {wind_speed:.1f}m/s</div>
        </div>
        """
    
    scroll_container = f"""
    <html>
    <head>
    <style>
        .scroll-container {{
            display: flex;
            overflow-x: auto;
            gap: 8px;
            padding: 4px 2px;
            width: 100%;
            white-space: nowrap;
        }}
        .scroll-container::-webkit-scrollbar {{
            height: 6px;
        }}
        .scroll-container::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 4px;
        }}
        .scroll-container::-webkit-scrollbar-thumb {{
            background: #888;
            border-radius: 4px;
        }}
    </style>
    </head>
    <body style="margin:0; background-color: transparent;">
        <div class="scroll-container">
            {cards_html}
        </div>
    </body>
    </html>
    """
    
    components.html(scroll_container, height=175)
else:
    st.write(f"選択された日（{target_date_str}）のデータが見つかりませんでした。")