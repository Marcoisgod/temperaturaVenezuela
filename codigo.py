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

- API Open-Meteo
- Streamlit
- Plotly
- GeoJSON de los estados de Venezuela
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

def interpretar_clima(codigo):
    tabla = {
        0:  "Despejado",
        1:  "Mayormente despejado",
        2:  "Parcialmente nublado",
        3:  "Nublado",
        45: "Neblina",
        48: "Niebla",
        51: "Llovizna ligera",
        61: "Lluvia ligera",
        63: "Lluvia moderada",
        65: "Lluvia fuerte",
        71: "Nevada ligera",
        80: "Chubascos",
        95: "Tormenta",
    }
    return tabla.get(codigo, "Sin datos")

# ==========================================
# ADQUISICIÓN DE DATOS — una sola petición
# batch a Open-Meteo con hasta 2 reintentos
# ==========================================

@st.cache_data(ttl=3600)
def cargar_datos():
    lats = ",".join(str(c[0]) for c in ESTADOS.values())
    lons = ",".join(str(c[1]) for c in ESTADOS.values())
    url  = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lats}&longitude={lons}"
        "&current=temperature_2m,relative_humidity_2m,weather_code"
        "&forecast_days=1"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }

    for intento in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                datos = r.json()
                if isinstance(datos, dict):
                    datos = [datos]
                registros = []
                for (estado, (lat, lon)), bloque in zip(ESTADOS.items(), datos):
                    cur = bloque.get("current", {})
                    registros.append({
                        "Estado":      estado,
                        "Latitud":     lat,
                        "Longitud":    lon,
                        "Temperatura": cur.get("temperature_2m"),
                        "Humedad":     cur.get("relative_humidity_2m"),
                        "Clima":       interpretar_clima(cur.get("weather_code")),
                    })
                return pd.DataFrame(registros)
            elif r.status_code == 429:
                # Rate-limit: espera y reintenta (máximo 2 veces)
                if intento < 2:
                    import time; time.sleep(30)
                continue
            else:
                return pd.DataFrame(), r.status_code
        except Exception as e:
            if intento == 2:
                return pd.DataFrame(), str(e)
            import time; time.sleep(10)

    return pd.DataFrame(), 429

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
    resultado = cargar_datos()

# cargar_datos() puede retornar un DataFrame solo (éxito)
# o una tupla (DataFrame_vacío, código_error) si falló
if isinstance(resultado, tuple):
    df, error = resultado
else:
    df    = resultado
    error = None

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
    st.plotly_chart(fig_bar, width="stretch")

    # ---- Mapa choropleth -------------------------------------
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
        st.plotly_chart(fig_map, width="stretch")

    except FileNotFoundError:
        # Mapa alternativo de puntos si no hay GeoJSON
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
            scope="south america",
            center=dict(lat=8.0, lon=-66.0),
            projection_scale=6, visible=True, showcountries=True,
        )
        st.plotly_chart(fig_pts, width="stretch")

else:
    if error == 429:
        st.warning(
            "⚠️ La API de clima tiene el acceso temporalmente limitado desde este servidor. "
            "Esto ocurre cuando muchas apps en Streamlit Cloud consultan la misma API al mismo tiempo. "
            "Espera unos minutos y presiona **🔄 Actualizar Temperaturas**."
        )
    else:
        st.error(
            f"❌ No se pudieron obtener datos meteorológicos. "
            f"Detalle: `{error}`. Revisa tu conexión e intenta de nuevo."
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
