import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image
import base64
import json
from io import BytesIO

# =========================
# CONFIGURACIÓN Y CATÁLOGO
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
    "violet": "violet", "zafiro": "royalblue", "sin_color": "gray",
    "gmb_morado": "#9400D3", "rsb_azul": "#0000FF", "rsb/gbm_subl": "#87CEFA",
    "amarillo": "#FFFF00", "azul_rey": "#0000CD", "rojo": "#FF0000",
    "turqueza": "#40E0D0", "turqueza_metalico": "#00CED1", "teal": "#008080",
    "mauva": "#E0B0FF", "lilac": "#C8A2C8", "azul_purpura": "#8A2BE2",
    "orquida": "#DA70D6", "purpura": "#800080", "salmon": "#FA8072",
    "gris": "#808080", "azul_agua": "#00FFFF", "verde_jade": "#00A86B",
    "morado": "#7A288A", "otro": "#D3D3D3"
}

def normalizar_color(c):
    if pd.isna(c) or c == "": return "sin_color"
    return str(c).lower().strip().replace(" ", "_")

def ajustar_color_por_tipo(row):
    tipo = str(row["tipo"]).lower()
    color = row["color_norm"]
    if tipo == "microperla": return color if color in COLOR_CATALOG else "otro"
    if tipo == "dicroico":
        if color in ["gmb_morado", "rsb_azul", "rsb/gbm_subl"]: return color
        return "gmb_morado"
    if tipo == "balin" and color not in ["plata", "dorado"]: return "plata"
    return color

