# frontend/servicios/ia_gratuita.py
"""
Servicio de IA con múltiples proveedores gratuitos.
Soporta: Ollama (local), Groq, Google Gemini, OpenRouter
"""

import requests
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


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
**PALABRAS CLAVE:** aumentar, disminuir, precio, valor, porcentaje, %, margen, ganancia, inflación, precio de venta, precio final
**ESQUEMA JSON COMPLETO:**
```json
{{
  "tipo": "ajuste_porcentual|margen_ganancia|inflacion|ajuste_fijo|ajuste_temporal",
  "porcentaje": 15,
  "operacion": "incrementar|decrementar",
  "base": "promedio_mercado|mediana_mercado|precio_minimo|precio_maximo",
  "condicion_marca": "Renault (si aplica)",
  "condicion_modelo": "Corolla (si aplica)",
  "condicion_año": 2020,
  "periodo_vigencia": {{
    "tipo": "mes|trimestre|rango_fechas|permanente",
    "mes": "enero",
    "año": 2025
  }},
  "motivo": "razón del ajuste"
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
# CLASE BASE
# ============================================

class ProveedorIA(ABC):
    """Clase base para proveedores de IA"""
    
    @abstractmethod
    def generar(self, prompt: str) -> Optional[str]:
        pass
    
    def generar_json_regla(self, descripcion: str, tipo: str) -> Optional[Dict]:
        """Genera JSON de parámetros para una regla"""
        prompt = PROMPT_GENERADOR.format(tipo=tipo, descripcion=descripcion)
        
        respuesta = self.generar(prompt)
        if not respuesta:
            return None
        
        # Limpiar respuesta
        texto = respuesta.strip()
        if texto.startswith("```json"):
            texto = texto[7:]
        if texto.startswith("```"):
            texto = texto[3:]
        if texto.endswith("```"):
            texto = texto[:-3]
        
        try:
            return json.loads(texto.strip())
        except json.JSONDecodeError:
            # Intentar extraer JSON de la respuesta
            import re
            match = re.search(r'\{[^{}]*\}', texto)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return None


# ============================================
# OLLAMA (Local, 100% Gratis)
# ============================================

