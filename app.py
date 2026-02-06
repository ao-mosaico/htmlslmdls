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
nombre_modelo = st.sidebar.text_input("Nombre del Modelo / Pieza", placeholder="Ej: PB-8612 A")
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
    img_format = img.format if img.format else "JPEG"
    img.save(buffered, format=img_format)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    data_uri = f"data:image/{img_format.lower()};base64,{img_base64}"

    puntos_json = df.to_json(orient='records')
    tipos_unicos = sorted(df["tipo"].unique().tolist())
    colores_unicos = sorted(df["color_norm"].unique().tolist())

    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reporte Pro: {nombre_modelo}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #f0f2f5; font-family: sans-serif; margin: 0; padding: 10px; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 15px; }}
            #viewer-container {{ width: 100%; height: 60vh; background: #333; border-radius: 12px; position: relative; }}
            .filter-card {{ background: white; padding: 15px; border-radius: 12px; margin-bottom: 15px; }}
            .btn-filter {{ border-radius: 20px; font-size: 11px; margin: 2px; text-transform: uppercase; }}
            
            /* CORRECCIÓN CRÍTICA: Eliminado 'transform: translate' para evitar doble centrado */
            .dot {{ 
                position: absolute; width: 14px; height: 14px; 
                border-radius: 50%; border: 1.5px solid white; 
                cursor: pointer; pointer-events: auto; z-index: 10;
                box-shadow: 0 0 3px rgba(0,0,0,0.5);
                /* IMPORTANTE: No usar transform aquí, OpenSeadragon ya centra el elemento */
            }}
            
            .osd-tooltip {{
                position: absolute; background: rgba(0,0,0,0.9); color: white;
                padding: 6px 12px; border-radius: 6px; font-size: 12px;
                pointer-events: none; display: none; z-index: 1000;
                white-space: nowrap; border: 1px solid #444;
            }}
        </style>
    </head>
    <body>
        <div id="tooltip" class="osd-tooltip"></div>
        <div class="header">
            <h1 style="font-size: 1.4rem; margin: 0;">REPORTE DE COMPONENTES</h1>
            <div style="color: #3498db; font-weight: bold;">{nombre_modelo.upper() if nombre_modelo else 'SIN NOMBRE'}</div>
        </div>

        <div class="filter-card">
            <div id="tipo-filters">
                <button class="btn btn-primary btn-sm btn-filter" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm btn-filter" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t}</button>' for t in tipos_unicos])}
            </div>
            <div id="color-filters" class="mt-2">
                <button class="btn btn-success btn-sm btn-filter" onclick="updateFilters('color', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-success btn-sm btn-filter" onclick="updateFilters(\'color\', \'{c}\', this)">{c}</button>' for c in colores_unicos])}
            </div>
        </div>

        <div id="viewer-container"></div>

        <div class="filter-card mt-3">
            <div id="tables-output"></div>
            <div class="text-end h5 mt-3 text-primary" id="total-text"></div>
        </div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            const imgH = {height};
            let filterT = 'all';
            let filterC = 'all';
            const tooltip = document.getElementById('tooltip');

            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{
                    type: 'image',
                    url: '{data_uri}'
                }},
                gestureSettingsTouch: {{ pinchRotate: false }},
                showNavigationControl: false,
                defaultZoomLevel: 0,
                minZoomLevel: 0,
                visibilityRatio: 1,
                constrainDuringPan: true
            }});

            function drawPoints() {{
                viewer.clearOverlays();
                const filtered = puntos.filter(p => {{
                    const mt = (filterT === 'all' || p.tipo === filterT);
                    const mc = (filterC === 'all' || p.color_norm === filterC);
                    return mt && mc;
                }});

                filtered.forEach(p => {{
                    const elt = document.createElement("div");
                    elt.className = "dot";
                    elt.style.backgroundColor = p.color_plot;
                    
                    const showInfo = (e) => {{
                        tooltip.style.display = 'block';
                        tooltip.innerHTML = `<b>${{p.tipo.toUpperCase()}}</b><br>${{p.color_norm}} | ${{p.tamaño}}`;
                        const xPos = (e.clientX || (e.touches && e.touches[0].clientX));
                        const yPos = (e.clientY || (e.touches && e.touches[0].clientY));
                        tooltip.style.left = (xPos + 15) + 'px';
                        tooltip.style.top = (yPos - 40) + 'px';
                    }};
                    
                    elt.onmouseover = showInfo;
                    elt.ontouchstart = (e) => showInfo(e);
                    elt.onmouseout = () => tooltip.style.display = 'none';

                    // PRECISION FINAL:
                    // Usamos la coordenada normalizada (x/ancho, y/ancho)
                    // Y dejamos que 'Placement.CENTER' haga el trabajo sucio sin interferencia CSS.
                    viewer.addOverlay({{
                        element: elt,
                        location: new OpenSeadragon.Point(p.x / imgW, p.y / imgW),
                        placement: OpenSeadragon.Placement.CENTER
                    }});
                }});
                renderTables(filtered);
            }}

            function updateFilters(mode, val, btn) {{
                const parent = btn.parentElement;
                const activeClass = mode === 'tipo' ? 'btn-primary' : 'btn-success';
                const outlineClass = mode === 'tipo' ? 'btn-outline-primary' : 'btn-outline-success';
                parent.querySelectorAll('.btn').forEach(b => {{ b.classList.remove(activeClass); b.classList.add(outlineClass); }});
                btn.classList.add(activeClass); btn.classList.remove(outlineClass);
                if(mode === 'tipo') filterT = val; else filterC = val;
                drawPoints();
            }}

            function renderTables(data) {{
                const container = document.getElementById('tables-output');
                const groups = {{}};
                data.forEach(p => {{
                    const key = p.tipo;
                    if(!groups[key]) groups[key] = {{}};
                    const subKey = p.color_norm + '|' + p.tamaño;
                    groups[key][subKey] = (groups[key][subKey] || 0) + 1;
                }});
                let html = '';
                for(const t in groups) {{
                    html += `<div class="mt-2"><strong>${{t.toUpperCase()}}</strong></div>
                             <table class="table table-sm" style="font-size: 11px;">
                             <thead><tr><th>Color</th><th>Tam.</th><th>Cant.</th></tr></thead><tbody>`;
                    for(const sk in groups[t]) {{
                        const [c, tam] = sk.split('|');
                        html += `<tr><td>${{c}}</td><td>${{tam}}</td><td>${{groups[t][sk]}}</td></tr>`;
                    }}
                    html += '</tbody></table>';
                }}
                container.innerHTML = html;
                document.getElementById('total-text').innerText = 'Piezas: ' + data.length;
            }}

            viewer.addHandler('open', drawPoints);
        </script>
    </body>
    </html>
    """

    st.divider()
    st.download_button(
        label="📥 DESCARGAR REPORTE: AJUSTE FINAL CSS",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo}.html",
        mime="text/html"
    )


