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

if "usuario_id" not in st.session_state:
    st.session_state.usuario_id = None
if "usuario_nombre" not in st.session_state:
    st.session_state.usuario_nombre = None
if "json_generado" not in st.session_state:
    st.session_state.json_generado = None
if "tipo_detectado" not in st.session_state:
    st.session_state.tipo_detectado = "fuente"


# ============================================
# VOCABULARIO DE DETECCIÓN POR TIPO DE REGLA
# ============================================

PALABRAS_FUENTE = [
    "kavak", "mercadolibre", "mercado libre", "autocosmos", "demotores", "olx",
    "seminuevos", "soloautos", "autoscout", "carfax", "carvana", "autofact",
    "url", "sitio", "portal", "página", "pagina", "web", "internet", "online",
    "enlace", "link", ".com", ".ar", ".mx", "http", "https", "www",
    "consultar en", "buscar en", "obtener de", "extraer de", "scrapear",
    "fuente de datos", "origen de datos", "portal de consulta",
    "sitio de referencia", "página de autos", "plataforma de venta"
]

PALABRAS_AJUSTE_CALCULO = [
    "aumentar", "incrementar", "subir", "sumar", "agregar", "añadir",
    "disminuir", "decrementar", "bajar", "restar", "reducir", "descontar",
    "ajustar", "modificar", "cambiar", "alterar", "variar",
    "precio", "valor", "costo", "monto", "importe", "cifra",
    "precio de venta", "precio final", "valor final", "precio objetivo",
    "precio publicación", "precio a publicar",
    "porcentaje", "%", "margen", "ganancia", "utilidad", "beneficio",
    "markup", "rentabilidad", "comisión", "recargo", "sobreprecio",
    "inflación", "inflacion", "ipc", "índice", "indice", "indexar",
    "actualizar precio", "ajuste económico", "corrección monetaria",
    "punto de decisión", "criterio de precio", "regla de precio",
    "determinar precio", "establecer precio", "definir precio", "fijar precio",
    "calcular precio de venta", "precio que aplicará", "precio a aplicar"
]

PALABRAS_DEPURACION = [
    "eliminar", "borrar", "quitar", "descartar", "excluir", "remover",
    "desechar", "filtrar fuera", "sacar", "depurar", "limpiar",
    "ruido", "desviación", "desvío", "outlier", "atípico", "anómalo",
    "inconsistente", "incoherente", "sospechoso", "dudoso",
    "más caro", "más barato", "más alto", "más bajo", "extremo",
    "máximo", "mínimo", "tope", "piso", "fuera de rango",
    "no verificado", "sin verificar", "usuario no confiable",
    "publicación vieja", "desactualizado", "duplicado", "repetido",
    "sin fotos", "sin descripción", "incompleto", "datos faltantes",
    "que pueden provocar", "que generan ruido", "que desvían",
    "publicaciones sospechosas", "eliminar los que", "quitar aquellos"
]

PALABRAS_FILTRO_BUSQUEDA = [
    "filtrar", "buscar", "encontrar", "localizar", "seleccionar por",
    "restringir", "limitar", "acotar", "parametrizar",
    "marca", "modelo", "versión", "version", "año", "anio", "kilometraje",
    "kilómetros", "kilometros", "km", "transmisión", "transmision",
    "automático", "automatico", "manual", "mecánico", "mecanico",
    "combustible", "gasolina", "diesel", "diésel", "nafta", "gnc", "híbrido", "hibrido", "eléctrico", "electrico",
    "color", "puertas", "motor", "cilindrada", "potencia", "hp", "cv",
    "equivalencia", "similar", "parecido", "comparable", "mismo",
    "rango de", "entre", "desde", "hasta", "mayor a", "menor a",
    "igual a", "aproximado", "cercano", "±", "mas menos", "más o menos",
    "coherente", "correspondiente", "acorde", "relacionado",
    "publicaciones similares", "autos similares", "vehículos similares",
    "características buscadas", "parámetros de búsqueda", "criterios de búsqueda"
]

PALABRAS_MUESTREO = [
    "muestrear", "tomar", "seleccionar", "elegir", "escoger", "extraer",
    "obtener muestra", "definir muestra", "determinar muestra",
    "muestra", "subconjunto", "subset", "porción", "parte", "fracción",
    "cantidad de publicaciones", "número de resultados", "tamaño de muestra",
    "aleatorio", "random", "al azar", "primeros", "últimos",
    "ordenar por", "top", "mejores", "peores",
    "tomar n", "seleccionar n", "los primeros", "las primeras",
    "cantidad a tomar", "cuántos tomar", "cuantos seleccionar"
]

