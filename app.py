import streamlit as st
import json
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import xmlrpc.client

# --- 1. CONFIGURACIÓN INICIAL ---
# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Tecniman Dashboard",
    page_icon="logo_tecniman.png",
    layout="wide"
)

# --- 2. ESTILOS CSS (MOBILE PREMIUM COMPACT) ---
st.markdown("""
    <style>
    /* Importar Poppins Font */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    
    /* Ocultar elementos default de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Reducir padding superior excesivo */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Fondo Global - Gris Suave Elegante */
    .stApp {
        background: #F5F7FA;
        font-family: 'Poppins', sans-serif;
    }
    
    /* Títulos con Poppins */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', sans-serif !important;
    }
    
    h1 {
        color: #1a1a1a;
        font-weight: 600;
        font-size: 1.75rem !important;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #2c2c2c;
        font-size: 1.3rem !important;
        font-weight: 600;
        margin-top: 1rem;
    }
    
    /* Step Indicator - Pill Style */
    .step-indicator {
        background: linear-gradient(135deg, #0066FF 0%, #0052CC 100%);
        color: white;
        padding: 12px 20px;
        text-align: center;
        border-radius: 50px;
        margin-bottom: 20px;
        font-weight: 600;
        font-size: 0.875rem;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.2);
    }
    
    /* PRODUCT CARD COMPACT - CRITICAL FOR MOBILE */
    .product-card {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0px 10px 20px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .product-card:hover {
        box-shadow: 0px 15px 30px rgba(0,0,0,0.08);
        transform: translateY(-3px);
    }
    
    /* Imagen del Producto - Mejorada para Alta Calidad */
    .product-image-container {
        width: 100%;
        height: 180px;
        max-height: 180px;
        display: flex;
        justify-content: center;
        align-items: center;
        background: #F8F9FA;
        border-radius: 15px;
        margin-bottom: 10px;
        overflow: hidden;
    }
    
    .product-image {
        width: 100%;
        height: auto;
        max-height: 180px;
        object-fit: contain;  /* Muestra imagen completa sin recortar */
        border-radius: 15px;
    }
    
    /* Nombre del Producto */
    .product-name {
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 0.875rem;
        color: #1a1a1a;
        margin-bottom: 4px;
        line-height: 1.3;
    }
    
    /* Unidad del Producto */
    .product-unit {
        font-size: 0.75rem;
        color: #6B7280;
        margin-bottom: 8px;
    }
    
    /* Botones - Pill Shape Moderno */
    .stButton > button {
        width: 100%;
        background: #0066FF;
        color: white;
        font-weight: 600;
        border-radius: 50px;  /* Pill shape */
        height: 50px;
        border: none;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.2);
        font-family: 'Poppins', sans-serif;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 102, 255, 0.3);
        background: #0052CC;
    }
    
    /* Number Input - Compacto */
    .stNumberInput > div > div > input {
        text-align: center;
        font-weight: 600;
        font-size: 1rem;
        border-radius: 12px;
        border: 2px solid #E5E7EB;
        padding: 8px;
        transition: border-color 0.3s ease;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #0066FF;
        box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
    }
    
    /* Text Input y Select - Más Redondeados */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        border-radius: 15px;
        border: 2px solid #E5E7EB;
        padding: 12px 16px;
        font-size: 0.95rem;
        font-family: 'Poppins', sans-serif;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #0066FF;
        box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
    }
    
    /* Summary Card - White on Gray */
    .summary-item {
        background: white;
        padding: 16px;
        margin: 10px 0;
        border-left: 4px solid #0066FF;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        font-family: 'Poppins', sans-serif;
    }
    
    .summary-item strong {
        color: #1a1a1a;
        font-size: 1rem;
    }
    
    /* Info/Success/Error Messages */
    .stInfo {
        background-color: #EBF5FF;
        border-left: 4px solid #0066FF;
        border-radius: 12px;
    }
    
    .stSuccess {
        background-color: #D1FAE5;
        border-left: 4px solid #10B981;
        border-radius: 12px;
    }
    
    .stError, .stWarning {
        background-color: #FEE2E2;
        border-left: 4px solid #EF4444;
        border-radius: 12px;
    }
    
    /* Caption Styling */
    .stCaption {
        color: #6B7280;
        font-size: 0.8rem;
        font-family: 'Poppins', sans-serif;
    }
    
    /* Reducir espacio entre columnas para compacidad */
    div[data-testid="column"] {
        padding: 0 6px !important;
    }
    
    /* RESPONSIVE: 2 columnas en móvil (hasta 768px) */
    @media (max-width: 768px) {
        /* Forzar que cada columna ocupe 50% en mobile */
        div[data-testid="column"] {
            width: 50% !important;
            min-width: 50% !important;
            max-width: 50% !important;
            flex: 0 0 50% !important;
        }
        
        /* Ocultar la tercera columna en cada fila (mantener solo 2) */
        div[data-testid="column"]:nth-child(3n) {
            display: none !important;
        }
    }
    
    </style>
""", unsafe_allow_html=True)

