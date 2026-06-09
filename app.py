import streamlit as st
import data_loader
import charts
import time
import pandas as pd

st.set_page_config(page_title="AWS SOC Dash", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

# Zachowane Twoje poprawne wczytywanie pliku skompresowanego!
df = data_loader.get_processed_data("AWS_Honeypot_marx-geo.csv.gz")

if df.empty:
    st.error("Błąd ładowania pliku. Upewnij się, że plik .gz jest w głównym folderze.")
    st.stop()

# --- SIDEBAR: FILTRY ---
st.sidebar.title("Filtry Ataków")

# 1. Filtr daty
min_d, max_d = df['datetime'].min().date(), df['datetime'].max().date()
date_range = st.sidebar.date_input("Zakres (DD-MM-YYYY):", value=(min_d, max_d), format="DD-MM-YYYY")

# 2. Filtr godziny (od kolegi)
hour_range = st.sidebar.slider("Zakres godzinowy:", min_value=0, max_value=23, value=(0, 23))

# 3. Filtr kraju
countries = ["Wszystkie"] + sorted(df['country'].unique().tolist())
selected_country = st.sidebar.selectbox("Wybierz kraj:", countries)

# 4. Filtr rodzaju ataku (od kolegi)
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

# --- LOGIKA MAPY FLY-TO ---
map_lat, map_lon, map_zoom = 20, 0, 1.2

if selected_country != "Wszystkie" and not f_df.empty:
    # 1. Filtrujemy TYLKO poprawne fizycznie współrzędne
    valid_coords = f_df[
        (f_df['latitude'] >= -90) & (f_df['latitude'] <= 90) &
        (f_df['longitude'] >= -180) & (f_df['longitude'] <= 180)
    ]
    
    # 2. Liczymy średnią tylko z dobrych danych
    if not valid_coords.empty:
        map_lat = valid_coords['latitude'].mean()
        map_lon = valid_coords['longitude'].mean()
        map_zoom = 4
        st.sidebar.info(f"Fly-to: {selected_country}")
    else:
        st.sidebar.warning("Adresy z tego regionu mają uszkodzone dane GPS w logach.")

# --- GŁÓWNY DASHBOARD ---
st.title("Wywiad zagrożeń AWS Honeypot")

# --- ALERTY BEZPIECZEŃSTWA ---
if not f_df.empty:
    total_attacks = len(f_df)
    
    # Reguła 1: Wykrywanie dominującego agresora 
    if 'src' in f_df.columns:
        top_ip = f_df['src'].value_counts().head(1)
        if not top_ip.empty:
            ip_count = top_ip.values[0]
            ip_addr = top_ip.index[0]
            if (ip_count / total_attacks) > 0.4 and total_attacks > 10:
                st.error(f"🚨 **Krytyczny Alert:** Adres IP **{ip_addr}** odpowiada za ponad 40% widocznych ataków ({ip_count} uderzeń). Możliwy zmasowany atak Brute-Force!")
    
    # Reguła 2: Wykrywanie kampanii na porty zarządzania (SSH/RDP)
    if attack_col is not None:
        ssh_rdp_mask = f_df[attack_col].astype(str).str.contains('ssh|rdp|22|3389', case=False, na=False)
        ssh_rdp_count = ssh_rdp_mask.sum()
        if (ssh_rdp_count / total_attacks) > 0.5 and total_attacks > 10:
            st.warning("⚠️ **Ostrzeżenie:** Ponad 50% aktywności w tym oknie czasowym jest wymierzone w porty zdalnego zarządzania (SSH/RDP).")

# METRYKI 
total, unique, top_p, top_proto = data_loader.get_kpi_metrics(f_df)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Łącznie Ataków", f"{total:,}")
m2.metric("Unikalne IP", unique)
m3.metric("Najczęstszy Cel", top_p)
m4.metric("Główny Protokół", top_proto)

st.divider()

# MAPA
st.pydeck_chart(charts.plot_attack_map(f_df, map_lat, map_lon, map_zoom))

st.divider()

# WYKRESY
if not f_df.empty:
    # Nowy trend liniowy od kolegi
    st.plotly_chart(charts.plot_attack_trend(f_df), use_container_width=True)
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.plot_port_ranking(f_df), use_container_width=True)
    with c2:
        st.plotly_chart(charts.plot_proto_pie(f_df), use_container_width=True)
    
    st.plotly_chart(charts.plot_time_heatmap(f_df), use_container_width=True)
else:
    st.warning("Brak danych dla wybranych filtrów. Zmień filtry w panelu bocznym.")

st.divider()

# SUROWE LOGI I POBIERANIE
st.subheader("Surowe logi zdarzeń")

with st.expander("👁️ Pokaż/Ukryj surowe logi zdarzeń", expanded=False):
    # Wyświetlanie tabeli 
    if 'src' in f_df.columns:
        cols = ['src'] + [col for col in f_df.columns if col != 'src']
        st.dataframe(f_df[cols], use_container_width=True)
    else:
        st.dataframe(f_df, use_container_width=True)

    # Generowanie i pobieranie pliku CSV 
    if not f_df.empty:
        csv_data = f_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇Pobierz przefiltrowane logi (CSV)",
            data=csv_data,
            file_name='wyfiltrowane_ataki_soc.csv',
            mime='text/csv',
        )