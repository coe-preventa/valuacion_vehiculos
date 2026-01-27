# backend/services/agente_service.py
"""
Servicio del agente de valuación.
Consume las reglas dinámicamente y ejecuta valuaciones con trazabilidad completa.
"""

import anthropic
from typing import Dict, Any, Optional
from datetime import datetime
import json
import time

from models import Vehiculo, Valuacion, Usuario, obtener_session
from services.reglas_service import ReglasService


class AgenteValuacionService:
    """
    Servicio que ejecuta el agente de valuación.
    Construye el prompt dinámicamente basado en las reglas activas.
    """
    
    def __init__(self, db_session, api_key: Optional[str] = None):
        self.db = db_session
        self.reglas_service = ReglasService(db_session)
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = "claude-sonnet-4-20250514"
    
    def _construir_system_prompt(self, config: Dict[str, Any]) -> str:
        """
        Construye el prompt del sistema dinámicamente basado en las reglas activas.
        """
        
        # Extraer configuraciones
        fuentes = config.get("fuentes", [])
        filtros = config.get("filtros_busqueda", [])
        depuracion = config.get("depuracion", [])
        muestreo = config.get("muestreo", [])
        puntos_control = config.get("puntos_control", [])
        metodos = config.get("metodos_valuacion", [])
        ajustes = config.get("ajustes_calculo", [])
        
        # Construir secciones del prompt
        prompt = f"""
Eres un asistente especializado en valuación de vehículos usados.
Tu trabajo es buscar datos de mercado, aplicar las reglas de negocio configuradas y calcular precios con total trazabilidad.

Fecha actual: {datetime.now().strftime('%d/%m/%Y %H:%M')}

═══════════════════════════════════════════════════════════════
                 REGLAS DE NEGOCIO ACTIVAS
═══════════════════════════════════════════════════════════════

## 1. FUENTES DE DATOS
{self._formatear_fuentes(fuentes)}

## 2. FILTROS DE BÚSQUEDA
{self._formatear_filtros(filtros)}

## 3. REGLAS DE DEPURACIÓN
{self._formatear_depuracion(depuracion)}

## 4. MUESTREO DE RESULTADOS
{self._formatear_muestreo(muestreo)}

## 5. PUNTOS DE CONTROL
{self._formatear_puntos_control(puntos_control)}

## 6. MÉTODOS DE VALUACIÓN
{self._formatear_metodos(metodos)}

## 7. AJUSTES DE CÁLCULO
{self._formatear_ajustes(ajustes)}

═══════════════════════════════════════════════════════════════
                    INSTRUCCIONES DE EJECUCIÓN
═══════════════════════════════════════════════════════════════

### PROCESO OBLIGATORIO:

1. **BÚSQUEDA**: Usar web_search para buscar en TODAS las fuentes configuradas
2. **FILTRADO**: Aplicar TODOS los filtros de búsqueda en orden
3. **DEPURACIÓN**: Eliminar resultados según las reglas de depuración
4. **CONTROL**: Verificar puntos de control. Si no se cumplen, ampliar búsqueda
5. **CÁLCULO**: Aplicar métodos de valuación configurados
6. **AJUSTES**: Aplicar todos los ajustes de cálculo en orden
7. **REPORTE**: Generar reporte estructurado

### FORMATO DE RESPUESTA OBLIGATORIO:

Responde SIEMPRE con un JSON válido con esta estructura exacta:

```json
{{
    "precio_sugerido": <número>,
    "precio_minimo": <número>,
    "precio_maximo": <número>,
    "confianza": "<ALTA|MEDIA|BAJA>",
    "analisis": {{
        "fuentes_consultadas": <número>,
        "resultados_iniciales": <número>,
        "resultados_tras_filtrado": <número>,
        "resultados_tras_depuracion": <número>,
        "precio_mercado_min": <número>,
        "precio_mercado_max": <número>,
        "precio_mercado_promedio": <número>,
        "precio_mercado_mediana": <número>
    }},
    "reglas_aplicadas": [
        {{"codigo": "<código>", "resultado": "<descripción>"}},
        ...
    ],
    "publicaciones": [
        {{"fuente": "<nombre>", "precio": <número>, "url": "<url>", "incluida": <true|false>}},
        ...
    ],
    "alertas": ["<alerta1>", "<alerta2>", ...],
    "reporte_detallado": "<markdown con el análisis completo>"
}}
```

### IMPORTANTE:
- Documenta CADA regla aplicada en "reglas_aplicadas"
- Lista TODAS las publicaciones encontradas (marcando cuáles se usaron)
- Si no hay suficientes resultados, indica en "alertas"
- El "reporte_detallado" debe ser legible para humanos
"""
        return prompt
    
    def _formatear_fuentes(self, fuentes: list) -> str:
        """Formatea la sección de fuentes para el prompt"""
        if not fuentes:
            return "⚠️ No hay fuentes configuradas. Usar fuentes genéricas."
        
        lineas = []
        for i, f in enumerate(fuentes, 1):
            params = f.get("parametros", {})
            url = params.get("url", "N/A")
            prioridad = params.get("prioridad", i)
            verificado = "✓" if params.get("verificado", False) else ""
            lineas.append(f"  {prioridad}. {url} {verificado}")
        
        return "\n".join(lineas)
    
    def _formatear_filtros(self, filtros: list) -> str:
        """Formatea la sección de filtros para el prompt"""
        if not filtros:
            return "Filtros por defecto: marca exacta, modelo exacto, año ±1, km ±10000"
        
        lineas = []
        for f in filtros:
            params = f.get("parametros", {})
            campo = params.get("campo", "?")
            operador = params.get("operador", "?")
            valor = params.get("valor", "?")
            relativo = "(relativo al vehículo)" if params.get("relativo") else ""
            lineas.append(f"  • {campo}: {operador} {valor} {relativo}")
        
        return "\n".join(lineas)
    
    def _formatear_depuracion(self, depuracion: list) -> str:
        """Formatea la sección de depuración para el prompt"""
        if not depuracion:
            return "Sin reglas de depuración específicas."
        
        lineas = []
        for d in depuracion:
            nombre = d.get("nombre", "Regla")
            params = d.get("parametros", {})
            accion = params.get("accion", "?")
            cantidad = params.get("cantidad", "?")
            criterio = params.get("criterio", "")
            lineas.append(f"  • {nombre}: {accion} - cantidad: {cantidad} {criterio}")
        
        return "\n".join(lineas)
    
    def _formatear_muestreo(self, muestreo: list) -> str:
        """Formatea la sección de muestreo para el prompt"""
        if not muestreo:
            return "Usar todos los resultados disponibles."
        
        lineas = []
        for m in muestreo:
            nombre = m.get("nombre", "Método")
            params = m.get("parametros", {})
            metodo = params.get("metodo", "?")
            cantidad = params.get("cantidad", "?")
            lineas.append(f"  • {nombre}: {metodo} - tomar {cantidad} resultados")
        
        return "\n".join(lineas)
    
    def _formatear_puntos_control(self, puntos: list) -> str:
        """Formatea la sección de puntos de control para el prompt"""
        if not puntos:
            return "Sin puntos de control adicionales."
        
        lineas = []
        for p in puntos:
            nombre = p.get("nombre", "Control")
            params = p.get("parametros", {})
            umbral = params.get("umbral_minimo", "?")
            accion = params.get("accion", "?")
            nuevos = params.get("nuevos_parametros", {})
            lineas.append(f"  • {nombre}:")
            lineas.append(f"    - Si resultados < {umbral}: {accion}")
            if nuevos:
                lineas.append(f"    - Nuevos parámetros: {json.dumps(nuevos)}")
        
        return "\n".join(lineas)
    
    def _formatear_metodos(self, metodos: list) -> str:
        """Formatea la sección de métodos de valuación para el prompt"""
        if not metodos:
            return "Método por defecto: MEDIANA"
        
        lineas = []
        for m in metodos:
            nombre = m.get("nombre", "Método")
            params = m.get("parametros", {})
            metodo = params.get("metodo", "?")
            peso = params.get("peso", 1.0)
            lineas.append(f"  • {nombre}: usar {metodo} (peso: {peso})")
        
        return "\n".join(lineas)
    
    def _formatear_ajustes(self, ajustes: list) -> str:
        """Formatea la sección de ajustes de cálculo para el prompt"""
        if not ajustes:
            return "Sin ajustes adicionales al precio base."
        
        lineas = []
        for a in ajustes:
            nombre = a.get("nombre", "Ajuste")
            params = a.get("parametros", {})
            tipo = params.get("tipo", "?")
            porcentaje = params.get("porcentaje", 0)
            periodo = params.get("periodo_dias", "")
            
            desc = f"  • {nombre}: {tipo}"
            if porcentaje:
                desc += f" {porcentaje}%"
            if periodo:
                desc += f" (a {periodo} días)"
            lineas.append(desc)
        
        return "\n".join(lineas)
    
    async def valuar_vehiculo(
        self,
        vehiculo: Vehiculo,
        usuario: Usuario,
        configuracion_override: Optional[Dict] = None
    ) -> Valuacion:
        """
        Ejecuta una valuación completa de un vehículo.
        
        Args:
            vehiculo: Vehículo a valuar
            usuario: Usuario que solicita la valuación
            configuracion_override: Configuración personalizada (opcional)
        
        Returns:
            Objeto Valuacion con todos los resultados
        """
        inicio = time.time()
        
        # Obtener configuración (override o dinámica de reglas)
        if configuracion_override:
            config = configuracion_override
        else:
            config = self.reglas_service.generar_configuracion_prompt()
        
        # Construir prompt
        system_prompt = self._construir_system_prompt(config)
        
        # Construir mensaje del usuario
        mensaje_usuario = self._construir_mensaje_vehiculo(vehiculo)
        
        # Llamar al agente
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=system_prompt,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 20
            }],
            messages=[{"role": "user", "content": mensaje_usuario}]
        )
        
        duracion = time.time() - inicio
        
        # Procesar respuesta
        resultado = self._procesar_respuesta(response)
        
        # Crear registro de valuación
        valuacion = Valuacion(
            vehiculo_id=vehiculo.id,
            usuario_id=usuario.id,
            precio_sugerido=resultado.get("precio_sugerido"),
            precio_minimo=resultado.get("precio_minimo"),
            precio_maximo=resultado.get("precio_maximo"),
            confianza=resultado.get("confianza"),
            fuentes_consultadas=resultado.get("analisis", {}).get("fuentes_consultadas", 0),
            resultados_encontrados=resultado.get("analisis", {}).get("resultados_iniciales", 0),
            resultados_filtrados=resultado.get("analisis", {}).get("resultados_tras_depuracion", 0),
            precio_mercado_minimo=resultado.get("analisis", {}).get("precio_mercado_min"),
            precio_mercado_maximo=resultado.get("analisis", {}).get("precio_mercado_max"),
            precio_mercado_promedio=resultado.get("analisis", {}).get("precio_mercado_promedio"),
            precio_mercado_mediana=resultado.get("analisis", {}).get("precio_mercado_mediana"),
            reglas_aplicadas=resultado.get("reglas_aplicadas", []),
            configuracion_usada=config,
            publicaciones_analizadas=resultado.get("publicaciones", []),
            reporte_completo=resultado.get("reporte_detallado", ""),
            fecha=datetime.utcnow(),
            duracion_segundos=duracion,
            tokens_usados={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens
            }
        )
        
        self.db.add(valuacion)
        self.db.commit()
        self.db.refresh(valuacion)
        
        return valuacion
    
    def _construir_mensaje_vehiculo(self, vehiculo: Vehiculo) -> str:
        """Construye el mensaje con los datos del vehículo a valuar"""
        mensaje = f"""
Realizá la valuación completa del siguiente vehículo aplicando TODAS las reglas configuradas:

══════════════════════════════════════
         VEHÍCULO A VALUAR
══════════════════════════════════════
• Marca: {vehiculo.marca}
• Modelo: {vehiculo.modelo}
• Año: {vehiculo.año}
• Kilometraje: {vehiculo.kilometraje:,} km
"""
        if vehiculo.version:
            mensaje += f"• Versión: {vehiculo.version}\n"
        if vehiculo.transmision:
            mensaje += f"• Transmisión: {vehiculo.transmision}\n"
        if vehiculo.combustible:
            mensaje += f"• Combustible: {vehiculo.combustible}\n"
        if vehiculo.color:
            mensaje += f"• Color: {vehiculo.color}\n"
        
        mensaje += """
══════════════════════════════════════

Ejecutá el proceso completo:
1. Buscá en TODAS las fuentes configuradas
2. Aplicá TODOS los filtros y reglas de depuración
3. Verificá los puntos de control
4. Calculá el precio usando los métodos configurados
5. Aplicá todos los ajustes
6. Generá el reporte con trazabilidad completa

Responde con el JSON estructurado según el formato especificado.
"""
        return mensaje
    
