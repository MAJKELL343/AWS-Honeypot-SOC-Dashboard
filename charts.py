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
    map_df = df.dropna(subset=['latitude', 'longitude'])
    
    transition_params = {
        "transitionDuration": 1500,
        "transitionInterp": FlyToInterpolator() if HAS_FLY_TO else None
    }

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