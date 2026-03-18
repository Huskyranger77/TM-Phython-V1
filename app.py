import streamlit as st
import xmlrpc.client
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import base64
import ssl
from dotenv import load_dotenv

# Configuración básica de la página
st.set_page_config(
    page_title="Tecniman - Solicitud de Materiales",
    page_icon="🔧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# GESTIÓN DEL ESTADO
# ==========================================
if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 1
if 'carrito' not in st.session_state: st.session_state.carrito = {}
if 'proyecto_seleccionado' not in st.session_state: st.session_state.proyecto_seleccionado = None
if 'pagina_mat' not in st.session_state: st.session_state.pagina_mat = 1
if 'busqueda_proyectos' not in st.session_state: st.session_state.busqueda_proyectos = ""

# Cargar variables de entorno del directorio server/.env (para rápido acceso local)
load_dotenv(os.path.join("server", ".env"))

# ==========================================
# CONFIGURACIÓN DE APIs
# ==========================================
ODOO_URL = st.secrets.get("ODOO_URL", "").rstrip('/')
ODOO_DB = st.secrets.get("ODOO_DB")
ODOO_USERNAME = st.secrets.get("ODOO_USERNAME")
ODOO_API_KEY = st.secrets.get("ODOO_API_KEY")

SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID")
GOOGLE_SERVICE_ACCOUNT_EMAIL = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_EMAIL")
GOOGLE_PRIVATE_KEY = st.secrets.get("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n').replace('"', '')

# Omitir verificación SSL para xmlrpc local
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ==========================================
# FUNCIONES DE ODOO (XML-RPC)
# ==========================================
@st.cache_data(ttl=3600, show_spinner="Conectando a Odoo...")
def get_odoo_products():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common', context=ctx)
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {})
        if not uid:
            raise Exception("Autenticación en Odoo fallida.")

        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', context=ctx)
        products = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'product.product', 'search_read',
            [[['active', '=', True]]],
            {'fields': ['id', 'name', 'uom_id', 'categ_id', 'image_1024'], 'limit': 2000}
        )
        
        # Mapear los datos para la interfaz
        mapped = []
        for p in products:
            unidad = "unidad"
            if p.get("uom_id") and isinstance(p["uom_id"], list) and len(p["uom_id"]) > 1:
                unidad = p["uom_id"][1]
            
            categoria = "Otras"
            if p.get("categ_id") and isinstance(p["categ_id"], list) and len(p["categ_id"]) > 1:
                # Odoo devuelve [id, "Todo / Iluminación / Cables"]
                cat_parts = p["categ_id"][1].split(" / ")
                categoria = cat_parts[-1] # Tomar la caja más específica

            mapped.append({
                "id": str(p["id"]),
                "nombre": p["name"],
                "unidad": unidad,
                "categoria": categoria,
                "imagen_b64": p.get("image_1024", False)
            })
        return mapped
    except Exception as e:
        st.error(f"Error cargando catálogo de Odoo: {e}")
        return []

# ==========================================
# FUNCIONES DE GOOGLE SHEETS
# ==========================================
@st.cache_resource
def get_google_sheets_service():
    if not GOOGLE_SERVICE_ACCOUNT_EMAIL or not GOOGLE_PRIVATE_KEY:
         return None
    
    credentials = service_account.Credentials.from_service_account_info(
        {
            "client_email": GOOGLE_SERVICE_ACCOUNT_EMAIL,
            "private_key": GOOGLE_PRIVATE_KEY,
            "token_uri": "https://oauth2.googleapis.com/token"
        },
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=credentials).spreadsheets()

