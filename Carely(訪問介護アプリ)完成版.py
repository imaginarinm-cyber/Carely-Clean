import streamlit as st
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium
import pandas as pd
import smtplib
import ssl

# --- デザイン（CSS） ---
st.markdown("""
<style>
/* 全体のフォントと背景 */
body {
    font-family: 'Helvetica', sans-serif;
}

/* カード風デザイン */
.card {
    padding: 20px;
    margin-bottom: 15px;
    border-radius: 10px;
    background-color: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* タイトルの余白調整 */
h1 {
    margin-bottom: 10px;
}

/* サブタイトル */
h3 {
    margin-top: 25px;
}

/* サイドバーの見出し */
.sidebar .sidebar-content {
    background-color: #f0f4ff;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* 全体のフォントと背景 */
body {
    font-family: 'Helvetica', sans-serif;
}

/* カード風デザイン */
.card {
    padding: 20px;
    margin-bottom: 15px;
    border-radius: 10px;
    background-color: #ffffff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* タイトルの余白調整 */
h1 {
    margin-bottom: 10px;
}

/* サブタイトル */
h3 {
    margin-top: 25px;
}

/* サイドバーの見出し */
.sidebar .sidebar-content {
    background-color: #f0f4ff;
}

/* ★ここに追加するCSS★ */
.visit-card {
    background-color: #ffffff;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border-left: 6px solid #2E7BEF;
}

    /* サイドバー背景と枠 */
section[data-testid="stSidebar"] {
    background-color: #F0F4FF;
    border-right: 2px solid #2E7BEF;
}
            
</style>
""", unsafe_allow_html=True)

# --- 0. メール送信用設定（必要なら編集） ---
# ここを自分の環境に合わせて設定してください。
EMAIL_SENDER = "your_email@example.com"   # 送信元メールアドレス
EMAIL_PASSWORD = "your_app_password"      # メールのアプリパスワード等
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL

def send_email(to_email: str, subject: str, body: str):
    """シンプルなメール送信関数。設定が未完了なら実行されても失敗するので注意。"""
    if not to_email:
        raise ValueError("送信先メールアドレスが指定されていません。")

    message = f"Subject: {subject}\nTo: {to_email}\nFrom: {EMAIL_SENDER}\n\n{body}"

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, message.encode("utf-8"))

# --- 1. アプリの見た目設定 ---
st.set_page_config(page_title="Carely", page_icon="🏥")
st.title("🏥 Carely (ケアリー)")
# --- ヒーローヘッダー ---
st.markdown("""
<div style="padding: 20px; background-color: #E6F2FF; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <h2 style="color: #2E7BEF;">訪問看護のスケジュールを、もっとスマートに。</h2>
  <p style="font-size: 16px; color: #333;">
    Carely は、訪問先の順番・業務内容・移動負荷を自動で計算し、<br>
    看護師の一日を最適化するアプリです。
  </p>
</div>
""", unsafe_allow_html=True)
st.markdown("### 訪問看護スケジュール & 疲れスコア")

# サイドバー（左側の設定パネル）
st.sidebar.header("⚙️ 設定")
speed_kmh = st.sidebar.slider("移動スピード (km/h)", 10, 40, 20)
start_hour = st.sidebar.number_input("開始時間 (時)", 8, 12, 9)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🏠 訪問先の住所入力")

# --- 2. 住所入力 & ジオコーディング準備 ---
geolocator = Nominatim(user_agent="carely_app")

def geocode_address(label, address):
    """住所を緯度経度に変換。失敗したら None を返す。"""
    if not address:
        return None
    try:
        loc = geolocator.geocode(address)
        if loc:
            return (loc.latitude, loc.longitude)
        else:
            st.sidebar.warning(f"{label} の住所が見つかりませんでした。デフォルト位置を使用します。")
            return None
    except Exception:
        st.sidebar.error(f"{label} の住所取得でエラーが発生しました。")
        return None

# サイドバーで住所入力
address_A = st.sidebar.text_input("Aさん宅の住所")
address_B = st.sidebar.text_input("Bさん宅の住所")
address_C = st.sidebar.text_input("Cさん宅の住所")

# --- 3. データ準備（深谷市周辺想定 + 入力住所を優先） ---
# デフォルト座標
default_points = {
    "駅": (36.1878, 139.2815),
    "Aさん宅": (36.1915, 139.2941),
    "Bさん宅": (36.1980, 139.3000),
    "Cさん宅": (36.1850, 139.3100)
}

