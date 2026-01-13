# frontend/app.py
import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime

# ============================================
# CONFIGURACIÓN
# ============================================

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Gestión de Reglas de Valuación",
    page_icon="🚗",
    layout="wide"
)

# Inicialización de Estados
if "usuario_id" not in st.session_state:
    st.session_state.usuario_id = None
if "usuario_nombre" not in st.session_state:
    st.session_state.usuario_nombre = None
if "json_generado" not in st.session_state:
    st.session_state.json_generado = None
# Estado para el SelectBox dinámico
if "tipo_seleccionado_index" not in st.session_state:
    st.session_state.tipo_seleccionado_index = 0


# ============================================
# PROMPT (CHAIN OF THOUGHT)
# ============================================

PROMPT_GENERADOR = """Eres un Arquitecto de Datos experto en Valuación de Vehículos.
Tu trabajo es traducir lenguaje natural a una estructura JSON técnica estricta.

### TUS OBJETIVOS:
1. ANALIZAR: Entiende qué quiere hacer el usuario.
2. CLASIFICAR: Asigna el "tipo_detectado" correcto.
3. ESTRUCTURAR: Genera el JSON "parametros".

### TIPOS DE REGLA Y SUS ESQUEMAS:

1. TIPO: "fuente" (Origen de datos)
   - Esquema: {{"url": "...", "nombre": "...", "prioridad": 1}}

2. TIPO: "filtro_busqueda" (Restricciones de búsqueda)
   - Esquema: {{"campo": "marca|modelo|año|km", "operador": "igual|entre|mayor", "valor": "..."}}

3. TIPO: "ajuste_calculo" (Modificar precio/valor)
   - Palabras clave: Aumentar, disminuir, sumar, restar, inflacion, ganancia, porcentaje, precio, valor.
   - Esquema A (Porcentual): {{"tipo": "ajuste_porcentual", "porcentaje": 10, "base": "promedio_mercado", "operacion": "incrementar|disminuir", "condicion": "opcional"}}
   - Esquema B (Fijo): {{"tipo": "margen_ganancia", "porcentaje": 20}}
   - Esquema C (Inflación): {{"tipo": "inflacion", "porcentaje": 5, "periodo_dias": 30}}

4. TIPO: "depuracion" (Limpieza)
   - Esquema: {{"accion": "eliminar_outliers", "cantidad": 5}}

### EJEMPLOS (Few-Shot):

Usuario: "Buscar precios en kavak.com"
JSON: {{"tipo_detectado": "fuente", "es_valido": true, "parametros": {{"url": "kavak.com", "nombre": "Kavak", "prioridad": 1}}}}

Usuario: "Aumentar 10% al valor de los autos Toyota"
JSON: {{"tipo_detectado": "ajuste_calculo", "es_valido": true, "parametros": {{"tipo": "ajuste_porcentual", "porcentaje": 10, "operacion": "incrementar", "base": "promedio_mercado", "condicion": "marca igual a Toyota"}}}}

---------------------------------------------------------
SOLICITUD ACTUAL:
"{descripcion}"

Responde SOLO con el JSON final:"""


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def generar_con_ia_generico(proveedor, api_key, modelo, descripcion):
    """Llamada a la IA"""
    try:
        prompt_final = PROMPT_GENERADOR.format(descripcion=descripcion)
        texto_respuesta = ""

        if proveedor == "ollama":
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": modelo,
                "prompt": prompt_final,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 600}
            }
            res = requests.post(url, json=payload, timeout=60)
            res.raise_for_status()
            texto_respuesta = res.json().get("response", "")
        
        elif proveedor == "groq":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt_final}],
                "temperature": 0.1
            }
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            texto_respuesta = res.json()["choices"][0]["message"]["content"]

        elif proveedor == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt_final}]}]}
            headers = {"Content-Type": "application/json"}
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            texto_respuesta = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            
        return limpiar_y_parsear_json(texto_respuesta)

    except Exception as e:
        st.error(f"Error IA ({proveedor}): {e}")
        return None

def limpiar_y_parsear_json(texto: str) -> dict:
    texto = texto.strip()
    if "```json" in texto:
        texto = texto.split("```json")[1]
    if "```" in texto:
        texto = texto.split("```")[0]
    try:
        return json.loads(texto.strip())
    except:
        import re
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
        return None

