import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image
import base64
from io import BytesIO
import re      
import json    
import zipfile 

# =========================================================
# CONFIGURACIÓN Y CATÁLOGO.
# =========================================================
st.set_page_config(page_title="Gestor de Mosaicos Pro", layout="wide")

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
    "vitral": "#9370DB", "ab_tanzanita": "#483D8B",
    "fuschia_metalico": "#FF1493"
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
# INTERFAZ PRINCIPAL CON PESTAÑAS
# =========================================================
try:
    banner_img = Image.open("banner_mosaico.png")
    st.image(banner_img, use_container_width=True)
except Exception:
    pass 

st.title("💎 Gestor de Mosaicos Pro")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["✨ Crear Nuevo Reporte", "🛠️ Reparar HTMLs", "📊 Tabla de Resumen"])

# =========================================================
# PESTAÑA 1: CREAR NUEVO HTML
# =========================================================
with tab1:
    st.subheader("Generador de Reporte Interactivo")
    
    col_a, col_b = st.columns(2)
    with col_a:
        nombre_modelo = st.text_input("Nombre del Modelo (Ej: PB-8612 A)")
        xml_file = st.file_uploader("1. Subir archivo XML", type=["xml"])
    with col_b:
        st.write("") 
        st.write("")
        img_file = st.file_uploader("2. Subir Imagen base", type=["jpg", "png", "jpeg"])

    if xml_file and img_file:
        with st.spinner("Procesando componentes..."):
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
            
            filas_limpias = []
            coordenadas_vistas = set()
            for row in rows:
                coord_id = (round(row["x"], 2), round(row["y"], 2))
                if coord_id not in coordenadas_vistas:
                    filas_limpias.append(row)
                    coordenadas_vistas.add(coord_id)
            rows = filas_limpias

            df = pd.DataFrame(rows)
            df["color_norm"] = df.apply(ajustar_color_por_tipo, axis=1)
            df["color_plot"] = df["color_norm"].map(lambda x: COLOR_CATALOG.get(x, "gray"))

            img = Image.open(img_file)
            width, height = img.size
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            data_uri = f"data:image/jpeg;base64,{img_base64}"

            logo_uri = ""
            mostrar_logo = "none"
            try:
                logo_img = Image.open("banner_mosaico.png")
                buffered_logo = BytesIO()
                logo_img.save(buffered_logo, format="PNG")
                logo_base64 = base64.b64encode(buffered_logo.getvalue()).decode()
                logo_uri = f"data:image/png;base64,{logo_base64}"
                mostrar_logo = "inline-block"
            except Exception:
                pass 

            puntos_json = df.to_json(orient='records')
            tipos_unicos = sorted(df["tipo"].unique().tolist())
            colores_unicos = sorted(df["color_norm"].unique().tolist())
            titulo_final = f"Componentes {nombre_modelo}" if nombre_modelo else "Componentes"

            btn_tipo_main = ' '.join([f'<button class="btn-custom-filter" data-val="{t}" onclick="updateFilters(\'tipo\', \'{t}\', this)">{t.upper()}</button>' for t in tipos_unicos])
            btn_color_main = ' '.join([f'<button class="btn-custom-filter" data-val="{c}" onclick="updateFilters(\'color\', \'{c}\', this)">{c.replace("_", " ").upper()}</button>' for c in colores_unicos])
            
            btn_tipo_fs = ' '.join([f'<button class="btn btn-outline-light btn-sm btn-filter-fs" data-val="{t}" onclick="syncAndFilter(\'tipo\', \'{t}\', this)">{t.upper()}</button>' for t in tipos_unicos])
            btn_color_fs = ' '.join([f'<button class="btn btn-outline-light btn-sm btn-filter-fs" style="text-align: left;" data-val="{c}" onclick="syncAndFilter(\'color\', \'{c}\', this)"><span style="display:inline-block;width:10px;height:10px;background:{COLOR_CATALOG.get(c, "gray")};margin-right:8px;border-radius:50%"></span>{c.replace("_", " ").upper()}</button>' for c in colores_unicos])

            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>__TITULO_FINAL__</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0, shrink-to-fit=no">
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
                <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
                <style>
                    /* FIX RESPONSIVO GLOBAL: Bloqueo de scroll horizontal */
                    * { box-sizing: border-box; }
                    html, body { 
                        background-color: #f4f7f6; padding: 0; margin: 0; 
                        font-family: 'Segoe UI', sans-serif; 
                        width: 100%; max-width: 100vw; overflow-x: hidden; 
                        touch-action: manipulation; 
                    }
                    
                    .header { background: white; color: black; padding: 25px 15px; text-align: center; border-bottom: 4px solid #1abc9c; width: 100%; }
                    .header h2 { 
                        font-family: 'Montserrat', sans-serif; 
                        letter-spacing: 3px; 
                        text-transform: uppercase;
                        font-weight: 700;
                        margin: 0;
                        font-size: 1.8rem;
                        word-wrap: break-word;
                    }
                    
                    /* NUEVA ESTRUCTURA INFO-BAR: Ahora vive afuera del lienzo para no estorbar a los botones */
                    #info-bar {
                        position: sticky; top: 0; z-index: 2000;
                        background: #f8f9fa; color: #2c3e50; padding: 12px 10px; text-align: center;
                        font-weight: bold; border-bottom: 3px solid #1abc9c; font-size: 18px;
                        width: 100%; display: block;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                        white-space: normal; word-wrap: break-word; /* Previene ensanchamiento por textos largos */
                    }

                    /* FIX WORKSPACE: Strict width bounds */
                    #workspace { background: #000; position: relative; width: 100%; max-width: 100vw; height: 75vh; overflow: hidden; display: block; }
                    #workspace:fullscreen { height: 100vh !important; width: 100vw !important; }
                    #viewer-container { width: 100%; height: 100%; touch-action: none; }
                    
                    /* BOTONES REPOSICIONADOS: Ya que la barra superior salió, los botones suben al top: 15px */
                    .custom-nav { position: absolute; top: 15px; left: 15px; z-index: 1005; display: flex; flex-direction: column; gap: 8px; }
                    .nav-btn { width: 44px; height: 44px; border-radius: 8px; border: 2px solid white; color: white; font-size: 22px; font-weight: bold; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s;}
                    .nav-btn:hover { transform: scale(1.1); }
                    .btn-zoom-in { background: #1abc9c !important; }
                    .btn-zoom-out { background: #ffb7c5 !important; color: #333 !important; }
                    .btn-home { background: #3498db !important; }
                    .btn-diagrama { background: #f39c12 !important; font-size: 20px; }

                    .btn-fs { position: absolute; top: 15px; right: 15px; z-index: 1005; background: #fff; border: 2px solid #2c3e50; padding: 8px 16px; border-radius: 20px; font-weight: bold; cursor: pointer; }

                    #fs-sidebar {
                        position: absolute; top: 0; right: -320px; width: 300px; height: 100%;
                        background: rgba(44, 62, 80, 0.95); backdrop-filter: blur(10px);
                        z-index: 3000; transition: 0.3s ease; padding: 25px; color: white;
                        box-shadow: -5px 0 15px rgba(0,0,0,0.5); overflow-y: auto;
                    }
                    #fs-sidebar.active { right: 0; }
                    
                    #toggle-sidebar-btn {
                        position: absolute; top: 70px; right: 15px; z-index: 3001;
                        background: #1abc9c; color: white; border: 2px solid white;
                        padding: 10px; border-radius: 8px; font-weight: bold; display: none; cursor: pointer;
                        transition: right 0.3s ease;
                    }
                    #fs-sidebar.active ~ #toggle-sidebar-btn { right: 315px; } 
                    #workspace:fullscreen #toggle-sidebar-btn { display: block; }

                    .sidebar-section-title { font-size: 12px; font-weight: bold; color: #1abc9c; letter-spacing: 1px; margin-bottom: 15px; border-bottom: 1px solid #3e5871; padding-bottom: 5px; }
                    
                    .dot { 
                        width: 18px; height: 18px; border-radius: 50%; border: none; 
                        opacity: 0.85; cursor: pointer; 
                        transition: transform 0.1s ease, opacity 0.1s ease; 
                        will-change: transform; 
                    }
                    .dot.selected { opacity: 1 !important; border: 3px solid #fff !important; box-shadow: 0 0 15px #fff; transform: scale(1.6); z-index: 999 !important; }

                    .diagram-label {
                        background: rgba(255, 255, 255, 0.90);
                        backdrop-filter: blur(4px);
                        padding: 6px 12px;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: bold;
                        color: #2c3e50;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                        pointer-events: none;
                        white-space: nowrap;
                        font-family: monospace;
                        will-change: transform;
                    }

                    .report-container { position: relative; z-index: 1; background: #f4f7f6; padding-top: 20px; width: 100%; max-width: 1200px; margin: 0 auto; }
                    .summary-card { background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 25px; margin: 0 15px 40px 15px; }
                    .category-row { background: #f1f4f8; border-left: 5px solid #3498db; padding: 10px 15px; margin-top: 15px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; border-radius: 4px; }
                    .item-table { width: 100%; margin-bottom: 10px; table-layout: fixed; }
                    .item-table td { padding: 10px 15px; border-bottom: 1px solid #eee; word-wrap: break-word; }
                    
                    .total-banner { background: black; color: white; padding: 25px; border-radius: 8px; text-align: center; font-size: 1.6rem; font-weight: 700; margin-top: 25px; font-family: 'Montserrat', sans-serif; letter-spacing: 1px; }
                    
                    .filter-section { 
                        background: white; padding: 20px 25px; border-radius: 12px; margin: 20px auto; 
                        box-shadow: 0 4px 15px rgba(0,0,0,0.04); font-family: 'Montserrat', sans-serif;
                        width: calc(100% - 30px); max-width: 1200px;
                    }
                    .filter-group-title { 
                        font-size: 0.85rem; font-weight: 700; color: #7f8c8d; text-transform: uppercase; 
                        letter-spacing: 1.5px; margin-bottom: 12px; display: block; 
                        border-bottom: 2px solid #ecf0f1; padding-bottom: 6px; width: 100%;
                    }
                    .filter-container { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
                    
                    .btn-custom-filter { 
                        background: #f8f9fa; color: #34495e; border: 1px solid #dcdde1; border-radius: 6px; 
                        padding: 8px 14px; font-size: 0.8rem; font-weight: 600; 
                        transition: all 0.2s ease; cursor: pointer; text-transform: uppercase;
                        touch-action: manipulation;
                    }
                    .btn-custom-filter:hover { background: #ecf0f1; border-color: #bdc3c7; transform: translateY(-1px); }
                    
                    .btn-custom-active-tipo { background: #2c3e50 !important; color: white !important; border-color: #2c3e50 !important; box-shadow: 0 4px 8px rgba(44,62,80,0.2); }
                    .btn-custom-active-color { background: #1abc9c !important; color: white !important; border-color: #1abc9c !important; box-shadow: 0 4px 8px rgba(26,188,156,0.2); }
                    .btn-custom-active-none { background: #e74c3c !important; color: white !important; border-color: #e74c3c !important; box-shadow: 0 4px 8px rgba(231,76,60,0.2); }
                    
                    /* ========================================= */
                    /* MEDIA QUERIES PARA MÓVILES (Smartphones)  */
                    /* ========================================= */
                    @media (max-width: 768px) {
                        .header { padding: 15px 10px; }
                        .header h2 { font-size: 1.3rem; letter-spacing: 1px; }
                        
                        .filter-section { width: calc(100% - 20px); padding: 15px 12px; margin: 10px auto; }
                        .btn-custom-filter { padding: 6px 10px; font-size: 0.7rem; }
                        .filter-group-title { font-size: 0.75rem; margin-bottom: 8px; }
                        
                        #info-bar { font-size: 13px; padding: 10px; }
                        
                        .summary-card { padding: 15px; margin: 0 10px 30px 10px; }
                        .category-row { font-size: 0.9rem; padding: 8px 10px; }
                        .item-table td { padding: 8px 10px; font-size: 0.85rem; }
                        .total-banner { font-size: 1.2rem; padding: 15px; margin-top: 15px; }
                        
                        /* Ajuste perfecto de controles sobre el lienzo negro */
                        .custom-nav { top: 10px; left: 10px; transform: scale(0.85); transform-origin: top left; }
                        .btn-fs { top: 10px; right: 10px; padding: 6px 12px; font-size: 11px; }
                        #toggle-sidebar-btn { top: 55px; right: 10px; font-size: 11px; padding: 6px 10px; }
                        
                        #workspace { height: 65vh; } /* Da más aire para scrollear la página */
                    }

                    .fs-close-btn { float: left; cursor: pointer; font-size: 24px; margin-bottom: 10px; }
                </style>
            </head>
            <body>
                <div style="background: white; text-align: center; padding-top: 20px; width: 100%; overflow: hidden;">
                    <img src="__LOGO_URI__" alt="Mosaico" style="max-height: 85px; max-width: 90%; object-fit: contain; display: __MOSTRAR_LOGO__;">
                </div>
                
                <div class="header" style="border-top: none; padding-top: 10px;">
                    <h2>__TITULO_FINAL__</h2>
                </div>
                
                <div id="main-filters" class="filter-section">
                    <div class="mb-4 filter-container" id="group-tipo-main">
                        <span class="filter-group-title">TIPO DE PIEZA</span>
                        <button class="btn-custom-filter btn-custom-active-tipo" data-val="all" onclick="updateFilters('tipo', 'all', this)">TODOS</button>
                        __BTN_TIPO_MAIN__
                        <button class="btn-custom-filter" data-val="none" onclick="updateFilters('tipo', 'none', this)">❌ NINGUNO</button>
                    </div>
                    <div class="filter-container" id="group-color-main">
                        <span class="filter-group-title">COLOR</span>
                        <button class="btn-custom-filter btn-custom-active-color" data-val="all" onclick="updateFilters('color', 'all', this)">TODOS</button>
                        __BTN_COLOR_MAIN__
                    </div>
                </div>

                <div id="info-bar">Selecciona un punto para ver su detalle</div>

                <div id="workspace">
                    <div id="fs-sidebar">
                        <span class="fs-close-btn" onclick="toggleFsSidebar()">×</span>
                        <div style="clear:both;"></div>
                        <h5 class="mb-4">🔍 Filtros de Inspección</h5>
                        
                        <div class="sidebar-section-title" style="margin-top: 20px;">NIVEL DE AGRUPAMIENTO DIAGRAMA</div>
                        <p style="font-size: 11px; color: #bdc3c7; line-height: 1.3; margin-bottom: 8px;">Ajusta la barra para dividir los componentes en grupos o juntar las cantidades:</p>
                        <input type="range" id="sensitivity-slider" min="10" max="50" value="15" style="width: 100%; cursor: pointer;">
                        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #ecf0f1; margin-bottom: 25px; font-weight: bold;">
                            <span>← SEPARAR GRUPOS</span>
                            <span>JUNTAR CANTIDADES →</span>
                        </div>

                        <div class="sidebar-section-title">TIPO DE COMPONENTE</div>
                        <div class="d-grid gap-2 mb-4" id="group-tipo-fs">
                            <button class="btn btn-primary btn-sm btn-filter-fs" data-val="all" onclick="syncAndFilter('tipo', 'all', this)">TODOS</button>
                            __BTN_TIPO_FS__
                            <button class="btn btn-outline-secondary btn-sm btn-filter-fs" data-val="none" onclick="syncAndFilter('tipo', 'none', this)">OCULTAR TODO</button>
                        </div>

                        <div class="sidebar-section-title">FILTRAR POR COLOR</div>
                        <div class="d-grid gap-2" id="group-color-fs">
                            <button class="btn btn-success btn-sm btn-filter-fs" data-val="all" onclick="syncAndFilter('color', 'all', this)">TODOS LOS COLORES</button>
                            __BTN_COLOR_FS__
                        </div>
                    </div>

                    <div class="custom-nav">
                        <div id="btn-in" class="nav-btn btn-zoom-in" title="Acercar">+</div>
                        <div id="btn-out" class="nav-btn btn-zoom-out" title="Alejar">−</div>
                        <div id="btn-home" class="nav-btn btn-home" title="Centrar">🏠</div>
                        <div id="btn-diagrama" class="nav-btn btn-diagrama" title="Activar Modo Diagrama (Márgenes)">📊</div>
                    </div>
                    
                    <button id="toggle-sidebar-btn" onclick="toggleFsSidebar()">☰ Filtros</button>
                    <button class="btn-fs" onclick="toggleFS()">📺 Pantalla Completa</button>
                    <div id="viewer-container"></div>
                </div>

                <div class="container-fluid report-container">
                    <div class="summary-card" id="tables-output"></div>
                </div>

                <script>
                    const puntos = __PUNTOS_JSON__;
                    const imgW = __WIDTH__;
                    let DISTANCE_THRESHOLD = 0.15;
                    
                    const viewer = OpenSeadragon({
                        id: "viewer-container",
                        prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                        tileSources: { type: 'image', url: '__DATA_URI__' },
                        showNavigationControl: false,
                        maxZoomLevel: 80,
                        minZoomImageRatio: 1.0,
                        visibilityRatio: 1.0,
                        constrainDuringPan: true,
                        animationTime: 0.3,
                        springStiffness: 15, 
                        gestureSettingsTouch: { clickToZoom: false, dblClickToZoom: false },
                        gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: false }
                    });

                    let filterT = 'all', filterC = 'all', lastSelected = null;
                    let diagramMode = false;

                    document.getElementById('sensitivity-slider').addEventListener('input', function(e) {
                        DISTANCE_THRESHOLD = e.target.value / 100.0;
                        if (diagramMode) drawPoints(); 
                    });

                    document.addEventListener('fullscreenchange', () => {
                        if (!document.fullscreenElement) {
                            document.getElementById('fs-sidebar').classList.remove('active');
                        }
                        setTimeout(() => { viewer.viewport.goHome(); }, 100);
                    });

                    function toggleFsSidebar() {
                        document.getElementById('fs-sidebar').classList.toggle('active');
                    }

                    function syncAndFilter(mode, value, btn) {
                        if (mode === 'tipo') {
                            filterT = value;
                            
                            const activeMainT = (value === 'none') ? 'btn-custom-active-none' : 'btn-custom-active-tipo';
                            highlightMainButtons('group-tipo-main', value, activeMainT);
                            
                            const activeFsT = (value === 'none') ? 'btn-secondary' : 'btn-primary';
                            const outlineFsT = (value === 'none') ? 'btn-outline-secondary' : 'btn-outline-light';
                            highlightFsButtons('group-tipo-fs', value, activeFsT, outlineFsT);
                            
                        } else {
                            filterC = value;
                            highlightMainButtons('group-color-main', value, 'btn-custom-active-color');
                            highlightFsButtons('group-color-fs', value, 'btn-success', 'btn-outline-light');
                        }
                        drawPoints();
                    }

                    function highlightMainButtons(groupId, value, activeClass) {
                        const container = document.getElementById(groupId);
                        container.querySelectorAll('.btn-custom-filter').forEach(btn => {
                            btn.className = 'btn-custom-filter'; 
                            if (btn.getAttribute('data-val') === value) {
                                btn.classList.add(activeClass);
                            }
                        });
                    }

                    function highlightFsButtons(groupId, value, activeClass, outlineClass) {
                        const container = document.getElementById(groupId);
                        container.querySelectorAll('.btn-filter-fs').forEach(btn => {
                            const btnVal = btn.getAttribute('data-val');
                            if (btnVal === value) {
                                btn.className = 'btn btn-sm ' + activeClass + ' btn-filter-fs';
                            } else {
                                btn.className = 'btn btn-sm ' + outlineClass + ' btn-filter-fs';
                            }
                        });
                    }

                    function updateFilters(mode, value, btn) { syncAndFilter(mode, value, btn); }

                    function getContrastColor(hex) {
                        if (hex.indexOf('#') === 0) hex = hex.slice(1);
                        const cssColors = { 'purple': '800080', 'black': '000000', 'royalblue': '4169E1', 'crimson': 'DC143C', 'gray': '808080' };
                        if (cssColors[hex]) hex = cssColors[hex];
                        if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
                        if (hex.length !== 6) return '#2c3e50';
                        const r = parseInt(hex.slice(0, 2), 16);
                        const g = parseInt(hex.slice(2, 4), 16);
                        const b = parseInt(hex.slice(4, 6), 16);
                        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
                        return (yiq >= 128) ? '#2c3e50' : '#ffffff';
                    }

                    viewer.addHandler('open', drawPoints);

                    function drawPoints() {
                        viewer.clearOverlays();
                        const bar = document.getElementById('info-bar');
                        if (filterT === 'none') {
                            bar.innerHTML = "MODO DE INSPECCIÓN: PUNTOS OCULTOS";
                            bar.style.backgroundColor = "#f8f9fa"; bar.style.color = "#2c3e50";
                            renderSummary([]); return;
                        }
                        bar.innerHTML = "Selecciona un punto para ver su detalle";
                        bar.style.backgroundColor = "#f8f9fa"; bar.style.color = "#2c3e50";

                        const filtered = puntos.filter(p => (filterT === 'all' || p.tipo === filterT) && (filterC === 'all' || p.color_norm === filterC));
                        
                        filtered.forEach(p => {
                            const elt = document.createElement("div");
                            elt.className = "dot"; elt.style.backgroundColor = p.color_plot;
                            
                            if(diagramMode) elt.style.opacity = "0.15"; 
                            
                            elt.addEventListener('pointerdown', (e) => {
                                e.stopPropagation();
                                e.preventDefault(); 
                                if(lastSelected) lastSelected.classList.remove('selected');
                                elt.classList.add('selected'); lastSelected = elt;
                                bar.style.backgroundColor = p.color_plot;
                                bar.style.color = getContrastColor(p.color_plot);
                                bar.innerHTML = "SELECCIONADO: " + p.tipo.toUpperCase() + " | " + p.color_norm.replace(/_/g, ' ').toUpperCase() + " (" + p.tamaño + ")";
                            });
                            viewer.addOverlay({ element: elt, location: new OpenSeadragon.Point(p.x/imgW, p.y/imgW), placement: 'CENTER' });
                        });

                        if (diagramMode) {
                            const groupsByType = {};
                            filtered.forEach(p => {
                                const key = p.tipo.toUpperCase() + " " + p.color_norm.replace(/_/g, ' ').toUpperCase() + " " + p.tamaño;
                                if (!groupsByType[key]) groupsByType[key] = [];
                                groupsByType[key].push(p);
                            });

                            let leftLabels = [];
                            let rightLabels = [];

                            for (let k in groupsByType) {
                                let points = groupsByType[k];
                                let clusters = [];

                                points.forEach(p => {
                                    let pX = p.x / imgW;
                                    let pY = p.y / imgW;
                                    let addedToCluster = false;
                                    for (let i = 0; i < clusters.length; i++) {
                                        let cluster = clusters[i];
                                        for (let cp of cluster.points) {
                                            let cpX = cp.x / imgW;
                                            let cpY = cp.y / imgW;
                                            if (Math.sqrt(Math.pow(pX - cpX, 2) + Math.pow(pY - cpY, 2)) < DISTANCE_THRESHOLD) {
                                                cluster.points.push(p);
                                                addedToCluster = true;
                                                break;
                                            }
                                        }
                                        if (addedToCluster) break;
                                    }
                                    if (!addedToCluster) clusters.push({ points: [p], color: p.color_plot });
                                });

                                clusters.forEach(cluster => {
                                    let count = cluster.points.length;
                                    let sumX = 0, sumY = 0;
                                    cluster.points.forEach(p => { sumX += (p.x / imgW); sumY += (p.y / imgW); });
                                    let centroidX = sumX / count;
                                    let centroidY = sumY / count;
                                    
                                    let bestP = cluster.points[0];
                                    let minDist = Infinity;
                                    cluster.points.forEach(p => {
                                        let pX = p.x / imgW;
                                        let pY = p.y / imgW;
                                        let d = Math.sqrt(Math.pow(pX - centroidX, 2) + Math.pow(pY - centroidY, 2));
                                        if (d < minDist) {
                                            minDist = d;
                                            bestP = p; 
                                        }
                                    });

                                    let cX = bestP.x / imgW;
                                    let cY = bestP.y / imgW;
                                    
                                    let isLeft = cX < 0.5;
                                    let edgeX = isLeft ? 0.05 : 0.95;
                                    
                                    let obj = { cluster, cX, cY, adjY: cY, edgeX, k, count };
                                    if (isLeft) leftLabels.push(obj); else rightLabels.push(obj);
                                });
                            }

                            function spreadLabels(labels) {
                                if (labels.length === 0) return;
                                labels.sort((a, b) => a.cY - b.cY);
                                const MIN_GAP = Math.min(0.045, 0.95 / labels.length); 
                                
                                for(let iter = 0; iter < 20; iter++) {
                                    for (let i = 0; i < labels.length - 1; i++) {
                                        let overlap = MIN_GAP - (labels[i+1].adjY - labels[i].adjY);
                                        if (overlap > 0) {
                                            labels[i].adjY -= overlap * 0.5;
                                            labels[i+1].adjY += overlap * 0.5;
                                        }
                                    }
                                }
                                
                                let topOverflow = 0.02 - labels[0].adjY;
                                if (topOverflow > 0) labels.forEach(l => l.adjY += topOverflow);
                                
                                let bottomOverflow = labels[labels.length-1].adjY - 0.98;
                                if (bottomOverflow > 0) labels.forEach(l => l.adjY -= bottomOverflow);
                            }

                            spreadLabels(leftLabels);
                            spreadLabels(rightLabels);

                            [...leftLabels, ...rightLabels].forEach(lbl => {
                                let { cX, cY, adjY, edgeX, cluster, k, count } = lbl;
                                let color = cluster.color;
                                let isLeft = cX < 0.5;
                                
                                let midX = cX + (edgeX - cX) * 0.5; 
                                
                                let w1 = Math.abs(midX - cX);
                                const hLine1 = document.createElement("div");
                                hLine1.style.borderTop = `2px dashed ${color}`;
                                hLine1.style.opacity = "0.6";
                                hLine1.style.pointerEvents = "none";
                                hLine1.style.willChange = "transform";
                                viewer.addOverlay({ element: hLine1, location: new OpenSeadragon.Rect(Math.min(cX, midX), cY, w1, 0.0001) });

                                let h2 = Math.abs(adjY - cY);
                                if (h2 > 0.001) { 
                                    const vLine = document.createElement("div");
                                    vLine.style.borderLeft = `2px dashed ${color}`;
                                    vLine.style.opacity = "0.6";
                                    vLine.style.pointerEvents = "none";
                                    vLine.style.willChange = "transform";
                                    viewer.addOverlay({ element: vLine, location: new OpenSeadragon.Rect(midX, Math.min(cY, adjY), 0.0001, h2) });
                                }

                                let w3 = Math.abs(edgeX - midX);
                                const hLine3 = document.createElement("div");
                                hLine3.style.borderTop = `2px dashed ${color}`;
                                hLine3.style.opacity = "0.6";
                                hLine3.style.pointerEvents = "none";
                                hLine3.style.willChange = "transform";
                                viewer.addOverlay({ element: hLine3, location: new OpenSeadragon.Rect(Math.min(midX, edgeX), adjY, w3, 0.0001) });

                                const anchorDot = document.createElement("div");
                                anchorDot.style.width = "12px";
                                anchorDot.style.height = "12px";
                                anchorDot.style.backgroundColor = color;
                                anchorDot.style.borderRadius = "50%";
                                anchorDot.style.border = "2px solid white";
                                anchorDot.style.boxShadow = "0 0 4px black";
                                anchorDot.style.willChange = "transform";
                                viewer.addOverlay({ element: anchorDot, location: new OpenSeadragon.Point(cX, cY), placement: 'CENTER' });

                                const elLabel = document.createElement("div");
                                elLabel.className = "diagram-label";
                                elLabel.style.borderLeftColor = isLeft ? color : "transparent";
                                elLabel.style.borderRightColor = isLeft ? "transparent" : color;
                                elLabel.style.borderLeftWidth = isLeft ? "6px" : "0px";
                                elLabel.style.borderRightWidth = isLeft ? "0px" : "6px";
                                elLabel.style.borderStyle = "solid";
                                elLabel.innerHTML = `<span style="color:${color}; font-size:14px;">●</span> <b>${count}</b> ${k}`;

                                viewer.addOverlay({
                                    element: elLabel,
                                    location: new OpenSeadragon.Point(edgeX, adjY),
                                    placement: isLeft ? 'LEFT' : 'RIGHT',
                                    checkResize: false
                                });
                            });
                        }

                        renderSummary(filtered);
                    }

                    function renderSummary(data) {
                        const container = document.getElementById('tables-output');
                        const groups = {}; let totalGral = 0;
                        const summaryData = (filterT === 'none') ? puntos : data;
                        summaryData.forEach(p => {
                            totalGral++;
                            if(!groups[p.tipo]) groups[p.tipo] = {};
                            const key = p.color_norm.replace(/_/g, ' ').toUpperCase() + " (" + p.tamaño + ")";
                            groups[p.tipo][key] = (groups[p.tipo][key] || 0) + 1;
                        });
                        let html = '<h4 class="fw-bold mb-4" style="font-family:Montserrat, sans-serif;">RESUMEN DE COMPONENTES</h4>';
                        for(let t in groups) {
                            let subtotal = Object.values(groups[t]).reduce((a, b) => a + b, 0);
                            html += '<div class="category-row"><span>' + t.toUpperCase() + '</span><span class="badge bg-primary">' + subtotal + ' pz</span></div><table class="item-table"><tbody>';
                            for(let k in groups[t]) html += '<tr><td>' + k + '</td><td class="text-end fw-bold">' + groups[t][k] + ' pz</td></tr>';
                            html += '</tbody></table>';
                        }
                        html += '<div class="total-banner">CANTIDAD TOTAL: ' + totalGral + ' PIEZAS</div>';
                        container.innerHTML = html;
                    }

                    function toggleFS() {
                        const el = document.getElementById("workspace");
                        if (!document.fullscreenElement) el.requestFullscreen(); else document.exitFullscreen();
                    }

                    document.getElementById('btn-in').onclick = () => viewer.viewport.zoomBy(1.4);
                    document.getElementById('btn-out').onclick = () => viewer.viewport.zoomBy(0.7);
                    document.getElementById('btn-home').onclick = () => viewer.viewport.goHome();
                    
                    document.getElementById('btn-diagrama').onclick = () => {
                        diagramMode = !diagramMode;
                        document.getElementById('btn-diagrama').style.background = diagramMode ? '#e74c3c' : '#f39c12';
                        drawPoints();
                    };
                </script>
            </body>
            </html>
            """
            
            html_report = html_template.replace("__TITULO_FINAL__", str(titulo_final))
            html_report = html_report.replace("__BTN_TIPO_MAIN__", btn_tipo_main)
            html_report = html_report.replace("__BTN_COLOR_MAIN__", btn_color_main)
            html_report = html_report.replace("__BTN_TIPO_FS__", btn_tipo_fs)
            html_report = html_report.replace("__BTN_COLOR_FS__", btn_color_fs)
            html_report = html_report.replace("__PUNTOS_JSON__", puntos_json)
            html_report = html_report.replace("__WIDTH__", str(width))
            html_report = html_report.replace("__DATA_URI__", data_uri)
            
            html_report = html_report.replace("__LOGO_URI__", logo_uri)
            html_report = html_report.replace("__MOSTRAR_LOGO__", mostrar_logo)

            nombre_archivo = f"{nombre_modelo}.html" if nombre_modelo else "Modelo_Sin_Nombre.html"

            st.success("✅ ¡Reporte generado exitosamente!")
            st.download_button(label="📥 DESCARGAR REPORTE HTML", data=html_report, file_name=nombre_archivo, mime="text/html", type="primary")

# =========================================================
# PESTAÑA 2: REPARAR HTMLs
# =========================================================
with tab2:
    st.subheader("Herramienta de Limpieza de Duplicados")
    st.info("Sube los archivos HTML generados en el pasado para limpiarlos. Se devolverá un archivo ZIP con todos los HTMLs corregidos.")

    html_files = st.file_uploader("Subir HTML(s) a corregir", type=["html"], accept_multiple_files=True, key="fixer_uploader")

    if html_files:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, html_file in enumerate(html_files):
                content = html_file.read().decode("utf-8")
                match = re.search(r'const puntos = (\[.*?\]);', content, re.DOTALL)
                
                if match:
                    puntos_raw = match.group(1)
                    try:
                        puntos_lista = json.loads(puntos_raw)
                        filas_limpias = []
                        coordenadas_vistas = set()
                        for row in puntos_lista:
                            coord_id = (round(float(row["x"]), 2), round(float(row["y"]), 2))
                            if coord_id not in coordenadas_vistas:
                                filas_limpias.append(row)
                                coordenadas_vistas.add(coord_id)
                        
                        puntos_json_limpio = json.dumps(filas_limpias)
                        nuevo_content = content.replace(f"const puntos = {puntos_raw};", f"const puntos = {puntos_json_limpio};")
                        st.success(f"✅ {html_file.name}: Pasó de {len(puntos_lista)} a {len(filas_limpias)} piezas.")
                        zip_file.writestr(f"Corregido_{html_file.name}", nuevo_content)
                        
                    except Exception as e:
                        st.error(f"Error procesando {html_file.name}: {e}")
                else:
                    st.error(f"No se encontró la base de datos en {html_file.name}.")

        st.download_button(
            label="📦 DESCARGAR TODOS LOS CORREGIDOS (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="HTMLs_Corregidos.zip",
            mime="application/zip",
            type="primary"
        )

# =========================================================
# PESTAÑA 3: TABLA DE RESUMEN GLOBAL
# =========================================================
with tab3:
    st.subheader("📊 Tabla Consolidada de Modelos")
    st.info("Sube múltiples archivos HTML (ya sean los originales o los corregidos) y la app extraerá el nombre del modelo y el conteo total de piezas para generar una tabla.")

    html_files_resumen = st.file_uploader("Subir HTML(s) para crear tabla", type=["html"], accept_multiple_files=True, key="resumen_uploader")

    if html_files_resumen:
        datos_tabla = []
        
        with st.spinner("Extrayendo datos de los HTMLs..."):
            for file in html_files_resumen:
                content = file.read().decode("utf-8")
                
                nombre_modelo = file.name.replace(".html", "").replace("Corregido_", "")
                match_title = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                if match_title:
                    nombre_modelo = match_title.group(1).replace("Componentes ", "").strip()
                    
                cantidad = 0
                match_puntos = re.search(r'const puntos = (\[.*?\]);', content, re.DOTALL)
                if match_puntos:
                    try:
                        puntos_lista = json.loads(match_puntos.group(1))
                        cantidad = len(puntos_lista)
                    except:
                        pass 
                        
                datos_tabla.append({
                    "Nombre del Modelo": nombre_modelo, 
                    "Cantidad Total de Piezas": cantidad
                })
                
        if datos_tabla:
            df_resumen = pd.DataFrame(datos_tabla)
            st.dataframe(df_resumen, use_container_width=True)
            csv = df_resumen.to_csv(index=False).encode('utf-8-sig') 
            st.download_button(
                label="📥 Exportar Tabla a Excel / CSV",
                data=csv,
                file_name="Resumen_Modelos.csv",
                mime="text/csv",
                type="primary"
            )
