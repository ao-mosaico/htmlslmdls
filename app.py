import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image
import base64
import json
from io import BytesIO

# =========================================================
# CONFIGURACIÓN Y CATÁLOGO (Solo se añadieron 3 líneas aquí)
# =========================================================
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
    # NUEVOS ATRIBUTOS DICROICOS SOLICITADOS
    "gmb_morado": "#9400D3",      # Morado intenso
    "rsb_azul": "#0000FF",         # Azul sólido
    "rsb/gbm_subl": "#87CEFA"     # Azul claro (Sublime)
}

def normalizar_color(c):
    if pd.isna(c) or c == "": return "sin_color"
    return str(c).lower().strip().replace(" ", "_")

def ajustar_color_por_tipo(row):
    tipo = str(row["tipo"]).lower()
    color = row["color_norm"]
    
    # Lógica específica para Dicroicos: Respeta los nuevos nombres
    if tipo == "dicroico":
        if color in ["gmb_morado", "rsb_azul", "rsb/gbm_subl"]:
            return color
        return "gmb_morado" # Fallback por seguridad
        
    if tipo == "balin" and color not in ["plata", "dorado"]: return "plata"
    return color

# =========================================================
# INTERFAZ LATERAL (Sin cambios)
# =========================================================
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
                    "tamaño": attrs.get("tamaño", ""),
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

    # =========================================================
    # HTML/JS (Manteniendo la estructura de botones de colores y 65px)
    # =========================================================
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{titulo_final}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
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
            #workspace:fullscreen {{ width: 100vw; height: 100vh; }}
            #workspace:fullscreen #viewer-container {{ flex: 1; height: auto; }}
            #viewer-container {{ width: 100%; height: 75vh; background: #000; }}
            
            .custom-nav {{
                position: absolute; top: 65px; left: 15px; z-index: 1005;
                display: flex; flex-direction: column; gap: 10px;
            }}
            .nav-btn {{
                width: 44px; height: 44px; border-radius: 10px; border: 2px solid white;
                color: white; font-size: 24px; font-weight: bold; display: flex;
                align-items: center; justify-content: center; cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: all 0.2s;
            }}
            .btn-zoom-in {{ background-color: #1abc9c !important; }}
            .btn-zoom-out {{ background-color: #ffb7c5 !important; color: #333 !important; }}
            .btn-home {{ background-color: #3498db !important; }}

            .btn-fs {{
                position: absolute; top: 65px; right: 15px; z-index: 1005;
                background: #ffffff; border: 2px solid #2c3e50; padding: 10px 20px;
                border-radius: 30px; font-weight: bold; cursor: pointer; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            }}

            .dot {{ width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; cursor: pointer; transition: all 0.2s; }}
            .dot.selected {{ border: 3px solid #fff !important; box-shadow: 0 0 12px 4px #fff, 0 0 8px 1px #ffeb3b; transform: scale(1.6); z-index: 999 !important; }}

            .p-container {{ padding: 15px; }}
            .filter-card {{ background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            .category-header {{ background: #e8f4fd; padding: 10px 15px; border-radius: 8px; color: #2980b9; display: flex; justify-content: space-between; margin-top: 20px; font-weight: bold; border-left: 6px solid #3498db; }}
            .total-banner {{ background: #2c3e50; color: white; padding: 18px; border-radius: 12px; text-align: center; font-size: 1.4rem; font-weight: bold; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="font-size: 1.4rem; margin: 0;">{titulo_final}</h2>
        </div>
        <div class="p-container">
            <div class="filter-card">
                <div class="mb-2">
                    <small class="text-muted fw-bold">TIPO DE PIEZA:</small>
                    <button class="btn btn-primary btn-sm rounded-pill px-3" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                    {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill px-3 mx-1" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t}</button>' for t in tipos_unicos])}
                </div>
                <div>
                    <small class="text-muted fw-bold">COLOR:</small>
                    <button class="btn btn-success btn-sm rounded-pill px-3" onclick="updateFilters('color', 'all', this)">TODOS</button>
                    {' '.join([f'<button class="btn btn-outline-success btn-sm rounded-pill px-3 mx-1" onclick="updateFilters(\'color\', \'{c}\', this)">{c}</button>' for c in colores_unicos])}
                </div>
            </div>
        </div>
        <div id="workspace">
            <div id="info-bar">Selecciona un punto para ver su descripción técnica</div>
            <div class="custom-nav">
                <div id="btn-in" class="nav-btn btn-zoom-in">+</div>
                <div id="btn-out" class="nav-btn btn-zoom-out">−</div>
                <div id="btn-home" class="nav-btn btn-home">🏠</div>
            </div>
            <button class="btn-fs" onclick="toggleFullScreen()">📺 Pantalla Completa</button>
            <div id="viewer-container"></div>
        </div>
        <div class="p-container">
            <div class="filter-card" id="tables-output"></div>
        </div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                showNavigationControl: false, maxZoomLevel: 60, minZoomImageRatio: 1.0, visibilityRatio: 1.0,
                constrainDuringPan: true, gestureSettingsTouch: {{ clickToZoom: false, dblClickToZoom: false }}
            }});

            document.getElementById('btn-in').onclick = () => viewer.viewport.zoomBy(1.3);
            document.getElementById('btn-out').onclick = () => viewer.viewport.zoomBy(0.7);
            document.getElementById('btn-home').onclick = () => viewer.viewport.goHome();

            viewer.addHandler('open', drawPoints);

            function toggleFullScreen() {{
                const elem = document.getElementById("workspace");
                if (!document.fullscreenElement) elem.requestFullscreen();
                else document.exitFullscreen();
            }}

            function drawPoints() {{
                viewer.clearOverlays();
                const filtered = puntos.filter(p => {{
                    const matchT = (filterT === 'all' || p.tipo === filterT);
                    const matchC = (filterC === 'all' || p.color_norm === filterC);
                    return matchT && matchC;
                }});
                filtered.forEach(p => {{
                    const elt = document.createElement("div");
                    elt.className = "dot";
                    elt.style.backgroundColor = p.color_plot;
                    elt.onclick = () => {{
                        if(lastSelectedElt) lastSelectedElt.classList.remove('selected');
                        elt.classList.add('selected'); lastSelectedElt = elt;
                        document.getElementById('info-bar').innerHTML = "PUNTO SELECCIONADO: " + p.tipo.toUpperCase() + " | " + p.color_norm.replace(/_/g, ' ') + " | " + p.tamaño;
                    }};
                    viewer.addOverlay({{ element: elt, location: new OpenSeadragon.Point(p.x/imgW, p.y/imgW), placement: 'CENTER' }});
                }});
                renderSummary(filtered);
            }}

            let filterT = 'all', filterC = 'all', lastSelectedElt = null;
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
                let totalGral = 0;
                data.forEach(p => {{
                    totalGral++;
                    if(!groups[p.tipo]) groups[p.tipo] = {{}};
                    const key = p.color_norm.replace(/_/g, ' ') + " (" + p.tamaño + ")";
                    groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                }});
                let html = '<h5 class="fw-bold">RESUMEN - {nombre_modelo}</h5>';
                for(let t in groups) {{
                    html += '<div class="category-header"><span>' + t.toUpperCase() + '</span></div>';
                    html += '<table class="table table-sm"><tbody>';
                    for(let k in groups[t]) html += '<tr><td>' + k + '</td><td>' + groups[t][k] + ' pz</td></tr>';
                    html += '</tbody></table>';
                }}
                html += '<div class="total-banner">TOTAL: ' + totalGral + ' PIEZAS</div>';
                container.innerHTML = html;
            }}
        </script>
    </body>
    </html>
    """
    st.divider()
    st.download_button(label=f"📥 DESCARGAR REPORTE", data=html_report, file_name=f"{titulo_final}.html", mime="text/html")