class OllamaProvider(ProveedorIA):
    """
    Ollama - Ejecuta modelos localmente
    Instalación: https://ollama.ai/download
    Modelos recomendados: llama3.2, phi3, mistral
    """
    
    def __init__(self, modelo: str = "llama3.2", url: str = "http://localhost:11434"):
        self.modelo = modelo
        self.url = url
    
    def generar(self, prompt: str) -> Optional[str]:
        try:
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Bajo para respuestas consistentes
                        "num_predict": 500
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"Error Ollama: {e}")
            return None
    
    @staticmethod
    def verificar_disponible(url: str = "http://localhost:11434") -> bool:
        """Verifica si Ollama está corriendo"""
        try:
            response = requests.get(f"{url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def listar_modelos(url: str = "http://localhost:11434") -> list:
        """Lista modelos disponibles en Ollama"""
        try:
            response = requests.get(f"{url}/api/tags", timeout=5)
            if response.status_code == 200:
                return [m["name"] for m in response.json().get("models", [])]
        except:
            pass
        return []


# ============================================
# GROQ (Gratis con límites generosos)
# ============================================

class GroqProvider(ProveedorIA):
    """
    Groq - API gratuita muy rápida
    Obtener API key: https://console.groq.com/keys
    Límites: 30 req/min, 14400 req/día gratis
    """
    
    def __init__(self, api_key: str, modelo: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.modelo = modelo
        # Modelos disponibles gratis:
        # - llama-3.1-8b-instant (rápido)
        # - llama-3.1-70b-versatile (mejor calidad)
        # - mixtral-8x7b-32768
        # - gemma2-9b-it
    
    def generar(self, prompt: str) -> Optional[str]:
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.modelo,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error Groq: {e}")
            return None


# ============================================
# GOOGLE GEMINI (Gratis con límites)
# ============================================

class GeminiProvider(ProveedorIA):
    """
    Google Gemini - API gratuita
    Obtener API key: https://aistudio.google.com/app/apikey
    Límites: 60 req/min gratis
    """
    
    def __init__(self, api_key: str, modelo: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.modelo = modelo
    
    def generar(self, prompt: str) -> Optional[str]:
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.modelo}:generateContent",
                params={"key": self.api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 500
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Error Gemini: {e}")
            return None


# ============================================
# OPENROUTER (Varios modelos, algunos gratis)
# ============================================

class OpenRouterProvider(ProveedorIA):
    """
    OpenRouter - Acceso a múltiples modelos
    Obtener API key: https://openrouter.ai/keys
    Modelos gratis: meta-llama/llama-3.2-3b-instruct:free
    """
    
    def __init__(self, api_key: str, modelo: str = "meta-llama/llama-3.2-3b-instruct:free"):
        self.api_key = api_key
        self.modelo = modelo
        # Modelos gratis:
        # - meta-llama/llama-3.2-3b-instruct:free
        # - microsoft/phi-3-mini-128k-instruct:free
        # - google/gemma-2-9b-it:free
    
    def generar(self, prompt: str) -> Optional[str]:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.modelo,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Error OpenRouter: {e}")
            return None


# ============================================
# HUGGING FACE (Gratis con límites)
# ============================================

class HuggingFaceProvider(ProveedorIA):
    """
    Hugging Face Inference API
    Obtener token: https://huggingface.co/settings/tokens
    Límites: Rate limited pero gratis
    """
    
    def __init__(self, api_token: str, modelo: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        self.api_token = api_token
        self.modelo = modelo
    
    def generar(self, prompt: str) -> Optional[str]:
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{self.modelo}",
                headers={"Authorization": f"Bearer {self.api_token}"},
                json={
                    "inputs": prompt,
                    "parameters": {
                        "temperature": 0.1,
                        "max_new_tokens": 500,
                        "return_full_text": False
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            return None
        except Exception as e:
            print(f"Error HuggingFace: {e}")
            return None


# ============================================
# FACTORY - Crear proveedor según configuración
# ============================================

def crear_proveedor(tipo: str, config: Dict[str, Any]) -> Optional[ProveedorIA]:
    """
    Crea un proveedor de IA según el tipo especificado.
    
    Args:
        tipo: "ollama", "groq", "gemini", "openrouter", "huggingface"
        config: Diccionario con la configuración necesaria
    
    Returns:
        Instancia del proveedor o None si hay error
    """
    proveedores = {
        "ollama": lambda c: OllamaProvider(
            modelo=c.get("modelo", "llama3.2"),
            url=c.get("url", "http://localhost:11434")
        ),
        "groq": lambda c: GroqProvider(
            api_key=c.get("api_key", ""),
            modelo=c.get("modelo", "llama-3.1-8b-instant")
        ),
        "gemini": lambda c: GeminiProvider(
            api_key=c.get("api_key", ""),
            modelo=c.get("modelo", "gemini-1.5-flash")
        ),
        "openrouter": lambda c: OpenRouterProvider(
            api_key=c.get("api_key", ""),
            modelo=c.get("modelo", "meta-llama/llama-3.2-3b-instruct:free")
        ),
        "huggingface": lambda c: HuggingFaceProvider(
            api_token=c.get("api_key", ""),
            modelo=c.get("modelo", "mistralai/Mistral-7B-Instruct-v0.2")
        )
    }
    
    if tipo not in proveedores:
        return None
    
    try:
        return proveedores[tipo](config)
    except Exception as e:
        print(f"Error creando proveedor {tipo}: {e}")
        return None


# ============================================
# EJEMPLO DE USO
# ============================================

if __name__ == "__main__":
    # Ejemplo con Ollama (local)
    if OllamaProvider.verificar_disponible():
        print("✅ Ollama disponible")
        modelos = OllamaProvider.listar_modelos()
        print(f"Modelos: {modelos}")
        
        ollama = OllamaProvider(modelo="llama3.2")
        resultado = ollama.generar_json_regla(
            descripcion="Ajustar un 20% el valor promedio encontrado en la web",
            tipo="ajuste_calculo"
        )
        print(f"JSON generado: {json.dumps(resultado, indent=2)}")
    else:
        print("❌ Ollama no está corriendo. Ejecuta: ollama serve")