PALABRAS_PUNTO_CONTROL = [
    "si", "cuando", "en caso de", "siempre que", "a menos que",
    "condición", "condicion", "condicional", "contingencia",
    "umbral", "límite", "limite", "mínimo", "minimo", "máximo", "maximo",
    "menos de", "más de", "mayor que", "menor que", "al menos", "como máximo",
    "no se encuentren", "no se hallen", "no hay suficientes",
    "entonces", "ampliar", "expandir", "extender", "aumentar rango",
    "reducir criterios", "flexibilizar", "relajar filtros",
    "flujo condicional", "punto de decisión", "bifurcación",
    "camino alternativo", "plan b", "fallback",
    "si no se encuentran", "si hay menos de", "si no hay suficientes",
    "en caso de no encontrar", "cuando no haya", "si faltan"
]

PALABRAS_METODO_VALUACION = [
    "mediana", "promedio", "media", "moda", "percentil",
    "media aritmética", "media ponderada", "promedio ponderado",
    "valor central", "tendencia central",
    "calcular", "computar", "determinar", "obtener", "derivar",
    "método de cálculo", "fórmula", "algoritmo",
    "precio de referencia", "valor de referencia", "precio de mercado",
    "valor de mercado", "referencia del mercado", "benchmark",
    "precio base", "valor base", "punto de partida",
    "valuación", "valuacion", "valoración", "valoracion", "tasación", "tasacion",
    "método de valuación", "criterio de valuación",
    "precio de referencia del mercado", "valor según el mercado",
    "con respecto a la muestra", "basado en las publicaciones"
]


# ============================================
# FUNCIÓN DE DETECCIÓN MEJORADA
# ============================================

def detectar_tipo_por_heuristica(descripcion: str) -> str:
    desc = descripcion.lower()
    
    puntajes = {
        "fuente": 0,
        "ajuste_calculo": 0,
        "depuracion": 0,
        "filtro_busqueda": 0,
        "muestreo": 0,
        "punto_control": 0,
        "metodo_valuacion": 0
    }
    
    for palabra in PALABRAS_FUENTE:
        if palabra in desc:
            puntajes["fuente"] += 1
    
    for palabra in PALABRAS_AJUSTE_CALCULO:
        if palabra in desc:
            puntajes["ajuste_calculo"] += 1
    
    for palabra in PALABRAS_DEPURACION:
        if palabra in desc:
            puntajes["depuracion"] += 1
    
    for palabra in PALABRAS_FILTRO_BUSQUEDA:
        if palabra in desc:
            puntajes["filtro_busqueda"] += 1
    
    for palabra in PALABRAS_MUESTREO:
        if palabra in desc:
            puntajes["muestreo"] += 1
    
    for palabra in PALABRAS_PUNTO_CONTROL:
        if palabra in desc:
            puntajes["punto_control"] += 1
    
    for palabra in PALABRAS_METODO_VALUACION:
        if palabra in desc:
            puntajes["metodo_valuacion"] += 1
    
    tipo_ganador = max(puntajes, key=puntajes.get)
    puntaje_maximo = puntajes[tipo_ganador]
    
    if puntaje_maximo == 0:
        return "fuente"
    
    return tipo_ganador


def obtener_debug_deteccion(descripcion: str) -> dict:
    desc = descripcion.lower()
    
    coincidencias = {
        "fuente": [p for p in PALABRAS_FUENTE if p in desc],
        "ajuste_calculo": [p for p in PALABRAS_AJUSTE_CALCULO if p in desc],
        "depuracion": [p for p in PALABRAS_DEPURACION if p in desc],
        "filtro_busqueda": [p for p in PALABRAS_FILTRO_BUSQUEDA if p in desc],
        "muestreo": [p for p in PALABRAS_MUESTREO if p in desc],
        "punto_control": [p for p in PALABRAS_PUNTO_CONTROL if p in desc],
        "metodo_valuacion": [p for p in PALABRAS_METODO_VALUACION if p in desc]
    }
    
    puntajes = {k: len(v) for k, v in coincidencias.items()}
    
    return {
        "coincidencias": coincidencias,
        "puntajes": puntajes,
        "ganador": max(puntajes, key=puntajes.get) if max(puntajes.values()) > 0 else "fuente"
    }


# ============================================
# PROMPT COMPLETO CON DEFINICIONES DE NEGOCIO
# ============================================

