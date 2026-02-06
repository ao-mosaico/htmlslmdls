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
            body {{ background-color: #f0f2f5; font-family: sans-serif; margin: 0; padding: 10px; overflow-x: hidden; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 15px; }}
            #viewer-container {{ width: 100%; height: 75vh; background: #333; border-radius: 12px; position: relative; }}
            .filter-card {{ background: white; padding: 15px; border-radius: 12px; margin-bottom: 15px; }}
            
            .dot {{ 
                width: 10px; height: 10px; 
                border-radius: 50%; border: 1px solid white; 
                cursor: pointer; pointer-events: auto;
                box-sizing: border-box; 
            }}
            
            .dot.active {{
                border: 2px solid #fff;
                box-shadow: 0 0 10px #ffeb3b, 0 0 5px #ffeb3b inset;
                transform: scale(1.6);
            }}

            /* TOOLTIP GLOBAL FLOTANTE */
            #floating-info {{
                position: fixed;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 10px 15px;
                border-radius: 8px;
                font-size: 13px;
                display: none;
                z-index: 9999;
                pointer-events: none;
                border: 1px solid #444;
                box-shadow: 0 4px 20px rgba(0,0,0,0.6);
                text-align: center;
                min-width: 120px;
            }}
        </style>
    </head>
    <body>
        <div id="floating-info"></div>
        
        <div class="header">
            <h1 style="font-size: 1.4rem; margin: 0;">REPORTE DE COMPONENTES</h1>
            <div style="color: #3498db; font-weight: bold;">{nombre_modelo.upper() if nombre_modelo else 'SIN NOMBRE'}</div>
        </div>

        <div class="filter-card">
            <div id="tipo-filters">
                <button class="btn btn-primary btn-sm rounded-pill" style="font-size:10px;" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill" style="font-size:10px; margin:2px;" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t}</button>' for t in tipos_unicos])}
            </div>
        </div>

        <div id="viewer-container"></div>

        <div class="filter-card mt-3" id="tables-output"></div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            const imgH = {height};
            let filterT = 'all';
            let currentSelectedDot = null;
            let currentData = null;
            
            const tooltip = document.getElementById('floating-info');

            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                gestureSettingsTouch: {{ clickToZoom: false, dblClickToZoom: true }},
                gestureSettingsMouse: {{ clickToZoom: false }},
                showNavigationControl: false,
                defaultZoomLevel: 0,
                maxZoomLevel: 50,
                detectRetina: false
            }});

            function drawPoints() {{
                viewer.clearOverlays();
                const filtered = puntos.filter(p => filterT === 'all' || p.tipo === filterT);

                filtered.forEach((p) => {{
                    const elt = document.createElement("div");
                    elt.className = "dot";
                    elt.style.backgroundColor = p.color_plot;
                    
                    const handleAction = (e) => {{
                        e.preventDefault();
                        e.stopPropagation();

                        if (currentSelectedDot) currentSelectedDot.classList.remove('active');
                        elt.classList.add('active');
                        currentSelectedDot = elt;
                        currentData = p;

                        updateTooltipPosition();
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

            function updateTooltipPosition() {{
                if (!currentSelectedDot || !currentData) return;

                // Obtener posición real del punto en la pantalla del dispositivo
                const rect = currentSelectedDot.getBoundingClientRect();
                
                tooltip.style.display = 'block';
                tooltip.innerHTML = `<b>${{currentData.tipo.toUpperCase()}}</b><br>${{currentData.color_norm}}<br>${{currentData.tamaño}}`;
                
                // Posicionar arriba del punto
                const x = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2);
                const y = rect.top - tooltip.offsetHeight - 15;

                tooltip.style.left = x + 'px';
                tooltip.style.top = y + 'px';
            }}

            // Mantener el cuadro pegado al punto durante el zoom o movimiento
            viewer.addHandler('animation', updateTooltipPosition);
            viewer.addHandler('canvas-drag', updateTooltipPosition);
            viewer.addHandler('canvas-scroll', updateTooltipPosition);

            viewer.addHandler('canvas-click', () => {{
                tooltip.style.display = 'none';
                if (currentSelectedDot) currentSelectedDot.classList.remove('active');
                currentSelectedDot = null;
            }});

            function updateFilters(mode, val, btn) {{
                const parent = btn.parentElement;
                parent.querySelectorAll('.btn').forEach(b => {{ b.classList.remove('btn-primary'); b.classList.add('btn-outline-primary'); }});
                btn.classList.add('btn-primary'); btn.classList.remove('btn-outline-primary');
                filterT = val;
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
                let html = '<h5 class="text-primary">Resumen de Materiales</h5>';
                for(const t in groups) {{
                    html += `<div class="mt-2"><strong>${{t.toUpperCase()}}</strong></div>
                             <table class="table table-sm" style="font-size: 11px;"><tbody>`;
                    for(const sk in groups[t]) {{
                        const [c, tam] = sk.split('|');
                        html += `<tr><td>${{c}}</td><td>${{tam}}</td><td>${{groups[t][sk]}} pz</td></tr>`;
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
        label="📥 DESCARGAR REPORTE: SOLUCIÓN DEFINITIVA",
        data=html_report,
        file_name=f"Reporte_{nombre_modelo}.html",
        mime="text/html"
    )

