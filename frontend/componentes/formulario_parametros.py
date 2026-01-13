# frontend/componentes/formulario_parametros.py
"""
Formularios dinámicos para cada tipo de regla.
Genera el JSON de parámetros de forma intuitiva.
"""

import streamlit as st
import json


def formulario_fuente() -> dict:
    """Formulario para reglas de tipo FUENTE"""
    st.markdown("#### Configuración de Fuente de Datos")
    
    col1, col2 = st.columns(2)
    with col1:
        url = st.text_input("URL del sitio", placeholder="kavak.com/ar")
        prioridad = st.number_input("Prioridad (1=más importante)", min_value=1, max_value=10, value=1)
    with col2:
        nombre_fuente = st.text_input("Nombre de la fuente", placeholder="Kavak Argentina")
        verificado = st.checkbox("Es fuente verificada/confiable", value=True)
    
    return {
        "url": url,
        "nombre": nombre_fuente,
        "prioridad": prioridad,
        "verificado": verificado
    }


def formulario_filtro_busqueda() -> dict:
    """Formulario para reglas de tipo FILTRO_BUSQUEDA"""
    st.markdown("#### Configuración de Filtro de Búsqueda")
    
    col1, col2 = st.columns(2)
    with col1:
        campo = st.selectbox(
            "Campo a filtrar",
            ["marca", "modelo", "año", "kilometraje", "version", "transmision", "combustible", "precio"]
        )
        operador = st.selectbox(
            "Operador",
            ["igual", "diferente", "mayor", "menor", "mayor_igual", "menor_igual", "entre", "contiene"]
        )
    
    with col2:
        relativo = st.checkbox(
            "Valor relativo al vehículo",
            value=True,
            help="Si está activo, el valor se suma/resta al valor del vehículo a valuar"
        )
        
        if operador == "entre":
            st.markdown("**Rango de valores:**")
            val_min = st.number_input("Valor mínimo (±)", value=-1)
            val_max = st.number_input("Valor máximo (±)", value=1)
            valor = [val_min, val_max]
        elif operador in ["igual", "diferente", "contiene"]:
            valor = st.text_input("Valor", placeholder="Texto o valor exacto")
        else:
            valor = st.number_input("Valor", value=0)
    
    return {
        "campo": campo,
        "operador": operador,
        "valor": valor,
        "relativo": relativo
    }


def formulario_depuracion() -> dict:
    """Formulario para reglas de tipo DEPURACION"""
    st.markdown("#### Configuración de Depuración de Resultados")
    
    accion = st.selectbox(
        "Tipo de depuración",
        [
            "eliminar_outliers_precio",
            "eliminar_no_verificados",
            "eliminar_antiguos",
            "eliminar_sin_fotos",
            "eliminar_duplicados",
            "eliminar_por_criterio"
        ],
        format_func=lambda x: {
            "eliminar_outliers_precio": "🔢 Eliminar outliers por precio",
            "eliminar_no_verificados": "❌ Eliminar usuarios no verificados",
            "eliminar_antiguos": "📅 Eliminar publicaciones antiguas",
            "eliminar_sin_fotos": "📷 Eliminar sin fotos",
            "eliminar_duplicados": "🔄 Eliminar duplicados",
            "eliminar_por_criterio": "🎯 Eliminar por criterio personalizado"
        }.get(x, x)
    )
    
    params = {"accion": accion}
    
    if accion == "eliminar_outliers_precio":
        col1, col2 = st.columns(2)
        with col1:
            params["cantidad"] = st.number_input("Cantidad a eliminar", min_value=1, max_value=20, value=5)
        with col2:
            params["extremo"] = st.selectbox("Extremo", ["inferior", "superior", "ambos"])
    
    elif accion == "eliminar_antiguos":
        params["dias_maximos"] = st.number_input("Días máximos de antigüedad", min_value=1, max_value=365, value=60)
    
    elif accion == "eliminar_por_criterio":
        params["campo"] = st.text_input("Campo a evaluar", placeholder="precio, km, etc")
        params["condicion"] = st.selectbox("Condición", ["menor_que", "mayor_que", "igual_a", "contiene"])
        params["valor"] = st.text_input("Valor de comparación")
    
    return params


