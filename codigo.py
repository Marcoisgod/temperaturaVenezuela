import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import json
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================

st.set_page_config(
    page_title="Temperaturas de Venezuela",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ Temperaturas Actuales por Estado de Venezuela")
st.markdown("""
Sistema de adquisición de datos meteorológicos en tiempo real utilizando:

- API Open-Meteo (Petición masiva optimizada)
- Streamlit
- Plotly
- GeoJSON de los estados de Venezuela
""")

# ==========================================
# COORDENADAS DE REFERENCIA
# (Capitales de estados)
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
# ADQUISICIÓN DE DATOS MASIVA (OPTIMIZADA)
# ==========================================

@st.cache_data(ttl=600)
def cargar_datos_masivos():
    # Extraemos y agrupamos todas las latitudes y longitudes en cadenas separadas por comas
    lats = ",".join([str(coords[0]) for coords in ESTADOS.values()])
    lons = ",".join([str(coords[1]) for coords in ESTADOS.values()])
    
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lats}"
        f"&longitude={lons}"
        f"&current=temperature_2m,relative_humidity_2m,weather_code"
    )
    
    registros = []
    
    try:
        respuesta = requests.get(url, timeout=15)
        if respuesta.status_code == 200:
            datos_api = respuesta.json()
            
            # Si se consulta más de una coordenada, Open-Meteo devuelve una lista de diccionarios
            # Si es solo una devuelve un diccionario plano. Validamos esto:
            if isinstance(datos_api, dict):
                datos_lista = [datos_api]
            else:
                datos_lista = datos_api
                
            for i, (estado, (lat, lon)) in enumerate(ESTADOS.items()):
                current_data = datos_lista[i]["current"]
                registros.append({
                    "Estado": estado,
                    "Latitud": lat,
                    "Longitud": lon,
                    "Temperatura": current_data["temperature_2m"],
                    "Humedad": current_data["relative_humidity_2m"],
                    "Clima": interpretar_clima(current_data["weather_code"])
                })
        else:
            st.error(f"Error de la API de clima. Código de respuesta: {respuesta.status_code}")
    except Exception as e:
        st.error(f"Ocurrió un error en la conexión de red: {e}")
        
    return pd.DataFrame(registros)

# ==========================================
# BOTÓN DE ACTUALIZACIÓN
# ==========================================

if st.button("🔄 Actualizar Temperaturas"):
    st.cache_data.clear()

# ==========================================
# CARGA DE DATOS
# ==========================================

with st.spinner("Consultando temperaturas actuales en tiempo real..."):
    df = cargar_datos_masivos()

# ==========================================
# INDICADORES Y GRÁFICOS
# ==========================================

if not df.empty:
    col1, col2, col3 = st.columns(3)

    temp_max = df.loc[df["Temperatura"].idxmax()]
    temp_min = df.loc[df["Temperatura"].idxmin()]
    temp_prom = round(df["Temperatura"].mean(), 1)

    with col1:
        st.metric(
            "🔥 Estado Más Caluroso",
            temp_max["Estado"],
            f"{temp_max['Temperatura']} °C"
        )

    with col2:
        st.metric(
            "❄️ Estado Más Fresco",
            temp_min["Estado"],
            f"{temp_min['Temperatura']} °C"
        )

    with col3:
        st.metric(
            "📊 Promedio Nacional",
            f"{temp_prom} °C"
        )

    st.divider()

    # ==========================================
    # TABLA DE DATOS
    # ==========================================

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
        xaxis_title="Estado",
        yaxis_title="Temperatura (°C)",
        height=600
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================================
    # MAPA DE VENEZUELA (CHOROPLETH)
    # ==========================================
    
    geojson_cargado = False
    try:
        with open("venezuela_estados.geojson", "r", encoding="utf-8") as archivo:
            geojson = json.load(archivo)
        
        fig = px.choropleth(
            df,
            geojson=geojson,
            locations="Estado",
            featureidkey="properties.nombre", 
            color="Temperatura",
            hover_name="Estado",
            color_continuous_scale="RdYlBu_r",
            title="Temperatura Actual por Estado", 
            hover_data={
                "Temperatura": True,
                "Humedad": True,
                "Clima": True
            }
        )

        fig.update_geos(
            scope="south america",
            center=dict(lat=8.0, lon=-66.0),
            projection_scale=6,
            visible=True,
            showcountries=True,
            showland=True,
            landcolor="lightgray"
        )

        fig.update_layout(
            height=700,
            margin=dict(l=0, r=0, t=50, b=0)
        )

        st.plotly_chart(fig, use_container_width=True)
        geojson_cargado = True

    except FileNotFoundError:
        st.warning("""
        ⚠️ No se encontró el archivo **venezuela_estados.geojson** para el mapa regional. 
        Mostrando mapa alternativo por puntos de coordenadas.
        """)

    # ==========================================
    # MAPA ALTERNATIVO
    # ==========================================
    if not geojson_cargado:
        fig_puntos = px.scatter_geo(
            df,
            lat="Latitud",
            lon="Longitud",
            hover_name="Estado",
            hover_data={
                "Temperatura": True,
                "Humedad": True,
                "Clima": True,
                "Latitud": False,
                "Longitud": False
            },
            text="Temperatura",
            title="Ubicación y Temperatura por Capital"
        )

        fig_puntos.update_traces(
            textposition="top center",
            marker=dict(size=12, color="red")
        )

        fig_puntos.update_geos(
            scope="south america",
            center=dict(lat=8.0, lon=-66.0),
            projection_scale=6,
            visible=True,
            showcountries=True
        )

        st.plotly_chart(fig_puntos, use_container_width=True)

else:
    st.error("No se pudieron recopilar datos climáticos en este momento. La estructura de respuesta falló.")

# ==========================================
# PIE DE PÁGINA
# ==========================================

st.divider()

col_foot1, col_foot2 = st.columns(2)

with col_foot1:
    st.markdown("**Temperaturas de Venezuela** - Desarrollado con ❤️ usando Streamlit y Plotly")

with col_foot2:
    st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
