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
# INTERFAZ LATERAL
# =========================
st.sidebar.title("💎 Panel de Control")
nombre_modelo = st.sidebar.text_input("Nombre del Modelo / Pieza", placeholder="Ej: Collar Primavera")
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

    # --- Filtros en la App ---
    st.subheader(f"Modelo: {nombre_modelo if nombre_modelo else 'Sin nombre'}")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tipo_filtro = st.multiselect("Filtrar por Tipo (App)", options=sorted(df["tipo"].unique()), default=sorted(df["tipo"].unique()))
    with col_f2:
        color_filtro = st.multiselect("Filtrar por Color (App)", options=sorted(df["color_norm"].unique()), default=sorted(df["color_norm"].unique()))

    df_app = df[(df["tipo"].isin(tipo_filtro)) & (df["color_norm"].isin(color_filtro))]

    # --- Imagen Base64 ---
    img = Image.open(img_file)
    width, height = img.size
    buffered = BytesIO()
    img_format = img.format if img.format else "JPEG"
    img.save(buffered, format=img_format)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    data_uri = f"data:image/{img_format.lower()};base64,{img_base64}"

    # --- Gráfico Principal (Vista App) ---
    fig = go.Figure()
    for (t, c, tam), d_sub in df_app.groupby(["tipo", "color_norm", "tamaño"]):
        fig.add_trace(go.Scatter(
            x=d_sub["x"].tolist(), y=d_sub["y"].tolist(), mode="markers",
            marker=dict(color=d_sub["color_plot"].iloc[0], size=8, opacity=0.8, line=dict(width=1, color='white')),
            name=f"{t} {c} {tam}",
            customdata=[{"tipo": t, "color": c}] * len(d_sub),
            hovertemplate=f"<b>{t}</b><br>{c} {tam}<extra></extra>"
        ))
    
    fig.add_layout_image(dict(source=data_uri, x=0, y=0, sizex=width, sizey=height, xref="x", yref="y", sizing="stretch", layer="below"))
    fig.update_layout(dragmode="pan", margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[0, width], visible=False, scaleanchor="y"), yaxis=dict(range=[height, 0], visible=False))

    st.plotly_chart(fig, use_container_width=True)

    # --- Tablas de Resumen en la App ---
    st.markdown("### 📊 Resumen de Materiales (App)")
    if not df_app.empty:
        conteo_app = df_app.groupby(["tipo", "color_norm", "tamaño"]).size().reset_index(name="Cant")
        for t in conteo_app["tipo"].unique():
            with st.expander(f"Detalle {t.upper()}", expanded=True):
                st.table(conteo_app[conteo_app["tipo"] == t][["color_norm", "tamaño", "Cant"]])
        st.metric("Total de piezas visibles", len(df_app))

    # --- Preparación HTML ---
    traces_json = json.dumps([t.to_plotly_json() for t in fig.data])
    layout_json = fig.layout.to_json()
    tipos_unicos = sorted(df["tipo"].unique().tolist())
    colores_unicos = sorted(df["color_norm"].unique().tolist())
    conteo_json = df.groupby(["tipo", "color_norm", "tamaño"]).size().reset_index(name="Cant").to_json(orient='records')

    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte de Componentes</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
        <style>
            body {{ background-color: #f8f9fa; padding: 15px; font-family: 'Segoe UI', sans-serif; }}
            .header-box {{ background: #2c3e50; color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; }}
            #plot-area {{ width: 100%; height: 65vh; background: #fff; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); overflow: hidden; }}
            .filter-section {{ background: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .filter-label {{ font-weight: bold; font-size: 0.8rem; text-transform: uppercase; color: #666; margin-bottom: 8px; display: block; }}
            .summary-card {{ background: white; border-radius: 10px; padding: 15px; margin-top: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            .btn-filter {{ margin: 2px; font-size: 0.75rem; border-radius: 20px; padding: 5px 15px; transition: 0.3s; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="header-box text-center">
                <h1 class="display-6 mb-1" style="font-weight: bold;">REPORTE DE COMPONENTES</h1>
                <h3 class="text-info mb-0">{nombre_modelo.upper() if nombre_modelo else 'SIN NOMBRE'}</h3>
            </div>

            <div class="filter-section">
                <span class="filter-label">Filtrar por Componente:</span>
                <div id="tipo-filters">
                    <button id="btn-tipo-all" class="btn btn-primary btn-sm btn-filter" onclick="filterData('tipo', 'all', this)">TODOS</button>
                    {' '.join([f'<button class="btn btn-outline-primary btn-sm btn-filter" onclick="filterData(\'tipo\', \'{t}\', this)">{t.upper()}</button>' for t in tipos_unicos])}
                </div>
                <span class="filter-label mt-3">Filtrar por Color:</span>
                <div id="color-filters">
                    <button id="btn-color-all" class="btn btn-success btn-sm btn-filter" onclick="filterData('color', 'all', this)">TODOS</button>
                    {' '.join([f'<button class="btn btn-outline-success btn-sm btn-filter" onclick="filterData(\'color\', \'{c}\', this)">{c.upper()}</button>' for c in colores_unicos])}
                </div>
            </div>

            <div id="plot-area"></div>

            <div class="summary-card">
                <h5 class="border-bottom pb-2">📋 Resumen de Materiales</h5>
                <div id="tables-container"></div>
                <hr>
                <h4 class="text-end text-primary" id="total-val">Total: {len(df)}</h4>
            </div>
        </div>

        <script>
            const fullTraces = {traces_json};
            const layout = {layout_json};
            const tableData = {conteo_json};
            const config = {{ responsive: true, scrollZoom: true, displayModeBar: false }};
            
            let currentType = 'all';
            let currentColor = 'all';

            Plotly.newPlot('plot-area', fullTraces, layout, config);

            function filterData(mode, val, btn) {{
                const parent = btn.parentElement;
                const buttons = parent.querySelectorAll('.btn-filter');
                const activeClass = mode === 'tipo' ? 'btn-primary' : 'btn-success';
                const outlineClass = mode === 'tipo' ? 'btn-outline-primary' : 'btn-outline-success';

                buttons.forEach(b => {{ b.classList.remove(activeClass); b.classList.add(outlineClass); }});
                btn.classList.remove(outlineClass);
                btn.classList.add(activeClass);

                if(mode === 'tipo') currentType = val;
                if(mode === 'color') currentColor = val;

                fullTraces.forEach(trace => {{
                    const tData = trace.customdata[0];
                    const matchT = (currentType === 'all' || tData.tipo.toLowerCase() === currentType.toLowerCase());
                    const matchC = (currentColor === 'all' || tData.color.toLowerCase() === currentColor.toLowerCase());
                    trace.visible = (matchT && matchC) ? true : 'legendonly';
                }});
                
                Plotly.react('plot-area', fullTraces, layout, config);
                renderTables();
            }}

            function renderTables() {{
                const container = document.getElementById('tables-container');
                const filtered = tableData.filter(d => {{
                    const matchT = (currentType === 'all' || d.tipo === currentType);
                    const matchC = (currentColor === 'all' || d.color_norm === currentColor);
                    return matchT && matchC;
                }});
                
                const total = filtered.reduce((acc, curr) => acc + curr.Cant, 0);
                let html = '';
                const groups = {{}};
                filtered.forEach(d => {{
                    if (!groups[d.tipo]) groups[d.tipo] = [];
                    groups[d.tipo].push(d);
                }});

                for (const t in groups) {{
                    const subTotal = groups[t].reduce((a, b) => a + b.Cant, 0);
                    html += `<div class="mt-3"><b>${{t.toUpperCase()}}</b> <span class="badge bg-secondary">${{subTotal}} pz</span></div>
                            <table class="table table-hover table-sm">
                                <thead><tr><th>Color</th><th>Tamaño</th><th>Cant.</th></tr></thead>
                                <tbody>`;
                    groups[t].forEach(row => {{
                        html += `<tr><td>${{row.color_norm}}</td><td>${{row.tamaño}}</td><td>${{row.Cant}}</td></tr>`;
                    }});
                    html += `</tbody></table>`;
                }}
                container.innerHTML = html || '<p class="text-muted text-center py-3">No hay elementos con estos filtros.</p>';
                document.getElementById('total-val').innerText = 'Total Visible: ' + total;
            }}
            renderTables();
        </script>
    </body>
    </html>
    """

    st.divider()
    st.download_button(
        label=f"📥 DESCARGAR REPORTE: {nombre_modelo if nombre_modelo else 'MOSAICO'}",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo if nombre_modelo else 'Mosaico'}.html",
        mime="text/html"
    )

else:
    st.info("Sube los archivos para comenzar. El reporte final dir