# --- 3. CONFIGURACIÓN DE GOOGLE SHEETS ---
SPREADSHEET_ID = "1A5G8k0rPNZ6PJ9hqvLOjYOOZon192hE3J2bBT2vxzYk"
SHEET_PROJECTS = "Proyectos"
SHEET_CONSUMPTION = "Consumo de material" # O "Consumos" si prefieres

# --- 4. DATOS SIMULADOS (MOCK DATA) ---
# (Eliminado: Usamos Odoo)

# --- 5. CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet():
    """Conecta a Google Sheets y devuelve el objeto Workbook"""
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scope
        )
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Sheets: {str(e)}")
        return None

# --- 6. CONEXIÓN A ODOO (ERP) ---
@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_odoo_products():
    """Obtiene productos desde Odoo vía XML-RPC"""
    try:
        # Credenciales desde secrets
        url = st.secrets["odoo"]["url"]
        db = st.secrets["odoo"]["db"]
        username = st.secrets["odoo"]["username"]
        api_key = st.secrets["odoo"]["api_key"]
        
        # Conexión de autenticación
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, api_key, {})
        
        if not uid:
            st.error("❌ Error de autenticación con Odoo")
            return []
        
        # Conexión a modelos
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Buscar TODOS los productos (almacenables + consumibles)
        # Dominio: ['|', ('type', '=', 'product'), ('type', '=', 'consu')]
        product_ids = models.execute_kw(
            db, uid, api_key,
            'product.product', 'search',
            [['|', ('type', '=', 'product'), ('type', '=', 'consu')]],  # Almacenables Y Consumibles
            {'limit': 200}  # Aumentado a 200
        )
        
        if not product_ids:
            return []
        
        # Leer datos de los productos
        products = models.execute_kw(
            db, uid, api_key,
            'product.product', 'read',
            [product_ids],
            {'fields': ['id', 'display_name', 'uom_id', 'image_512', 'type', 'categ_id']}  # image_512 para mejor calidad + categ_id
        )
        
        # Formatear datos para el catálogo
        catalog = []
        for p in products:
            # Imagen: Base64 directo o placeholder (usando image_512 para mejor calidad)
            if p.get('image_512'):
                img_data = p['image_512']  # Ya viene como string Base64
                img_src = f"data:image/png;base64,{img_data}"
            else:
                img_src = "https://via.placeholder.com/300/CCCCCC/FFFFFF?text=Sin+Imagen"
            
            # Procesar categoría: Odoo devuelve [ID, "Nombre"] o False
            category_name = "Sin Categoría"
            if p.get('categ_id') and isinstance(p['categ_id'], list) and len(p['categ_id']) > 1:
                category_name = p['categ_id'][1]  # Segundo elemento es el nombre
            
            catalog.append({
                'id': str(p['id']),
                'name': p['display_name'],
                'unit': p['uom_id'][1] if p.get('uom_id') else 'Unidad',
                'img': img_src,
                'category': category_name
            })
        
        st.success(f"✅ {len(catalog)} productos cargados correctamente")
        return catalog
        
    except Exception as e:
        st.error(f"❌ Error al conectar con Odoo: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        # Fallback a catálogo mock si falla Odoo
        return [
            {"id": "mat_01", "name": "Cable THHN #12", "unit": "Metros", "img": "https://placehold.co/200x200/3b82f6/white?text=Cable+12", "category": "Cables"},
            {"id": "mat_02", "name": "Breaker 20A 1P", "unit": "Unidad", "img": "https://placehold.co/200x200/1e40af/white?text=Breaker", "category": "Protección"}
        ]

# --- 7. FUNCIONES DE GOOGLE SHEETS ---
def load_projects():
    """Carga y filtra proyectos activos (Estado != 'Completado')"""
    try:
        sh = get_google_sheet()
        if sh is None:
            return ["Error de Conexión"]

        worksheet = sh.worksheet(SHEET_PROJECTS)
        records = worksheet.get_all_records()
        
        # Filtrar: mostrar solo proyectos que NO estén completados
        active_projects = []
        for row in records:
            # Obtener datos de la fila
            state = str(row.get('Estado', '')).strip().lower()
            proyecto = str(row.get('Proyecto', '')).strip()
            cliente = str(row.get('Cliente', '')).strip()
            
            # Incluir proyecto si tiene nombre Y el estado NO es 'completado'
            if proyecto and state != 'completado':
                # Formato: "Proyecto - Cliente"
                display_name = f"{proyecto} - {cliente}" if cliente else proyecto
                active_projects.append(display_name)
                
        return active_projects if active_projects else ["No hay proyectos activos"]

    except Exception as e:
        st.error(f"❌ Error al leer proyectos: {str(e)}")
        # Fallback a mensaje simple si hay error
        return ["Error al cargar proyectos"]

def save_consumption(project, technician, items):
    """Guarda una fila por ítem en la hoja de Consumo"""
    try:
        sh = get_google_sheet()
        if sh is None:
            return False

        worksheet = sh.worksheet(SHEET_CONSUMPTION)
        # Formato de fecha: DD/M/YYYY (como en la imagen del usuario)
        timestamp = datetime.now().strftime("%d/%m/%Y")

        # Encontrar la siguiente fila vacía (evita sobrescribir)
        all_values = worksheet.get_all_values()
        next_row = len(all_values) + 1  # Primera fila vacía después de los datos existentes
        
        # Preparar TODAS las filas a insertar (una por material)
        rows_to_append = []
        for item in items:
            row = [
                timestamp,
                project,
                item['item_name'],
                item['quantity'],
                item['unit'],
                technician
            ]
            rows_to_append.append(row)
        
        # Insertar todas las filas comenzando desde next_row
        if rows_to_append:
            # Actualizar rango específico: A{next_row}:F{next_row + num_items - 1}
            num_items = len(rows_to_append)
            range_to_update = f'A{next_row}:F{next_row + num_items - 1}'
            worksheet.update(range_to_update, rows_to_append, value_input_option='USER_ENTERED')
            
        return True

    except Exception as e:
        st.error(f"❌ Error al guardar consumo: {str(e)}")
        return False

# --- 6. GESTIÓN DE ESTADO (SESSION STATE) ---
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None

# Cargar catálogo de Odoo al iniciar
if 'catalog' not in st.session_state:
    st.session_state.catalog = get_odoo_products()

if 'cart' not in st.session_state:
    st.session_state.cart = {}
    for item in st.session_state.catalog:
        st.session_state.cart[item['id']] = 0

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

if 'technician_name' not in st.session_state:
    st.session_state.technician_name = ""

# Paginación y filtros
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if 'items_per_page' not in st.session_state:
    st.session_state.items_per_page = 12  # 6 filas x 2 columnas

if 'letter_filter' not in st.session_state:
    st.session_state.letter_filter = "Todas"

if 'category_filter' not in st.session_state:
    st.session_state.category_filter = "Todas"

# Lista de materiales ingresados manualmente (fuera de Odoo)
if 'manual_items' not in st.session_state:
    st.session_state.manual_items = []

# --- 7. FUNCIONES DE UTILIDAD ---
def reset_app():
    """Reinicia toda la aplicación al estado inicial"""
    st.session_state.current_step = 1
    st.session_state.selected_project = None
    st.session_state.search_query = ""
    st.session_state.technician_name = ""
    st.session_state.letter_filter = "Todas"
    st.session_state.category_filter = "Todas"
    st.session_state.current_page = 1
    
    # Reiniciar carrito y materiales manuales
    if 'catalog' in st.session_state:
        for item in st.session_state.catalog:
            st.session_state.cart[item['id']] = 0
    st.session_state.manual_items = []

def filter_catalog(query, letter_filter="Todas", category_filter="Todas"):
    """Filtra el catálogo según búsqueda de texto, letra inicial y categoría"""
    catalog = st.session_state.catalog
    
    # Aplicar filtro por categoría
    if category_filter != "Todas":
        catalog = [item for item in catalog if item.get('category') == category_filter]
    
    # Aplicar filtro por letra
    if letter_filter != "Todas":
        catalog = [item for item in catalog if item['name'].upper().startswith(letter_filter)]
    
    # Aplicar filtro de búsqueda de texto
    if query:
        query_lower = query.lower()
        catalog = [item for item in catalog if query_lower in item['name'].lower()]
    
    return catalog

def paginate_items(items, page, items_per_page):
    """Divide items en páginas y retorna los items de la página actual"""
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    total_pages = (len(items) + items_per_page - 1) // items_per_page  # Ceil division
    
    return {
        'items': items[start_idx:end_idx],
        'total_items': len(items),
        'total_pages': max(1, total_pages),
        'current_page': page,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }

def get_selected_items():
    """Retorna lista de items con cantidad > 0"""
    return {k: v for k, v in st.session_state.cart.items() if v > 0}

# --- 8. INTERFAZ GRÁFICA (UI) - WIZARD FLOW ---

# ============================================
# PASO 1: SELECCIÓN DE PROYECTO 🏗️
# ============================================
if st.session_state.current_step == 1:
    st.markdown('<div class="step-indicator">📍 PASO 1 DE 3: Selecciona el Proyecto</div>', unsafe_allow_html=True)
    
    # Logo y Título Integrados (Logo izquierda + Título derecha)
    col_logo, col_title = st.columns([1, 3])
    
    with col_logo:
        st.image("logo_tecniman.png", use_container_width=True)
    
    with col_title:
        st.markdown("""
            <div style="display: flex; align-items: center; height: 100%;">
                <div>
                    <h1 style="margin: 0; padding: 0;">⚡ Registro de Materiales</h1>
                    <p style="margin: 0; color: #6B7280; font-size: 0.95rem;">
                        Selecciona el proyecto donde registrarás el consumo de materiales.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Cargar proyectos desde Google Sheets
    projects_list = load_projects()
    
    project = st.selectbox(
        "🏗️ Proyecto Activo",
        options=projects_list,
        index=projects_list.index(st.session_state.selected_project) if st.session_state.selected_project in projects_list else None,
        placeholder="Selecciona un proyecto..."
    )
    
    st.markdown("<br>" * 2, unsafe_allow_html=True)
    
    if st.button("Continuar al Catálogo ➡️", type="primary"):
        if project:
            st.session_state.selected_project = project
            st.session_state.current_step = 2
            st.rerun()
        else:
            st.error("⚠️ Debes seleccionar un proyecto para continuar.")

# ============================================
# PASO 2: CATÁLOGO 📦
# ============================================
elif st.session_state.current_step == 2:
    st.markdown('<div class="step-indicator">📦 PASO 2 DE 3: Selecciona los Materiales</div>', unsafe_allow_html=True)
    
    st.title("Catálogo de Materiales")
    st.caption(f"Proyecto: **{st.session_state.selected_project}**")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Barra de Herramientas: Búsqueda + Letra + Categoría
    col_search, col_letter, col_category = st.columns([2, 1, 1.5])
    
    with col_search:
        search_query = st.text_input(
            "🔍 Buscar",
            value=st.session_state.search_query,
            placeholder="🔍 Buscar cable, breaker...",
            key="search_input",
            label_visibility="collapsed"
        )
        # Si cambió la búsqueda, resetear a página 1
        if search_query != st.session_state.search_query:
            st.session_state.search_query = search_query
            st.session_state.current_page = 1
    
    with col_letter:
        letter_options = ["Todas"] + [chr(i) for i in range(65, 91)]  # A-Z
        letter_filter = st.selectbox(
            "🔤 Letra",
            options=letter_options,
            key="letter_select"
        )
        # Si cambió la letra, resetear a página 1
        if letter_filter != st.session_state.get('letter_filter', 'Todas'):
            st.session_state.letter_filter = letter_filter
            st.session_state.current_page = 1
    
    with col_category:
        # Extraer categorías únicas del catálogo
        unique_categories = sorted(list(set([item.get('category', 'Sin Categoría') for item in st.session_state.catalog])))
        category_options = ["Todas"] + unique_categories
        
        # Usar el valor del widget directamente
        category_filter = st.selectbox(
            "📂 Categoría",
            options=category_options,
            key="category_select"
        )
        
        # Actualizar session state solo si cambió (para resetear paginación)
        if category_filter != st.session_state.get('category_filter', 'Todas'):
            st.session_state.category_filter = category_filter
            st.session_state.current_page = 1
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # CRÍTICO: Usar valores ACTUALES de los widgets para reactividad inmediata
    filtered_items = filter_catalog(st.session_state.search_query, letter_filter, category_filter)
    
    if not filtered_items:
        st.warning("🔍 No se encontraron materiales que coincidan con tu búsqueda.")
    else:
        # Aplicar paginación
        pagination_data = paginate_items(
            filtered_items,
            st.session_state.current_page,
            st.session_state.items_per_page
        )
        
        # Mostrar info de paginación
        st.caption(f"Mostrando {len(pagination_data['items'])} de {pagination_data['total_items']} productos")
        
        # GRID DE PRODUCTOS - 3 columnas por fila
        paginated_items = pagination_data['items']
        
        # Iterar en chunks de 3
        for i in range(0, len(paginated_items), 3):
            cols = st.columns(3)
            chunk = paginated_items[i:i+3]
            
            for idx, item in enumerate(chunk):
                with cols[idx]:
                    # Contenedor con borde para cada producto (Native App Style)
                    with st.container(border=True):
                        # Imagen del producto
                        st.image(item['img'], use_container_width=True)
                        
                        # Nombre del producto (en negrita)
                        st.markdown(f"**{item['name']}**")
                        
                        # Unidad (gris pequeño)
                        st.caption(f"📦 {item['unit']}")
                        
                        # Control de cantidad (compacto al pie)
                        qty = st.number_input(
                            "Cantidad",
                            min_value=0,
                            key=f"qty_{item['id']}",
                            value=st.session_state.cart.get(item['id'], 0),
                            label_visibility="collapsed"
                        )
                        
                        st.session_state.cart[item['id']] = qty
        
        # CONTROLES DE PAGINACIÓN
        if pagination_data['total_pages'] > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            
            with col_prev:
                if st.button("⬅️ Anterior", disabled=not pagination_data['has_prev'], key="page_prev"):
                    st.session_state.current_page -= 1
                    st.rerun()
            
            with col_info:
                st.markdown(
                    f"<div style='text-align: center; padding-top: 8px;'>"
                    f"<strong>Página {pagination_data['current_page']} de {pagination_data['total_pages']}</strong>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            
            with col_next:
                if st.button("Siguiente ➡️", disabled=not pagination_data['has_next'], key="page_next"):
                    st.session_state.current_page += 1
                    st.rerun()
    
    # Resumen rápido
    total_from_catalog = sum([q for q in st.session_state.cart.values() if q > 0])
    total_manual = sum([m['quantity'] for m in st.session_state.manual_items])
    total_selected = total_from_catalog + total_manual
    if total_selected > 0:
        label_parts = []
        if total_from_catalog > 0:
            label_parts.append(f"{int(total_from_catalog)} del catálogo")
        if total_manual > 0:
            label_parts.append(f"{len(st.session_state.manual_items)} manuales")
        st.info(f"✅ **Seleccionados: {', '.join(label_parts)}**")

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------
    # EXPANDER: Agregar Material Manual
    # -----------------------------------------------
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
            color: white;
            padding: 14px 18px;
            border-radius: 16px;
            font-weight: 700;
            font-size: 0.95rem;
            text-align: center;
            margin-bottom: 8px;
            box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35);
            letter-spacing: 0.3px;
        ">
            ✏️ ¿No encuentras el material? ¡Agrégalo manualmente!
        </div>
    """, unsafe_allow_html=True)

    with st.expander("➕ Agregar Material Manual", expanded=False):
        with st.form("form_material_manual", clear_on_submit=True):
            manual_name = st.text_input("📝 Nombre del Material",
                                        placeholder="Ej: Tornillos Especiales M8")
            manual_qty = st.number_input("📦 Cantidad", min_value=1, value=1, step=1)
            submitted = st.form_submit_button("➕ Agregar a la lista", use_container_width=True)

            if submitted:
                if manual_name.strip():
                    # Generar ID único para diferenciar manuales
                    manual_id = f"MANUAL-{len(st.session_state.manual_items) + 1:03d}"
                    st.session_state.manual_items.append({
                        'id': manual_id,
                        'name': manual_name.strip(),
                        'quantity': manual_qty,
                        'unit': 'Unidad'
                    })
                    st.success(f"✅ **{manual_name.strip()}** (x{manual_qty}) agregado a la lista.")
                else:
                    st.error("⚠️ El nombre del material no puede estar vacío.")

        # Mostrar materiales manuales ya agregados en esta sesión
        if st.session_state.manual_items:
            st.markdown("**Materiales en la lista:**")
            for i, m in enumerate(st.session_state.manual_items):
                col_m, col_del = st.columns([4, 1])
                with col_m:
                    st.markdown(f"• **{m['name']}** — {m['quantity']} {m['unit']}")
                with col_del:
                    if st.button("🗑️", key=f"del_manual_{i}", help="Eliminar"):
                        st.session_state.manual_items.pop(i)
                        st.rerun()


    st.markdown("<br>", unsafe_allow_html=True)

    # Botones de navegación
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Volver"):
            st.session_state.current_step = 1
            st.rerun()

    with col2:
        if st.button("Revisar Pedido ✅", type="primary"):
            selected_items = get_selected_items()
            if selected_items or st.session_state.manual_items:
                st.session_state.current_step = 3
                st.rerun()
            else:
                st.error("⚠️ El carrito está vacío. Agrega al menos un material con cantidad mayor a 0.")

# ============================================
# PASO 3: CONFIRMACIÓN ✅
# ============================================
elif st.session_state.current_step == 3:
    st.markdown('<div class="step-indicator">✅ PASO 3 DE 3: Confirma y Registra</div>', unsafe_allow_html=True)
    
    st.title("Resumen del Pedido")
    st.caption(f"Proyecto: **{st.session_state.selected_project}**")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Mostrar items seleccionados
    st.markdown("### 📋 Materiales Seleccionados")
    selected_items = get_selected_items()
    
    # Items del catálogo Odoo
    for item_id, qty in selected_items.items():
        item_data = next((x for x in st.session_state.catalog if x['id'] == item_id), None)
        if item_data:
            st.markdown(
                f'<div class="summary-item">'
                f'<strong>{item_data["name"]}</strong><br>'
                f'<span style="color: #64748b;">Cantidad: <strong style="color: #3b82f6;">{qty}</strong> {item_data["unit"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # Items manuales (fuera de BD)
    if st.session_state.manual_items:
        st.markdown("**✏️ Materiales Manuales:**")
        for m in st.session_state.manual_items:
            st.markdown(
                f'<div class="summary-item" style="border-left-color: #F59E0B;">'
                f'<strong>{m["name"]}</strong> <span style="font-size:0.75rem;color:#F59E0B;">● Manual</span><br>'
                f'<span style="color: #64748b;">Cantidad: <strong style="color: #F59E0B;">{m["quantity"]}</strong> {m["unit"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")
    
    # Input de nombre de técnico
    st.markdown("### 👤 Identificación del Técnico")
    technician = st.text_input(
        "Nombre Completo",
        value=st.session_state.technician_name,
        placeholder="Ej: Juan Pérez"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botones de navegación
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⬅️ Volver al Catálogo"):
            st.session_state.current_step = 2
            st.rerun()
    
    with col2:
        if st.button("🚀 Registrar", type="primary"):
            if not technician.strip():
                st.error("⚠️ Por favor escribe tu **Nombre** antes de confirmar.")
            else:
                # Guardar nombre
                st.session_state.technician_name = technician
                
                # Preparar items del catálogo Odoo
                items_to_save = [
                    {
                        "item_id": i_id,
                        "item_name": next((x['name'] for x in st.session_state.catalog if x['id'] == i_id), "Unknown"),
                        "quantity": qty,
                        "unit": next((x['unit'] for x in st.session_state.catalog if x['id'] == i_id), "Unknown")
                    }
                    for i_id, qty in selected_items.items()
                ]

                # Agregar materiales manuales a la lista
                for m in st.session_state.manual_items:
                    items_to_save.append({
                        "item_id": m['id'],
                        "item_name": f"[MANUAL] {m['name']}",
                        "quantity": m['quantity'],
                        "unit": m['unit']
                    })
                
                # Guardar en Google Sheets
                success = save_consumption(
                    st.session_state.selected_project,
                    technician,
                    items_to_save
                )
                
                if success:
                    st.success("✅ ¡Registro Exitoso! Tu consumo ha sido guardado en Google Sheets.")
                else:
                    st.warning("⚠️ Hubo un problema al guardar. Revisa la consola para más detalles.")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Botón de reinicio
                st.button("🔄 Nuevo Registro", on_click=reset_app)