def formulario_muestreo() -> dict:
    """Formulario para reglas de tipo MUESTREO"""
    st.markdown("#### Configuración de Muestreo")
    
    metodo = st.selectbox(
        "Método de selección",
        ["aleatorio", "primeros_por_precio_asc", "primeros_por_precio_desc", "todos"],
        format_func=lambda x: {
            "aleatorio": "🎲 Aleatorio",
            "primeros_por_precio_asc": "📈 Primeros N ordenados por precio (menor a mayor)",
            "primeros_por_precio_desc": "📉 Primeros N ordenados por precio (mayor a menor)",
            "todos": "📋 Usar todos los resultados"
        }.get(x, x)
    )
    
    params = {"metodo": metodo}
    
    if metodo != "todos":
        params["cantidad"] = st.number_input("Cantidad de resultados a tomar", min_value=1, max_value=100, value=20)
    
    return params


def formulario_punto_control() -> dict:
    """Formulario para reglas de tipo PUNTO_CONTROL"""
    st.markdown("#### Configuración de Punto de Control")
    
    umbral = st.number_input(
        "Umbral mínimo de resultados",
        min_value=1,
        max_value=50,
        value=5,
        help="Si hay menos resultados que este número, se ejecuta la acción"
    )
    
    accion = st.selectbox(
        "Acción a ejecutar",
        ["ampliar_busqueda", "usar_fuentes_secundarias", "alertar", "abortar"],
        format_func=lambda x: {
            "ampliar_busqueda": "🔍 Ampliar parámetros de búsqueda",
            "usar_fuentes_secundarias": "📍 Incluir fuentes secundarias",
            "alertar": "⚠️ Solo alertar (continuar con lo que hay)",
            "abortar": "🛑 Abortar valuación"
        }.get(x, x)
    )
    
    params = {
        "umbral_minimo": umbral,
        "accion": accion
    }
    
    if accion == "ampliar_busqueda":
        st.markdown("**Nuevos parámetros de búsqueda:**")
        col1, col2 = st.columns(2)
        with col1:
            nuevo_rango_año = st.number_input("Nuevo rango de año (±)", min_value=1, max_value=5, value=2)
        with col2:
            nuevo_rango_km = st.number_input("Nuevo rango de km (±)", min_value=5000, max_value=50000, value=15000, step=5000)
        
        params["nuevos_parametros"] = {
            "año": [-nuevo_rango_año, nuevo_rango_año],
            "km": [-nuevo_rango_km, nuevo_rango_km]
        }
    
    return params


def formulario_metodo_valuacion() -> dict:
    """Formulario para reglas de tipo METODO_VALUACION"""
    st.markdown("#### Configuración de Método de Valuación")
    
    metodo = st.selectbox(
        "Método estadístico",
        ["mediana", "promedio", "promedio_ponderado", "moda", "percentil"],
        format_func=lambda x: {
            "mediana": "📊 Mediana (valor central - recomendado)",
            "promedio": "📈 Promedio simple",
            "promedio_ponderado": "⚖️ Promedio ponderado",
            "moda": "🔢 Moda (valor más frecuente)",
            "percentil": "📉 Percentil específico"
        }.get(x, x)
    )
    
    params = {"metodo": metodo}
    
    if metodo == "promedio_ponderado":
        st.markdown("**Configurar pesos:**")
        params["pesos"] = {
            "antiguedad_publicacion": st.slider("Peso por antigüedad (más reciente = más peso)", 0.0, 2.0, 1.0),
            "verificacion_vendedor": st.slider("Peso por vendedor verificado", 0.0, 2.0, 1.5),
            "similitud_km": st.slider("Peso por similitud de km", 0.0, 2.0, 1.0)
        }
    
    elif metodo == "percentil":
        params["percentil"] = st.slider("Percentil a usar", 1, 99, 50)
    
    params["peso_en_calculo_final"] = st.slider(
        "Peso de este método en el cálculo final",
        0.0, 2.0, 1.0,
        help="Si hay múltiples métodos, este peso determina su influencia"
    )
    
    return params


