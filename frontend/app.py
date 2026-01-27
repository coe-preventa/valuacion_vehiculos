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

═══════════════════════════════════════════════════════════════════════════════
### 1. TIPO: "fuente"
═══════════════════════════════════════════════════════════════════════════════
**DEFINICIÓN DE NEGOCIO:** Reglas para obtener los PORTALES O SITIOS DE INTERNET de consulta sobre datos relevantes de autos publicados en internet con las características buscadas.
**PROPÓSITO:** Definir de dónde se extraen los datos de precios del mercado.

**ESCENARIOS CONTEMPLADOS:**
- Agregar un nuevo portal de consulta (Kavak, MercadoLibre, Autocosmos, etc.)
- Definir prioridad entre fuentes (cuál consultar primero)
- Marcar fuentes como verificadas o confiables
- Fuentes específicas por país o región (Argentina, México, Chile)
- Fuentes especializadas por tipo de vehículo (autos de lujo, comerciales, etc.)
- Excluir o deshabilitar una fuente temporalmente

**PALABRAS CLAVE:** kavak, mercadolibre, autocosmos, demotores, olx, seminuevos, sitio, portal, web, url, .com, página, fuente, plataforma, consultar, buscar en, agregar fuente, quitar fuente, prioridad, principal, secundaria, confiable, verificado

**ESQUEMA JSON:**
```json
{{
  "url": "kavak.com.ar",
  "nombre": "Kavak Argentina",
  "pais": "Argentina",
  "prioridad": 1,
  "verificado": true,
  "tipo_vehiculos": "todos|autos|motos|comerciales",
  "activo": true,
  "notas": "información adicional"
}}
```

**ESQUEMA JSON PARA MÚLTIPLES FUENTES:**
```json
{{
  "fuentes": [
    {{"url": "kavak.com.ar", "nombre": "Kavak", "prioridad": 1}},
    {{"url": "mercadolibre.com.ar", "nombre": "MercadoLibre", "prioridad": 2}}
  ]
}}
```

═══════════════════════════════════════════════════════════════════════════════
### 2. TIPO: "filtro_busqueda"
═══════════════════════════════════════════════════════════════════════════════
**DEFINICIÓN DE NEGOCIO:** Reglas de FILTRADO que usa el vendedor para establecer los PARÁMETROS DE BÚSQUEDA de publicaciones coherentes con el auto que se quiere publicar. Establece EQUIVALENCIAS como Marca, modelo, kilometraje, tipo de transmisión, etc.
**PROPÓSITO:** Asegurar que solo se comparen autos similares al que se va a vender.

**ESCENARIOS CONTEMPLADOS:**
- Filtrar por marca exacta o lista de marcas equivalentes
- Filtrar por modelo exacto o familia de modelos
- Rango de años (±1, ±2 años del vehículo a valuar)
- Rango de kilometraje (±10000 km, ±20000 km)
- Tipo de transmisión (automática, manual, CVT, secuencial)
- Tipo de combustible (nafta, diesel, GNC, híbrido, eléctrico)
- Cantidad de puertas (2, 3, 4, 5)
- Color específico o grupo de colores
- Versión o equipamiento específico
- Ubicación geográfica (provincia, ciudad, zona)
- Estado del vehículo (nuevo, usado, 0km)
- Tipo de vendedor (particular, concesionaria, agencia)
- Filtros combinados con múltiples condiciones

**PALABRAS CLAVE:** filtrar, buscar, marca, modelo, año, kilometraje, km, transmisión, automático, manual, combustible, nafta, diesel, gnc, híbrido, eléctrico, puertas, color, versión, ubicación, provincia, ciudad, rango, entre, desde, hasta, mayor, menor, igual, similar, equivalente, ±, más menos

**OPERADORES DISPONIBLES:** igual, diferente, mayor, menor, mayor_igual, menor_igual, entre, contiene, en_lista

**ESQUEMA JSON:**
```json
{{
  "filtros": [
    {{"campo": "marca", "operador": "igual", "valor": "Toyota"}},
    {{"campo": "marca", "operador": "en_lista", "valor": ["Toyota", "Honda", "Nissan"]}},
    {{"campo": "modelo", "operador": "contiene", "valor": "Corolla"}},
    {{"campo": "año", "operador": "entre", "valor": [-2, 2], "relativo": true}},
    {{"campo": "año", "operador": "mayor_igual", "valor": 2018}},
    {{"campo": "kilometraje", "operador": "menor", "valor": 80000}},
    {{"campo": "kilometraje", "operador": "entre", "valor": [-15000, 15000], "relativo": true}},
    {{"campo": "transmision", "operador": "igual", "valor": "automatica"}},
    {{"campo": "combustible", "operador": "en_lista", "valor": ["nafta", "gnc"]}},
    {{"campo": "ubicacion", "operador": "igual", "valor": "Buenos Aires"}},
    {{"campo": "tipo_vendedor", "operador": "igual", "valor": "concesionaria"}}
  ]
}}
```

═══════════════════════════════════════════════════════════════════════════════
### 3. TIPO: "ajuste_calculo"
═══════════════════════════════════════════════════════════════════════════════
**DEFINICIÓN DE NEGOCIO:** Reglas que se utilizan para DEFINIR EL PRECIO DE VENTA que aplicará el sitio objetivo de la aplicación, donde el vendedor aplicará una serie de PUNTOS DE DECISIÓN para poder determinar dicho precio. Es el cálculo final sobre el precio de referencia del mercado.
**PROPÓSITO:** Convertir el precio de mercado en un precio de venta rentable para el vendedor.

