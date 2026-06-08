import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# ======================================
# CONFIG
# ======================================

st.set_page_config(
    page_title="Weather Venezuela PRO",
    page_icon="🌤️",
    layout="wide"
)

st.title("🌦️ Venezuela Weather Dashboard PRO")

# ======================================
# PRUEBA DIRECTA API
# ======================================

st.subheader("🔍 Diagnóstico Open-Meteo")

try:

    test_url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=10.5"
        "&longitude=-66.9"
        "&current=temperature_2m,relative_humidity_2m,weather_code"
    )

    test = requests.get(test_url, timeout=15)

    st.write("Código HTTP:", test.status_code)

    if test.status_code == 200:
        st.success("La API responde correctamente")
        st.json(test.json())
    else:
        st.error("La API devolvió un error")
        st.code(test.text)

except Exception as e:
    st.error(f"Error de conexión: {e}")

# ======================================
# ESTADOS
# ======================================

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

# ======================================
# CLIMA
# ======================================

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

# ======================================
# OBTENER UN ESTADO
# ======================================

def obtener_estado(estado, lat, lon):

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,weather_code"
    )

    try:

        r = requests.get(
            url,
            timeout=15
        )

        if r.status_code != 200:

            st.warning(
                f"{estado}: HTTP {r.status_code}"
            )

            return None

        datos = r.json()

        if "current" not in datos:

            st.warning(
                f"{estado}: no existe 'current'"
            )

            st.json(datos)

            return None

        current = datos["current"]

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

    except Exception as e:

        st.error(
            f"{estado}: {e}"
        )

        return None

# ======================================
# CARGAR DATOS
# ======================================

@st.cache_data(ttl=1800)
def cargar_datos():

    registros = []

    for estado, (lat, lon) in ESTADOS.items():

        dato = obtener_estado(
            estado,
            lat,
            lon
        )

        if dato:
            registros.append(dato)

    return pd.DataFrame(registros)

# ======================================
# BOTÓN
# ======================================

if st.button("🔄 Actualizar"):

    st.cache_data.clear()

# ======================================
# CARGA
# ======================================

df = cargar_datos()

# ======================================
# RESULTADOS
# ======================================

st.subheader("📊 DataFrame obtenido")

st.write(df)

if df.empty:

    st.error(
        "No fue posible obtener datos climáticos."
    )

else:

    st.success(
        f"Estados cargados: {len(df)}"
    )

    fig = px.scatter_geo(
        df,
        lat="Latitud",
        lon="Longitud",
        hover_name="Estado",
        color="Temperatura",
        size="Temperatura"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

st.divider()

st.caption(
    f"Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
)
