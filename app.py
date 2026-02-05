import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import base64
import json
from io import BytesIO

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(page_title="Generador de Mosaicos", layout="wide")

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
# INTERFAZ
# =========================
st.sidebar.title("💎 Panel de Control")
xml_file = st.sidebar.file_uploader("1. Subir XML", type=["xml"])
img_file = st.sidebar.file_uploader("2. Subir Imagen", type=["jpg", "png", "jpeg"])

if xml_file and img_file:
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
                    "color_norm": normalizar_color(attrs.get("color", "")), 
                    "tamaño": attrs.get("tamaño", "")
                })
    
    df = pd.DataFrame(rows)
    df["color_norm"] = df.apply(ajustar_color_por_tipo, axis=1)
    df["color_plot"] = df["color_norm"].map(COLOR_CATALOG).fillna("gray")

    # Imagen
    img = Image.open(img_file)
    width, height = img.size
    buffered = BytesIO()
    img_format = img.format if img.format else "JPEG"
    img.save(buffered, format=img_format)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    # --- Gráfico ---
    fig = go.Figure()
    for (t, c, tam), d_sub in df.groupby(["tipo", "color_norm", "tamaño"]):
        fig.add_trace(go.Scatter(
            x=d_sub["x"], y=d_sub["y"], mode="markers",
            marker=dict(color=d_sub["color_plot"].iloc[0], size=8, opacity=0.75, line=dict(width=1, color='white')),
            name=f"{t} {c} {tam}",
            customdata=[t]*len(d_sub), # Guardamos el tipo para el filtro JS
            hovertemplate=f"<b>{t}</b><br>{c} {tam}<extra></extra>"
        ))
    
    fig.add_layout_image(dict(source=f"data:image/{img_format.lower()};base64,{img_base64}", x=0, y=0, sizex=width, sizey=height, xref="x", yref="y", sizing="stretch", layer="below"))
    fig.update_layout(dragmode="pan", margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[0, width], visible=False, scaleanchor="y"), yaxis=dict(range=[height, 0], visible=False))

    st.plotly_chart(fig, use_container_width=True)

    # --- Generación de Reporte HTML ---
    tipos_unicos = sorted(df["tipo"].unique().tolist())
    conteo = df.groupby(["tipo", "color_norm", "tamaño"]).size().reset_index(name="Cant")
    
    # HTML Dinámico
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte Interactivo</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
        <style>
            body {{ background-color: #f4f4f9; padding: 10px; font-family: sans-serif; }}
            .card {{ margin-bottom: 15px; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            #plot-container {{ width: 100%; height: 65vh; background: white; }}
            .btn-group-wrap {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }}
            .table-container {{ font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <h4 class="text-center my-2">Mosaico: {img_file.name}</h4>
            
            <div class="btn-group-wrap">
                <button class="btn btn-dark btn-sm" onclick="filterType('all')">Todos</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm" onclick="filterType(\'{t}\')">{t}</button>' for t in tipos_unicos])}
            </div>

            <div class="card p-0">
                <div id="plot-container"></div>
            </div>

            <div class="card p-3">
                <div id="resumen-container" class="table-container">
                    </div>
                <hr>
                <h5 class="text-end" id="total-general">Total: {len(df)}</h5>
            </div>
        </div>

        <script>
            var plotData = {fig.to_json()};
            var fullData = plotData.data;
            var layout = plotData.layout;
            var config = {{ responsive: true, scrollZoom: true, displayModeBar: false }};
            
            // Inicializar gráfico
            Plotly.newPlot('plot-container', fullData, layout, config);

            // Datos para las tablas
            var tableData = {conteo.to_json(orient='records')};

            function filterType(tipo) {{
                var update = [];
                var visibleIndices = [];
                
                fullData.forEach((trace, index) => {{
                    var isVisible = (tipo === 'all' || trace.name.startsWith(tipo));
                    update.push(isVisible ? true : 'legendonly');
                }});
                
                Plotly.restyle('plot-container', {{ 'visible': update }});
                updateTables(tipo);
            }}

            function updateTables(tipo) {{
                var container = document.getElementById('resumen-container');
                var totalEl = document.getElementById('total-general');
                var filtered = tableData.filter(d => tipo === 'all' || d.tipo === tipo);
                var totalSum = filtered.reduce((a, b) => a + b.Cant, 0);
                
                var html = '';
                var grouped = {{}};
                filtered.forEach(d => {{
                    if(!grouped[d.tipo]) grouped[d.tipo] = [];
                    grouped[d.tipo].push(d);
                }});

                for(var t in grouped) {{
                    var catSum = grouped[t].reduce((a, b) => a + b.Cant, 0);
                    html += `<h6><b>${{t.toUpperCase()}} (Total: ${{catSum}})</b></h6>
                             <table class="table table-sm table-striped">
                             <thead><tr><th>Color</th><th>Tam</th><th>Cant</th></tr></thead><tbody>`;
                    grouped[t].forEach(d => {{
                        html += `<tr><td>${{d.color_norm}}</td><td>${{d.tamaño}}</td><td>${{d.Cant}}</td></tr>`;
                    }});
                    html += '</tbody></table>';
                }}
                container.innerHTML = html;
                totalEl.innerHTML = 'Total Visible: ' + totalSum;
            }}

            // Cargar tablas iniciales
            updateTables('all');
        </script>
    </body>
    </html>
    """

    st.download_button(
        label="📥 Descargar Reporte Interactivo Full",
        data=html_template,
        file_name=f"Reporte_{img_file.name}.html",
        mime="text/html"
    )

else:
    st.info("Sube los archivos para generar el reporte descargable.")