**ESCENARIOS CONTEMPLADOS:**
- Ajuste porcentual general (aumentar/disminuir X% a todos los autos)
- Ajuste porcentual por marca específica (Renault +15%, Toyota -5%)
- Ajuste porcentual por modelo específico (Corolla +10%)
- Ajuste porcentual por año (autos 2020+ tienen +5%)
- Ajuste porcentual por rango de precio (autos > $5M tienen -3%)
- Ajuste fijo en pesos (sumar/restar $50000)
- Ajuste fijo en dólares (sumar/restar USD 500)
- Ajuste por inflación mensual/anual
- Ajuste por temporada o mes específico (enero, diciembre, verano)
- Ajuste por trimestre (Q1, Q2, Q3, Q4)
- Ajuste por demanda (alta demanda +X%, baja demanda -X%)
- Ajuste por antigüedad del vehículo
- Ajuste por kilometraje (bajo km +X%, alto km -X%)
- Margen de ganancia fijo o porcentual
- Comisión de venta
- Ajuste por condición especial (único dueño, service oficial, etc.)
- Ajuste combinado con múltiples condiciones

**PALABRAS CLAVE:** aumentar, incrementar, subir, sumar, agregar, disminuir, decrementar, bajar, restar, reducir, descontar, ajustar, precio, valor, porcentaje, %, pesos, $, dólares, USD, monto, margen, ganancia, utilidad, inflación, temporada, mes, trimestre, demanda, comisión

**IMPORTANTE - DISTINGUIR ENTRE TIPOS:**
- "%" o "porcentaje" o "por ciento" → tipo: "ajuste_porcentual" con campo "porcentaje"
- "$" o "pesos" o "monto" (número sin %) → tipo: "ajuste_fijo" con campo "monto"
- "dólares" o "USD" o "usd" → tipo: "ajuste_fijo" con moneda: "USD"
- "inflación" → tipo: "inflacion"
- "margen" o "ganancia" → tipo: "margen_ganancia"

**ESQUEMA JSON PARA ajuste_porcentual:**
```json
{{
  "tipo": "ajuste_porcentual",
  "porcentaje": 15,
  "operacion": "incrementar|decrementar",
  "base": "promedio_mercado|mediana_mercado|precio_minimo|precio_maximo",
  "condicion_marca": "Marca (si aplica)",
  "condicion_modelo": "Modelo (si aplica)",
  "condicion_año": 2020,
  "condicion_año_operador": "igual|mayor|menor|mayor_igual|menor_igual",
  "condicion_km_max": 50000,
  "condicion_km_min": 0,
  "condicion_precio_min": 1000000,
  "condicion_precio_max": 5000000,
  "periodo_vigencia": {{"tipo": "mes|trimestre|semestre|año|permanente|rango_fechas", "mes": "enero", "año": 2026, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"}},
  "motivo": "razón del ajuste"
}}
```

**ESQUEMA JSON PARA ajuste_fijo:**
```json
{{
  "tipo": "ajuste_fijo",
  "monto": 50000,
  "moneda": "ARS|USD",
  "operacion": "incrementar|decrementar",
  "condicion_marca": "Marca (si aplica)",
  "condicion_modelo": "Modelo (si aplica)",
  "condicion_año": 2020,
  "periodo_vigencia": {{"tipo": "mes|trimestre|permanente", "mes": "enero", "año": 2026}},
  "motivo": "razón del ajuste"
}}
```

**ESQUEMA JSON PARA inflacion:**
```json
{{
  "tipo": "inflacion",
  "porcentaje": 5,
  "periodo_dias": 30,
  "aplicar_automatico": true,
  "fuente_indice": "INDEC|privado",
  "motivo": "ajuste por inflación mensual"
}}
```

**ESQUEMA JSON PARA margen_ganancia:**
```json
{{
  "tipo": "margen_ganancia",
  "porcentaje": 12,
  "minimo_pesos": 100000,
  "maximo_pesos": 500000,
  "motivo": "margen de ganancia estándar"
}}
```

═══════════════════════════════════════════════════════════════════════════════
### 4. TIPO: "depuracion"
═══════════════════════════════════════════════════════════════════════════════
**DEFINICIÓN DE NEGOCIO:** Reglas que utiliza el vendedor para DESECHAR O ELIMINAR PUBLICACIONES de los sitios de búsqueda que pueden provocar RUIDO O DESVÍO en el cálculo del precio de referencia del mercado.
**PROPÓSITO:** Limpiar datos atípicos que distorsionarían el cálculo del precio justo.

**ESCENARIOS CONTEMPLADOS:**
- Eliminar N publicaciones más caras (outliers superiores)
- Eliminar N publicaciones más baratas (outliers inferiores)
- Eliminar extremos de ambos lados
- Eliminar por porcentaje (el 10% más caro y más barato)
- Eliminar publicaciones sin fotos
- Eliminar publicaciones sin descripción completa
- Eliminar publicaciones de vendedores no verificados
- Eliminar publicaciones muy antiguas (más de X días)
- Eliminar publicaciones duplicadas
- Eliminar publicaciones con precios sospechosos (muy por debajo/encima del promedio)
- Eliminar por desviación estándar (más de 2 desviaciones del promedio)
- Eliminar publicaciones de cierta ubicación
- Eliminar publicaciones sin precio visible
- Eliminar publicaciones de vendedores con mala reputación

**PALABRAS CLAVE:** eliminar, borrar, quitar, descartar, excluir, remover, desechar, depurar, limpiar, filtrar fuera, sacar, ruido, outlier, atípico, extremo, más caro, más barato, sospechoso, no verificado, sin verificar, duplicado, repetido, sin fotos, sin descripción, incompleto, antiguo, viejo, desactualizado

**ESQUEMA JSON:**
```json
{{
  "accion": "eliminar_outliers|eliminar_extremos_porcentaje|eliminar_sin_fotos|eliminar_sin_descripcion|eliminar_no_verificados|eliminar_duplicados|eliminar_antiguos|eliminar_por_desviacion|eliminar_por_criterio",
  "cantidad": 5,
  "porcentaje": 10,
  "extremo": "inferior|superior|ambos",
  "dias_maximos": 60,
  "desviaciones_estandar": 2,
  "criterio_campo": "campo a evaluar",
  "criterio_condicion": "igual|mayor|menor",
  "criterio_valor": "valor a comparar",
  "motivo": "razón de la depuración"
}}
```