PROMPT_GENERADOR = """Eres un Arquitecto de Datos EXHAUSTIVO experto en Valuación de Vehículos Usados.
Tu trabajo es traducir descripciones en lenguaje natural a JSON técnico SIN OMITIR NINGÚN DETALLE.

## CONTEXTO DEL SISTEMA

Este sistema ayuda a vendedores de autos usados a determinar el precio de venta óptimo. El proceso es:
1. Consultar portales de autos usados (Kavak, MercadoLibre, etc.)
2. Filtrar publicaciones similares al auto que se quiere vender
3. Depurar resultados que generen ruido o distorsión
4. Tomar una muestra representativa
5. Calcular un precio de referencia del mercado
6. Aplicar ajustes para obtener el precio de venta final

## TIPOS DE REGLAS - DEFINICIONES COMPLETAS DE NEGOCIO

### 1. TIPO: "fuente"
**DEFINICIÓN DE NEGOCIO:** Reglas para obtener los PORTALES O SITIOS DE INTERNET de consulta sobre datos relevantes de autos publicados en internet con las características buscadas.
**PROPÓSITO:** Definir de dónde se extraen los datos de precios del mercado.
**PALABRAS CLAVE:** kavak, mercadolibre, sitio, portal, web, url, .com, página, fuente de datos, plataforma
**ESQUEMA JSON:**
```json
{{
  "url": "kavak.com",
  "nombre": "Kavak Argentina",
  "prioridad": 1,
  "verificado": true,
  "notas": "información adicional"
}}
```

### 2. TIPO: "filtro_busqueda"
**DEFINICIÓN DE NEGOCIO:** Reglas de FILTRADO que usa el vendedor para establecer los PARÁMETROS DE BÚSQUEDA de publicaciones coherentes con el auto que se quiere publicar. Establece EQUIVALENCIAS como Marca, modelo, kilometraje, tipo de transmisión, etc.
**PROPÓSITO:** Asegurar que solo se comparen autos similares al que se va a vender.
**PALABRAS CLAVE:** filtrar, marca, modelo, año, kilometraje, transmisión, combustible, rango, equivalencia, similar, ±
**ESQUEMA JSON:**
```json
{{
  "filtros": [
    {{"campo": "marca", "operador": "igual", "valor": "Toyota"}},
    {{"campo": "año", "operador": "entre", "valor": [-2, 2], "relativo": true}},
    {{"campo": "kilometraje", "operador": "entre", "valor": [-15000, 15000], "relativo": true}}
  ]
}}
```

### 3. TIPO: "ajuste_calculo"
**DEFINICIÓN DE NEGOCIO:** Reglas que se utilizan para DEFINIR EL PRECIO DE VENTA que aplicará el sitio objetivo de la aplicación, donde el vendedor aplicará una serie de PUNTOS DE DECISIÓN para poder determinar dicho precio. Es el cálculo final sobre el precio de referencia del mercado.
**PROPÓSITO:** Convertir el precio de mercado en un precio de venta rentable para el vendedor.
**PALABRAS CLAVE:** aumentar, disminuir, precio, valor, porcentaje, %, margen, ganancia, inflación, precio de venta, precio final, pesos, $, monto

**IMPORTANTE - DISTINGUIR ENTRE TIPOS DE AJUSTE:**
- Si menciona "%" o "porcentaje" → tipo: "ajuste_porcentual" con campo "porcentaje"
- Si menciona "$", "pesos", "monto fijo", o un número sin % → tipo: "ajuste_fijo" con campo "monto"
- Si menciona "inflación" → tipo: "inflacion"
- Si menciona "margen" o "ganancia" → tipo: "margen_ganancia"

**ESQUEMA JSON PARA ajuste_porcentual:**
```json
{{
  "tipo": "ajuste_porcentual",
  "porcentaje": 15,
  "operacion": "incrementar|decrementar",
  "base": "promedio_mercado|mediana_mercado",
  "condicion_marca": "Marca (si aplica)",
  "condicion_modelo": "Modelo (si aplica)",
  "condicion_año": 2020,
  "periodo_vigencia": {{"tipo": "mes|trimestre|permanente", "mes": "enero", "año": 2025}},
  "motivo": "razón del ajuste"
}}
```

**ESQUEMA JSON PARA ajuste_fijo (MONTO EN PESOS):**
```json
{{
  "tipo": "ajuste_fijo",
  "monto": 20000,
  "moneda": "ARS|USD",
  "operacion": "incrementar|decrementar",
  "condicion_marca": "Marca (si aplica)",
  "condicion_modelo": "Modelo (si aplica)",
  "condicion_año": 2020,
  "periodo_vigencia": {{"tipo": "mes|trimestre|permanente", "mes": "enero", "año": 2025}},
  "motivo": "razón del ajuste"
}}
```

**ESQUEMA JSON PARA inflacion:**
```json
{{
  "tipo": "inflacion",
  "porcentaje": 5,
  "periodo_dias": 30,
  "motivo": "ajuste por inflación"
}}
```

### 4. TIPO: "depuracion"
**DEFINICIÓN DE NEGOCIO:** Reglas que utiliza el vendedor para DESECHAR O ELIMINAR PUBLICACIONES de los sitios de búsqueda que pueden provocar RUIDO O DESVÍO en el cálculo del precio de referencia del mercado.
**PROPÓSITO:** Limpiar datos atípicos que distorsionarían el cálculo del precio justo.
**PALABRAS CLAVE:** eliminar, descartar, quitar, ruido, outlier, más caro, más barato, sospechoso, no verificado, duplicado
**ESQUEMA JSON:**
```json
{{
  "accion": "eliminar_outliers|eliminar_no_verificados|eliminar_duplicados|eliminar_antiguos",
  "cantidad": 5,
  "extremo": "inferior|superior|ambos",
  "dias_maximos": 60,
  "motivo": "razón de la depuración"
}}
```

### 5. TIPO: "muestreo"
**DEFINICIÓN DE NEGOCIO:** Reglas que establece el vendedor para DETERMINAR LA MUESTRA de publicaciones de los sitios de consulta de precios en internet.
**PROPÓSITO:** Seleccionar un subconjunto representativo de publicaciones para el cálculo.
**PALABRAS CLAVE:** muestra, tomar, seleccionar, aleatorio, cantidad, primeros, top, tamaño de muestra
**ESQUEMA JSON:**
```json
{{
  "metodo": "aleatorio|primeros_por_precio_asc|primeros_por_precio_desc|todos",
  "cantidad": 20,
  "criterio_orden": "precio|fecha|relevancia"
}}
```

### 6. TIPO: "punto_control"
**DEFINICIÓN DE NEGOCIO:** Reglas que establece el vendedor para determinar CONDICIONES que permitan establecer FLUJOS CONDICIONALES dentro del proceso de cálculo de precio de venta. Por ejemplo: si no se hallan más de 5 publicaciones de autos similares, aumentar el rango de búsqueda de kilometraje.
**PROPÓSITO:** Manejar casos excepcionales donde no hay suficientes datos.
**PALABRAS CLAVE:** si, cuando, condición, umbral, menos de, más de, ampliar, expandir, si no se encuentran
**ESQUEMA JSON:**
```json
{{
  "umbral_minimo": 5,
  "condicion": "si hay menos de N publicaciones",
  "condicion_marca": "Chevrolet (si aplica)",
  "condicion_modelo": "Cruze (si aplica)",
  "accion": "ampliar_busqueda|usar_fuentes_secundarias|alertar|abortar",
  "nuevos_parametros": {{
    "año_rango": [-3, 3],
    "km_rango": [-20000, 20000]
  }}
}}
```

### 7. TIPO: "metodo_valuacion"
**DEFINICIÓN DE NEGOCIO:** Reglas que DEFINEN EL PRECIO DE VENTA DE REFERENCIA DEL MERCADO. Es el MÉTODO DE VALUACIÓN con respecto a la muestra obtenida de publicaciones. Define cómo se calcula el valor central a partir de los datos.
**PROPÓSITO:** Calcular un precio de referencia justo basado en la muestra de mercado.
**PALABRAS CLAVE:** mediana, promedio, media, percentil, precio de referencia, valor de mercado, valuación, método de cálculo
**ESQUEMA JSON:**
```json
{{
  "metodo": "mediana|promedio|promedio_ponderado|percentil|moda",
  "percentil": 50,
  "excluir_extremos": true,
  "ponderaciones": {{
    "antiguedad_publicacion": 1.0,
    "verificacion_vendedor": 1.5,
    "similitud_km": 1.0
  }}
}}
```

## REGLAS DE EXTRACCIÓN - MUY IMPORTANTE

⚠️ DEBES CAPTURAR **ABSOLUTAMENTE TODOS** LOS DETALLES DE LA DESCRIPCIÓN:
- Marcas de autos mencionadas (Toyota, Renault, Chevrolet, etc.)
- Modelos específicos (Corolla, Clio, Cruze, etc.)
- Porcentajes o valores numéricos exactos
- Fechas, meses, períodos temporales (enero, febrero, Q1, trimestre, etc.)
- Años específicos
- Rangos de kilometraje
- Condiciones específicas mencionadas
- Motivos o razones explicadas
- Cualquier otro detalle relevante

NUNCA omitas información. Si el usuario menciona "enero", debe aparecer en el JSON.
Si menciona "Renault", debe aparecer. Si menciona "15%", debe aparecer exactamente.

## EJEMPLOS DE EXTRACCIÓN EXHAUSTIVA

ENTRADA: "Aumentar el precio de los autos Renault un 15% por el mes de enero"
```json
{{
  "tipo_detectado": "ajuste_calculo",
  "es_valido": true,
  "parametros": {{
    "tipo": "ajuste_porcentual",
    "porcentaje": 15,
    "operacion": "incrementar",
    "base": "promedio_mercado",
    "condicion_marca": "Renault",
    "periodo_vigencia": {{
      "tipo": "mes",
      "mes": "enero"
    }}
  }}
}}
```

ENTRADA: "Aumentar en 20000$ el precio de los autos Renault solo por el mes de enero de 2026"
```json
{{
  "tipo_detectado": "ajuste_calculo",
  "es_valido": true,
  "parametros": {{
    "tipo": "ajuste_fijo",
    "monto": 20000,
    "moneda": "ARS",
    "operacion": "incrementar",
    "condicion_marca": "Renault",
    "periodo_vigencia": {{
      "tipo": "mes",
      "mes": "enero",
      "año": 2026
    }}
  }}
}}
```

ENTRADA: "Restar 50000 pesos a los Toyota Corolla 2020"
```json
{{
  "tipo_detectado": "ajuste_calculo",
  "es_valido": true,
  "parametros": {{
    "tipo": "ajuste_fijo",
    "monto": 50000,
    "moneda": "ARS",
    "operacion": "decrementar",
    "condicion_marca": "Toyota",
    "condicion_modelo": "Corolla",
    "condicion_año": 2020
  }}
}}
```

ENTRADA: "Reducir 10% el valor de los Toyota Corolla 2020 durante el primer trimestre por baja demanda"
```json
{{
  "tipo_detectado": "ajuste_calculo",
  "es_valido": true,
  "parametros": {{
    "tipo": "ajuste_porcentual",
    "porcentaje": 10,
    "operacion": "decrementar",
    "base": "promedio_mercado",
    "condicion_marca": "Toyota",
    "condicion_modelo": "Corolla",
    "condicion_año": 2020,
    "periodo_vigencia": {{
      "tipo": "trimestre",
      "valor": "Q1"
    }},
    "motivo": "baja demanda"
  }}
}}
```

ENTRADA: "Consultar precios en Kavak y MercadoLibre como fuentes principales"
```json
{{
  "tipo_detectado": "fuente",
  "es_valido": true,
  "parametros": {{
    "fuentes": [
      {{"url": "kavak.com", "nombre": "Kavak", "prioridad": 1}},
      {{"url": "mercadolibre.com.ar", "nombre": "MercadoLibre", "prioridad": 1}}
    ],
    "notas": "fuentes principales"
  }}
}}
```

ENTRADA: "Eliminar las 5 publicaciones más baratas porque distorsionan el promedio"
```json
{{
  "tipo_detectado": "depuracion",
  "es_valido": true,
  "parametros": {{
    "accion": "eliminar_outliers",
    "cantidad": 5,
    "extremo": "inferior",
    "motivo": "distorsionan el promedio"
  }}
}}
```

ENTRADA: "Filtrar solo autos con menos de 50000 km, año 2020 en adelante, transmisión automática"
```json
{{
  "tipo_detectado": "filtro_busqueda",
  "es_valido": true,
  "parametros": {{
    "filtros": [
      {{"campo": "kilometraje", "operador": "menor", "valor": 50000}},
      {{"campo": "año", "operador": "mayor_igual", "valor": 2020}},
      {{"campo": "transmision", "operador": "igual", "valor": "automatica"}}
    ]
  }}
}}
```

ENTRADA: "Tomar una muestra de 30 publicaciones ordenadas por precio de menor a mayor"
```json
{{
  "tipo_detectado": "muestreo",
  "es_valido": true,
  "parametros": {{
    "metodo": "primeros_por_precio_asc",
    "cantidad": 30
  }}
}}
```

ENTRADA: "Si no hay al menos 10 publicaciones de Chevrolet Cruze, ampliar la búsqueda a ±3 años y ±20000 km"
```json
{{
  "tipo_detectado": "punto_control",
  "es_valido": true,
  "parametros": {{
    "umbral_minimo": 10,
    "condicion_marca": "Chevrolet",
    "condicion_modelo": "Cruze",
    "accion": "ampliar_busqueda",
    "nuevos_parametros": {{
      "año_rango": [-3, 3],
      "km_rango": [-20000, 20000]
    }}
  }}
}}
```

ENTRADA: "Usar la mediana como precio de referencia del mercado, excluyendo los valores extremos"
```json
{{
  "tipo_detectado": "metodo_valuacion",
  "es_valido": true,
  "parametros": {{
    "metodo": "mediana",
    "excluir_extremos": true
  }}
}}
```

---------------------------------------------------------
SOLICITUD ACTUAL:
"{descripcion}"

RECUERDA: 
1. Identifica correctamente el TIPO de regla según las definiciones de negocio
2. Extrae ABSOLUTAMENTE TODOS los detalles mencionados
3. No omitas fechas, marcas, modelos, porcentajes, condiciones ni ningún otro elemento

Responde SOLO con el JSON (sin explicaciones):"""


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
                "options": {"temperature": 0.1, "num_predict": 1000}
            }
            res = requests.post(url, json=payload, timeout=120)
            res.raise_for_status()
            texto_respuesta = res.json().get("response", "")
        
        elif proveedor == "groq":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": modelo if modelo else "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt_final}],
                "temperature": 0.1,
                "max_tokens": 1000
            }
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            texto_respuesta = res.json()["choices"][0]["message"]["content"]

        elif proveedor == "gemini":
            modelo_uso = modelo if modelo else "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_uso}:generateContent?key={api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt_final}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1000
                }
            }
            headers = {"Content-Type": "application/json"}
            
            res = requests.post(url, headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            texto_respuesta = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            
        return limpiar_y_parsear_json(texto_respuesta)

    except Exception as e:
        st.error(f"Error IA ({proveedor}) - Modelo: {modelo}: {e}")
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

# Descripciones completas para mostrar al usuario
TIPO_REGLA_DESCRIPCIONES = {
    "fuente": "Portales o sitios de internet de consulta sobre datos de autos publicados (Kavak, MercadoLibre, etc.)",
    "filtro_busqueda": "Parámetros de búsqueda coherentes con el auto a publicar: marca, modelo, km, transmisión, etc.",
    "depuracion": "Eliminar publicaciones que generan ruido o desvío en el cálculo del precio de referencia",
    "muestreo": "Determinar la muestra de publicaciones de los sitios de consulta",
    "punto_control": "Condiciones para flujos condicionales (ej: si hay menos de 5 publicaciones, ampliar búsqueda)",
    "metodo_valuacion": "Método para calcular el precio de referencia del mercado (mediana, promedio, etc.)",
    "ajuste_calculo": "Definir el precio de venta final aplicando puntos de decisión del vendedor"
}

CLAVES_TIPOS = list(TIPO_REGLA_LABELS.keys())


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
    modelo_seleccionado = ""
    
    if proveedor_ia == "ollama":
        if ollama_ok and ollama_modelos:
            modelo_seleccionado = st.selectbox("Modelo Ollama", ollama_modelos)
        else: 
            st.error("Ollama no detectado")
        
    elif proveedor_ia == "gemini":
        api_key_ia = st.text_input("API Key Google AI", type="password")
        
        opciones_gemini = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "Otro (Escribir manual)"
        ]
        
        seleccion = st.selectbox("Modelo Gemini", opciones_gemini)
        
        if seleccion == "Otro (Escribir manual)":
            modelo_seleccionado = st.text_input("Nombre del modelo", placeholder="ej: gemini-1.5-pro")
        else:
            modelo_seleccionado = seleccion
            
    elif proveedor_ia == "groq":
        api_key_ia = st.text_input("API Key Groq", type="password")
        modelo_seleccionado = st.selectbox(
            "Modelo Groq",
            ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
        )

    st.markdown("---")
    
    debug_mode = st.checkbox("🔧 Modo Debug", value=False)
    
    st.markdown("---")
    
    if not st.session_state.usuario_id:
        if st.button("Ingresar como Admin"):
            st.session_state.usuario_id = "admin" 
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
    st.title("Sistema de Valuación de Vehículos")
    st.info("Ingresa desde la barra lateral")
    st.stop()