@st.cache_data(ttl=600, show_spinner="Cargando proyectos...")
def get_proyectos():
    service = get_google_sheets_service()
    if not service:
        st.error("Credenciales de Google no encontradas en st.secrets.")
        return []
    
    try:
        result = service.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Proyectos!A3:E"
        ).execute()
        
        rows = result.get('values', [])
        proyectos = []
        for i, row in enumerate(rows):
            if not row or not str(row[0]).strip(): continue
            codigo = str(row[0]).strip()
            nombre = str(row[1]).strip() if len(row) > 1 else ""
            estado = str(row[2]).strip() if len(row) > 2 else ""
            cliente = str(row[4]).strip() if len(row) > 4 else ""
            if estado.lower() == 'proceso':
                proyectos.append({
                    "id": codigo,
                    "nombre": nombre,
                    "cliente": cliente,
                    "rowIdx": i + 3
                })
        return proyectos
    except Exception as e:
        st.error(f"Error cargando proyectos de Google Sheets: {e}")
        return []

def save_consumo(proyecto_id, cliente, materiales_carrito, solicitante):
    service = get_google_sheets_service()
    if not service: return False
    
    from datetime import datetime
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    rows_to_insert = []
    for item in materiales_carrito.values():
        rows_to_insert.append([
            ahora,                  # A: Marca temporal
            solicitante,            # B: Solicitante
            proyecto_id,            # C: ID Proyecto
            cliente,                # D: Cliente
            item["nombre"],         # E: Material
            item["unidad"],         # F: Unidad
            item["cantidad"]        # G: Cantidad
        ])
        
    try:
        service.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Reporte de material!A:G",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows_to_insert}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")
        return False

# ==========================================
# RUTAS DE LA APP
# ==========================================

