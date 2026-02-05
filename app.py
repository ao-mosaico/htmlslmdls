import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO, StringIO

# ==========================================
# CONFIGURACIÓN DE PÁGINA (MOBILE OPTIMIZED)
# ==========================================
st.set_page_config(page_title="Generador de Mosaicos Pro", layout="wide")

# CSS para habilitar gestos táctiles y mejorar visualización
st.markdown("""
    <style>
    .reportview-container .main .block-container { padding-top: 1rem; }
    /* Forzamos que el gráfico acepte gestos de zoom con los dedos */
    .js-plotly-plot .plotly .main-svg {
        touch-action: pinch-zoom !important;
    }
    .stPlotlyChart { height: 75vh !important; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# CATÁLOGO Y FUNCIONES
# =========================
COLOR_CATALOG = {
    "plata": "silver", "dorado": "gold", "rosa": "pink",
    "ab_aguamarina": "aquamarine", "ab_amatista": "mediumpurple",
    "ab_cristal": "lightcyan", "ab_peridot": "lightgreen",
    "ab_rose": "lightpink", "ab_zafiro": "deepskyblue",
    "aguamarina": "turquoise", "amatista": "purple",
    "black_diamond": "black", "blue_zircon": "darkturquoise",
    "cristal": "silver", "fuschia": "fuchsia", "jet": "black",
    "jonquil": "gold", "opal_blue_zircone": "skyblue",
    "opal_green": "lightgreen", "peridot": "limegreen",
    "rose": "pink", "siam": "crimson", "topaz": "orange",
    "violet": "violet", "zafiro": "royalblue", "sin_color": "gray"
}

def normalizar_color(c):
    if pd.isna(c) or c == "": return "sin_color"
    return c.lower().strip().replace(" ", "_")

def ajustar_color_por_tipo(row):
    tipo, color = row["tipo"].lower(), row["color_norm"]
    if tipo == "balin" and color not in ["plata", "dorado"]: return "plata"
    if tipo == "dicroico" and color == "sin_color": return "rosa"
    return color

# =========================
# INTERFAZ LATERAL
# =========================
st.sidebar.title("💎 Panel de Control")
xml_file = st.sidebar.file_uploader("1. Subir XML", type=["xml"])
img_file = st.sidebar.file_uploader("2. Subir Imagen", type=["jpg", "png", "jpeg"])

if xml_file and img_file:
    # --- Procesamiento de Datos ---
    tree = ET.parse(xml_file)
    root = tree.getroot()
    rows = []
    for image in root.findall("image"):
        for points in image.findall("points"):
            coords = points.attrib["points"].split(";")
            tipo = points.attrib.get("label", "sin_tipo")
            attrs = {a.attrib["name"]: a.text for a in points.findall("attribute")}
            for c in coords:
                x, y = map(float, c.split(","))
                rows.append({
                    "x": x, "y": y, "tipo": tipo, 
                    "color_orig": attrs.get("color", "sin_color"), 
                    "tamaño": attrs.get("tamaño", "")
                })
    
    df = pd.DataFrame(rows)
    df["color_norm"] = df["color_orig"].apply(normalizar_color)
    df["color_norm"] = df.apply(ajustar_color_por_tipo, axis=1)
    df["color_plot"] = df["color_norm"].map(COLOR_CATALOG).fillna("gray")

    # Filtros
    st.sidebar.subheader("Filtros")
    tipos_disp = ["Todos"] + sorted(list(df["tipo"].unique()))
    tipo_sel = st.sidebar.selectbox("Tipo", tipos_disp)
    
    df_f = df.copy()
    if tipo_sel != "Todos": df_f = df_f[df_f["tipo"] == tipo_sel]

    # --- Imagen Base64 ---
    img = Image.open(img_file)
    width, height = img.size
    buffered = BytesIO()
    img_format = img.format if img.format else "JPEG"
    img.save(buffered, format=img_format)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    data_uri = f"data:image/{img_format.lower()};base64,{img_base64}"

    # =========================
    # CONSTRUCCIÓN DE FIGURA
    # =========================
    fig = go.Figure()
    
    for (t, c, tam), d_sub in df_f.groupby(["tipo", "color_norm", "tamaño"]):
        fig.add_trace(go.Scatter(
            x=d_sub["x"], y=d_sub["y"], mode="markers",
            marker=dict(color=d_sub["color_plot"].iloc[0], size=8, opacity=0.75,
                        line=dict(width=1, color='white')),
            name=f"{t} {c} {tam}",
            hovertemplate=f"<b>{t}</b><br>{c} {tam}<extra></extra>"
        ))

    fig.add_layout_image(dict(
        source=data_uri, x=0, y=0, sizex=width, sizey=height,
        xref="x", yref="y", sizing="stretch", layer="below"
    ))

    # CONFIGURACIÓN DE INTERACCIÓN
    fig.update_layout(
        dragmode="pan",  # Permite mover la imagen con un dedo
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(range=[0, width], visible=False, scaleanchor="y"),
        yaxis=dict(range=[height, 0], visible=False),
        showlegend=False,
        uirevision=True
    )

    # Mostrar en la App con soporte de gestos táctiles
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,        # ACTIVA ZOOM CON DEDOS (PINCH)
        'displayModeBar': False,   # Limpia la interfaz en móvil
        'doubleClick': 'reset'     # Doble toque para resetear zoom
    })

    # ==========================================
    # BOTÓN DE EXPORTACIÓN (CON GESTOS ACTIVOS)
    # ==========================================
    st.divider()
    st.subheader("📤 Exportar para Google Sites")
    
    html_buffer = StringIO()
    # Guardamos el HTML incluyendo la configuración de scrollZoom
    fig.write_html(html_buffer, include_plotlyjs='cdn', full_html=True, config={
        'scrollZoom': True,
        'displayModeBar': False
    })
    
    st.download_button(
        label="💾 Descargar HTML para Sites",
        data=html_buffer.getvalue(),
        file_name="mosaico_zoom_tactil.html",
        mime="text/html"
    )

    # =========================
    # RESUMEN DE COMPONENTES
    # =========================
    st.subheader("📊 Resumen de Componentes")
    if not df_f.empty:
        conteo = df_f.groupby(["tipo", "color_norm", "tamaño"]).size().reset_index(name="Cantidad")
        for t_en_conteo in conteo["tipo"].unique():
            sub_c = conteo[conteo["tipo"] == t_en_conteo]
            total_cat = sub_c["Cantidad"].sum()
            with st.expander(f"Detalle de {t_en_conteo.upper()} = {total_cat}", expanded=True):
                st.table(sub_c[["color_norm", "tamaño", "Cantidad"]])
        st.metric("Total visible", len(df_f))

else:
    st.warning("⚠️ Sube los archivos en el panel lateral.")
