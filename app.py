import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
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

    img = Image.open(img_file)
    width, height = img.size
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    data_uri = f"data:image/jpeg;base64,{img_base64}"

    puntos_json = df.to_json(orient='records')
    tipos_unicos = sorted(df["tipo"].unique().tolist())
    colores_unicos = sorted(df["color_norm"].unique().tolist())

    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte: {nombre_modelo}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #f4f7f6; margin: 0; padding: 10px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .header {{ background: #2c3e50; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            
            #main-container {{ position: relative; width: 100%; }}
            #viewer-container {{ width: 100%; height: 65vh; background: #222; border-radius: 12px; border: 2px solid #34495e; overflow: hidden; }}
            
            .filter-card {{ background: white; padding: 15px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
            
            .dot {{ width: 10px; height: 10px; border-radius: 50%; border: 1.5px solid white; cursor: pointer; }}
            .dot.active {{ border: 2.5px solid #fff; box-shadow: 0 0 15px #f1c40f; transform: scale(1.8); z-index: 999 !important; }}

            /* CAJA FLOTANTE REFORZADA */
            #tooltip {{
                position: fixed;
                background: #000;
                color: #fff;
                padding: 10px 15px;
                border-radius: 8px;
                font-size: 14px;
                display: none;
                z-index: 99999;
                pointer-events: none;
                border: 2px solid #f1c40f;
                text-align: center;
                box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            }}

            /* PANEL INFERIOR DE RESPALDO */
            #info-panel {{
                background: #fff;
                border-left: 5px solid #f1c40f;
                padding: 12px;
                margin-top: 10px;
                border-radius: 8px;
                display: none;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}

            .total-card {{
                background: linear-gradient(135deg, #3498db, #2980b9);
                color: white;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                font-size: 1.4rem;
                font-weight: bold;
                margin-top: 20px;
                box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4);
            }}
        </style>
    </head>
    <body>
        <div id="tooltip"></div>
        
        <div class="header">
            <h2 style="font-size: 1.2rem; margin: 0;">REPORTE TÉCNICO: {nombre_modelo.upper() if nombre_modelo else 'SIN NOMBRE'}</h2>
        </div>

        <div class="filter-card">
            <div class="mb-3">
                <label class="text-muted small fw-bold">TIPO DE PIEZA:</label><br>
                <button class="btn btn-primary btn-sm rounded-pill px-3" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill px-3 mx-1" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t}</button>' for t in tipos_unicos])}
            </div>
            <div>
                <label class="text-muted small fw-bold">COLOR:</label><br>
                <button class="btn btn-success btn-sm rounded-pill px-3" onclick="updateFilters('color', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-success btn-sm rounded-pill px-3 mx-1" onclick="updateFilters(\'color\', \'{c}\', this)">{c}</button>' for c in colores_unicos])}
            </div>
        </div>

        <div id="main-container">
            <div id="viewer-container"></div>
        </div>

        <div id="info-panel">
            <h6 class="text-warning mb-1">Detalle Seleccionado:</h6>
            <div id="info-content"></div>
        </div>

        <div class="filter-card mt-3" id="tables-output"></div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            const imgH = {height};
            let filterT = 'all';
            let filterC = 'all';
            let currentSelectedDot = null;
            let currentData = null;
            
            const tooltip = document.getElementById('tooltip');
            const infoPanel = document.getElementById('info-panel');
            const infoContent = document.getElementById('info-content');

            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                showNavigationControl: false,
                maxZoomLevel: 50,
                defaultZoomLevel: 0,
                gestureSettingsTouch: {{ clickToZoom: false, dblClickToZoom: true }}
            }});

            function drawPoints() {{
                viewer.clearOverlays();
                const filtered = puntos.filter(p => {{
                    const matchT = (filterT === 'all' || p.tipo === filterT);
                    const matchC = (filterC === 'all' || p.color_norm === filterC);
                    return matchT && matchC;
                }});

                filtered.forEach((p, idx) => {{
                    const elt = document.createElement("div");
                    elt.className = "dot";
                    elt.style.backgroundColor = p.color_plot;
                    
                    const handleInput = (e) => {{
                        if(e) {{ e.preventDefault(); e.stopPropagation(); }}
                        
                        if (currentSelectedDot) currentSelectedDot.classList.remove('active');
                        elt.classList.add('active');
                        currentSelectedDot = elt;
                        currentData = p;

                        // Mostrar en ambos lugares para asegurar visibilidad
                        const txt = "<b>" + p.tipo.toUpperCase() + "</b><br>" + p.color_norm + " | " + p.tamaño;
                        
                        tooltip.innerHTML = txt;
                        tooltip.style.display = 'block';
                        
                        infoContent.innerHTML = txt;
                        infoPanel.style.display = 'block';

                        updateTooltipPos();
                    }};

                    elt.addEventListener('click', handleInput);
                    elt.addEventListener('touchstart', handleInput);

                    viewer.addOverlay({{
                        element: elt,
                        location: new OpenSeadragon.Point(p.x / imgW, p.y / imgW),
                        placement: OpenSeadragon.Placement.CENTER
                    }});
                }});
                renderTables(filtered);
            }}

            function updateTooltipPos() {{
                if (!currentSelectedDot || !currentData) return;
                
                const viewportPoint = new OpenSeadragon.Point(currentData.x / imgW, currentData.y / imgW);
                const pixel = viewer.viewport.pixelFromPoint(viewportPoint, true);
                const containerRect = document.getElementById('viewer-container').getBoundingClientRect();

                tooltip.style.left = (pixel.x + containerRect.left - tooltip.offsetWidth / 2) + "px";
                tooltip.style.top = (pixel.y + containerRect.top - tooltip.offsetHeight - 20) + "px";
            }}

            viewer.addHandler('animation', updateTooltipPos);
            viewer.addHandler('canvas-drag', updateTooltipPos);
            viewer.addHandler('canvas-scroll', updateTooltipPos);
            
            viewer.addHandler('canvas-click', () => {{
                tooltip.style.display = 'none';
                infoPanel.style.display = 'none';
                if (currentSelectedDot) currentSelectedDot.classList.remove('active');
            }});

            function updateFilters(mode, val, btn) {{
                const parent = btn.parentElement;
                const activeC = mode === 'tipo' ? 'btn-primary' : 'btn-success';
                const outlineC = mode === 'tipo' ? 'btn-outline-primary' : 'btn-outline-success';
                parent.querySelectorAll('.btn').forEach(b => {{ b.classList.remove(activeC); b.classList.add(outlineC); }});
                btn.classList.add(activeC); btn.classList.remove(outlineC);
                if (mode === 'tipo') filterT = val; else filterC = val;
                drawPoints();
            }}

            function renderTables(data) {{
                const container = document.getElementById('tables-output');
                const groups = {{}};
                let totalCount = 0;

                data.forEach(p => {{
                    totalCount++;
                    if(!groups[p.tipo]) groups[p.tipo] = {{}};
                    const key = p.color_norm + " (" + p.tamaño + ")";
                    groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                }});

                let html = '<h5 class="text-dark mb-3 border-bottom pb-2">Desglose de Materiales</h5>';
                for(let t in groups) {{
                    html += '<div class="mt-3"><strong>' + t.toUpperCase() + '</strong></div>';
                    html += '<table class="table table-sm table-hover mb-0" style="font-size: 11px;">';
                    html += '<thead><tr><th>Descripción</th><th class="text-end">Cantidad</th></tr></thead><tbody>';
                    for(let k in groups[t]) {{
                        html += '<tr><td>' + k + '</td><td class="text-end fw-bold">' + groups[t][k] + ' pz</td></tr>';
                    }}
                    html += '</tbody></table>';
                }}
                
                html += '<div class="total-card">TOTAL DE COMPONENTES: ' + totalCount + ' PIEZAS</div>';
                container.innerHTML = html;
            }}

            viewer.addHandler('open', drawPoints);
        </script>
    </body>
    </html>
    """

    st.divider()
    st.download_button(
        label="📥 DESCARGAR REPORTE: SOLUCIÓN FINAL CON TOTALES",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo}.html",
        mime="text/html"
    )