def _procesar_respuesta(self, response) -> Dict[str, Any]:
        """Procesa la respuesta del agente y extrae el JSON de forma robusta"""
        texto = ""
        
        # 1. Extracción segura del texto (Maneja casos donde content es lista o string)
        if isinstance(response.content, list):
            for block in response.content:
                if hasattr(block, 'text'):
                    texto += block.text
        else:
            texto = str(response.content)
        
        # --- INICIO DEPURACIÓN ---
        print("\n" + "="*50)
        print("🤖 RESPUESTA CRUDA DE GEMINI:")
        print(texto)
        print("="*50 + "\n")
        # --- FIN DEPURACIÓN ---

        # 2. Limpieza de Markdown (Claude suele envolver en ```json)
        texto_limpio = texto.replace("```json", "").replace("```", "").strip()

        # 3. Intentar parseo directo primero
        try:
            return json.loads(texto_limpio)
        except json.JSONDecodeError:
            pass

        # 4. Búsqueda con Regex (Si hay texto alrededor)
        try:
            import re
            # Busca el primer { y el último }
            json_match = re.search(r'(\{[\s\S]*\})', texto_limpio)
            if json_match:
                # Intenta parsear lo encontrado
                return json.loads(json_match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 5. Fallback: Retornar error estructurado para depuración
        print(f"DEBUG - Texto recibido de IA que falló: {texto[:200]}...") # Log para ver qué llega
        return {
            "precio_sugerido": 0,
            "confianza": "ERROR_PARSEO",
            "alertas": ["No se pudo parsear la respuesta estructurada"],
            "reporte_detallado": f"La IA respondió pero no en formato JSON válido. Respuesta parcial: {texto[:500]}..."
        }


class GeneradorPromptDinamico:
    """
    Clase utilitaria para generar el prompt completo
    que puede ser usado directamente en Claude.ai o exportado.
    """
    
    def __init__(self, db_session):
        self.reglas_service = ReglasService(db_session)
    
    def generar_prompt_completo(self) -> str:
        """
        Genera el prompt completo en formato texto
        para usar en Claude.ai directamente.
        """
        config = self.reglas_service.generar_configuracion_prompt()
        
        prompt = f"""
# ASISTENTE DE VALUACIÓN DE VEHÍCULOS

Eres un asistente especializado en valuación de vehículos usados.
Fecha: {datetime.now().strftime('%d/%m/%Y')}

## CONFIGURACIÓN ACTIVA

```json
{json.dumps(config, indent=2, ensure_ascii=False)}
```

## INSTRUCCIONES

[El resto del prompt se genera dinámicamente basado en las reglas...]
"""
        return prompt
    
    def exportar_configuracion(self, formato: str = "json") -> str:
        """
        Exporta la configuración actual para backup o documentación.
        """
        config = self.reglas_service.generar_configuracion_prompt()
        
        if formato == "json":
            return json.dumps(config, indent=2, ensure_ascii=False)
        elif formato == "yaml":
            import yaml
            return yaml.dump(config, default_flow_style=False, allow_unicode=True)
        else:
            return str(config)
