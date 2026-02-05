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
st.set_page_config(page_title="Gestor de Mosaicos Pro", layout="wide")

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
    # --- Procesamiento XML ---
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

    # --- Imagen Base64 ---
    img = Image.open(img_file)
    width, height = img.size
    buffered = BytesIO()
    img_format = img.format if img.format else "JPEG"
    img.save(buffered, format=img_format)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    data_uri = f"data:image/{img_format.lower()};base64,{img_base64}"

    # --- Gráfico ---
    fig = go.Figure()
    
    # Creamos las trazas
    for (t, c, tam), d_sub in df.groupby(["tipo", "color_norm", "tamaño"]):
        fig.add_trace(go.Scatter(
            x=d_sub["x"].tolist(), 
            y=d_sub["y"].tolist(), 
            mode="markers",
            marker=dict(color=d_sub["color_plot"].iloc[0], size=8, opacity=0.8, line=dict(width=1, color='white')),
            name=f"{t} {c} {tam}",
            customdata=[t]*len(d_sub),
            hovertemplate=f"<b>{t}</b><br>{c} {tam}<extra></extra>"
        ))
    
    fig.add_layout_image(dict(source=data_uri, x=0, y=0, sizex=width, sizey=height, xref="x", yref="y", sizing="stretch", layer="below"))
    
    fig.update_layout(
        dragmode="pan", 
        margin=dict(l=0, r=0, t=0, b=0), 
        xaxis=dict(range=[0, width], visible=False, scaleanchor="y"), 
        yaxis=dict(range=[height, 0], visible=False),
        uirevision=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Preparación HTML ---
    # Convertimos los datos de las trazas a JSON limpio para JS
    traces_json = json.dumps([t.to_plotly_json() for t in fig.data])
    layout_json = fig.layout.to_json()
    tipos_unicos = sorted(df["tipo"].unique().tolist())
    conteo_json = df.groupby(["tipo", "color_norm", "tamaño"]).size().reset_index(name="Cant").to_json(orient='records')

    # HTML Template
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte de Mosaico</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
        <style>
            body {{ background-color: #f0f2f6; padding: 10px; }}
            #plot-area {{ width: 100%; height: 60vh; background: #fff; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); overflow: hidden; }}
            .filter-btn {{ margin: 2px; font-size: 0.8rem; }}
            .summary-card {{ background: white; border-radius: 10px; padding: 15px; margin-top: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .table {{ font-size: 0.85rem; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <h5 class="mb-3 text-primary">💎 Filtros por Tipo:</h5>
            <div class="mb-3">
                <button class="btn btn-dark btn-sm filter-btn" onclick="filterData('all')">VER TODOS</button>
                {' '.join([f'<button class="btn btn-primary btn-sm filter-btn" onclick="filterData(\'{t}\')">{t.upper()}</button>' for t in tipos_unicos])}
            </div>

            <div id="plot-area"></div>

            <div class="summary-card">
                <div id="tables-container"></div>
                <hr>
                <h4 class="text-end" id="total-val">Total: {len(df)}</h4>
            </div>
        </div>

        <script>
            const fullTraces = {traces_json};
            const layout = {layout_json};
            const tableData = {conteo_json};
            const config = {{ responsive: true, scrollZoom: true, displayModeBar: false }};

            // Renderizado Inicial
            Plotly.newPlot('plot-area', fullTraces, layout, config);

            function filterData(tipo) {{
                const newTraces = [];
                fullTraces.forEach(trace => {{
                    // Filtramos basándonos en si el nombre empieza por el tipo seleccionado
                    if (tipo === 'all' || trace.name.toLowerCase().startsWith(tipo.toLowerCase())) {{
                        trace.visible = true;
                    }} else {{
                        trace.visible = 'legendonly';
                    }}
                }});
                
                Plotly.react('plot-area', fullTraces, layout, config);
                renderTables(tipo);
            }}

            function renderTables(tipo) {{
                const container = document.getElementById('tables-container');
                const filtered = tableData.filter(d => tipo === 'all' || d.tipo === tipo);
                const total = filtered.reduce((acc, curr) => acc + curr.Cant, 0);
                
                let html = '';
                const groups = {{}};
                filtered.forEach(d => {{
                    if (!groups[d.tipo]) groups[d.tipo] = [];
                    groups[d.tipo].push(d);
                }});

                for (const t in groups) {{
                    const subTotal = groups[t].reduce((a, b) => a + b.Cant, 0);
                    html += `<h6><b>${{t.toUpperCase()}} (Total: ${{subTotal}})</b></h6>
                            <table class="table table-striped table-sm mb-3">
                                <thead class="table-light"><tr><th>Color</th><th>Tamaño</th><th>Cant.</th></tr></thead>
                                <tbody>`;
                    groups[t].forEach(row => {{
                        html += `<tr><td>${{row.color_norm}}</td><td>${{row.tamaño}}</td><td>${{row.Cant}}</td></tr>`;
                    }});
                    html += `</tbody></table>`;
                }}
                container.innerHTML = html;
                document.getElementById('total-val').innerText = 'Total: ' + total;
            }}

            // Carga inicial de tablas
            renderTables('all');
        </script>
    </body>
    </html>
    """

    st.divider()
    st.download_button(
        label="📥 DESCARGAR REPORTE HTML FINAL",
        data=html_report,
        file_name=f"Reporte_{img_file.name.split('.')[0]}.html",
        mime="text/html"
    )

else:
    st.info("Sube los archivos XML e Imagen para generar el reporte descargable.")