# ----------------- PASO 3 (Resumen) -----------------
if st.session_state.paso_actual == 3:
    st.header("Resumen del Registro")
    
    if not st.session_state.proyecto_seleccionado or not st.session_state.carrito:
        st.warning("Faltan datos. Por favor vuelve al inicio.")
        if st.button("Volver al Inicio"):
            st.session_state.paso_actual = 1
            st.rerun()
    else:
        p = st.session_state.proyecto_seleccionado
        st.markdown(f"""
        <div style='background:#f0f9ff; padding:15px; border-radius:8px; border-left:4px solid #3b82f6; margin-bottom:20px;'>
            <strong>Proyecto:</strong> {p['id']} - {p['nombre']}
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Materiales a solicitar:")
        items_count = 0
        for mat in st.session_state.carrito.values():
            st.markdown(f"""
            <div style='display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #e2e8f0;'>
                <span style='font-size:14px;'>{mat['nombre']}</span>
                <span style='font-weight:bold; color:#0f172a;'>{mat['cantidad']} <span style='font-size:12px; color:#64748b; font-weight:normal;'>{mat['unidad']}</span></span>
            </div>
            """, unsafe_allow_html=True)
            items_count += mat['cantidad']
            
        st.markdown(f"<div style='text-align:right; margin-top:10px; font-weight:bold;'>Total items: {items_count}</div><br>", unsafe_allow_html=True)
        
        solicitante = st.text_input("Tu Nombre (Solicitante):", key="solicitante_input")
        
        col_b_back, col_b_send = st.columns([1,2])
        with col_b_back:
            if st.button("← Editar Materiales"):
                st.session_state.paso_actual = 2
                st.rerun()
        with col_b_send:
            if st.button("Enviar Registro", type="primary", use_container_width=True):
                if not solicitante.strip():
                    st.error("Por favor, ingresa tu nombre.")
                else:
                    with st.spinner("Guardando en Google Sheets..."):
                        exito = save_consumo(
                            p['id'], 
                            p['cliente'], 
                            st.session_state.carrito, 
                            solicitante
                        )
                        if exito:
                            st.success("✅ ¡Registro guardado exitosamente!")
                            
                            col_img1, col_img2, col_img3 = st.columns([1,2,1])
                            with col_img2:
                                st.image("tecniman-logo.png", use_container_width=True)
                                
                            # Limpiar estado
                            st.session_state.carrito = {}
                            st.session_state.proyecto_seleccionado = None
                            st.session_state.busqueda_proyectos = ""
                            st.session_state.pagina_mat = 1
                            
                            # Botón para nueva solicitud
                            if st.button("Hacer Nueva Solicitud", key="btn_nueva", type="primary"):
                                st.session_state.paso_actual = 1
                                st.rerun()

# ==========================================
# GESTIÓN DEL ESTADO
# ==========================================
if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 1
if 'carrito' not in st.session_state: st.session_state.carrito = {}
if 'proyecto_seleccionado' not in st.session_state: st.session_state.proyecto_seleccionado = None
if 'pagina_mat' not in st.session_state: st.session_state.pagina_mat = 1
if 'busqueda_proyectos' not in st.session_state: st.session_state.busqueda_proyectos = ""

# ==========================================
# ESTILOS MÓVILES (CSS)
# ==========================================
st.markdown("""
<style>
    .stApp { max-width: 680px; margin: 0 auto; }
    .project-card {
        padding: 15px; 
        border-radius: 12px; 
        border: 1px solid #e2e8f0;
        margin-bottom: 10px;
        background: white;
    }
    .project-card h4 { margin: 0 0 5px 0; font-size: 16px; color: #0f172a;}
    .project-card p { margin: 0; font-size: 13px; color: #64748b;}
    
    /* Ocultar menú de hamburguesa y header */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# UI: NAVEGADOR SUPERIOR (Stepper)
# ==========================================
def render_stepper():
    cols = st.columns(3)
    pasos = ["1. Proyecto", "2. Materiales", "3. Registro"]
    for i, col in enumerate(cols):
        paso_num = i + 1
        with col:
            if st.session_state.paso_actual == paso_num:
                st.markdown(f"**<span style='color:#3b82f6;'>{pasos[i]}</span>**", unsafe_allow_html=True)
            elif st.session_state.paso_actual > paso_num:
                st.markdown(f"<span style='color:#22c55e;'>✓ {pasos[i].split('.')[1]}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color:#94a3b8;'>{pasos[i]}</span>", unsafe_allow_html=True)
    st.markdown("---")

render_stepper()

# ==========================================
# RUTAS DE LA APP
# ==========================================

# ----------------- PASO 1 -----------------
if st.session_state.paso_actual == 1:
    col_l1, col_l2, col_l3 = st.columns([1,3,1])
    with col_l2:
        st.image("tecniman-logo.png", use_container_width=True)

    st.header("Selecciona el proyecto")
    st.write("Busca el proyecto en el cual usarás los materiales:")
    
    proyectos = get_proyectos()
    
    if not proyectos:
        st.warning("No hay proyectos cargados. Verifica la conexión.")
    else:
        # Si ya hay un proyecto seleccionado, mostrar resumen y botón para cambiar
        if st.session_state.proyecto_seleccionado:
            p = st.session_state.proyecto_seleccionado
            st.info(f"**Proyecto Actual:** {p['id']} - {p['nombre']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Cambiar Proyecto"):
                    st.session_state.proyecto_seleccionado = None
                    st.rerun()
            with col2:
                if st.button("Continuar a Materiales", type="primary"):
                    st.session_state.paso_actual = 2
                    st.rerun()
        else:
            # Dropdown con búsqueda nativa
            opciones_proyectos = {f"{p['id']} - {p['nombre']}": p for p in proyectos}
            
            seleccion_texto = st.selectbox(
                "Selecciona un proyecto de la lista (puedes escribir para buscar):",
                options=list(opciones_proyectos.keys()),
                index=None,
                placeholder="Ej. P004 o Torre Doretto..."
            )
            
            if seleccion_texto:
                st.session_state.proyecto_seleccionado = opciones_proyectos[seleccion_texto]
                st.session_state.paso_actual = 2
                st.rerun()

# ----------------- PASO 2 -----------------
elif st.session_state.paso_actual == 2:
    st.header("Catálogo de Materiales")
    
    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("← Volver a Proyectos"):
            st.session_state.paso_actual = 1
            st.rerun()
    with col_next:
        if st.button("Ver Resumen →", type="primary"):
            st.session_state.paso_actual = 3
            st.rerun()

    materiales = get_odoo_products()
    
    if not materiales:
        st.warning("No hay materiales cargados desde Odoo.")
    else:
        # Extraer categorías únicas
        categorias = sorted(list(set([m['categoria'] for m in materiales])))
        categorias.insert(0, "Todas")
        
        # Filtros
        col_search, col_cat = st.columns(2)
        with col_search:
            busqueda_mat = st.text_input("Buscar material:", placeholder="Ej. Cable, tubo...")
        with col_cat:
            categoria_sel = st.selectbox("Categoría:", categorias)
            
        # Aplicar filtros
        filtrados = materiales
        if categoria_sel != "Todas":
            filtrados = [m for m in filtrados if m['categoria'] == categoria_sel]
        if busqueda_mat:
            q = busqueda_mat.lower()
            filtrados = [m for m in filtrados if q in m['nombre'].lower()]
            
        st.caption(f"Mostrando {len(filtrados)} resultados.")
        
        # Paginación
        ITEMS_PER_PAGE = 20
        total_paginas = max(1, (len(filtrados) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        
        # Resetear página si el número actual es mayor al total debido a un filtro
        if st.session_state.pagina_mat > total_paginas:
            st.session_state.pagina_mat = 1
            
        inicio = (st.session_state.pagina_mat - 1) * ITEMS_PER_PAGE
        fin = inicio + ITEMS_PER_PAGE
        materiales_pagina = filtrados[inicio:fin]
        
        # Controles de Paginación Superior
        col_prev, col_info, col_next_p = st.columns([1, 2, 1])
        with col_prev:
            if st.button("◀ Ant", disabled=(st.session_state.pagina_mat == 1)):
                st.session_state.pagina_mat -= 1
                st.rerun()
        with col_info:
            st.markdown(f"<div style='text-align:center; padding-top:8px;'>Página {st.session_state.pagina_mat} de {total_paginas}</div>", unsafe_allow_html=True)
        with col_next_p:
            if st.button("Sig ▶", disabled=(st.session_state.pagina_mat == total_paginas)):
                st.session_state.pagina_mat += 1
                st.rerun()
                
        # GRID DE PRODUCTOS (3 Columnas)
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, mat in enumerate(materiales_pagina):
            with cols[i % 3]:
                # Renderizar Imagen si existe
                if mat.get("imagen_b64"):
                    try:
                        img_bytes = base64.b64decode(mat["imagen_b64"])
                        st.image(img_bytes, use_container_width=True)
                    except Exception:
                        pass # Ignorar errores si el base64 viene corrupto
                        
                st.markdown(f"""
                <div style='background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0; display:flex; flex-direction:column; justify-content:space-between; margin-bottom:5px;'>
                    <div style='font-size:12px; font-weight:bold; line-height:1.2; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical;'>{mat['nombre']}</div>
                    <div style='font-size:10px; color:#64748b; margin-top:4px;'>{mat['unidad']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Input de cantidad numérico
                qty = st.number_input(
                    "Cant", 
                    min_value=0, 
                    value=st.session_state.carrito.get(mat['id'], {}).get("cantidad", 0), 
                    step=1, 
                    key=f"qty_{mat['id']}",
                    label_visibility="collapsed"
                )
                
                # Actualizar el carrito
                if qty > 0:
                    st.session_state.carrito[mat['id']] = {
                        "id": mat['id'],
                        "nombre": mat['nombre'],
                        "cantidad": qty,
                        "unidad": mat['unidad']
                    }
                elif mat['id'] in st.session_state.carrito:
                    del st.session_state.carrito[mat['id']]


        # Control de agregar manual
        with st.expander("➕ Agregar Material Manual"):
            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                man_name = st.text_input("Nombre del material")
            with col_m2:
                man_qty = st.number_input("Cant.", min_value=1, value=1, key="man_qty")
            if st.button("Añadir al Carrito"):
                if man_name:
                    man_id = f"manual_{len(st.session_state.carrito)}"
                    st.session_state.carrito[man_id] = {
                        "id": man_id,
                        "nombre": f"(Manual) {man_name}",
                        "cantidad": man_qty,
                        "unidad": "unidad"
                    }
                    st.success(f"Añadido {man_qty} {man_name}")
                else:
                    st.error("Ingrese el nombre del material")