═══════════════════════════════════════════════════════════════════════════════
### 5. TIPO: "muestreo"
═══════════════════════════════════════════════════════════════════════════════
**DEFINICIÓN DE NEGOCIO:** Reglas que establece el vendedor para DETERMINAR LA MUESTRA de publicaciones de los sitios de consulta de precios en internet.
**PROPÓSITO:** Seleccionar un subconjunto representativo de publicaciones para el cálculo.

**ESCENARIOS CONTEMPLADOS:**
- Tomar todas las publicaciones disponibles
- Tomar N publicaciones aleatorias
- Tomar las N más recientes (por fecha de publicación)
- Tomar las N más baratas (precio ascendente)
- Tomar las N más caras (precio descendente)
- Tomar las N más relevantes (según criterio de la fuente)
- Tomar las N con más fotos o mejor descripción
- Tomar las N de vendedores verificados
- Tomar un porcentaje del total
- Tomar estratificado por fuente (X de cada portal)
- Limitar máximo de publicaciones por fuente
- Muestreo ponderado por antigüedad de publicación

**PALABRAS CLAVE:** muestra, muestreo, tomar, seleccionar, elegir, escoger, cantidad, número, primeros, últimos, aleatorio, random, al azar, más recientes, más baratos, más caros, top, mejores, todos, porcentaje, máximo, límite

**ESQUEMA JSON:**
```json
{{
  "metodo": "todos|aleatorio|primeros_por_precio_asc|primeros_por_precio_desc|primeros_por_fecha|primeros_por_relevancia|estratificado",
  "cantidad": 20,
  "porcentaje": 50,
  "maximo_por_fuente": 10,
  "criterio_orden": "precio|fecha|relevancia|verificacion",
  "priorizar_verificados": true,
  "solo_con_fotos": true
}}
```

═══════════════════════════════════════════════════════════════════════════════
### 6. TIPO: "punto_control"
═══════════════════════════════════════════════════════════════════════════════
**DEFINICIÓN DE NEGOCIO:** Reglas que establece el vendedor para determinar CONDICIONES que permitan establecer FLUJOS CONDICIONALES dentro del proceso de cálculo de precio de venta. Por ejemplo: si no se hallan más de 5 publicaciones de autos similares, aumentar el rango de búsqueda de kilometraje.
**PROPÓSITO:** Manejar casos excepcionales donde no hay suficientes datos o condiciones especiales.

**ESCENARIOS CONTEMPLADOS:**
- Si hay menos de N publicaciones, ampliar rango de años
- Si hay menos de N publicaciones, ampliar rango de kilometraje
- Si hay menos de N publicaciones, agregar marcas similares
- Si hay menos de N publicaciones, buscar en más fuentes
- Si hay menos de N publicaciones, alertar al usuario
- Si hay menos de N publicaciones, abortar valuación
- Si el precio promedio supera X, aplicar ajuste especial
- Si la desviación es muy alta, eliminar más outliers
- Si no hay publicaciones de concesionarias, incluir particulares
- Si el modelo es muy nuevo, usar solo fuentes verificadas
- Si el modelo es muy viejo, ampliar búsqueda
- Validación cruzada entre fuentes
- Condiciones específicas por marca/modelo

**PALABRAS CLAVE:** si, cuando, en caso de, siempre que, a menos que, condición, umbral, mínimo, máximo, menos de, más de, al menos, como máximo, no se encuentran, no hay suficientes, entonces, ampliar, expandir, extender, reducir, flexibilizar, alertar, abortar, cancelar, usar alternativa, plan b, fallback

**ESQUEMA JSON:**
```json
{{
  "condicion_tipo": "cantidad_minima|cantidad_maxima|precio_promedio|desviacion_alta|sin_resultados",
  "umbral_minimo": 5,
  "umbral_maximo": 100,
  "condicion_marca": "Marca específica (si aplica)",
  "condicion_modelo": "Modelo específico (si aplica)",
  "condicion_año": 2020,
  "accion": "ampliar_busqueda|reducir_busqueda|usar_fuentes_secundarias|agregar_marcas_similares|alertar|abortar|aplicar_ajuste_especial",
  "nuevos_parametros": {{
    "año_rango": [-3, 3],
    "km_rango": [-30000, 30000],
    "marcas_adicionales": ["Honda", "Nissan"],
    "incluir_particulares": true
  }},
  "mensaje_alerta": "Mensaje personalizado para el usuario",
  "ajuste_especial": {{"tipo": "porcentual", "valor": -5}}
}}
```

═══════════════════════════════════════════════════════════════════════════════
### 7. TIPO: "metodo_valuacion"
═══════════════════════════════════════════════════════════════════════════════
**DEFINICIÓN DE NEGOCIO:** Reglas que DEFINEN EL PRECIO DE VENTA DE REFERENCIA DEL MERCADO. Es el MÉTODO DE VALUACIÓN con respecto a la muestra obtenida de publicaciones. Define cómo se calcula el valor central a partir de los datos.
**PROPÓSITO:** Calcular un precio de referencia justo basado en la muestra de mercado.

**ESCENARIOS CONTEMPLADOS:**
- Usar mediana (valor central, resistente a outliers)
- Usar promedio simple (media aritmética)
- Usar promedio ponderado (dar más peso a ciertas publicaciones)
- Usar moda (valor más frecuente)
- Usar percentil específico (P25, P50, P75, P90)
- Usar precio mínimo o máximo de la muestra
- Combinar métodos (70% mediana + 30% promedio)
- Excluir extremos antes de calcular
- Ponderar por antigüedad de publicación (más recientes pesan más)
- Ponderar por verificación del vendedor
- Ponderar por similitud con el vehículo a valuar
- Ponderar por cantidad de fotos/descripción
- Usar rango de precios (mínimo-máximo sugerido)

