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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #eceff1; padding: 10px; font-family: sans-serif; }}
            .header {{ background: #263238; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 10px; }}
            
            /* BARRA DE INFORMACIÓN FIJA */
            #info-bar {{
                background: #ffd600;
                color: #000;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 10px;
                text-align: center;
                font-weight: bold;
                min-height: 50px;
                border: 2px solid #000;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }}

            #viewer-container {{ width: 100%; height: 60vh; background: #000; border-radius: 8px; position: relative; }}
            
            .filter-card {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            
            .dot {{ 
                width: 12px; height: 12px; 
                border-radius: 50%; border: 2px solid white; 
                cursor: pointer; pointer-events: auto !important;
            }}
            .dot:active {{ transform: scale(2); background-color: yellow !important; }}

            .total-banner {{
                background: #0277bd;
                color: white;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                font-size: 1.2rem;
                font-weight: bold;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="font-size: 1rem; margin: 0;">MODELO: {nombre_modelo.upper() if nombre_modelo else 'PENDIENTE'}</h2>
        </div>

        <div id="info-bar">Toca un cristal para ver sus detalles</div>

        <div class="filter-card">
            <div class="mb-2">
                <small class="fw-bold">TIPO:</small>
                <button class="btn btn-primary btn-sm rounded-pill px-2" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill px-2 mx-1" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t}</button>' for t in tipos_unicos])}
            </div>
            <div>
                <small class="fw-bold">COLOR:</small>
                <button class="btn btn-success btn-sm rounded-pill px-2" onclick="updateFilters('color', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-success btn-sm rounded-pill px-2 mx-1" onclick="updateFilters(\'color\', \'{c}\', this)">{c}</button>' for c in colores_unicos])}
            </div>
        </div>

        <div id="viewer-container"></div>
        <div class="filter-card mt-3" id="tables-output"></div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            let filterT = 'all';
            let filterC = 'all';
            
            const infoBar = document.getElementById('info-bar');

            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                showNavigationControl: false,
                maxZoomLevel: 50,
                // DESACTIVAR ZOOM POR CLIC PARA QUE NO ROBE EL EVENTO AL PUNTO
                gestureSettingsTouch: {{ clickToZoom: false, dblClickToZoom: false }},
                gestureSettingsMouse: {{ clickToZoom: false, dblClickToZoom: false }}
            }});

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
                    
                    // Acción al tocar
                    const action = (e) => {{
                        e.preventDefault();
                        e.stopPropagation(); // Evita que OpenSeadragon mueva el mapa
                        
                        infoBar.innerHTML = "SELECCIONADO: " + p.tipo.toUpperCase() + " | " + p.color_norm + " | " + p.tamaño;
                        infoBar.style.backgroundColor = "#ccff00";
                    }};

                    elt.addEventListener('pointerdown', action); // Mejor para móviles que click

                    viewer.addOverlay({{
                        element: elt,
                        location: new OpenSeadragon.Point(p.x / imgW, p.y / imgW),
                        placement: OpenSeadragon.Placement.CENTER
                    }});
                }});
                
                renderSummary(filtered);
            }}

            function updateFilters(mode, val, btn) {{
                const parent = btn.parentElement;
                const activeC = mode === 'tipo' ? 'btn-primary' : 'btn-success';
                const outlineC = mode === 'tipo' ? 'btn-outline-primary' : 'btn-outline-success';
                parent.querySelectorAll('.btn').forEach(b => {{ b.classList.remove(activeC); b.classList.add(outlineC); }});
                btn.classList.add(activeC); btn.classList.remove(outlineC);
                if (mode === 'tipo') filterT = val; else filterC = val;
                drawPoints();
            }}

            function renderSummary(data) {{
                const container = document.getElementById('tables-output');
                const groups = {{}};
                let totalGral = 0;

                data.forEach(p => {{
                    totalGral++;
                    if(!groups[p.tipo]) groups[p.tipo] = {{}};
                    const key = p.color_norm + " (" + p.tamaño + ")";
                    groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                }});

                let html = '<h6 class="text-primary border-bottom pb-2">RESUMEN DE MATERIALES</h6>';
                for(let t in groups) {{
                    html += '<div class="mt-2 small"><strong>' + t.toUpperCase() + '</strong></div>';
                    html += '<table class="table table-sm table-striped mb-0" style="font-size: 11px;"><tbody>';
                    for(let k in groups[t]) {{
                        html += '<tr><td>' + k + '</td><td class="text-end"><b>' + groups[t][k] + '</b> pz</td></tr>';
                    }}
                    html += '</tbody></table>';
                }}
                
                html += '<div class="total-banner">CANTIDAD TOTAL: ' + totalGral + ' PIEZAS</div>';
                container.innerHTML = html;
            }}

            viewer.addHandler('open', drawPoints);
        </script>
    </body>
    </html>
    """

    st.divider()
    st.download_button(
        label="📥 DESCARGAR REPORTE: VERSIÓN ULTRA-COMPATIBLE",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo}.html",
        mime="text/html"
    )
