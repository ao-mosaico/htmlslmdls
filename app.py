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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=10.0, user-scalable=yes">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #f0f2f5; font-family: sans-serif; margin: 0; padding: 10px; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 15px; }}
            #viewer-container {{ width: 100%; height: 75vh; background: #333; border-radius: 12px; position: relative; }}
            .filter-card {{ background: white; padding: 15px; border-radius: 12px; margin-bottom: 15px; }}
            .btn-filter {{ border-radius: 20px; font-size: 11px; margin: 2px; text-transform: uppercase; }}
            
            .dot {{ 
                width: 10px; height: 10px; 
                border-radius: 50%; border: 1px solid white; 
                cursor: pointer; pointer-events: auto; z-index: 10;
                box-shadow: 0 0 2px rgba(0,0,0,0.5);
                box-sizing: border-box; 
                transition: transform 0.2s ease;
            }}
            
            .dot.active {{
                border: 2px solid #fff;
                box-shadow: 0 0 12px #ffeb3b, 0 0 5px #ffeb3b inset;
                transform: scale(1.6);
                z-index: 20;
            }}
            
            /* ESTILO DEL CUADRO DE INFORMACIÓN (MODO OVERLAY) */
            .info-box {{
                background: rgba(0, 0, 0, 0.85);
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 11px;
                pointer-events: none;
                white-space: nowrap;
                border: 1px solid #555;
                box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                z-index: 1000;
            }}
        </style>
    </head>
    <body>
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
            let currentSelectedDot = null;
            let currentOverlayId = "active-info";

            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                gestureSettingsTouch: {{ pinchRotate: false, clickToZoom: false, dblClickToZoom: true }},
                gestureSettingsMouse: {{ clickToZoom: false }},
                showNavigationControl: false,
                defaultZoomLevel: 0,
                minZoomLevel: 0,
                maxZoomLevel: 50,
                visibilityRatio: 1,
                constrainDuringPan: true,
                detectRetina: false
            }});

            function drawPoints() {{
                viewer.clearOverlays();
                const filtered = puntos.filter(p => {{
                    const mt = (filterT === 'all' || p.tipo === filterT);
                    const mc = (filterC === 'all' || p.color_norm === filterC);
                    return mt && mc;
                }});

                filtered.forEach((p, index) => {{
                    const elt = document.createElement("div");
                    elt.className = "dot";
                    elt.id = "dot-" + index;
                    elt.style.backgroundColor = p.color_plot;
                    
                    const handleSelect = (e) => {{
                        if(e) {{ e.preventDefault(); e.stopPropagation(); }}

                        // Limpiar anterior
                        if (currentSelectedDot) currentSelectedDot.classList.remove('active');
                        viewer.removeOverlay(currentOverlayId);

                        // Activar punto
                        elt.classList.add('active');
                        currentSelectedDot = elt;

                        // Crear Cuadro de Información como Overlay
                        const info = document.createElement("div");
                        info.id = currentOverlayId;
                        info.className = "info-box";
                        info.innerHTML = `<b>${{p.tipo.toUpperCase()}}</b><br>${{p.color_norm}} | ${{p.tamaño}}`;

                        viewer.addOverlay({{
                            element: info,
                            location: new OpenSeadragon.Point(p.x / imgW, (p.y / imgW) - (15/imgW)), // Un poco arriba del punto
                            placement: OpenSeadragon.Placement.BOTTOM // Se ancla abajo para quedar sobre el punto
                        }});
                    }};
                    
                    elt.addEventListener('click', handleSelect);
                    elt.addEventListener('touchstart', handleSelect, {{passive: false}});

                    viewer.addOverlay({{
                        element: elt,
                        location: new OpenSeadragon.Point(p.x / imgW, p.y / imgW),
                        placement: OpenSeadragon.Placement.CENTER
                    }});
                }});
                renderTables(filtered);
            }}

            // Cerrar al tocar el fondo
            viewer.addHandler('canvas-click', function(event) {{
                if (!event.originalTarget.classList.contains('dot')) {{
                    viewer.removeOverlay(currentOverlayId);
                    if (currentSelectedDot) {{
                        currentSelectedDot.classList.remove('active');
                        currentSelectedDot = null;
                    }}
                }}
            }});

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
        label="📥 DESCARGAR REPORTE: CORRECCIÓN DE CUADROS",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo}.html",
        mime="text/html"
    )



