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

    # SE USAN DOBLES LLAVES {{ }} PARA CSS Y JS PORQUE ESTAMOS DENTRO DE UN F-STRING
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte Pro: {nombre_modelo}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=10.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #f8f9fa; font-family: sans-serif; margin: 0; padding: 10px; }}
            .header {{ background: #2c3e50; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; }}
            #viewer-container {{ width: 100%; height: 70vh; background: #222; border-radius: 12px; position: relative; border: 2px solid #ddd; }}
            .filter-card {{ background: white; padding: 12px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            
            .dot {{ 
                width: 10px; height: 10px; 
                border-radius: 50%; border: 1px solid white; 
                cursor: pointer; box-sizing: border-box; 
            }}
            .dot.active {{
                border: 2px solid #fff;
                box-shadow: 0 0 10px #ffeb3b, 0 0 5px #ffeb3b inset;
                transform: scale(1.6);
            }}

            #floating-info {{
                position: fixed;
                background: rgba(0, 0, 0, 0.95);
                color: #fff;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 13px;
                display: none;
                z-index: 10000;
                pointer-events: none;
                border: 1px solid #ffeb3b;
                box-shadow: 0 5px 25px rgba(0,0,0,0.7);
                text-align: center;
                min-width: 140px;
            }}
            #floating-info b {{ color: #3498db; text-transform: uppercase; }}
        </style>
    </head>
    <body>
        <div id="floating-info"></div>
        
        <div class="header">
            <h2 style="font-size: 1.2rem; margin: 0;">{nombre_modelo.upper() if nombre_modelo else 'REPORTE DE PIEZA'}</h2>
        </div>

        <div class="filter-card">
            <div class="mb-2">
                <small class="text-muted d-block mb-1">FILTRAR POR TIPO:</small>
                <button class="btn btn-primary btn-sm rounded-pill px-3" style="font-size:10px;" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill px-3" style="font-size:10px; margin:2px;" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t}</button>' for t in tipos_unicos])}
            </div>
            <div>
                <small class="text-muted d-block mb-1">FILTRAR POR COLOR:</small>
                <button class="btn btn-success btn-sm rounded-pill px-3" style="font-size:10px;" onclick="updateFilters('color', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-success btn-sm rounded-pill px-3" style="font-size:10px; margin:2px;" onclick="updateFilters(\'color\', \'{c}\', this)">{c}</button>' for c in colores_unicos])}
            </div>
        </div>

        <div id="viewer-container"></div>
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
                maxZoomLevel: 50,
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
                        showTooltip(p);
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

            function showTooltip(data) {{
                tooltip.style.display = 'block';
                tooltip.innerHTML = `<b>${{data.tipo}}</b><br>${{data.color_norm}}<br>${{data.tamaño}}`;
                updateTooltipPos();
            }}

            function updateTooltipPos() {{
                if (!currentSelectedDot || !currentPointData) return;
                
                const viewportPoint = new OpenSeadragon.Point(currentPointData.x / imgW, currentPointData.y / imgW);
                const pixel = viewer.viewport.pixelFromPoint(viewportPoint, true);
                const containerRect = document.getElementById('viewer-container').getBoundingClientRect();

                const x = pixel.x + containerRect.left - (tooltip.offsetWidth / 2);
                const y = pixel.y + containerRect.top - tooltip.offsetHeight - 20;

                tooltip.style.left = x + 'px';
                tooltip.style.top = y + 'px';
            }}

            viewer.addHandler('animation', updateTooltipPos);
            viewer.addHandler('canvas-drag', updateTooltipPos);
            viewer.addHandler('canvas-scroll', updateTooltipPos);

            viewer.addHandler('canvas-click', () => {{
                tooltip.style.display = 'none';
                if (currentSelectedDot) currentSelectedDot.classList.remove('active');
                currentSelectedDot = null;
                currentPointData = null;
            }});

            function updateFilters(mode, val, btn) {{
                const parent = btn.parentElement;
                const activeClass = mode === 'tipo' ? 'btn-primary' : 'btn-success';
                const outlineClass = mode === 'tipo' ? 'btn-outline-primary' : 'btn-outline-success';
                
                parent.querySelectorAll('.btn').forEach(b => {{ 
                    b.classList.remove(activeClass); b.classList.add(outlineClass); 
                }});
                btn.classList.add(activeClass); btn.classList.remove(outlineClass);
                
                if (mode === 'tipo') filterT = val; else filterC = val;
                
                tooltip.style.display = 'none';
                drawPoints();
            }}

            function renderTables(data) {{
                const container = document.getElementById('tables-output');
                const groups = {{}};
                data.forEach(p => {{
                    if(!groups[p.tipo]) groups[p.tipo] = {{}};
                    const key = p.color_norm + '|' + p.tamaño;
                    groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                }});
                let html = '<h6 class="text-primary border-bottom pb-2">RESUMEN DE MATERIALES</h6>';
                for(const t in groups) {{
                    html += `<div class="mt-2 small"><strong>${{t.toUpperCase()}}</strong></div>
                             <table class="table table-sm table-striped" style="font-size: 10px;"><tbody>`;
                    for(const sk in groups[t]) {{
                        const [c, tam] = sk.split('|');
                        html += `<tr><td>${{c}}</td><td>${{tam}}</td><td class="text-end"><b>${{groups[t][sk]}}</b> pz</td></tr>`;
                    }}
                    html += '</tbody></table>';
                }}
                container.innerHTML = html;
            }}

            viewer.addHandler('open', drawPoints);
        </script>
    </body>
    </html>
    """

    st.divider()
    st.download_button(
        label="📥 DESCARGAR REPORTE CORREGIDO",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo}.html",
        mime="text/html"
    )



