import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import json
import time
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
- **API wttr.in** · Streamlit · Plotly · GeoJSON Venezuela
""")

# ==========================================
# COORDENADAS DE REFERENCIA (Capitales)
# ==========================================

ESTADOS = {
    "Amazonas":      (-5.6639,  -67.6236),
    "Anzoátegui":    (10.1362,  -64.6862),
    "Apure":         ( 7.8891,  -67.3443),
    "Aragua":        (10.2469,  -67.5958),
    "Barinas":       ( 8.6226,  -70.2075),
    "Bolívar":       ( 8.1222,  -63.5497),
    "Carabobo":      (10.1620,  -68.0077),
    "Cojedes":       ( 9.6226,  -68.9188),
    "Delta Amacuro": ( 8.8875,  -61.5922),
    "Falcón":        (11.4045,  -69.6734),
    "Guárico":       ( 9.9041,  -67.3538),
    "Lara":          (10.0678,  -69.3467),
    "Mérida":        ( 8.5897,  -71.1561),
    "Miranda":       (10.4880,  -66.8792),
    "Monagas":       ( 9.7477,  -63.1832),
    "Nueva Esparta": (10.9971,  -63.9113),
    "Portuguesa":    ( 9.5545,  -69.1956),
    "Sucre":         (10.4563,  -64.1675),
    "Táchira":       ( 7.7669,  -72.2250),
    "Trujillo":      ( 9.3653,  -70.4347),
    "La Guaira":     (10.6000,  -66.9333),
    "Yaracuy":       (10.3399,  -68.7425),
    "Zulia":         (10.6545,  -71.6533),
}

# ==========================================
# ADQUISICIÓN DE DATOS — API wttr.in
# (gratuita, sin key, funciona en la nube)
# ==========================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

def obtener_clima_wttr(estado, lat, lon):
    """Consulta wttr.in para una coordenada en español."""
    # Añadimos &lang=es para que la API traduzca la descripción del clima
    url = f"https://wttr.in/{lat},{lon}?format=j1&lang=es"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            cc = data["current_condition"][0]
            
            # wttr.in a veces devuelve la traducción en el campo "lang_es" 
            # si no existe, cae de maduro a "weatherDesc"
            clima_es = cc.get("lang_es", [{}])[0].get("value", None)
            if not clima_es:
                clima_es = cc["weatherDesc"][0]["value"]

            return {
                "Estado":      estado,
                "Latitud":     lat,
                "Longitud":    lon,
                "Temperatura": float(cc["temp_C"]),
                "Humedad":     int(cc["humidity"]),
                "Clima":       clima_es,  # <--- Guardamos el resultado en español
            }
    except Exception:
        pass
    return None

@st.cache_data(ttl=3600)
def cargar_datos():
    """Carga el clima de todos los estados. Pura: sin llamadas a st.*"""
    registros = []
    for estado, (lat, lon) in ESTADOS.items():
        dato = obtener_clima_wttr(estado, lat, lon)
        if dato:
            registros.append(dato)
        time.sleep(0.4)   # pausa educada entre peticiones
    return pd.DataFrame(registros)

# ==========================================
# BOTÓN DE ACTUALIZACIÓN
# ==========================================

if st.button("🔄 Actualizar Temperaturas"):
    st.cache_data.clear()
    st.rerun()

# ==========================================
# CARGA DE DATOS
# ==========================================

with st.spinner("🌐 Consultando temperaturas actuales..."):
    df = cargar_datos()

# ==========================================
# INDICADORES Y GRÁFICOS
# ==========================================

if df is not None and not df.empty:

    col1, col2, col3 = st.columns(3)
    temp_max  = df.loc[df["Temperatura"].idxmax()]
    temp_min  = df.loc[df["Temperatura"].idxmin()]
    temp_prom = round(df["Temperatura"].mean(), 1)

    with col1:
        st.metric("🔥 Estado Más Caluroso", temp_max["Estado"],
                  f"{temp_max['Temperatura']} °C")
    with col2:
        st.metric("❄️ Estado Más Fresco", temp_min["Estado"],
                  f"{temp_min['Temperatura']} °C")
    with col3:
        st.metric("📊 Promedio Nacional", f"{temp_prom} °C")

    st.divider()

    # ---- Tabla ------------------------------------------------
    st.subheader("📋 Temperaturas por Estado")
    df_ord = df.sort_values("Temperatura", ascending=False)
    st.dataframe(df_ord, width="stretch")

    # ---- Gráfico de barras ------------------------------------
    st.subheader("📈 Comparación de Temperaturas")
    fig_bar = px.bar(
        df_ord, x="Estado", y="Temperatura",
        color="Temperatura", text="Temperatura",
        color_continuous_scale="RdYlBu_r",
    )
    fig_bar.update_layout(
        xaxis_title="Estado", yaxis_title="Temperatura (°C)", height=600
    )
    st.plotly_chart(fig_bar, width="stretch", config={"displayModeBar": False})

    # ---- Mapa choropleth ------------------------------------
    st.subheader("🗺️ Mapa de Temperaturas")
    try:
        with open("venezuela_estados.geojson", "r", encoding="utf-8") as f:
            geojson = json.load(f)

        fig_map = px.choropleth(
            df, geojson=geojson,
            locations="Estado", featureidkey="properties.nombre",
            color="Temperatura", hover_name="Estado",
            color_continuous_scale="RdYlBu_r",
            title="Temperatura Actual por Estado",
            hover_data={"Temperatura": True, "Humedad": True, "Clima": True},
        )
        fig_map.update_geos(
            scope="south america",
            center=dict(lat=8.0, lon=-66.0),
            projection_scale=6,
            visible=True, showcountries=True,
            showland=True, landcolor="lightgray",
        )
        fig_map.update_layout(height=700, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig_map, width="stretch", config={"displayModeBar": False})

    except FileNotFoundError:
        fig_pts = px.scatter_geo(
            df, lat="Latitud", lon="Longitud",
            hover_name="Estado", text="Temperatura",
            hover_data={"Temperatura": True, "Humedad": True,
                        "Clima": True, "Latitud": False, "Longitud": False},
            title="Ubicación y Temperatura por Capital",
        )
        fig_pts.update_traces(textposition="top center",
                              marker=dict(size=12, color="red"))
        fig_pts.update_geos(
            scope="south america", center=dict(lat=8.0, lon=-66.0),
            projection_scale=6, visible=True, showcountries=True,
        )
        st.plotly_chart(fig_pts, width="stretch", config={"displayModeBar": False})

else:
    st.error(
        "❌ No se pudieron obtener datos meteorológicos. "
        "Verifica tu conexión e intenta de nuevo con **🔄 Actualizar Temperaturas**."
    )

# ==========================================
# PIE DE PÁGINA
# ==========================================

st.divider()
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.markdown("**Temperaturas de Venezuela** — Desarrollado con ❤️ usando Streamlit y Plotly")
with col_f2:
    st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