def verificar_ollama() -> tuple:
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=1)
        if response.status_code == 200:
            modelos = [m["name"] for m in response.json().get("models", [])]
            return True, modelos
    except: pass
    return False, []

# Helpers API
def api_get(ep): 
    try: return requests.get(f"{API_URL}{ep}").json()
    except: return None
def api_post(ep, d, p=None): 
    try: return requests.post(f"{API_URL}{ep}", json=d, params=p).json()
    except Exception as e: st.error(f"Error: {e}"); return None
def api_put(ep, d, p=None): 
    try: return requests.put(f"{API_URL}{ep}", json=d, params=p).json()
    except Exception as e: st.error(f"Error: {e}"); return None

TIPO_REGLA_LABELS = {
    "fuente": "📍 Fuente de Datos",
    "filtro_busqueda": "🔍 Filtro de Búsqueda",
    "depuracion": "🧹 Depuración",
    "muestreo": "📊 Muestreo",
    "punto_control": "⚠️ Punto de Control",
    "metodo_valuacion": "📈 Método de Valuación",
    "ajuste_calculo": "💰 Ajuste de Cálculo"
}


# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.title("🚗 Valuación")
    st.markdown("---")
    st.subheader("🤖 Configuración IA")
    ollama_ok, ollama_modelos = verificar_ollama()
    
    proveedor_ia = st.selectbox("Proveedor", ["ollama", "groq", "gemini"])
    api_key_ia = ""
    modelo_ollama = "llama3.2"
    
    if proveedor_ia == "ollama":
        if ollama_ok and ollama_modelos:
            modelo_ollama = st.selectbox("Modelo", ollama_modelos)
        else: st.error("Ollama no detectado")
    else:
        api_key_ia = st.text_input("API Key", type="password")

    st.markdown("---")
    if not st.session_state.usuario_id:
        if st.button("Ingresar como Admin"):
            st.session_state.usuario_id = "admin" # Simplificado
            st.session_state.usuario_nombre = "Admin Sistema"
            st.rerun()
    else:
        st.success(f"👤 {st.session_state.usuario_nombre}")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_id = None
            st.rerun()
        st.markdown("---")
        pagina = st.radio("Menú", ["📋 Reglas Activas", "🔧 Nueva Regla", "📜 Auditoría"], label_visibility="collapsed")


# ============================================
# MAIN
# ============================================

if not st.session_state.usuario_id:
    st.title("Sistema de Valuación")
    st.info("Ingresa desde la barra lateral")
    st.stop()


# ============================================
# NUEVA REGLA (LAYOUT CORREGIDO)
# ============================================

