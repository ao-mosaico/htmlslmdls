import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objects as go
from PIL import Image

# ==========================================
# CONFIGURACIÓN DE PÁGINA (MOBILE FIRST)
# ==========================================
st.set_page_config(page_title="Gestor de Joyas", layout="wide")

# Estilo para maximizar el espacio en móviles
st.markdown("""
    <style>
    .reportview-container .main .block-container { padding-top: 1rem; }
    .stPlotlyChart { height: 70vh !important; }
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

    # --- Filtros Nativos ---
    st.sidebar.subheader("Filtros de Vista")
    tipos_disp = ["Todos"] + sorted(list(df["tipo"].unique()))
    tipo_sel = st.sidebar.selectbox("Filtrar por Tipo", tipos_disp)
    
    colores_disp = ["Todos"] + sorted(list(df["color_norm"].unique()))
    color_sel = st.sidebar.selectbox("Filtrar por Color", colores_disp)

    # Aplicar filtros
    df_f = df.copy()
    if tipo_sel != "Todos": df_f = df_f[df_f["tipo"] == tipo_sel]
    if color_sel != "Todos": df_f = df_f[df_f["color_norm"] == color_sel]

    # =========================
    # CONSTRUCCIÓN DE FIGURA
    # =========================
    # ESTA ES LA LÍNEA 93 QUE DABA ERROR:
    img = Image.open(img_file)
    width, height = img.size

    fig = go.Figure()
    
    # Agrupamos para crear las trazas
    if not df_f.empty:
        for (t, c, tam), d_sub in df_f.groupby(["tipo", "color_norm", "tamaño"]):
            hover_text = f"<b>{t}</b><br>{c} {tam}<extra></extra>"
            
            fig.add_trace(go.Scatter(
                x=d_sub["x"], 
                y=d_sub["y"], 
                mode="markers",
                marker=dict(
                    color=d_sub["color_plot"].iloc[0], 
                    size=8, 
                    opacity=0.75,
                    line=dict(width=1, color='white')
                ),
                name=f"{t} {c} {tam}",
                hovertemplate=hover_text
            ))

    # Imagen de Fondo
    fig.add_layout_image(dict(
        source=img, x=0, y=0, sizex=width, sizey=height,
        xref="x", yref="y", sizing="stretch", layer="below"
    ))

    # Layout Ajustado
    fig.update_layout(
        dragmode="pan",
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(range=[0, width], visible=False, scaleanchor="y"),
        yaxis=dict(range=[height, 0], visible=False),
        showlegend=False,
        uirevision=True
    )

    # Mostrar Gráfico
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,
        'displayModeBar': False
    })

    # =========================
    # RESUMEN DE COMPONENTES
    # =========================
    st.subheader("📊 Resumen de Componentes")
    
    if not df_f.empty:
        # 1. Agrupamos los datos
        conteo = df_f.groupby(["tipo", "color_norm", "tamaño"]).size().reset_index(name="Cantidad")
        
        # 2. Generamos los desplegables por tipo
        for t_en_conteo in conteo["tipo"].unique():
            # Filtramos el conteo solo para este tipo (ej. Balín)
            sub_c = conteo[conteo["tipo"] == t_en_conteo]
            
            # CALCULAMOS EL TOTAL DE ESTE TIPO
            total_categoria = sub_c["Cantidad"].sum()
            
            # CREAMOS EL TÍTULO DINÁMICO: "Detalle de CRISTAL (Total: 163)"
            titulo_desplegable = f"Detalle de {t_en_conteo.upper()} (Total: {total_categoria})"
            
            with st.expander(titulo_desplegable, expanded=True):
                # Mostramos la tabla limpia
                st.table(sub_c[["color_norm", "tamaño", "Cantidad"]])

        # Métrica general al final
        st.divider()
        st.metric("TOTAL GENERAL VISIBLE", len(df_f))
    else:
        st.write("No hay elementos con los filtros seleccionados.")