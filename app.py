import streamlit as st
import data_loader
import charts
import time

st.set_page_config(page_title="AWS SOC Dash", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

df = data_loader.get_processed_data("AWS_Honeypot_marx-geo.csv")

if df.empty:
    st.error("Błąd ładowania pliku CSV. Upewnij się, że plik jest w głównym folderze.")
    st.stop()

st.sidebar.title("Filtry Ataków")
min_d, max_d = df['datetime'].min().date(), df['datetime'].max().date()
date_range = st.sidebar.date_input("Zakres (DD-MM-YYYY):", value=(min_d, max_d), format="DD-MM-YYYY")


countries = ["Wszystkie"] + sorted(df['country'].unique().tolist())
selected_country = st.sidebar.selectbox("Wybierz kraj:", countries)


mask = (df['datetime'].dt.date >= date_range[0]) & (df['datetime'].dt.date <= date_range[1])
if selected_country != "Wszystkie":
    mask &= (df['country'] == selected_country)
f_df = df.loc[mask]


map_lat, map_lon, map_zoom = 20, 0, 1.2
if selected_country != "Wszystkie" and not f_df.empty:
    map_lat = f_df['latitude'].mean()
    map_lon = f_df['longitude'].mean()
    map_zoom = 4
    st.sidebar.info(f"Fly-to: {selected_country}")


st.title("Wywiad zagrożeń AWS Honeypot")


total, unique, top_p, top_proto = data_loader.get_kpi_metrics(f_df)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Łącznie Ataków", f"{total:,}")
m2.metric("Unikalne IP", unique)
m3.metric("Najczęstszy Cel", top_p)
m4.metric("Główny Protokół", top_proto)

st.divider()

st.pydeck_chart(charts.plot_attack_map(f_df, map_lat, map_lon, map_zoom))

st.divider()

if not f_df.empty:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.plot_port_ranking(f_df), use_container_width=True)
    with c2:
        st.plotly_chart(charts.plot_proto_pie(f_df), use_container_width=True)
    
    st.plotly_chart(charts.plot_time_heatmap(f_df), use_container_width=True)
else:
    st.warning("Brak danych dla wybranych filtrów. Zmień zakres dat lub kraj.")