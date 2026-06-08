import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================

st.set_page_config(
    page_title="Temperaturas de Venezuela PRO",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ Temperaturas Actuales por Estado de Venezuela")

st.markdown("""
Sistema de monitoreo climático en tiempo real utilizando:

- Open-Meteo API
- Streamlit
- Plotly
- Consultas paralelas optimizadas
""")

# ==========================================
# ESTADOS Y COORDENADAS
# ==========================================

ESTADOS = {
    "Amazonas": (-5.6639, -67.6236),
    "Anzoátegui": (10.1362, -64.6862),
    "Apure": (7.8891, -67.3443),
    "Aragua": (10.2469, -67.5958),
    "Barinas": (8.6226, -70.2075),
    "Bolívar": (8.1222, -63.5497),
    "Carabobo": (10.1620, -68.0077),
    "Cojedes": (9.6226, -68.9188),
    "Delta Amacuro": (8.8875, -61.5922),
    "Falcón": (11.4045, -69.6734),
    "Guárico": (9.9041, -67.3538),
    "Lara": (10.0678, -69.3467),
    "Mérida": (8.5897, -71.1561),
    "Miranda": (10.4880, -66.8792),
    "Monagas": (9.7477, -63.1832),
    "Nueva Esparta": (10.9971, -63.9113),
    "Portuguesa": (9.5545, -69.1956),
    "Sucre": (10.4563, -64.1675),
    "Táchira": (7.7669, -72.2250),
    "Trujillo": (9.3653, -70.4347),
    "La Guaira": (10.6000, -66.9333),
    "Yaracuy": (10.3399, -68.7425),
    "Zulia": (10.6545, -71.6533)
}

# ==========================================
# INTERPRETAR CLIMA
# ==========================================

def interpretar_clima(codigo):

    clima = {
        0: "Despejado",
        1: "Mayormente despejado",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Neblina",
        48: "Niebla",
        51: "Llovizna ligera",
        61: "Lluvia ligera",
        63: "Lluvia moderada",
        65: "Lluvia fuerte",
        71: "Nevada ligera",
        80: "Chubascos",
        95: "Tormenta"
    }

    return clima.get(codigo, "Sin datos")

# ==========================================
# CONSULTA DE UN ESTADO
# ==========================================

def obtener_estado(datos):

    estado, (lat, lon) = datos

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,weather_code"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if r.status_code != 200:
            return None

        datos_api = r.json()

        current = datos_api["current"]

        return {
            "Estado": estado,
            "Latitud": lat,
            "Longitud": lon,
            "Temperatura": current["temperature_2m"],
            "Humedad": current["relative_humidity_2m"],
            "Clima": interpretar_clima(
                current["weather_code"]
            )
        }

    except:
        return None

# ==========================================
# CARGA MASIVA
# ==========================================

@st.cache_data(ttl=1800)
def cargar_datos():

    registros = []

    with ThreadPoolExecutor(max_workers=10) as executor:

        resultados = executor.map(
            obtener_estado,
            ESTADOS.items()
        )

        for resultado in resultados:

            if resultado is not None:
                registros.append(resultado)

    return pd.DataFrame(registros)

# ==========================================
# BOTÓN ACTUALIZAR
# ==========================================

if st.button("🔄 Actualizar Datos"):

    st.cache_data.clear()
    st.rerun()

# ==========================================
# CARGA DE DATOS
# ==========================================

with st.spinner("Consultando datos meteorológicos..."):

    df = cargar_datos()

# ==========================================
# VALIDACIÓN
# ==========================================

if df.empty:

    st.error(
        "No fue posible obtener datos climáticos."
    )

    st.stop()

# ==========================================
# MÉTRICAS
# ==========================================

st.divider()

col1, col2, col3 = st.columns(3)

temp_max = df.loc[df["Temperatura"].idxmax()]
temp_min = df.loc[df["Temperatura"].idxmin()]
temp_prom = round(df["Temperatura"].mean(), 1)

with col1:

    st.metric(
        "🔥 Más Caluroso",
        temp_max["Estado"],
        f"{temp_max['Temperatura']} °C"
    )

with col2:

    st.metric(
        "❄️ Más Fresco",
        temp_min["Estado"],
        f"{temp_min['Temperatura']} °C"
    )

with col3:

    st.metric(
        "📊 Promedio Nacional",
        f"{temp_prom} °C"
    )

# ==========================================
# TABLA
# ==========================================

st.divider()

st.subheader("📋 Temperaturas por Estado")

df_ordenado = df.sort_values(
    by="Temperatura",
    ascending=False
)

st.dataframe(
    df_ordenado,
    use_container_width=True
)

# ==========================================
# GRÁFICO DE BARRAS
# ==========================================

st.divider()

st.subheader("📈 Comparación de Temperaturas")

fig_bar = px.bar(
    df_ordenado,
    x="Estado",
    y="Temperatura",
    color="Temperatura",
    text="Temperatura",
    color_continuous_scale="RdYlBu_r"
)

fig_bar.update_layout(
    height=600,
    xaxis_title="Estado",
    yaxis_title="Temperatura (°C)"
)

st.plotly_chart(
    fig_bar,
    use_container_width=True
)

# ==========================================
# MAPA
# ==========================================

st.divider()

st.subheader("🗺️ Temperaturas de Venezuela")

fig_mapa = px.scatter_geo(
    df,
    lat="Latitud",
    lon="Longitud",
    color="Temperatura",
    size="Temperatura",
    hover_name="Estado",
    hover_data={
        "Humedad": True,
        "Clima": True,
        "Latitud": False,
        "Longitud": False
    },
    projection="natural earth",
    color_continuous_scale="RdYlBu_r"
)

fig_mapa.update_geos(
    scope="south america",
    center=dict(lat=8, lon=-66),
    projection_scale=6,
    showcountries=True,
    showland=True
)

fig_mapa.update_layout(
    height=700
)

st.plotly_chart(
    fig_mapa,
    use_container_width=True
)

# ==========================================
# PIE DE PÁGINA
# ==========================================

st.divider()

col1, col2 = st.columns(2)

with col1:

    st.markdown(
        "**Dashboard Climático Venezuela PRO**"
    )

with col2:

    st.caption(
        f"Última actualización: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
