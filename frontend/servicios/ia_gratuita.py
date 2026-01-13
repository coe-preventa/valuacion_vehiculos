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
# PROMPT INTELIGENTE (COT & SCHEMA ENFORCEMENT)
# ============================================

PROMPT_GENERADOR = """Eres un Arquitecto de Datos experto en Valuación de Vehículos.
Tu trabajo es traducir lenguaje natural a una estructura JSON técnica estricta.

### TUS OBJETIVOS:
1. ANALIZAR: Entiende qué quiere hacer el usuario (Filtrar, Ajustar Precio, Buscar, etc.).
2. CLASIFICAR: Asigna el "tipo_detectado" correcto basándote en la lista de abajo.
3. ESTRUCTURAR: Genera el JSON "parametros" usando SOLO los campos permitidos.

### TIPOS DE REGLA Y SUS ESQUEMAS (Usa estos campos):

1. TIPO: "fuente" (Origen de datos)
   - Esquema: {{"url": "...", "nombre": "...", "prioridad": 1}}

2. TIPO: "filtro_busqueda" (Restricciones de qué autos buscar)
   - Esquema: {{"campo": "marca|modelo|año|km", "operador": "igual|entre|mayor", "valor": "..."}}

3. TIPO: "ajuste_calculo" (Modificar el precio final)
   - Palabras clave: Aumentar, disminuir, sumar, restar, inflacion, ganancia.
   - Esquema A (Porcentual): {{"tipo": "ajuste_porcentual", "porcentaje": 10, "base": "promedio_mercado", "operacion": "incrementar|disminuir", "condicion": "opcional (ej: marca=Toyota)"}}
   - Esquema B (Fijo): {{"tipo": "margen_ganancia", "porcentaje": 20}}

4. TIPO: "depuracion" (Eliminar resultados sucios)
   - Esquema: {{"accion": "eliminar_outliers", "cantidad": 5}}

### EJEMPLOS DE RAZONAMIENTO (Few-Shot Learning):

Usuario: "Buscar precios en kavak.com"
Razonamiento: El usuario quiere agregar un origen de datos -> fuente.
JSON: {{"tipo_detectado": "fuente", "es_valido": true, "parametros": {{"url": "kavak.com", "nombre": "Kavak", "prioridad": 1}}}}

Usuario: "Aumentar 10% al valor de los autos Toyota"
Razonamiento: El usuario quiere modificar el precio (Aumentar) -> ajuste_calculo. Tiene una condición (Toyota).
JSON: {{"tipo_detectado": "ajuste_calculo", "es_valido": true, "parametros": {{"tipo": "ajuste_porcentual", "porcentaje": 10, "operacion": "incrementar", "base": "promedio_mercado", "condicion_aplicacion": "marca igual a Toyota"}}}}

Usuario: "Eliminar los autos con precio muy bajo"
Razonamiento: El usuario quiere limpiar datos -> depuracion.
JSON: {{"tipo_detectado": "depuracion", "es_valido": true, "parametros": {{"accion": "eliminar_outliers_precio", "extremo": "inferior", "cantidad": 5}}}}

---------------------------------------------------------
SOLICITUD ACTUAL:
"{descripcion}"

Responde SOLO con el JSON final:"""


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