# =========================
# INTERFAZ Y PROCESAMIENTO
# =========================
st.sidebar.title("💎 Panel de Control")
nombre_modelo = st.sidebar.text_input("Nombre del Modelo", placeholder="Ej: PB-8612 A")
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
                    "tamaño": attrs.get("tamaño", "pp01" if tipo == "microperla" else ""),
                    "color_plot": COLOR_CATALOG.get(normalizar_color(attrs.get("color", "")), "gray")
                })
    
    df = pd.DataFrame(rows)
    df["color_norm"] = df.apply(ajustar_color_por_tipo, axis=1)
    df["color_plot"] = df["color_norm"].map(lambda x: COLOR_CATALOG.get(x, "gray"))

    img = Image.open(img_file)
    width, height = img.size
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    data_uri = f"data:image/jpeg;base64,{img_base64}"

    puntos_json = df.to_json(orient='records')
    tipos_unicos = sorted(df["tipo"].unique().tolist())
    colores_unicos = sorted(df["color_norm"].unique().tolist())
    titulo_final = f"Componentes {nombre_modelo}" if nombre_modelo else "Componentes"

    # =========================
    # REPORTE HTML (LLAVES DUPLICADAS {{ }} PARA EVITAR SYNTAX ERROR)
    # =========================
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{titulo_final}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #f8f9fa; padding: 0; margin: 0; font-family: 'Segoe UI', sans-serif; }}
            .header {{ background: #2c3e50; color: white; padding: 15px; text-align: center; border-bottom: 4px solid #1abc9c; }}
            #info-bar {{
                position: -webkit-sticky; position: sticky; top: 0; z-index: 2000;
                background: #fff9c4; color: #333; padding: 12px; text-align: center;
                font-weight: bold; border-bottom: 2px solid #fbc02d; font-size: 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); min-height: 50px;
            }}
            #workspace {{ background: #1a1a1a; position: relative; display: flex; flex-direction: column; }}
            #viewer-container {{ width: 100%; height: 75vh; background: #000; }}
            .custom-nav {{
                position: absolute; top: 65px; left: 15px; z-index: 1005;
                display: flex; flex-direction: column; gap: 10px;
            }}
            .nav-btn {{
                width: 44px; height: 44px; border-radius: 10px; border: 2px solid white;
                color: white; font-size: 24px; font-weight: bold; display: flex;
                align-items: center; justify-content: center; cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }}
            .btn-zoom-in {{ background-color: #1abc9c !important; }}
            .btn-zoom-out {{ background-color: #ffb7c5 !important; color: #333 !important; }}
            .btn-home {{ background-color: #3498db !important; }}
            .btn-fs {{
                position: absolute; top: 65px; right: 15px; z-index: 1005;
                background: #ffffff; border: 2px solid #2c3e50; padding: 10px 20px;
                border-radius: 30px; font-weight: bold; cursor: pointer;
            }}
            .dot {{ width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; cursor: pointer; }}
            .dot.selected {{ border: 3px solid #fff !important; box-shadow: 0 0 12px 4px #fff; transform: scale(1.6); z-index: 999 !important; }}
            .p-container {{ padding: 15px; }}
            .filter-card {{ background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            .category-header {{ background: #e8f4fd; padding: 10px 15px; border-radius: 8px; color: #2980b9; display: flex; justify-content: space-between; margin-top: 20px; font-weight: bold; border-left: 6px solid #3498db; }}
            .total-banner {{ background: #2c3e50; color: white; padding: 18px; border-radius: 12px; text-align: center; font-size: 1.4rem; font-weight: bold; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="header"><h2>{titulo_final}</h2></div>
        <div class="p-container">
            <div class="filter-card">
                <div class="mb-2">
                    <small class="text-muted fw-bold">TIPO:</small>
                    <button class="btn btn-primary btn-sm rounded-pill px-3" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                    {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill px-3 mx-1" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t.upper()}</button>' for t in tipos_unicos])}
                </div>
                <div>
                    <small class="text-muted fw-bold">COLOR:</small>
                    <button class="btn btn-success btn-sm rounded-pill px-3" onclick="updateFilters('color', 'all', this)">TODOS</button>
                    {' '.join([f'<button class="btn btn-outline-success btn-sm rounded-pill px-3 mx-1" onclick="updateFilters(\'color\', \'{c}\', this)">{c.replace("_", " ").upper()}</button>' for c in colores_unicos])}
                </div>
            </div>
        </div>
        <div id="workspace">
            <div id="info-bar">Selecciona un elemento en la imagen</div>
            <div class="custom-nav">
                <div id="btn-in" class="nav-btn btn-zoom-in">+</div>
                <div id="btn-out" class="nav-btn btn-zoom-out">−</div>
                <div id="btn-home" class="nav-btn btn-home">🏠</div>
            </div>
            <button class="btn-fs" onclick="toggleFS()">📺 Pantalla Completa</button>
            <div id="viewer-container"></div>
        </div>
        <div class="p-container"><div id="tables-output"></div></div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                showNavigationControl: false, maxZoomLevel: 80,
                gestureSettingsTouch: {{ clickToZoom: false, dblClickToZoom: false }},
                gestureSettingsMouse: {{ clickToZoom: false, dblClickToZoom: false }}
            }});

            document.getElementById('btn-in').onclick = () => viewer.viewport.zoomBy(1.4);
            document.getElementById('btn-out').onclick = () => viewer.viewport.zoomBy(0.7);
            document.getElementById('btn-home').onclick = () => viewer.viewport.goHome();

            function toggleFS() {{
                const el = document.getElementById("workspace");
                if (!document.fullscreenElement) el.requestFullscreen();
                else document.exitFullscreen();
            }}

            let filterT = 'all', filterC = 'all', lastSelected = null;

            viewer.addHandler('open', drawPoints);

            function drawPoints() {{
                viewer.clearOverlays();
                const filtered = puntos.filter(p => {{
                    return (filterT === 'all' || p.tipo === filterT) && (filterC === 'all' || p.color_norm === filterC);
                }});
                filtered.forEach(p => {{
                    const elt = document.createElement("div");
                    elt.className = "dot";
                    elt.style.backgroundColor = p.color_plot;
                    elt.addEventListener('pointerdown', (e) => {{
                        e.stopPropagation();
                        if(lastSelected) lastSelected.classList.remove('selected');
                        elt.classList.add('selected'); lastSelected = elt;
                        document.getElementById('info-bar').innerHTML = "SELECCIONADO: " + p.tipo.toUpperCase() + " | " + p.color_norm.replace(/_/g, ' ').toUpperCase() + " | " + p.tamaño;
                    }});
                    viewer.addOverlay({{ element: elt, location: new OpenSeadragon.Point(p.x/imgW, p.y/imgW), placement: 'CENTER' }});
                }});
                renderSummary(filtered);
            }}

            function updateFilters(m, v, b) {{
                const p = b.parentElement;
                const ac = m === 'tipo' ? 'btn-primary' : 'btn-success';
                const oc = m === 'tipo' ? 'btn-outline-primary' : 'btn-outline-success';
                p.querySelectorAll('.btn').forEach(x => {{ x.classList.remove(ac); x.classList.add(oc); }});
                b.classList.add(ac); b.classList.remove(oc);
                if (m === 'tipo') filterT = v; else filterC = v;
                drawPoints();
            }}

            function renderSummary(data) {{
                const container = document.getElementById('tables-output');
                const groups = {{}};
                let total = 0;
                data.forEach(p => {{
                    total++;
                    if(!groups[p.tipo]) groups[p.tipo] = {{}};
                    const key = p.color_norm.replace(/_/g, ' ').toUpperCase() + " (" + p.tamaño + ")";
                    groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                }});
                let html = '<div class="filter-card"><h5 class="fw-bold">RESUMEN</h5>';
                for(let t in groups) {{
                    html += '<div class="category-header"><span>' + t.toUpperCase() + '</span></div>';
                    html += '<table class="table table-sm"><tbody>';
                    for(let k in groups[t]) html += '<tr><td>' + k + '</td><td class="text-end"><b>' + groups[t][k] + '</b> pz</td></tr>';
                    html += '</tbody></table>';
                }}
                html += '<div class="total-banner">TOTAL: ' + total + ' PIEZAS</div></div>';
                container.innerHTML = html;
            }}
        </script>
    </body>
    </html>
    """
    st.divider()
    st.download_button(label="📥 DESCARGAR REPORTE TÉCNICO", data=html_report, file_name=f"{titulo_final}.html", mime="text/html")

