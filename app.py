import streamlit as st
import data_loader
import charts
import pandas as pd
import redis
import hashlib
import json

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="AWS SOC Dash", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- POŁĄCZENIE Z REDIS ---
try:
    # Pobieramy dane z "Sekretów" Streamlita. Jeśli ich nie ma, używamy ustawień lokalnych.
    redis_host = st.secrets.get("REDIS_HOST", "localhost")
    redis_port = st.secrets.get("REDIS_PORT", 6379)
    redis_password = st.secrets.get("REDIS_PASSWORD", None)

    r = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        ssl=True if redis_password else False, # Upstash wymaga bezpiecznego połączenia SSL
        db=0,
        decode_responses=True
    )
    r.ping()
    global_views = r.incr('soc_dashboard_views')
    
    # Dynamiczny status - pokazuje czy jesteś w chmurze czy u siebie
    redis_status = "🟢 Redis: Online (Cloud)" if redis_password else "🟢 Redis: Online (Local)"
except Exception as e:
    global_views = "Brak połączenia"
    redis_status = "🔴 Redis: Offline"

# --- WCZYTYWANIE DANYCH ---
df = data_loader.get_processed_data("AWS_Honeypot_marx-geo.csv.gz")

if df.empty:
    st.error("Błąd ładowania pliku. Upewnij się, że plik .gz jest w głównym folderze.")
    st.stop()

# --- SIDEBAR: FILTRY ---
st.sidebar.title("🛡️ Panel SOC")
st.sidebar.markdown("---")
st.sidebar.caption(redis_status)
st.sidebar.metric("Globalne wejścia", global_views)
st.sidebar.markdown("---")

min_d, max_d = df['datetime'].min().date(), df['datetime'].max().date()
date_range = st.sidebar.date_input("Zakres dat:", value=(min_d, max_d), format="DD-MM-YYYY")
hour_range = st.sidebar.slider("Zakres godzinowy:", min_value=0, max_value=23, value=(0, 23))

countries = ["Wszystkie"] + sorted(df['country'].unique().tolist())
selected_country = st.sidebar.selectbox("Wybierz kraj:", countries)

if 'service' in df.columns:
    attack_types = ["Wszystkie"] + sorted(df['service'].astype(str).unique().tolist())
    attack_col = 'service'
elif 'proto' in df.columns:
    attack_types = ["Wszystkie"] + sorted(df['proto'].astype(str).unique().tolist())
    attack_col = 'proto'
else:
    attack_types = ["Wszystkie"]
    attack_col = None

selected_attack = st.sidebar.selectbox("Rodzaj ataku:", attack_types)

# --- LOGIKA FILTROWANIA MASOWEGO ---
mask = (df['datetime'].dt.date >= date_range[0]) & (df['datetime'].dt.date <= date_range[1])
mask &= (df['datetime'].dt.hour >= hour_range[0]) & (df['datetime'].dt.hour <= hour_range[1])

if selected_country != "Wszystkie":
    mask &= (df['country'] == selected_country)

if selected_attack != "Wszystkie" and attack_col is not None:
    mask &= (df[attack_col].astype(str) == selected_attack)

f_df = df.loc[mask]

# --- LOGIKA MAPY FLY-TO (Sanity Check) ---
map_lat, map_lon, map_zoom = 20, 0, 1.2
if selected_country != "Wszystkie" and not f_df.empty:
    valid_coords = f_df[(f_df['latitude'] >= -90) & (f_df['latitude'] <= 90) & (f_df['longitude'] >= -180) & (f_df['longitude'] <= 180)]
    if not valid_coords.empty:
        map_lat = valid_coords['latitude'].mean()
        map_lon = valid_coords['longitude'].mean()
        map_zoom = 4
        st.sidebar.info(f"Fly-to: {selected_country}")
    else:
        st.sidebar.warning("⚠️ Uszkodzone dane GPS w tym rejonie.")

st.title("Wywiad zagrożeń AWS Honeypot")

