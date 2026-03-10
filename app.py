import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image
import base64
from io import BytesIO

# =========================================================
# CONFIGURACIÓN Y CATÁLOGO
# =========================================================
# Se agregó initial_sidebar_state="expanded" para mantener el panel abierto
st.set_page_config(page_title="Gestor de Mosaicos Pro", layout="wide", initial_sidebar_state="expanded")

COLOR_CATALOG = {
    "plata": "silver", "dorado": "gold", "rosa": "pink",
    "ab_aguamarina": "aquamarine", "ab_amatista": "mediumpurple",
    "ab_cristal": "lightcyan", "ab_peridot": "lightgreen",
    "ab_rose": "lightpink", "ab_zafiro": "deepskyblue",
    "aguamarina": "turquoise", "amatista": "purple",
    "black_diamond": "black", "blue_zircon": "darkturquoise",
    "cristal": "silver", "fuschia": "fuchsia", "fuschua": "fuchsia", "jet": "black",
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
    "morado": "#7A288A", "otro": "#D3D3D3",
    "vitral": "#9370DB", "ab_tanzanita": "#483D8B"
}

def normalizar_color(c):
    if pd.isna(c) or c == "": return "sin_color"
    return str(c).lower().strip().replace(" ", "_")

def ajustar_color_por_tipo(row):
    tipo = str(row["tipo"]).lower()
    color = row["color_norm"]
    if tipo == "microperla" or tipo == "marquiz": return color if color in COLOR_CATALOG else "otro"
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

st.sidebar.divider()
st.sidebar.subheader("Ajustes del Reporte")
# Nuevo slider para controlar el agrupamiento
sensibilidad_cluster = st.sidebar.slider(
    "Sensibilidad de Agrupamiento (%)", 
    min_value=1, 
    max_value=50, 
    value=10, 
    step=1,
    help="Define qué tan cerca deben estar las piezas para contarse juntas en el Modo Diagrama. Auméntalo si las etiquetas se enciman."
)

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
                
                # Asignación de tamaño por defecto según el tipo
                tamaño_defecto = ""
                if tipo == "microperla": tamaño_defecto = "pp01"
                elif tipo == "marquiz": tamaño_defecto = "6x3mm"
                elif tipo == "cristal": tamaño_defecto = "ss18"

                rows.append({
                    "x": x, "y": y, "tipo": tipo, 
                    "color_norm": normalizar_color(attrs.get("color", "")), 
                    "tamaño": attrs.get("tamaño", tamaño_defecto),
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

            /* SIDEBAR DERECHO */
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

            /* ESTILO BOTONES Y PUNTOS */
            .btn-primary, .btn-success, .btn-secondary {{ color: white !important; }}
            .sidebar-section-title {{ font-size: 12px; font-weight: bold; color: #1abc9c; letter-spacing: 1px; margin-bottom: 15px; border-bottom: 1px solid #3e5871; padding-bottom: 5px; }}
            .nav-btn {{ width: 44px; height: 44px; border-radius: 8px; border: 2px solid white; color: white; font-size: 22px; font-weight: bold; display: flex; align-items: center; justify-content: center; cursor: pointer; }}
            .btn-zoom-in {{ background: #1abc9c !important; }}
            .btn-zoom-out {{ background: #ffb7c5 !important; color: #333 !important; }}
            .btn-home {{ background: #3498db !important; }}
            .btn-diagrama {{ background: #f39c12 !important; font-size: 20px; }}

            .dot {{ width: 14px; height: 14px; border-radius: 50%; border: none; opacity: 0.7; cursor: pointer; transition: transform 0.2s, opacity 0.2s; }}
            .dot.selected {{ opacity: 1 !important; border: 3px solid #fff !important; box-shadow: 0 0 15px #fff; transform: scale(1.6); z-index: 999 !important; }}

            /* ETIQUETAS DEL MODO DIAGRAMA (Rayita removida) */
            .diagram-label {{
                background: rgba(255, 255, 255, 0.95);
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                color: #2c3e50;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                pointer-events: none;
                white-space: nowrap;
                position: relative;
                border-left: 5px solid #000;
                font-family: monospace;
            }}

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
                <div class="d-grid