# ============================================
# NUEVA REGLA
# ============================================

if pagina == "🔧 Nueva Regla":
    st.title("🔧 Nueva Regla Inteligente")
    st.caption("Describe la regla en detalle. El sistema capturará TODOS los elementos mencionados.")

    # 1. INPUTS PRIMARIOS
    col1, col2 = st.columns(2)
    with col1:
        codigo = st.text_input("Código *", placeholder="Ej: AJUSTE_RENAULT_ENERO")
        nombre = st.text_input("Nombre *", placeholder="Ej: Aumento Renault Enero")
    with col2:
        orden = st.number_input("Orden", value=10)

    # 2. DESCRIPCIÓN Y BOTÓN GENERAR
    descripcion = st.text_area(
        "Descripción (Lenguaje Natural) *", 
        height=120, 
        placeholder="Ej: Aumentar el precio de los autos Renault un 15% por el mes de enero debido a alta demanda estacional"
    )
    
    # Tips de uso mejorados
    with st.expander("💡 Tips y Guía de Tipos de Regla"):
        st.markdown("""
        ### Tipos de Regla Disponibles:
        
        | Tipo | Descripción | Ejemplo |
        |------|-------------|---------|
        | **📍 Fuente** | Portales de consulta de precios | "Agregar Kavak como fuente principal" |
        | **🔍 Filtro** | Parámetros de búsqueda (marca, modelo, km) | "Filtrar autos Toyota con menos de 50000 km" |
        | **🧹 Depuración** | Eliminar publicaciones con ruido | "Eliminar las 5 publicaciones más baratas" |
        | **📊 Muestreo** | Tamaño de muestra a analizar | "Tomar 30 publicaciones aleatorias" |
        | **⚠️ Punto Control** | Flujos condicionales | "Si hay menos de 5 autos, ampliar rango de años" |
        | **📈 Método Valuación** | Cálculo del precio de referencia | "Usar mediana como precio de referencia" |
        | **💰 Ajuste Cálculo** | Precio de venta final | "Aumentar 15% al precio de los Renault en enero" |
        
        ### Incluí todos los detalles:
        - 🚗 **Marca/Modelo**: "autos Toyota Corolla"
        - 📊 **Porcentajes**: "aumentar 15%", "reducir 10%"
        - 📅 **Fechas/Períodos**: "por el mes de enero", "durante Q1"
        - 🎯 **Condiciones**: "si hay menos de 5 publicaciones"
        - 💬 **Motivos**: "por alta demanda", "debido a inflación"
        """)
    
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        generar = st.button("✨ Generar", type="primary", use_container_width=True)
    with col_btn2:
        limpiar = st.button("🗑️ Limpiar", use_container_width=True)

    if limpiar:
        st.session_state.json_generado = None
        st.session_state.tipo_detectado = "fuente"
        st.rerun()

    # 3. LÓGICA DE PROCESAMIENTO
    if generar and descripcion:
        if proveedor_ia != "ollama" and not api_key_ia:
            st.error("Falta API Key")
        else:
            with st.spinner(f"🧠 Analizando con {modelo_seleccionado}..."):
                resultado = generar_con_ia_generico(proveedor_ia, api_key_ia, modelo_seleccionado, descripcion)
                
                # Debug info (solo para mostrar, no para decidir)
                debug_info = obtener_debug_deteccion(descripcion) if debug_mode else None
                
                if resultado and resultado.get("es_valido", False):
                    # PRIORIDAD: El tipo lo define la IA
                    tipo_ia = str(resultado.get("tipo_detectado", "")).lower().strip()
                    
                    # Validar que el tipo de la IA sea válido
                    if tipo_ia in CLAVES_TIPOS:
                        tipo_final = tipo_ia
                    else:
                        # Fallback a heurística solo si la IA devuelve un tipo inválido
                        tipo_heuristica = detectar_tipo_por_heuristica(descripcion)
                        tipo_final = tipo_heuristica if tipo_heuristica in CLAVES_TIPOS else "fuente"
                        st.warning(f"⚠️ Tipo de IA '{tipo_ia}' no reconocido. Usando heurística: {tipo_final}")
                    
                    st.success(f"✅ Análisis completo | Tipo detectado por IA: **{TIPO_REGLA_LABELS.get(tipo_final, tipo_final)}**")
                    
                    if debug_mode and debug_info:
                        with st.expander("🔧 Debug de Detección (Solo referencia)"):
                            st.write("**Tipo definido por IA:**", tipo_ia)
                            st.write("**Puntajes heurísticos (referencia):**")
                            st.json(debug_info["puntajes"])
                            st.write("**Palabras coincidentes:**")
                            for tipo, palabras in debug_info["coincidencias"].items():
                                if palabras:
                                    st.write(f"- **{tipo}**: {', '.join(palabras[:5])}{'...' if len(palabras) > 5 else ''}")
                    
                    st.session_state.tipo_detectado = tipo_final
                    st.session_state.json_generado = resultado.get("parametros", {})
                    
                    st.rerun()
                else:
                    # Solo si la IA falla completamente, usar heurística como fallback
                    tipo_heuristica = detectar_tipo_por_heuristica(descripcion)
                    st.warning(f"⚠️ IA sin resultado válido. Usando heurística como fallback: **{TIPO_REGLA_LABELS.get(tipo_heuristica)}**")
                    st.session_state.tipo_detectado = tipo_heuristica
                    st.session_state.json_generado = {}

    st.markdown("---")

    # 4. OUTPUTS
    col_out1, col_out2 = st.columns([1, 1])
    
    with col_out1:
        st.info("Tipo de Regla Detectado (Editable)")
        
        tipo_actual = st.session_state.tipo_detectado
        if tipo_actual in CLAVES_TIPOS:
            indice_tipo = CLAVES_TIPOS.index(tipo_actual)
        else:
            indice_tipo = 0
        
        tipo = st.selectbox(
            "Seleccione Tipo", 
            CLAVES_TIPOS, 
            index=indice_tipo,
            format_func=lambda x: TIPO_REGLA_LABELS[x],
            key="sb_tipo_final",
            label_visibility="collapsed"
        )
        
        # Mostrar descripción del tipo seleccionado
        st.caption(f"ℹ️ {TIPO_REGLA_DESCRIPCIONES.get(tipo, '')}")
        
        if tipo != st.session_state.tipo_detectado:
            st.session_state.tipo_detectado = tipo

    with col_out2:
        st.info("Parámetros JSON Generados (Editable)")
        json_val = json.dumps(st.session_state.json_generado, indent=2, ensure_ascii=False) if st.session_state.json_generado else "{}"
        json_editado = st.text_area("", value=json_val, height=300, label_visibility="collapsed")
        
        try:
            json.loads(json_editado)
            st.caption("✅ JSON válido")
        except:
            st.caption("❌ JSON inválido")

    # 5. GUARDAR
    puede_guardar = json_editado and json_editado != "{}"
    
    if st.button("💾 Guardar Regla", type="primary", use_container_width=True, disabled=not puede_guardar):
        if not codigo or not nombre:
            st.error("Código y Nombre son obligatorios")
        else:
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
                    st.success("✅ Regla guardada exitosamente")
                    st.session_state.json_generado = None
                    st.session_state.tipo_detectado = "fuente"
                    st.balloons()
            except json.JSONDecodeError:
                st.error("El JSON no es válido. Corregilo antes de guardar.")
            except Exception as e:
                st.error(f"Error: {e}")