def formulario_ajuste_calculo() -> dict:
    """Formulario para reglas de tipo AJUSTE_CALCULO"""
    st.markdown("#### Configuración de Ajuste de Cálculo")
    
    tipo_ajuste = st.selectbox(
        "Tipo de ajuste",
        [
            "inflacion",
            "margen_ganancia",
            "ajuste_porcentual",
            "ajuste_fijo",
            "margen_historico",
            "margen_indexado",
            "ajuste_por_condicion"
        ],
        format_func=lambda x: {
            "inflacion": "📈 Ajuste por inflación",
            "margen_ganancia": "💰 Margen de ganancia fijo",
            "ajuste_porcentual": "🔢 Ajuste porcentual sobre base",
            "ajuste_fijo": "💵 Ajuste de monto fijo",
            "margen_historico": "📊 Margen basado en ventas históricas",
            "margen_indexado": "📉 Margen indexado (tendencia de mercado)",
            "ajuste_por_condicion": "🎯 Ajuste condicional"
        }.get(x, x)
    )
    
    params = {"tipo": tipo_ajuste}
    
    if tipo_ajuste == "inflacion":
        col1, col2 = st.columns(2)
        with col1:
            params["porcentaje"] = st.number_input("Tasa de inflación mensual (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
        with col2:
            params["periodo_dias"] = st.number_input("Período de proyección (días)", min_value=1, max_value=180, value=30)
    
    elif tipo_ajuste == "margen_ganancia":
        params["porcentaje"] = st.number_input("Porcentaje de margen (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5)
        params["aplicar_sobre"] = st.selectbox("Aplicar sobre", ["precio_compra", "precio_mercado", "mediana"])
    
    elif tipo_ajuste == "ajuste_porcentual":
        st.info("💡 Este ajuste permite incrementar o decrementar el precio base en un porcentaje")
        col1, col2 = st.columns(2)
        with col1:
            params["porcentaje"] = st.number_input("Porcentaje (%)", min_value=-50.0, max_value=100.0, value=15.0, step=0.5)
        with col2:
            params["base"] = st.selectbox(
                "Calcular sobre",
                ["promedio_mercado", "mediana_mercado", "precio_minimo", "precio_maximo"],
                format_func=lambda x: {
                    "promedio_mercado": "Promedio del mercado",
                    "mediana_mercado": "Mediana del mercado",
                    "precio_minimo": "Precio mínimo encontrado",
                    "precio_maximo": "Precio máximo encontrado"
                }.get(x, x)
            )
        params["operacion"] = "incrementar" if params["porcentaje"] >= 0 else "decrementar"
    
    elif tipo_ajuste == "ajuste_fijo":
        params["monto"] = st.number_input("Monto a ajustar ($)", value=0)
        params["operacion"] = st.selectbox("Operación", ["sumar", "restar"])
    
    elif tipo_ajuste == "margen_historico":
        params["periodo_dias"] = st.number_input("Período de análisis (días)", min_value=30, max_value=365, value=90)
        params["descripcion"] = "Calcula el margen promedio entre precio de venta y precio de mercado en ventas pasadas"
    
    elif tipo_ajuste == "margen_indexado":
        col1, col2 = st.columns(2)
        with col1:
            params["periodo_integracion"] = st.number_input("Período de integración (días)", min_value=15, max_value=90, value=45)
        with col2:
            params["factor_tendencia"] = st.selectbox(
                "Factor por tendencia",
                ["automatico", "subiendo", "estable", "bajando"],
                format_func=lambda x: {
                    "automatico": "🤖 Detectar automáticamente",
                    "subiendo": "📈 Mercado subiendo (+ajuste)",
                    "estable": "➡️ Mercado estable (sin ajuste)",
                    "bajando": "📉 Mercado bajando (-ajuste)"
                }.get(x, x)
            )
    
    elif tipo_ajuste == "ajuste_por_condicion":
        st.markdown("**Configurar condición:**")
        params["condicion_campo"] = st.selectbox("Si el campo", ["kilometraje", "año", "precio_mercado", "cantidad_resultados"])
        params["condicion_operador"] = st.selectbox("Es", ["mayor_que", "menor_que", "entre"])
        params["condicion_valor"] = st.text_input("Valor (usar coma para rangos)", placeholder="50000 o 30000,70000")
        params["entonces_porcentaje"] = st.number_input("Entonces ajustar (%)", value=0.0, step=0.5)
    
    return params


def mostrar_formulario_parametros(tipo_regla: str) -> dict:
    """
    Muestra el formulario correspondiente al tipo de regla
    y retorna el diccionario de parámetros.
    """
    formularios = {
        "fuente": formulario_fuente,
        "filtro_busqueda": formulario_filtro_busqueda,
        "depuracion": formulario_depuracion,
        "muestreo": formulario_muestreo,
        "punto_control": formulario_punto_control,
        "metodo_valuacion": formulario_metodo_valuacion,
        "ajuste_calculo": formulario_ajuste_calculo
    }
    
    if tipo_regla in formularios:
        return formularios[tipo_regla]()
    else:
        # Fallback a JSON manual
        st.warning("Tipo de regla no reconocido. Ingrese JSON manualmente.")
        json_str = st.text_area("Parámetros (JSON)", value="{}")
        try:
            return json.loads(json_str)
        except:
            return {}


def preview_json(params: dict):
    """Muestra una vista previa del JSON generado"""
    st.markdown("---")
    st.markdown("#### 📋 JSON Generado (Preview)")
    st.code(json.dumps(params, indent=2, ensure_ascii=False), language="json")