points = {
    "駅": default_points["駅"]
}

# 住所が正しく取れたらそれを使い、ダメならデフォルト座標
geo_A = geocode_address("Aさん宅", address_A)
geo_B = geocode_address("Bさん宅", address_B)
geo_C = geocode_address("Cさん宅", address_C)

points["Aさん宅"] = geo_A if geo_A else default_points["Aさん宅"]
points["Bさん宅"] = geo_B if geo_B else default_points["Bさん宅"]
points["Cさん宅"] = geo_C if geo_C else default_points["Cさん宅"]

# --- 4. サービス区分 ---
SERVICE_NORMAL = 45   # 分
SERVICE_LONG = 75     # 分
LUNCH_BREAK = 60      # 分
LOAD_BODY = 8
LOAD_NORMAL = 5

def get_data(p1, p2):
    """2点間の距離・移動時間・移動負荷を計算"""
    dist = geodesic(points[p1], points[p2]).km
    time = (dist / speed_kmh) * 60 + 3  # 分。+3分は乗降・信号待ちなど
    load = dist * 2                     # 距離に応じた移動負荷（仮）
    return dist, time, load

def format_time(minutes):
    """分を HH:MM 表記に変換"""
    return f"{int(minutes // 60):02}:{int(minutes % 60):02}"

# --- 5. 業務内容の定義 & 選択 UI ---

st.sidebar.markdown("---")
st.sidebar.markdown("#### 📝 訪問時の業務内容")

TASK_CONFIG = {
    "バイタル測定": {"extra_minutes": 5, "extra_load": 1},
    "清拭・入浴介助": {"extra_minutes": 20, "extra_load": 4},
    "服薬管理": {"extra_minutes": 5, "extra_load": 1},
    "創傷処置": {"extra_minutes": 10, "extra_load": 2},
    "排泄介助": {"extra_minutes": 10, "extra_load": 2},
    "リハビリ": {"extra_minutes": 20, "extra_load": 3},
    "医療処置（点滴・吸引など）": {"extra_minutes": 15, "extra_load": 3},
    "記録": {"extra_minutes": 5, "extra_load": 1},
    "家族支援": {"extra_minutes": 10, "extra_load": 2},
    "相談対応": {"extra_minutes": 10, "extra_load": 2},
}

task_options = list(TASK_CONFIG.keys())

tasks_A = st.sidebar.multiselect("Aさん宅の業務内容", task_options)
tasks_B = st.sidebar.multiselect("Bさん宅の業務内容", task_options)
tasks_C = st.sidebar.multiselect("Cさん宅の業務内容", task_options)

task_map = {
    "Aさん宅": tasks_A,
    "Bさん宅": tasks_B,
    "Cさん宅": tasks_C,
}

# --- 6. スケジュール計算 ---
current_time = start_hour * 60
total_load = 0
records = []  # 訪問ごとの記録保存用

# 基本ルート（ここは今まで通り）
route = [
    ("駅", "Aさん宅", SERVICE_NORMAL, LOAD_NORMAL),
    ("Aさん宅", "Bさん宅", SERVICE_LONG, LOAD_NORMAL),
    ("Bさん宅", "Cさん宅", SERVICE_NORMAL, LOAD_BODY)
]

st.subheader("📅 本日の流れ")
current_loc = "駅"