# --- ALERTY BEZPIECZEŃSTWA ---
if not f_df.empty:
    total_attacks = len(f_df)
    if 'src' in f_df.columns:
        top_ip = f_df['src'].value_counts().head(1)
        if not top_ip.empty and (top_ip.values[0] / total_attacks) > 0.4 and total_attacks > 10:
            st.error(f"🚨 **Krytyczny Alert:** Adres IP **{top_ip.index[0]}** generuje >40% ataków ({top_ip.values[0]} uderzeń). Możliwy Brute-Force!")
    
    if attack_col is not None:
        ssh_rdp_mask = f_df[attack_col].astype(str).str.contains('ssh|rdp|22|3389', case=False, na=False)
        if (ssh_rdp_mask.sum() / total_attacks) > 0.5 and total_attacks > 10:
            st.warning("⚠️ **Ostrzeżenie:** >50% ruchu wycelowane w porty zarządzania (SSH/RDP).")

# --- REDIS CACHE (PAMIĘĆ PODRĘCZNA ZAPYTAŃ) ---
st.divider()
st.subheader("⚡ Silnik Optymalizacji Zapytań (Redis Cache)")

filter_signature = f"{selected_country}_{date_range}_{hour_range}_{selected_attack}"
cache_key = "kpi_cache_" + hashlib.md5(filter_signature.encode()).hexdigest()

try:
    cached_data = r.get(cache_key)
    if cached_data:
        total, unique, top_p, top_proto = json.loads(cached_data)
        st.success("🟢 Załadowano z pamięci RAM błyskawicznie (Redis Cache Hit)")
    else:
        total, unique, top_p, top_proto = data_loader.get_kpi_metrics(f_df)
        r.setex(cache_key, 3600, json.dumps((total, unique, str(top_p), str(top_proto))))
        st.info("🟡 Policzono klasycznie i zapisano w cache (Redis Cache Miss)")
except Exception:
    total, unique, top_p, top_proto = data_loader.get_kpi_metrics(f_df)
    st.caption("Redis offline - standardowe obliczenia.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Łącznie Ataków", f"{total:,}")
m2.metric("Unikalne IP", unique)
m3.metric("Najczęstszy Cel", top_p)
m4.metric("Główny Protokół", top_proto)

st.divider()

# --- MAPA I WYKRESY ---
st.pydeck_chart(charts.plot_attack_map(f_df, map_lat, map_lon, map_zoom))
st.divider()

if not f_df.empty:
    st.plotly_chart(charts.plot_attack_trend(f_df), use_container_width=True)
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.plot_port_ranking(f_df), use_container_width=True)
    with c2:
        st.plotly_chart(charts.plot_proto_pie(f_df), use_container_width=True)
    st.plotly_chart(charts.plot_time_heatmap(f_df), use_container_width=True)

st.divider()

# --- SUROWE LOGI ---
with st.expander("👁️ Pokaż/Ukryj surowe logi zdarzeń", expanded=False):
    st.dataframe(f_df, use_container_width=True)
    if not f_df.empty:
        st.download_button(label="⬇️ Pobierz przefiltrowane logi (CSV)", data=f_df.to_csv(index=False).encode('utf-8'), file_name='wyfiltrowane_ataki_soc.csv', mime='text/csv')

# --- REDIS MESSAGE BROKER (BUFOR LOGÓW) ---
st.divider()
st.subheader("📡 Bufor Strumieniowy (Kolejka Wiadomości Redis)")
st.markdown("Symulacja odczytu asynchronicznego z kolejki Message Broker chroniącej przed atakami DDoS.")

try:
    live_logs = r.lrange("live_soc_buffer", 0, 4)
    if live_logs:
        for log in live_logs:
            st.code(log, language="bash")
        st.button("🔄 Odśwież kolejkę")
    else:
        st.info("Kolejka jest pusta. Uruchom skrypt live_attacks.py w osobnym terminalu.")
except Exception:
    st.error("Uruchom serwer Redis, aby włączyć nasłuch strumienia.")