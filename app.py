import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import base64
from io import BytesIO

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Generador de Mosaicos", layout="wide")

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
    # --- Procesamiento ---
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
                rows.append({"x": x, "y": y, "tipo": tipo, "color_norm": normalizar_color(attrs.get("color", "")), "tamaño": attrs.get("tamaño", "")})
    
    df = pd.DataFrame(rows)
    df["color_norm"] = df.apply(ajustar_color_por_tipo, axis=1)
    df["color_plot"] = df["color_norm"].map(COLOR_CATALOG).fillna("gray")

    # --- Imagen a Base64 ---
    img = Image.open(img_file)
    width, height = img.size
    buffered = BytesIO()
    img_format = img.format if img.format else "JPEG"
    img.save(buffered, format=img_format)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    # --- Generación de Gráfico ---
    fig = go.Figure()
    for (t, c, tam), d_sub in df.groupby(["tipo", "color_norm", "tamaño"]):
        fig.add_trace(go.Scatter(
            x=d_sub["x"], y=d_sub["y"], mode="markers",
            marker=dict(color=d_sub["color_plot"].iloc[0], size=8, opacity=0.75, line=dict(width=1, color='white')),
            name=f"{t} {c} {tam}",
            hovertemplate=f"<b>{t}</b><br>{c} {tam}<extra></extra>"
        ))
    
    fig.add_layout_image(dict(source=f"data:image/{img_format.lower()};base64,{img_base64}", x=0, y=0, sizex=width, sizey=height, xref="x", yref="y", sizing="stretch", layer="below"))
    fig.update_layout(dragmode="pan", margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[0, width], visible=False, scaleanchor="y"), yaxis=dict(range=[height, 0], visible=False), uirevision=True)

    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    # ==========================================
    # GENERADOR DE HTML COMPLETO (OFFLINE)
    # ==========================================
    st.divider()
    
    # 1. Crear las tablas de resumen en formato HTML para el archivo
    conteo = df.groupby(["tipo", "color_norm", "tamaño"]).size().reset_index(name="Cant")
    tablas_html = ""
    for t in conteo["tipo"].unique():
        sub = conteo[conteo["tipo"] == t]
        tablas_html += f"<h5>Detalle de {t.upper()} (Total: {sub['Cant'].sum()})</h5>"
        tablas_html += sub[["color_norm", "tamaño", "Cant"]].to_html(classes='table table-striped table-sm', index=False, border=0)
        tablas_html += "<br>"

    # 2. Construir el documento HTML final
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mosaico Resultado</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
        <style>
            body {{ background-color: #f8f9fa; padding: 15px; }}
            .card {{ margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            #plot-container {{ width: 100%; height: 70vh; background: white; border-radius: 8px; overflow: hidden; }}
            .table {{ font-size: 0.85rem; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <h2 class="text-center my-3">💎 Resultado de Mosaico</h2>
            
            <div class="card">
                <div class="card-body p-0">
                    <div id="plot-container"></div>
                </div>
            </div>

            <div class="card">
                <div class="card-header bg-primary text-white">📊 Resumen de Componentes</div>
                <div class="card-body">
                    {tablas_html}
                    <hr>
                    <h4 class="text-end">Total General: {len(df)}</h4>
                </div>
            </div>
        </div>

        <script>
            var figure = {fig.to_json()};
            var config = {{ 
                responsive: true, 
                scrollZoom: true, 
                displayModeBar: false 
            }};
            Plotly.newPlot('plot-container', figure.data, figure.layout, config);
        </script>
    </body>
    </html>
    """

    st.download_button(
        label="📥 Descargar Reporte HTML Completo",
        data=html_template,
        file_name="reporte_mosaico.html",
        mime="text/html",
        help="Descarga un archivo único con el gráfico interactivo y todas las tablas."
    )

    # Resumen visual en la app (opcional, para ver mientras trabajas)
    with st.expander("Ver tablas en la App"):
        st.write(conteo)

else:
    st.info("Sube los archivos para generar el reporte.")