**PALABRAS CLAVE:** mediana, promedio, media, moda, percentil, valor central, método, calcular, computar, precio de referencia, valor de mercado, valuación, tasación, ponderado, peso, combinar, excluir extremos

**ESQUEMA JSON:**
```json
{{
  "metodo": "mediana|promedio|promedio_ponderado|moda|percentil|minimo|maximo|combinado",
  "percentil": 50,
  "excluir_extremos": true,
  "cantidad_excluir": 2,
  "combinacion": [
    {{"metodo": "mediana", "peso": 0.7}},
    {{"metodo": "promedio", "peso": 0.3}}
  ],
  "ponderaciones": {{
    "antiguedad_publicacion": {{"peso": 1.5, "dias_max": 30}},
    "verificacion_vendedor": {{"peso": 2.0, "solo_verificados": false}},
    "similitud_km": {{"peso": 1.2, "tolerancia": 10000}},
    "cantidad_fotos": {{"peso": 1.1, "minimo": 5}},
    "tipo_vendedor": {{"concesionaria": 1.3, "particular": 1.0}}
  }},
  "calcular_rango": true,
  "rango_porcentaje": 10
}}
```

═══════════════════════════════════════════════════════════════════════════════
## REGLAS DE EXTRACCIÓN - MUY IMPORTANTE
═══════════════════════════════════════════════════════════════════════════════

⚠️ DEBES CAPTURAR **ABSOLUTAMENTE TODOS** LOS DETALLES DE LA DESCRIPCIÓN:
- Marcas de autos mencionadas (Toyota, Renault, Chevrolet, Ford, Volkswagen, Fiat, Honda, etc.)
- Modelos específicos (Corolla, Clio, Cruze, Focus, Gol, Cronos, Civic, etc.)
- Versiones o variantes (SE, XLE, Titanium, Highline, etc.)
- Porcentajes o valores numéricos exactos
- Montos en pesos ($) o dólares (USD)
- Fechas, meses, períodos temporales (enero, febrero, Q1, trimestre, primer semestre, etc.)
- Años específicos (2020, 2021, 2022, etc.)
- Rangos de kilometraje (±10000 km, menos de 50000 km, etc.)
- Rangos de años (±2 años, 2018 en adelante, etc.)
- Condiciones específicas mencionadas (único dueño, service oficial, etc.)
- Motivos o razones explicadas (por alta demanda, por baja rotación, etc.)
- Ubicaciones geográficas (Buenos Aires, Córdoba, CABA, etc.)
- Tipos de vendedor (concesionaria, particular, agencia)
- Cualquier otro detalle relevante mencionado

NUNCA omitas información. Si el usuario menciona "enero", debe aparecer en el JSON.
Si menciona "Renault", debe aparecer. Si menciona "15%", debe aparecer exactamente.
Si menciona "$50000", debe ser ajuste_fijo con monto 50000.
Si menciona "50000 pesos", debe ser ajuste_fijo con monto 50000.

═══════════════════════════════════════════════════════════════════════════════
## EJEMPLOS DE EXTRACCIÓN EXHAUSTIVA
═══════════════════════════════════════════════════════════════════════════════

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

ENTRADA: "Restar 500 dólares a los Toyota Corolla 2020 importados"
```json
{{
  "tipo_detectado": "ajuste_calculo",
  "es_valido": true,
  "parametros": {{
    "tipo": "ajuste_fijo",
    "monto": 500,
    "moneda": "USD",
    "operacion": "decrementar",
    "condicion_marca": "Toyota",
    "condicion_modelo": "Corolla",
    "condicion_año": 2020,
    "motivo": "importados"
  }}
}}
```

ENTRADA: "Aplicar margen de ganancia del 12% con mínimo de 100000 pesos"
```json
{{
  "tipo_detectado": "ajuste_calculo",
  "es_valido": true,
  "parametros": {{
    "tipo": "margen_ganancia",
    "porcentaje": 12,
    "minimo_pesos": 100000
  }}
}}
```

ENTRADA: "Consultar precios en Kavak, MercadoLibre y Autocosmos priorizando Kavak"
```json
{{
  "tipo_detectado": "fuente",
  "es_valido": true,
  "parametros": {{
    "fuentes": [
      {{"url": "kavak.com.ar", "nombre": "Kavak", "prioridad": 1}},
      {{"url": "mercadolibre.com.ar", "nombre": "MercadoLibre", "prioridad": 2}},
      {{"url": "autocosmos.com.ar", "nombre": "Autocosmos", "prioridad": 3}}
    ]
  }}
}}
```

ENTRADA: "Eliminar las 5 publicaciones más baratas y las 3 más caras porque distorsionan"
```json
{{
  "tipo_detectado": "depuracion",
  "es_valido": true,
  "parametros": {{
    "accion": "eliminar_outliers",
    "extremo": "ambos",
    "cantidad_inferior": 5,
    "cantidad_superior": 3,
    "motivo": "distorsionan"
  }}
}}
```

ENTRADA: "Eliminar publicaciones con más de 45 días de antigüedad y sin fotos"
```json
{{
  "tipo_detectado": "depuracion",
  "es_valido": true,
  "parametros": {{
    "accion": "eliminar_por_criterio",
    "criterios": [
      {{"tipo": "eliminar_antiguos", "dias_maximos": 45}},
      {{"tipo": "eliminar_sin_fotos"}}
    ]
  }}
}}
```

