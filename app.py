import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image
import base64
from io import BytesIO

# =========================================================
# CONFIGURACIÓN Y CATÁLOGO
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

# =========================================================
# PROCESAMIENTO
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

    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{titulo_final}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
        <style>
            body {{ background-color: #f4f7f6; padding: 0; margin: 0; font-family: 'Segoe UI', sans-serif; overflow-x: hidden; }}
            .header {{ background: #2c3e50; color: white; padding: 15px; text-align: center; border-bottom: 4px solid #1abc9c; }}
            
            #info-bar {{
                position: sticky; top: 0; z-index: 2000;
                background: #f8f9fa; color: #2c3e50; padding: 12px; text-align: center;
                font-weight: bold; border-bottom: 3px solid #1abc9c; font-size: 18px;
                min-height: 54px; width: 100%;
            }}

            #workspace {{ background: #000; position: relative; width: 100%; height: 75vh; overflow: hidden; }}
            #workspace:fullscreen {{ height: 100vh !important; width: 100vw !important; }}
            #viewer-container {{ width: 100%; height: 100%; }}
            
            .custom-nav {{ position: absolute; top: 125px; left: 15px; z-index: 1005; display: flex; flex-direction: column; gap: 8px; }}
            .btn-fs {{ position: absolute; top: 125px; right: 15px; z-index: 1005; background: #fff; border: 2px solid #2c3e50; padding: 8px 16px; border-radius: 20px; font-weight: bold; cursor: pointer; }}

            /* SIDEBAR DERECHO PARA PANTALLA COMPLETA */
            #fs-sidebar {{
                position: absolute; top: 0; right: -320px; width: 300px; height: 100%;
                background: rgba(44, 62, 80, 0.95); backdrop-filter: blur(10px);
                z-index: 3000; transition: 0.3s ease; padding: 25px; color: white;
                box-shadow: -5px 0 15px rgba(0,0,0,0.5); overflow-y: auto;
            }}
            #fs-sidebar.active {{ right: 0; }}
            
            #toggle-sidebar-btn {{
                position: absolute; top: 185px; right: 15px; z-index: 3001;
                background: #1abc9c; color: white; border: 2px solid white;
                padding: 10px; border-radius: 8px; font-weight: bold; display: none; cursor: pointer;
                transition: right 0.3s ease;
            }}
            #fs-sidebar.active ~ #toggle-sidebar-btn {{ right: 315px; }} 
            
            #workspace:fullscreen #toggle-sidebar-btn {{ display: block; }}

            .sidebar-section-title {{ font-size: 12px; font-weight: bold; color: #1abc9c; letter-spacing: 1px; margin-bottom: 15px; border-bottom: 1px solid #3e5871; padding-bottom: 5px; }}
            .nav-btn {{ width: 44px; height: 44px; border-radius: 8px; border: 2px solid white; color: white; font-size: 22px; font-weight: bold; display: flex; align-items: center; justify-content: center; cursor: pointer; }}
            .btn-zoom-in {{ background: #1abc9c !important; }}
            .btn-zoom-out {{ background: #ffb7c5 !important; color: #333 !important; }}
            .btn-home {{ background: #3498db !important; }}

            /* APARIENCIA DE PUNTOS */
            .dot {{ width: 14px; height: 14px; border-radius: 50%; border: none; opacity: 0.7; cursor: pointer; transition: transform 0.2s, opacity 0.2s; }}
            .dot.selected {{ opacity: 1 !important; border: 3px solid #fff !important; box-shadow: 0 0 15px #fff; transform: scale(1.6); z-index: 999 !important; }}

            .report-container {{ position: relative; z-index: 1; background: #f4f7f6; padding-top: 20px; }}
            .summary-card {{ background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 25px; margin-bottom: 40px; }}
            .category-row {{ background: #f1f4f8; border-left: 5px solid #3498db; padding: 10px 15px; margin-top: 15px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; border-radius: 4px; }}
            .item-table {{ width: 100%; margin-bottom: 10px; }}
            .item-table td {{ padding: 10px 15px; border-bottom: 1px solid #eee; }}
            .total-banner {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; text-align: center; font-size: 1.5rem; font-weight: bold; margin-top: 25px; }}
            .filter-section {{ background: white; padding: 15px; border-radius: 12px; margin: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            
            .fs-close-btn {{ float: left; cursor: pointer; font-size: 24px; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="header"><h2>{titulo_final}</h2></div>
        
        <div id="main-filters" class="filter-section">
            <div class="mb-2" id="group-tipo-main">
                <small class="fw-bold text-muted">TIPO DE PIEZA:</small>
                <button class="btn btn-primary btn-sm rounded-pill px-3" data-val="all" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-primary btn-sm rounded-pill px-3 mx-1" data-val="{t}" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t.upper()}</button>' for t in tipos_unicos])}
                <button class="btn btn-outline-secondary btn-sm rounded-pill px-3 mx-1" data-val="none" onclick="updateFilters('tipo', 'none', this)">❌ NINGUNO</button>
            </div>
            <div id="group-color-main">
                <small class="fw-bold text-muted">COLOR:</small>
                <button class="btn btn-success btn-sm rounded-pill px-3" data-val="all" onclick="updateFilters('color', 'all', this)">TODOS</button>
                {' '.join([f'<button class="btn btn-outline-success btn-sm rounded-pill px-3 mx-1" data-val="{c}" onclick="updateFilters(\'color\', \'{c}\', this)">{c.replace("_", " ").upper()}</button>' for c in colores_unicos])}
            </div>
        </div>

        <div id="workspace">
            <div id="fs-sidebar">
                <span class="fs-close-btn" onclick="toggleFsSidebar()">×</span>
                <div style="clear:both;"></div>
                <h5 class="mb-4">🔍 Filtros de Inspección</h5>
                
                <div class="sidebar-section-title">TIPO DE COMPONENTE</div>
                <div class="d-grid gap-2 mb-4" id="group-tipo-fs">
                    <button class="btn btn-primary btn-sm btn-filter-fs" data-val="all" onclick="syncAndFilter('tipo', 'all', this)">TODOS</button>
                    {' '.join([f'<button class="btn btn-outline-light btn-sm btn-filter-fs" data-val="{t}" onclick="syncAndFilter(\'tipo\', \'{t}\', this)">{t.upper()}</button>' for t in tipos_unicos])}
                    <button class="btn btn-outline-secondary btn-sm btn-filter-fs" data-val="none" onclick="syncAndFilter('tipo', 'none', this)">OCULTAR TODO</button>
                </div>

                <div class="sidebar-section-title">FILTRAR POR COLOR</div>
                <div class="d-grid gap-2" id="group-color-fs">
                    <button class="btn btn-success btn-sm btn-filter-fs" data-val="all" onclick="syncAndFilter('color', 'all', this)">TODOS LOS COLORES</button>
                    {' '.join([f'<button class="btn btn-outline-light btn-sm btn-filter-fs" style="text-align: left;" data-val="{c}" onclick="syncAndFilter(\'color\', \'{c}\', this)"><span style="display:inline-block;width:10px;height:10px;background:{COLOR_CATALOG.get(c, "gray")};margin-right:8px;border-radius:50%"></span>{c.replace("_", " ").upper()}</button>' for c in colores_unicos])}
                </div>
            </div>

            <div id="info-bar">Selecciona un punto para ver su detalle</div>
            
            <div class="custom-nav">
                <div id="btn-in" class="nav-btn btn-zoom-in">+</div>
                <div id="btn-out" class="nav-btn btn-zoom-out">−</div>
                <div id="btn-home" class="nav-btn btn-home">🏠</div>
            </div>
            
            <button id="toggle-sidebar-btn" onclick="toggleFsSidebar()">☰ Filtros</button>
            <button class="btn-fs" onclick="toggleFS()">📺 Pantalla Completa</button>
            
            <div id="viewer-container"></div>
        </div>

        <div class="container-fluid report-container">
            <div class="summary-card" id="tables-output"></div>
        </div>

        <script>
            const puntos = {puntos_json};
            const imgW = {width};
            
            const viewer = OpenSeadragon({{
                id: "viewer-container",
                prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                tileSources: {{ type: 'image', url: '{data_uri}' }},
                showNavigationControl: false,
                maxZoomLevel: 80,
                minZoomImageRatio: 1.0,
                visibilityRatio: 1.0,
                constrainDuringPan: true,
                gestureSettingsTouch: {{ clickToZoom: false, dblClickToZoom: false }},
                gestureSettingsMouse: {{ clickToZoom: false, dblClickToZoom: false }}
            }});

            let filterT = 'all', filterC = 'all', lastSelected = null;

            document.addEventListener('fullscreenchange', () => {{
                if (!document.fullscreenElement) {{
                    document.getElementById('fs-sidebar').classList.remove('active');
                }}
                setTimeout(() => {{ viewer.viewport.goHome(); }}, 100);
            }});

            function toggleFsSidebar() {{
                document.getElementById('fs-sidebar').classList.toggle('active');
            }}

            // Lógica unificada para iluminar botones
            function highlightButtons(groupId, value, activeClass, outlineClass) {{
                const container = document.getElementById(groupId);
                container.querySelectorAll('.btn').forEach(btn => {{
                    if (btn.getAttribute('data-val') === value) {{
                        btn.classList.remove(outlineClass);
                        btn.classList.add(activeClass);
                    }} else {{
                        btn.classList.remove(activeClass);
                        btn.classList.add(outlineClass);
                    }}
                }});
            }}

            function syncAndFilter(mode, value, btn) {{
                if (mode === 'tipo') {{
                    filterT = value;
                    highlightButtons('group-tipo-fs', value, (value==='none'?'btn-secondary':'btn-primary'), (value==='none'?'btn-outline-secondary':'btn-outline-light'));
                    highlightButtons('group-tipo-main', value, (value==='none'?'btn-secondary':'btn-primary'), (value==='none'?'btn-outline-secondary':'btn-outline-primary'));
                }} else {{
                    filterC = value;
                    highlightButtons('group-color-fs', value, 'btn-success', 'btn-outline-light');
                    highlightButtons('group-color-main', value, 'btn-success', 'btn-outline-success');
                }}
                drawPoints();
            }}

            function updateFilters(mode, value, btn) {{
                syncAndFilter(mode, value, btn);
            }}

            function getContrastColor(hex) {{
                if (hex.indexOf('#') === 0) hex = hex.slice(1);
                const cssColors = {{ 'purple': '800080', 'black': '000000', 'royalblue': '4169E1', 'crimson': 'DC143C', 'gray': '808080' }};
                if (cssColors[hex]) hex = cssColors[hex];
                if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
                if (hex.length !== 6) return '#2c3e50';
                const r = parseInt(hex.slice(0, 2), 16);
                const g = parseInt(hex.slice(2, 4), 16);
                const b = parseInt(hex.slice(4, 6), 16);
                const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
                return (yiq >= 128) ? '#2c3e50' : '#ffffff';
            }}

            viewer.addHandler('open', drawPoints);

            function drawPoints() {{
                viewer.clearOverlays();
                const bar = document.getElementById('info-bar');
                
                if (filterT === 'none') {{
                    bar.innerHTML = "MODO DE INSPECCIÓN: PUNTOS OCULTOS";
                    bar.style.backgroundColor = "#f8f9fa";
                    bar.style.color = "#2c3e50";
                    renderSummary([]);
                    return;
                }} else {{
                    bar.innerHTML = "Selecciona un punto para ver su detalle";
                    bar.style.backgroundColor = "#f8f9fa";
                    bar.style.color = "#2c3e50";
                }}

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
                        elt.classList.add('selected'); 
                        lastSelected = elt;
                        bar.style.backgroundColor = p.color_plot;
                        bar.style.color = getContrastColor(p.color_plot);
                        bar.innerHTML = "SELECCIONADO: " + p.tipo.toUpperCase() + " | " + p.color_norm.replace(/_/g, ' ').toUpperCase() + " (" + p.tamaño + ")";
                    }});
                    
                    viewer.addOverlay({{ element: elt, location: new OpenSeadragon.Point(p.x/imgW, p.y/imgW), placement: 'CENTER' }});
                }});
                renderSummary(filtered);
            }}

            function renderSummary(data) {{
                const container = document.getElementById('tables-output');
                const groups = {{}};
                let totalGral = 0;
                const summaryData = (filterT === 'none') ? puntos : data;

                summaryData.forEach(p => {{
                    totalGral++;
                    if(!groups[p.tipo]) groups[p.tipo] = {{}};
                    const key = p.color_norm.replace(/_/g, ' ').toUpperCase() + " (" + p.tamaño + ")";
                    groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                }});

                let html = '<h4 class="fw-bold mb-4">RESUMEN DE COMPONENTES</h4>';
                for(let t in groups) {{
                    let subtotal = Object.values(groups[t]).reduce((a, b) => a + b, 0);
                    html += '<div class="category-row"><span>' + t.toUpperCase() + '</span><span class="badge bg-primary">' + subtotal + ' pz</span></div>';
                    html += '<table class="item-table"><tbody>';
                    for(let k in groups[t]) {{
                        html += '<tr><td>' + k + '</td><td class="text-end fw-bold">' + groups[t][k] + ' pz</td></tr>';
                    }}
                    html += '</tbody></table>';
                }}
                html += '<div class="total-banner">CANTIDAD TOTAL: ' + totalGral + ' PIEZAS</div>';
                container.innerHTML = html;
            }}

            function toggleFS() {{
                const el = document.getElementById("workspace");
                if (!document.fullscreenElement) {{
                    el.requestFullscreen().catch(err => {{ alert("Error: " + err.message); }});
                }} else {{
                    document.exitFullscreen();
                }}
            }}

            document.getElementById('btn-in').onclick = () => viewer.viewport.zoomBy(1.4);
            document.getElementById('btn-out').onclick = () => viewer.viewport.zoomBy(0.7);
            document.getElementById('btn-home').onclick = () => viewer.viewport.goHome();
        </script>
    </body>
    </html>
    """
    st.divider()
    st.download_button(label="📥 DESCARGAR REPORTE CON FILTROS INTELIGENTES", data=html_report, file_name=f"{titulo_final}.html", mime="text/html")