if pagina == "🔧 Nueva Regla":
    st.title("🔧 Nueva Regla Inteligente")
    st.caption("Describe la regla, presiona Generar y el sistema completará el tipo y los parámetros.")

    # 1. INPUTS PRIMARIOS
    col1, col2 = st.columns(2)
    with col1:
        codigo = st.text_input("Código *", placeholder="Ej: AJUSTE_TOYOTA")
        nombre = st.text_input("Nombre *", placeholder="Ej: Aumentar valor Toyota")
    with col2:
        orden = st.number_input("Orden", value=10)

    # 2. DESCRIPCIÓN Y BOTÓN GENERAR
    descripcion = st.text_area("Descripción (Lenguaje Natural) *", height=100, placeholder="Ej: Aumentar un 10% el valor de los autos Toyota")
    
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        generar = st.button("✨ Generar", type="primary", use_container_width=True)
    with col_btn2:
        limpiar = st.button("🗑️ Limpiar", use_container_width=True)

    if limpiar:
        st.session_state.json_generado = None
        st.rerun()

    # 3. LÓGICA DE PROCESAMIENTO (Ocurre al presionar)
    if generar and descripcion:
        if proveedor_ia != "ollama" and not api_key_ia:
            st.error("Falta API Key")
        else:
            with st.spinner("🧠 Analizando..."):
                resultado = generar_con_ia_generico(proveedor_ia, api_key_ia, modelo_ollama, descripcion)
                
                if resultado and resultado.get("es_valido", False):
                    # --- HEURÍSTICA FUERTE EN PYTHON ---
                    # Esto sobreescribe a la IA si encuentra palabras clave obvias
                    raw_tipo = str(resultado.get("tipo_detectado", "")).lower()
                    desc_lower = descripcion.lower()
                    
                    claves_tipos = list(TIPO_REGLA_LABELS.keys())
                    tipo_final = raw_tipo # Por defecto lo que diga la IA

                    # Reglas forzadas (Safety Net)
                    if "http" in desc_lower or ".com" in desc_lower:
                        tipo_final = "fuente"
                    elif any(x in desc_lower for x in ["aumentar", "restar", "precio", "valor", "%", "ajustar"]):
                        tipo_final = "ajuste_calculo"
                    elif "eliminar" in desc_lower or "borrar" in desc_lower:
                        tipo_final = "depuracion"
                    elif "buscar" in desc_lower and "precio" not in desc_lower:
                        tipo_final = "filtro_busqueda"

                    # Mapeo de sinónimos extra
                    mapa_correccion = {"url": "fuente", "calculo": "ajuste_calculo", "filtro": "filtro_busqueda"}
                    tipo_final = mapa_correccion.get(tipo_final, tipo_final)

                    # Actualizar estado
                    if tipo_final in claves_tipos:
                        st.session_state.tipo_seleccionado_index = claves_tipos.index(tipo_final)
                    
                    st.session_state.json_generado = resultado.get("parametros", {})
                    st.toast(f"✅ Detectado: {TIPO_REGLA_LABELS.get(tipo_final, tipo_final)}", icon="🎯")
                    st.rerun() # RECARGA PARA MOSTRAR EL SELECTBOX CORRECTO ABAJO
                else:
                    st.error("No se pudo generar una regla válida.")

    st.markdown("---")

    # 4. OUTPUTS (Se muestran DEBAJO de los botones)
    # Al hacer rerun(), estos componentes se renderizan con el nuevo index del session_state
    
    col_out1, col_out2 = st.columns([1, 1])
    
    with col_out1:
        st.info("Tipo de Regla Detectado (Editable)")
        claves_tipos = list(TIPO_REGLA_LABELS.keys())
        
        # Selectbox controlado por el índice del estado
        idx_seguro = st.session_state.tipo_seleccionado_index
        if idx_seguro >= len(claves_tipos): idx_seguro = 0
            
        tipo = st.selectbox(
            "Seleccione Tipo", 
            claves_tipos, 
            index=idx_seguro,
            format_func=lambda x: TIPO_REGLA_LABELS[x],
            key="sb_tipo_final",
            label_visibility="collapsed"
        )

    with col_out2:
        st.info("Parámetros JSON Generados")
        json_val = json.dumps(st.session_state.json_generado, indent=2, ensure_ascii=False) if st.session_state.json_generado else "{}"
        json_editado = st.text_area("", value=json_val, height=250, label_visibility="collapsed")

    # 5. GUARDAR
    if st.button("💾 Guardar Regla", type="secondary", use_container_width=True, disabled=json_val=="{}"):
        try:
            payload = {
                "codigo": codigo.upper().replace(" ", "_"),
                "nombre": nombre,
                "tipo": tipo,
                "parametros": json.loads(json_editado),
                "descripcion": descripcion,
                "orden": orden
            }
            res = api_post("/reglas", payload, {"usuario_id": st.session_state.usuario_id})
            if res:
                st.success("Guardado exitosamente")
                st.session_state.json_generado = None
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")


# ============================================
# LISTADO Y AUDITORIA (Simplificado)
# ============================================

elif pagina == "📋 Reglas Activas":
    st.title("📋 Reglas")
    reglas = api_get("/reglas")
    if reglas:
        for r in reglas:
            with st.expander(f"{r['nombre']} ({r['tipo']})"):
                st.json(r['parametros'])
                if st.button("Eliminar", key=r['id']):
                    api_put(f"/reglas/{r['id']}", {"activo": False}, {"usuario_id": st.session_state.usuario_id})
                    st.rerun()

elif pagina == "📜 Auditoría":
    st.title("📜 Auditoría")
    aud = api_get("/auditoria")
    if aud: st.dataframe(pd.DataFrame(aud))