ENTRADA: "Filtrar Toyota y Honda, modelos 2019 a 2023, menos de 80000 km, solo automáticos de concesionarias"
```json
{{
  "tipo_detectado": "filtro_busqueda",
  "es_valido": true,
  "parametros": {{
    "filtros": [
      {{"campo": "marca", "operador": "en_lista", "valor": ["Toyota", "Honda"]}},
      {{"campo": "año", "operador": "entre", "valor": [2019, 2023]}},
      {{"campo": "kilometraje", "operador": "menor", "valor": 80000}},
      {{"campo": "transmision", "operador": "igual", "valor": "automatica"}},
      {{"campo": "tipo_vendedor", "operador": "igual", "valor": "concesionaria"}}
    ]
  }}
}}
```

ENTRADA: "Tomar máximo 30 publicaciones, priorizando las más recientes de vendedores verificados"
```json
{{
  "tipo_detectado": "muestreo",
  "es_valido": true,
  "parametros": {{
    "metodo": "primeros_por_fecha",
    "cantidad": 30,
    "priorizar_verificados": true
  }}
}}
```

ENTRADA: "Si hay menos de 8 publicaciones de Ford Focus, ampliar a ±4 años y ±25000 km y agregar Ford Fiesta"
```json
{{
  "tipo_detectado": "punto_control",
  "es_valido": true,
  "parametros": {{
    "condicion_tipo": "cantidad_minima",
    "umbral_minimo": 8,
    "condicion_marca": "Ford",
    "condicion_modelo": "Focus",
    "accion": "ampliar_busqueda",
    "nuevos_parametros": {{
      "año_rango": [-4, 4],
      "km_rango": [-25000, 25000],
      "modelos_adicionales": ["Fiesta"]
    }}
  }}
}}
```

ENTRADA: "Usar 70% mediana y 30% promedio, excluyendo los 2 valores más extremos de cada lado"
```json
{{
  "tipo_detectado": "metodo_valuacion",
  "es_valido": true,
  "parametros": {{
    "metodo": "combinado",
    "combinacion": [
      {{"metodo": "mediana", "peso": 0.7}},
      {{"metodo": "promedio", "peso": 0.3}}
    ],
    "excluir_extremos": true,
    "cantidad_excluir": 2
  }}
}}
```

ENTRADA: "Usar percentil 75 para autos de alta gama y percentil 50 para el resto"
```json
{{
  "tipo_detectado": "metodo_valuacion",
  "es_valido": true,
  "parametros": {{
    "metodo": "percentil",
    "percentil": 75,
    "condicion": "alta_gama",
    "percentil_alternativo": 50,
    "motivo": "diferenciar alta gama del resto"
  }}
}}
```

---------------------------------------------------------
SOLICITUD ACTUAL:
"{descripcion}"

RECUERDA: 
1. Identifica correctamente el TIPO de regla según las definiciones de negocio
2. Extrae ABSOLUTAMENTE TODOS los detalles mencionados
3. No omitas fechas, marcas, modelos, porcentajes, montos, condiciones ni ningún otro elemento
4. Distingue correctamente entre ajuste_porcentual (%) y ajuste_fijo ($, pesos, monto)
5. Captura rangos, listas y condiciones múltiples cuando se mencionen

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


# Orden según README: 1.Fuente, 2.Filtro, 3.Ajuste, 4.Depuración, 5.Muestreo, 6.Control, 7.Método
TIPO_REGLA_LABELS = {
    "fuente": "📍 Fuente de Datos",
    "filtro_busqueda": "🔍 Filtro de Búsqueda",
    "ajuste_calculo": "💰 Ajuste de Cálculo",
    "depuracion": "🧹 Depuración",
    "muestreo": "📊 Muestreo",
    "punto_control": "⚠️ Punto de Control",
    "metodo_valuacion": "📈 Método de Valuación"
}