for start_loc, next_loc, service_time_base, work_load_base in route:
    # Cさん宅の前にお昼休憩
    if next_loc == "Cさん宅":
        st.warning(f"🍱 {format_time(current_time)} 〜 {format_time(current_time + LUNCH_BREAK)} お昼休憩")
        current_time += LUNCH_BREAK

    # 距離・移動時間・移動負荷
    d, t, move_load = get_data(current_loc, next_loc)
    arrival = current_time + t

    # 業務による追加時間・追加負荷
    selected_tasks = task_map.get(next_loc, [])
    extra_minutes = sum(TASK_CONFIG[t]["extra_minutes"] for t in selected_tasks)
    extra_task_load = sum(TASK_CONFIG[t]["extra_load"] for t in selected_tasks)

    # 実際のサービス時間（基本 + 業務分）
    service_time_adjusted = service_time_base + extra_minutes
    departure = arrival + service_time_adjusted

    # 負荷計算（移動 + 基本作業 + 業務負荷）
    visit_total_load = move_load + work_load_base + extra_task_load
    total_load += visit_total_load

    # --- カード開始 ---
    st.markdown('<div class="visit-card">', unsafe_allow_html=True)

    # 画面に見やすく表示
    with st.expander(f"📍 {next_loc} への訪問"):
        st.write(f"**到着予定:** {format_time(arrival)}")
        st.write(f"**出発予定:** {format_time(departure)}")
        st.caption(
            f"移動距離: {d:.1f} km / "
            f"基本サービス時間: {service_time_base} 分 / "
            f"業務追加時間: {extra_minutes} 分 / "
            f"合計サービス時間: {service_time_adjusted} 分"
        )
        st.caption(
            f"移動負荷: {move_load:.1f} / "
            f"基本作業負荷: {work_load_base} / "
            f"業務負荷: {extra_task_load} / "
            f"この訪問の合計負荷: {visit_total_load:.1f}"
        )

        # 業務内容の表示（ここに1か所だけ）
        if selected_tasks:
            st.write("**業務内容:**")
            for t_name in selected_tasks:
                cfg = TASK_CONFIG[t_name]
                st.write(f"- {t_name}（+{cfg['extra_minutes']}分, +{cfg['extra_load']}負荷）")
        else:
            st.write("業務内容: （未選択）")

    # --- カード終了 ---
    st.markdown('</div>', unsafe_allow_html=True)

    # 記録データ保存（for の中 / with の外）
    records.append({
        "訪問先": next_loc,
        "到着予定": format_time(arrival),
        "出発予定": format_time(departure),
        "移動距離_km": round(d, 2),
        "基本サービス時間_分": service_time_base,
        "業務追加時間_分": extra_minutes,
        "合計サービス時間_分": service_time_adjusted,
        "移動負荷": round(move_load, 2),
        "基本作業負荷": work_load_base,
        "業務負荷": extra_task_load,
        "訪問合計負荷": round(visit_total_load, 2),
        "業務内容一覧": " / ".join(selected_tasks) if selected_tasks else "",
    })

    current_time = departure
    current_loc = next_loc

# --- 7. 診断表示 ---
st.divider()
st.subheader("📊 疲れスコア診断")
st.metric(label="トータル負荷", value=f"{total_load:.1f}")

if total_load > 25:
    st.error("⚠️ 過労の可能性があります！調整を検討してください。")
else:
    st.success("✅ 理想的なスケジュールです。")

# --- 8. 訪問記録の保存・ダウンロード・メール送信 ---

st.divider()
st.subheader("🗂️ 訪問記録")

if records:
    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True)

    # CSV ダウンロードボタン
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 訪問記録をCSVでダウンロード",
        data=csv_bytes,
        file_name="carely_visit_log.csv",
        mime="text/csv",
    )

    st.markdown("#### ✉️ 訪問内容をメール送信")

    email_to = st.text_input("送信先メールアドレス（例: xxx@example.com）")
    email_note = st.text_area("メール本文に追記したいメモ（任意）")

    if st.button("メールを送信する"):
        try:
            body_lines = []
            body_lines.append("本日の訪問記録です。\n")
            body_lines.append(df.to_string(index=False))
            if email_note:
                body_lines.append("\n\n【メモ】\n" + email_note)

            body = "\n".join(body_lines)
            send_email(
                to_email=email_to,
                subject="Carely 訪問記録",
                body=body
            )
            st.success("メールを送信しました。")
        except Exception as e:
            st.error(f"メール送信に失敗しました: {e}")
else:
    st.info("まだ訪問記録がありません。")

# --- 9. 地図表示（折りたたみ） ---
st.divider()
st.subheader("🗺️ 訪問先マップ")

with st.expander("地図を開く / 閉じる", expanded=False):
    # 地図作成（駅を中心）
    m = folium.Map(location=points["駅"], zoom_start=13)

    # 駅
    folium.Marker(
        points["駅"],
        popup="駅",
        tooltip="駅",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # Aさん宅
    folium.Marker(
        points["Aさん宅"],
        popup="Aさん宅",
        tooltip="Aさん宅",
        icon=folium.Icon(color="blue")
    ).add_to(m)

    # Bさん宅
    folium.Marker(
        points["Bさん宅"],
        popup="Bさん宅",
        tooltip="Bさん宅",
        icon=folium.Icon(color="green")
    ).add_to(m)

    # Cさん宅
    folium.Marker(
        points["Cさん宅"],
        popup="Cさん宅",
        tooltip="Cさん宅",
        icon=folium.Icon(color="purple")
    ).add_to(m)

    # 地図表示
    st_folium(m, width=700, height=450)