import plotly.express as px
import pydeck as pdk
import pandas as pd

try:
    from pydeck.data_objects import FlyToInterpolator
    HAS_FLY_TO = True
except ImportError:
    HAS_FLY_TO = False

def style_chart(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=40, b=10)
    )
    return fig

def plot_attack_map(df, lat=20, lon=0, zoom=1):
    # 1. Usuwamy całkowicie puste rzędy
    map_df = df.dropna(subset=['latitude', 'longitude']).copy()
    
    # 2. TARCZA OCHRONNA: Zostawiamy tylko poprawne współrzędne kuli ziemskiej
    map_df = map_df[
        (map_df['latitude'] >= -90) & (map_df['latitude'] <= 90) &
        (map_df['longitude'] >= -180) & (map_df['longitude'] <= 180)
    ]
    
    transition_params = {
        "transitionDuration": 1500,
        "transitionInterp": FlyToInterpolator() if HAS_FLY_TO else None
    }
# ... (reszta funkcji pozostaje bez zmian)

    view_state = pdk.ViewState(
        latitude=lat, longitude=lon, zoom=zoom,
        pitch=45 if zoom > 2 else 0,
        bearing=0, **transition_params
    )

    layer = pdk.Layer(
        'ScatterplotLayer',
        data=map_df,
        get_position='[longitude, latitude]',
        get_color='[255, 0, 0, 150]',
        get_radius=50000 if zoom < 3 else 10000,
        pickable=True,
    )

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={"text": "Ataki w: {country}"}
    )

def plot_port_ranking(df):
    if df.empty: return px.bar(title="Brak danych")
    counts = df['service'].value_counts().head(10).reset_index()
    fig = px.bar(counts, x='count', y='service', orientation='h',
                 color='count', color_continuous_scale='Reds', title="Top 10 Portów")
    return style_chart(fig)

def plot_proto_pie(df):
    if df.empty: return px.pie(title="Brak danych")
    fig = px.pie(df, names='proto', hole=0.5, title="Protokoły",
                 color_discrete_sequence=px.colors.sequential.Reds_r)
    return style_chart(fig)

def plot_time_heatmap(df):
    if df.empty: return px.imshow([[0]], title="Brak danych")
    heatmap_data = df.groupby(['day_of_week', 'hour'], observed=True).size().unstack(fill_value=0)
    if heatmap_data.empty: return px.imshow([[0]], title="Brak danych")
    fig = px.imshow(heatmap_data, color_continuous_scale='YlOrRd',
                    labels=dict(x="Godzina", y="Dzień", color="Ataki"),
                    title="Intensywność czasowa")
    return style_chart(fig)


def plot_attack_trend(df):
    """Generuje interaktywny wykres liniowy przedstawiający trend liczby ataków w czasie."""
    if df.empty:
        return px.line(title="Brak danych")
    
    # Grupowanie danych po samej dacie (rok-miesiąc-dzień) i zliczanie wystąpień
    trend_df = df.groupby(df['datetime'].dt.date).size().reset_index(name='Liczba ataków')
    trend_df.columns = ['Data', 'Liczba ataków']
    trend_df = trend_df.sort_values('Data')
    
    # Tworzenie wykresu liniowego Plotly
    fig = px.line(
        trend_df,
        x='Data',
        y='Liczba ataków',
        title='Trend intensywności ataków w osi czasu',
        labels={'Data': 'Data zdarzenia', 'Liczba ataków': 'Suma zarejestrowanych ataków'},
        markers=True
    )
    
    # Stylizacja wykresu pod ciemny motyw interfejsu
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_gridcolor='#30363d',
        yaxis_gridcolor='#30363d',
        title_font_size=18,
        hovermode='x unified'
    )
    
    fig.update_traces(line_color='#00e5ff', line_width=3)
    
    return fig