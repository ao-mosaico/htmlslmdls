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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=10.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #f8f9fa; margin: 0; padding: 10px; }}
            .header {{ background: #2c3e50; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; }}
            
            /* Contenedor del Visor */
            #viewer-wrapper {{ position: relative; width: 100%; height: 70vh; border-radius: 12px; overflow: hidden; border: 2px solid #ddd; }}
            #viewer-container {{ width: 100%; height: 100%; background: #222; }}
            
            .filter-card {{ background: white; padding: 12px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            
            .dot {{ width: 10px; height: 10px; border-radius: 50%; border: 1px solid white; cursor: pointer; }}
            .dot.active {{ border: 2px solid #fff; box-shadow: 0 0 10px #ffeb3b, 0 0 5px #ffeb3b inset; transform: scale(1.6); }}

            /* TOOLTIP POSICIONADO DENTRO DEL CONTENEDOR */
            #floating-info {{
                position: absolute;
                background: rgba(0, 0, 0, 0.95);
                color: #fff;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 12px;
                display: none;
                z-index: 1000;
                pointer-events: none;
                border: 1px solid #ffeb3b;
                text-align: center;
                white-space: nowrap;
            }}
            .total-banner {{ background: #e3f2fd; border: 2px solid #2196f3; color: #0d47a1; padding: 10px; border-radius: 8px; font-weight: bold; text-align: center; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="font-size: 1.1rem; margin: 0;">REPORTE: {nombre_modelo.upper() if nombre_modelo else 'SIN NOMBRE'}</h2>
        </div>

        <div class="filter-card">
            <div class="mb-2">
                <small class="text-muted d-block mb-1">TIPO:</small>
                <button class="btn btn-primary btn-sm rounded-pill" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill mx-1" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t}</button>' for t in tipos_unicos])}
            </div>
            <div>
                <small class="text-muted d-block mb-1">COLOR:</small>
                <button class="btn btn-success btn-sm rounded-pill" onclick="updateFilters('color', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-success btn-sm rounded-pill mx-1" onclick="updateFilters(\'color\', \'{c}\', this)">{c}</button>' for c in colores_unicos])}
            </div>
        </div>

        <div id="viewer-wrapper">
            <div id="viewer-container"></div>
            <div id="floating-info"></div>
        </div>

        <div class="filter-card mt-3" id="tables-output"></div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            const imgH = {height};
            let filterT = 'all';
            let filterC = 'all';
            let currentSelectedDot = null;
            let currentPointData = null;
            
            const tooltip = document.getElementById('floating-info');

            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                gestureSettingsTouch: {{ clickToZoom: false, dblClickToZoom: true }},
                gestureSettingsMouse: {{ clickToZoom: false }},
                showNavigationControl: false,
                maxZoomLevel: 60,
                detectRetina: false
            }});

            function drawPoints() {{
                viewer.clearOverlays();
                const filtered = puntos.filter(p => {{
                    const matchT = (filterT === 'all' || p.tipo === filterT);
                    const matchC = (filterC === 'all' || p.color_norm === filterC);
                    return matchT && matchC;
                }});

                filtered.forEach((p) => {{
                    const elt = document.createElement("div");
                    elt.className = "dot";
                    elt.style.backgroundColor = p.color_plot;
                    
                    const handleAction = (e) => {{
                        e.preventDefault(); e.stopPropagation();
                        if (currentSelectedDot) currentSelectedDot.classList.remove('active');
                        elt.classList.add('active');
                        currentSelectedDot = elt;
                        currentPointData = p;
                        
                        tooltip.style.display = 'block';
                        tooltip.innerHTML = `<b>${{p.tipo.toUpperCase()}}</b><br>${{p.color_norm}}<br>${{p.tamaño}}`;
                        updateTooltipPos();
                    }};

                    elt.addEventListener('click', handleAction);
                    elt.addEventListener('touchstart', handleAction);

                    viewer.addOverlay({{
                        element: elt,
                        location: new OpenSeadragon.Point(p.x / imgW, p.y / imgW),
                        placement: OpenSeadragon.Placement.CENTER
                    }});
                }});
                renderTables(filtered);
            }}

            function updateTooltipPos() {{
                if (!currentSelectedDot || !currentPointData) return;
                
                // Cálculo de píxeles relativo al CONTENEDOR del visor, no a la pantalla
                const viewportPoint = new OpenSeadragon.Point(currentPointData.x / imgW, currentPointData.y / imgW);
                const pixel = viewer.viewport.pixelFromPoint(viewportPoint, true);

                tooltip.style.left = (pixel.x - tooltip.offsetWidth / 2) + 'px';
                tooltip.style.top = (pixel.y - tooltip.offsetHeight - 15) + 'px';
            }}

            // Eventos para que el cuadro siga al zoom/movimiento
            viewer.addHandler('animation', updateTooltipPos);
            viewer.addHandler('canvas-drag', updateTooltipPos);
            viewer.addHandler('canvas-scroll', updateTooltipPos);
            viewer.addHandler('canvas-click', () => {{
                tooltip.style.display = 'none';
                if (currentSelectedDot) currentSelectedDot.classList.remove('active');
                currentSelectedDot = null;
            }});

            function updateFilters(mode, val, btn) {{
                const parent = btn.parentElement;
                const activeC = mode === 'tipo' ? 'btn-primary' : 'btn-success';
                const outlineC = mode === 'tipo' ? 'btn-outline-primary' : 'btn-outline-success';
                parent.querySelectorAll('.btn').forEach(b => {{ b.classList.remove(activeC); b.classList.add(outlineC); }});
                btn.classList.add(activeC); btn.classList.remove(outlineC);
                if (mode === 'tipo') filterT = val; else filterC = val;
                tooltip.style.display = 'none';
                drawPoints();
            }}

            function renderTables(data) {{
                const container = document.getElementById('tables-output');
                const groups = {{}};
                let granTotal = 0;

                data.forEach(p => {{
                    granTotal++;
                    if(!groups[p.tipo]) groups[p.tipo] = {{}};
                    const key = p.color_norm + '|' + p.tamaño;
                    groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                }});

                let html = '<h6 class="text-primary border-bottom pb-2">RESUMEN DE MATERIALES</h6>';
                for(const t in groups) {{
                    html += `<div class="mt-2 small"><strong>${{t.toUpperCase()}}</strong></div>
                             <table class="table table-sm table-striped mb-0" style="font-size: 10px;"><tbody>`;
                    for(const sk in groups[t]) {{
                        const [c, tam] = sk.split('|');
                        html += `<tr><td>${{c}}</td><td>${{tam}}</td><td class="text-end"><b>${{groups[t][sk]}}</b> pz</td></tr>`;
                    }}
                    html += '</tbody></table>';
                }}
                
                // EL TOTAL GENERAL SOLICITADO
                html += `<div class="total-banner">TOTAL DE COMPONENTES: ${{granTotal}} PIEZAS</div>`;
                container.innerHTML = html;
            }}

            viewer.addHandler('open', drawPoints);
        </script>
    </body>
    </html>
    """

    st.divider()
    st.download_button(
        label="📥 DESCARGAR REPORTE CON TOTALES Y CAJAS FIJAS",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo}.html",
        mime="text/html"
    )