# Descripciones completas para mostrar al usuario
TIPO_REGLA_DESCRIPCIONES = {
    "fuente": "Portales o sitios de internet de consulta sobre datos de autos publicados (Kavak, MercadoLibre, etc.)",
    "filtro_busqueda": "Parámetros de búsqueda coherentes con el auto a publicar: marca, modelo, km, transmisión, etc.",
    "ajuste_calculo": "Definir el precio de venta final aplicando puntos de decisión del vendedor (+%, -$, inflación, margen)",
    "depuracion": "Eliminar publicaciones que generan ruido o desvío en el cálculo del precio de referencia",
    "muestreo": "Determinar la muestra de publicaciones de los sitios de consulta",
    "punto_control": "Condiciones para flujos condicionales (ej: si hay menos de 5 publicaciones, ampliar búsqueda)",
    "metodo_valuacion": "Método para calcular el precio de referencia del mercado (mediana, promedio, etc.)"
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
            "gemini-exp-1206",
            "gemini-2.0-flash-thinking-exp",
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
        pagina = st.radio("Menú", ["🚗 Valuar Vehículo", "📋 Reglas Activas", "🔧 Nueva Regla", "📜 Auditoría", "📊 Historial Valuaciones"], label_visibility="collapsed")


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

    # 1. INPUTS PRIMARIOS (sin Orden - se define después de generar JSON)
    col1, col2 = st.columns([3, 1])
    with col1:
        codigo = st.text_input("Código *", placeholder="Ej: AJUSTE_RENAULT_ENERO")
    with col2:
        pass  # Espacio reservado
    
    nombre = st.text_input("Nombre *", placeholder="Ej: Aumento Renault Enero")

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

    # 5. SELECTOR DE ORDEN VISUAL (solo si hay JSON generado)
    orden = 10  # valor por defecto
    
    if st.session_state.json_generado:
        st.markdown("---")
        st.subheader(f"📊 Ordenamiento de Reglas: {TIPO_REGLA_LABELS.get(tipo, tipo)}")
        
        # Obtener reglas existentes del mismo tipo
        todas_reglas = api_get("/reglas") or []
        reglas_mismo_tipo = [r for r in todas_reglas if r.get('tipo') == tipo]
        reglas_mismo_tipo = sorted(reglas_mismo_tipo, key=lambda x: x.get('orden', 0))
        
        if reglas_mismo_tipo:
            st.markdown("**Reglas existentes en esta categoría:**")
            
            # Crear opciones de posición
            posiciones = []
            posiciones.append({"orden": 0, "label": "🔝 Al inicio (antes de todas)", "pos": "inicio"})
            
            for i, regla in enumerate(reglas_mismo_tipo):
                orden_actual = regla.get('orden', 0)
                posiciones.append({
                    "orden": orden_actual,
                    "label": f"📍 Orden {orden_actual}: {regla.get('nombre', 'Sin nombre')}",
                    "pos": "existente",
                    "regla": regla
                })
                # Opción para insertar después de esta regla
                orden_siguiente = orden_actual + 1
                if i < len(reglas_mismo_tipo) - 1:
                    orden_siguiente = (orden_actual + reglas_mismo_tipo[i+1].get('orden', orden_actual + 2)) // 2
                posiciones.append({
                    "orden": orden_siguiente,
                    "label": f"   ↳ Insertar aquí (orden {orden_siguiente})",
                    "pos": "insertar",
                    "orden_sugerido": orden_siguiente
                })
            
            # Mostrar tabla visual
            st.markdown("---")
            col_tabla, col_nueva = st.columns([2, 1])
            
            with col_tabla:
                # Tabla de reglas existentes
                tabla_data = []
                for regla in reglas_mismo_tipo:
                    tabla_data.append({
                        "Orden": regla.get('orden', 0),
                        "Código": regla.get('codigo', ''),
                        "Nombre": regla.get('nombre', ''),
                        "Activo": "✅" if regla.get('activo', True) else "❌"
                    })
                
                if tabla_data:
                    df_reglas = pd.DataFrame(tabla_data)
                    st.dataframe(df_reglas, use_container_width=True, hide_index=True)
            
            with col_nueva:
                st.markdown("**🆕 Nueva regla:**")
                st.markdown(f"**{nombre or 'Sin nombre'}**")
                st.caption(f"Código: {codigo or 'Sin código'}")
                
                # Calcular opciones de orden
                ordenes_existentes = [r.get('orden', 0) for r in reglas_mismo_tipo]
                orden_min = min(ordenes_existentes) if ordenes_existentes else 0
                orden_max = max(ordenes_existentes) if ordenes_existentes else 0
                
                opciones_orden = [
                    (orden_min - 10 if orden_min > 10 else 1, f"🔝 Al inicio (orden {orden_min - 10 if orden_min > 10 else 1})"),
                ]
                
                for i, regla in enumerate(reglas_mismo_tipo):
                    ord_actual = regla.get('orden', 0)
                    if i < len(reglas_mismo_tipo) - 1:
                        ord_siguiente = reglas_mismo_tipo[i+1].get('orden', ord_actual + 10)
                        orden_medio = (ord_actual + ord_siguiente) // 2
                        if orden_medio != ord_actual:
                            opciones_orden.append((orden_medio, f"↳ Después de '{regla.get('nombre', '')}' (orden {orden_medio})"))
                    else:
                        opciones_orden.append((ord_actual + 10, f"↳ Después de '{regla.get('nombre', '')}' (orden {ord_actual + 10})"))
                
                # Selector de posición
                opcion_seleccionada = st.radio(
                    "Posición de la nueva regla:",
                    options=range(len(opciones_orden)),
                    format_func=lambda i: opciones_orden[i][1],
                    key="selector_orden"
                )
                
                orden = opciones_orden[opcion_seleccionada][0]
                
                st.success(f"**Orden seleccionado: {orden}**")
        
        else:
            st.info("No hay reglas existentes de este tipo. Esta será la primera.")
            orden = st.number_input("Orden", value=10, min_value=1, key="orden_primera_regla")
        
        # Previsualización del nuevo ordenamiento
        if reglas_mismo_tipo:
            st.markdown("---")
            st.markdown("**📋 Previsualización del nuevo ordenamiento:**")
            
            # Crear lista con la nueva regla incluida
            preview_data = []
            nueva_insertada = False
            
            for regla in reglas_mismo_tipo:
                ord_regla = regla.get('orden', 0)
                
                # Insertar nueva regla en su posición
                if not nueva_insertada and orden <= ord_regla:
                    preview_data.append({
                        "Orden": orden,
                        "Código": codigo.upper().replace(" ", "_") if codigo else "NUEVO",
                        "Nombre": f"🆕 {nombre or 'Nueva Regla'}",
                        "Estado": "🆕 NUEVA"
                    })
                    nueva_insertada = True
                
                preview_data.append({
                    "Orden": ord_regla,
                    "Código": regla.get('codigo', ''),
                    "Nombre": regla.get('nombre', ''),
                    "Estado": "✅ Existente"
                })
            
            # Si no se insertó, va al final
            if not nueva_insertada:
                preview_data.append({
                    "Orden": orden,
                    "Código": codigo.upper().replace(" ", "_") if codigo else "NUEVO",
                    "Nombre": f"🆕 {nombre or 'Nueva Regla'}",
                    "Estado": "🆕 NUEVA"
                })
            
            df_preview = pd.DataFrame(preview_data)
            st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    else:
        # Si no hay JSON generado, mostrar input simple de orden
        orden = 10

    # 6. GUARDAR
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
        
        # Ordenar por el orden definido en CLAVES_TIPOS (según README)
        for tipo in CLAVES_TIPOS:
            if tipo in reglas_por_tipo:
                lista = reglas_por_tipo[tipo]
                # Ordenar reglas dentro del tipo por campo 'orden'
                lista = sorted(lista, key=lambda x: x.get('orden', 0))
                
                st.subheader(TIPO_REGLA_LABELS.get(tipo, tipo))
                st.caption(TIPO_REGLA_DESCRIPCIONES.get(tipo, ''))
                
                for r in lista:
                    orden_num = r.get('orden', 0)
                    with st.expander(f"{'✅' if r.get('activo', True) else '❌'} [{orden_num}] {r['nombre']} - `{r.get('codigo', '')}`"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            if r.get('descripcion'):
                                st.caption(f"📝 {r['descripcion']}")
                            st.json(r['parametros'])
                        
                        with col2:
                            st.caption(f"Orden: {orden_num}")
                            st.caption(f"Versión: {r.get('version', 1)}")
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
# VALUAR VEHÍCULO
# ============================================

elif pagina == "🚗 Valuar Vehículo":
    st.title("🚗 Valuar Vehículo")
    st.caption("Ingrese los datos del vehículo para obtener una valuación basada en las reglas configuradas.")
    
    # Inicializar estado de valuación
    if "valuacion_resultado" not in st.session_state:
        st.session_state.valuacion_resultado = None
    if "valuacion_en_proceso" not in st.session_state:
        st.session_state.valuacion_en_proceso = False
    
    # Formulario de vehículo
    st.subheader("📝 Datos del Vehículo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        marca = st.text_input("Marca *", placeholder="Ej: Toyota, Renault, Chevrolet")
        año = st.number_input("Año *", min_value=1990, max_value=2026, value=2020)
        version = st.text_input("Versión", placeholder="Ej: SE, XLE, Titanium (opcional)")
        combustible = st.selectbox("Combustible", ["", "Nafta", "Diesel", "GNC", "Híbrido", "Eléctrico"])
    
    with col2:
        modelo = st.text_input("Modelo *", placeholder="Ej: Corolla, Clio, Cruze")
        kilometraje = st.number_input("Kilometraje (km) *", min_value=0, max_value=500000, value=50000, step=1000)
        transmision = st.selectbox("Transmisión", ["", "Automática", "Manual", "CVT"])
    
    st.markdown("---")
    
    # Configuración de IA
    st.subheader("🤖 Proveedor de Valuación")
    
    col_ia1, col_ia2 = st.columns(2)
    
    with col_ia1:
        proveedor_valuacion = st.selectbox(
            "Motor de Valuación",
            ["mock", "ollama", "groq", "gemini"],
            format_func=lambda x: {
                "mock": "🧪 Demo (Sin IA real)",
                "ollama": "🦙 Ollama (Local)",
                "groq": "⚡ Groq (Cloud)",
                "gemini": "🔷 Google Gemini (Cloud)"
            }.get(x, x)
        )
    
    with col_ia2:
        if proveedor_valuacion == "ollama":
            modelo_valuacion = st.text_input("Modelo Ollama", value="llama3.2")
            api_key_valuacion = None
        elif proveedor_valuacion == "groq":
            modelo_valuacion = st.selectbox("Modelo Groq", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"])
            api_key_valuacion = st.text_input("API Key Groq", type="password")
        elif proveedor_valuacion == "gemini":
            modelo_valuacion = st.selectbox(
                "Modelo Gemini", 
                [
                    "gemini-2.0-flash",
                    "gemini-2.0-flash-exp",
                    "gemini-1.5-flash",
                    "gemini-1.5-pro",
                    "gemini-exp-1206",
                    "gemini-2.0-flash-thinking-exp",
                    "gemini-3-flash-preview",
                    "gemini-3-pro-preview"
                ]
            )
            api_key_valuacion = st.text_input("API Key Gemini", type="password")
        else:
            modelo_valuacion = None
            api_key_valuacion = None
            st.info("Modo demo: genera valores de ejemplo sin consultar IA real")
    
    st.markdown("---")
    
    # Resumen de reglas activas
    with st.expander("📋 Ver reglas activas que se aplicarán"):
        reglas = api_get("/reglas") or []
        if reglas:
            reglas_por_tipo = {}
            for r in reglas:
                tipo = r.get('tipo', 'otro')
                if tipo not in reglas_por_tipo:
                    reglas_por_tipo[tipo] = []
                reglas_por_tipo[tipo].append(r)
            
            # Ordenar según CLAVES_TIPOS (orden del README)
            for tipo in CLAVES_TIPOS:
                if tipo in reglas_por_tipo:
                    lista = sorted(reglas_por_tipo[tipo], key=lambda x: x.get('orden', 0))
                    st.markdown(f"**{TIPO_REGLA_LABELS.get(tipo, tipo)}** ({len(lista)})")
                    for r in lista:
                        st.caption(f"  • [{r.get('orden', 0)}] {r.get('nombre', 'Sin nombre')}")
        else:
            st.warning("No hay reglas configuradas. La valuación usará valores por defecto.")
    
    # Botón de valuación
    st.markdown("---")
    
    puede_valuar = marca and modelo and año and kilometraje
    
    if proveedor_valuacion in ["groq", "gemini"] and not api_key_valuacion:
        st.warning(f"⚠️ Ingrese la API Key de {proveedor_valuacion.title()} para continuar")
        puede_valuar = False
    
    if st.button("🔍 Ejecutar Valuación", type="primary", use_container_width=True, disabled=not puede_valuar):
        st.session_state.valuacion_en_proceso = True
        
        with st.spinner("⏳ Ejecutando valuación... Esto puede tomar unos segundos."):
            payload = {
                "marca": marca,
                "modelo": modelo,
                "año": año,
                "kilometraje": kilometraje,
                "version": version if version else None,
                "transmision": transmision if transmision else None,
                "combustible": combustible if combustible else None,
                "proveedor_ia": proveedor_valuacion,
                "modelo_ia": modelo_valuacion,
                "api_key_ia": api_key_valuacion
            }
            
            resultado = api_post("/valuaciones", payload, {"usuario_id": st.session_state.usuario_id})
            
            if resultado:
                st.session_state.valuacion_resultado = resultado
                st.session_state.valuacion_en_proceso = False
                st.rerun()
            else:
                st.error("❌ Error al ejecutar la valuación")
                st.session_state.valuacion_en_proceso = False
    
    # Mostrar resultado
    if st.session_state.valuacion_resultado:
        resultado = st.session_state.valuacion_resultado
        
        st.markdown("---")
        st.subheader("📊 Resultado de la Valuación")
        
        # Precio principal
        col_precio1, col_precio2, col_precio3 = st.columns(3)
        
        with col_precio1:
            precio_min = resultado.get("precio_minimo")
            if precio_min:
                st.metric("💰 Precio Mínimo", f"${precio_min:,.0f}")
        
        with col_precio2:
            precio_sug = resultado.get("precio_sugerido")
            if precio_sug:
                st.metric("⭐ Precio Sugerido", f"${precio_sug:,.0f}")
            else:
                st.warning("No se pudo calcular precio")
        
        with col_precio3:
            precio_max = resultado.get("precio_maximo")
            if precio_max:
                st.metric("💎 Precio Máximo", f"${precio_max:,.0f}")
        
        # Confianza y métricas
        col_met1, col_met2, col_met3 = st.columns(3)
        
        with col_met1:
            confianza = resultado.get("confianza", "N/A")
            color = {"ALTA": "🟢", "MEDIA": "🟡", "BAJA": "🔴"}.get(confianza, "⚪")
            st.metric("Confianza", f"{color} {confianza}")
        
        with col_met2:
            duracion = resultado.get("duracion_segundos")
            if duracion:
                st.metric("⏱️ Duración", f"{duracion:.1f}s")
        
        with col_met3:
            analisis = resultado.get("analisis", {})
            fuentes = analisis.get("fuentes_consultadas", 0)
            st.metric("🌐 Fuentes", fuentes)
        
        # Alertas
        alertas = resultado.get("alertas", [])
        if alertas:
            st.markdown("### ⚠️ Alertas")
            for alerta in alertas:
                st.warning(alerta)
        
        # Análisis detallado
        with st.expander("📈 Análisis de Mercado"):
            analisis = resultado.get("analisis", {})
            if analisis:
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.metric("Resultados iniciales", analisis.get("resultados_iniciales", 0))
                    st.metric("Precio mercado mín", f"${analisis.get('precio_mercado_min', 0):,.0f}" if analisis.get('precio_mercado_min') else "N/A")
                with col_a2:
                    st.metric("Resultados tras filtrado", analisis.get("resultados_tras_depuracion", analisis.get("resultados_tras_filtrado", 0)))
                    st.metric("Precio mercado máx", f"${analisis.get('precio_mercado_max', 0):,.0f}" if analisis.get('precio_mercado_max') else "N/A")
        
        # Reglas aplicadas
        with st.expander("📋 Reglas Aplicadas"):
            reglas_aplicadas = resultado.get("reglas_aplicadas", [])
            if reglas_aplicadas:
                for regla in reglas_aplicadas:
                    st.markdown(f"• **{regla.get('codigo', 'N/A')}**: {regla.get('resultado', '')}")
            else:
                st.info("No se registraron reglas aplicadas")
        
        # Publicaciones analizadas
        with st.expander("🔗 Publicaciones Analizadas"):
            publicaciones = resultado.get("publicaciones", [])
            if publicaciones:
                df_pub = pd.DataFrame(publicaciones)
                if 'precio' in df_pub.columns:
                    df_pub['precio'] = df_pub['precio'].apply(lambda x: f"${x:,.0f}" if x else "N/A")
                st.dataframe(df_pub, use_container_width=True)
            else:
                st.info("No hay publicaciones registradas")
        
        # Reporte completo
        with st.expander("📄 Reporte Completo"):
            reporte = resultado.get("reporte", "")
            if reporte:
                st.markdown(reporte)
            else:
                st.info("No hay reporte disponible")
        
        # Botón para nueva valuación
        if st.button("🔄 Nueva Valuación"):
            st.session_state.valuacion_resultado = None
            st.rerun()


# ============================================
# HISTORIAL DE VALUACIONES
# ============================================

elif pagina == "📊 Historial Valuaciones":
    st.title("📊 Historial de Valuaciones")
    
    valuaciones = api_get("/valuaciones")
    
    if valuaciones:
        st.caption(f"Total: {len(valuaciones)} valuaciones")
        
        for val in valuaciones:
            vehiculo = val.get("vehiculo", {})
            precio = val.get("precio_sugerido")
            confianza = val.get("confianza", "N/A")
            fecha = val.get("fecha", "")
            
            titulo = f"{vehiculo.get('marca', '?')} {vehiculo.get('modelo', '?')} {vehiculo.get('año', '?')}"
            precio_texto = f"${precio:,.0f}" if precio else "Sin precio"
            
            with st.expander(f"🚗 {titulo} - {precio_texto} ({confianza})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Vehículo:** {titulo}")
                    st.markdown(f"**Precio Sugerido:** {precio_texto}")
                    st.markdown(f"**Confianza:** {confianza}")
                
                with col2:
                    st.markdown(f"**Fecha:** {fecha[:16] if fecha else 'N/A'}")
                    duracion = val.get("duracion_segundos")
                    st.markdown(f"**Duración:** {duracion:.1f}s" if duracion else "**Duración:** N/A")
                    st.markdown(f"**ID:** `{val.get('id', '')[:8]}...`")
                
                if st.button("Ver detalle completo", key=f"det_{val.get('id')}"):
                    detalle = api_get(f"/valuaciones/{val.get('id')}")
                    if detalle:
                        st.json(detalle)
    else:
        st.info("No hay valuaciones registradas. Ve a 'Valuar Vehículo' para crear una.")


# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.caption(f"Sistema de Valuación v2.4 | Usuario: {st.session_state.usuario_nombre} | {datetime.now().strftime('%H:%M')}")