# ============================================
# LISTADO DE REGLAS
# ============================================

elif pagina == "📋 Reglas Activas":
    st.title("📋 Reglas Activas")
    
    reglas = api_get("/reglas")
    
    if not reglas:
        st.info("No hay reglas configuradas. Ve a 'Nueva Regla' para crear una.")
    else:
        reglas_por_tipo = {}
        for r in reglas:
            tipo = r.get('tipo', 'otro')
            if tipo not in reglas_por_tipo:
                reglas_por_tipo[tipo] = []
            reglas_por_tipo[tipo].append(r)
        
        for tipo, lista in reglas_por_tipo.items():
            st.subheader(TIPO_REGLA_LABELS.get(tipo, tipo))
            st.caption(TIPO_REGLA_DESCRIPCIONES.get(tipo, ''))
            
            for r in lista:
                with st.expander(f"{'✅' if r.get('activo', True) else '❌'} {r['nombre']} - `{r.get('codigo', '')}`"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        if r.get('descripcion'):
                            st.caption(f"📝 {r['descripcion']}")
                        st.json(r['parametros'])
                    
                    with col2:
                        if st.button("🗑️ Desactivar", key=f"del_{r['id']}"):
                            api_put(f"/reglas/{r['id']}", {"activo": False}, {"usuario_id": st.session_state.usuario_id})
                            st.rerun()


# ============================================
# AUDITORÍA
# ============================================

elif pagina == "📜 Auditoría":
    st.title("📜 Registro de Auditoría")
    
    aud = api_get("/auditoria")
    
    if aud:
        df = pd.DataFrame(aud)
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay registros de auditoría")


# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.caption(f"Sistema de Valuación v1.9 | Usuario: {st.session_state.usuario_nombre} | {datetime.now().strftime('%H:%M')}")