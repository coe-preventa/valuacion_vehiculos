import asyncio
import json
import sys
import re
import httpx
from playwright.async_api import async_playwright
from typing import AsyncGenerator, List, Dict, Any

class BrowserService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def _limpiar_arbol(self, arbol_raw: Dict) -> List[Dict]:
        nodos = arbol_raw.get("nodes", [])
        datos_limpios = []
        for i, nodo in enumerate(nodos):
            if nodo.get("ignored"): continue
            rol = nodo.get("role", {}).get("value")
            nombre = nodo.get("name", {}).get("value")
            valor = nodo.get("value", {}).get("value", "")
            descripcion = nodo.get("description", {}).get("value", "")
            
            # Capturar estados críticos para que la IA sepa si un filtro está activo
            estados = []
            for prop in nodo.get("properties", []):
                if prop.get("name") in ["selected", "checked", "pressed", "expanded"] and prop.get("value", {}).get("value") is True:
                    estados.append(prop["name"])
            
            url_destino = ""
            if rol == "link":
                for prop in nodo.get("properties", []):
                    if prop.get("name") in ["url", "href"]:
                        url_destino = prop.get("value", {}).get("value", "")

            if (nombre or valor or descripcion) and rol:
                # Enriquecemos el texto con el rol y estados (ej: [button] [selected] Marca)
                estado_str = f" [{' '.join(estados)}]" if estados else ""
                texto_final = f"[{rol}]{estado_str} {nombre or ''} {valor or ''} {descripcion or ''}".strip()
                if texto_final:
                    item = {"id": i, "tipo": rol, "texto": " ".join(texto_final.split())}
                    if url_destino: item["url"] = url_destino
                    datos_limpios.append(item)
        return datos_limpios

    async def _consultar_ia_paso(self, page, objetivo: str, historia: List[Dict], proveedor: str, modelo: str, api_key: str) -> Dict:
        """Suministra los datos del sitio a la IA para determinar el siguiente paso."""
        try:
            client = await page.context.new_cdp_session(page)
            arbol = await client.send("Accessibility.getFullAXTree")
            nodos = self._limpiar_arbol(arbol)
            
            # Filtrar para no saturar el contexto de Llama
            nodos_interactuables = [n for n in nodos if n['tipo'] in ['button', 'combobox', 'listbox', 'link', 'menuitem', 'textbox', 'checkbox', 'searchbox', 'radio']]
            
            prompt = f"""
            Eres un Agente de Navegación Experto. Tu misión es lograr el OBJETIVO analizando el estado actual del sitio.
            
            URL ACTUAL: {page.url}
            OBJETIVO: {objetivo}
            HISTORIAL DE ACCIONES PREVIAS: {json.dumps(historia[-3:])}
            
            ESTADO ACTUAL (Elementos con ID):
            {json.dumps(nodos_interactuables[:200], ensure_ascii=False)}
            
            REGLAS DE ORO:
            1. ANALIZA: Mira los elementos y su estado ([selected], [expanded]).
            2. ACCIÓN: Elige la acción atómica necesaria (click, escribir, esperar).
            3. VERIFICACIÓN: Si el objetivo ya se ve cumplido en el AXTree, responde con accion "finalizar".
            4. OBSTÁCULOS: Si hay pop-ups o banners de cookies, tu prioridad es CERRARLOS.
            5. FILTROS: Para aplicar un filtro, primero debes abrir el menú (click) y en el SIGUIENTE paso seleccionar la opción.
            
            Responde ESTRICTAMENTE en JSON:
            {{
                "pensamiento": "análisis detallado de lo que ves y por qué eliges la acción",
                "accion": "click" | "escribir" | "esperar" | "finalizar",
                "elemento_id": <id numérico del elemento en el AXTree>,
                "elemento_texto": "texto del elemento para referencia",
                "valor": "texto a escribir (solo si accion es escribir)",
                "objetivo_verificado": true | false
            }}
            """
            
            async with httpx.AsyncClient() as client_http:
                res_text = ""
                if proveedor == "ollama":
                    response = await client_http.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": modelo or "llama3.2",
                            "prompt": prompt,
                            "stream": False,
                            "format": "json"
                        },
                        timeout=20.0
                    )
                    if response.status_code == 200:
                        res_text = response.json().get("response", "{}")
                
                elif proveedor == "gemini":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo or 'gemini-2.0-flash'}:generateContent?key={api_key}"
                    response = await client_http.post(
                        url,
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
                        },
                        timeout=20.0
                    )
                    if response.status_code == 200:
                        res_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                
                elif proveedor == "groq":
                    response = await client_http.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": modelo or "llama-3.3-70b-versatile",
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"}
                        },
                        timeout=20.0
                    )
                    if response.status_code == 200:
                        res_text = response.json()["choices"][0]["message"]["content"]

                if res_text:
                    try:
                        return json.loads(res_text)
                    except:
                        match = re.search(r'\{.*\}', res_text, re.DOTALL)
                        if match:
                            return json.loads(match.group())
            return {}
        except Exception:
            return {}

    async def _ejecutar_con_ia(self, page, objetivo: str, proveedor: str, modelo: str, api_key: str, max_pasos: int = 10) -> AsyncGenerator[str, None]:
        """Bucle agentic que suministra datos del sitio a la IA en cada paso."""
        historia = []
        for i in range(max_pasos):
            yield f"🧠 IA ({proveedor} - {modelo or 'default'}) analizando paso {i+1}..."
            decision = await self._consultar_ia_paso(page, objetivo, historia, proveedor, modelo, api_key)
            
            if decision.get("pensamiento"):
                yield f"💭 IA: {decision['pensamiento']}"

            accion = decision.get("accion")
            target = decision.get("elemento_texto")
            target_id = decision.get("elemento_id")
            
            if accion == "finalizar" or not accion or decision.get("objetivo_verificado") is True:
                yield f"✅ Objetivo verificado por IA: {objetivo}"
                return

            historia.append({"paso": i+1, "accion": accion, "target": target})

            try:
                if accion == "click":
                    yield f"🖱️ IA decidió click en '{target}'"
                    
                    # Intentamos localizar el elemento de forma robusta
                    # Si el ID es válido, intentamos usarlo vía texto para mayor precisión
                    if target:
                        # Limpiar el texto del target (quitar el prefijo [rol] si la IA lo incluyó)
                        clean_target = re.sub(r'\[.*?\]', '', target).strip()
                        elem = page.get_by_role("button", name=clean_target, exact=False).or_(
                               page.get_by_role("link", name=clean_target, exact=False)).or_(
                               page.get_by_text(clean_target, exact=False)).first
                    else:
                        yield "⚠️ No se proporcionó texto de elemento para el click."
                        continue
                    
                    if await elem.count() > 0:
                        await elem.scroll_into_view_if_needed()
                        await elem.evaluate("node => { (node.closest('button, a, [role=\"button\"], [role=\"link\"], [role=\"combobox\"]') || node).click(); }")
                        await asyncio.sleep(2)
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    else:
                        yield f"⚠️ No se encontró '{target}'"
                
                elif accion == "escribir":
                    valor_escribir = decision.get("valor", "")
                    yield f"⌨️ IA decidió escribir '{valor_escribir}' en '{target}'"
                    
                    clean_target = re.sub(r'\[.*?\]', '', target).strip()
                    input_elem = page.get_by_role("textbox", name=clean_target, exact=False).or_(
                                 page.get_by_placeholder(clean_target, exact=False)).or_(
                                 page.get_by_label(clean_target, exact=False)).first
                    
                    if await input_elem.count() > 0:
                        await input_elem.scroll_into_view_if_needed()
                        # Forzar activación si es readonly
                        if not await input_elem.is_editable() or await input_elem.get_attribute("readonly"):
                            yield "🖱️ Activando campo readonly..."
                            await input_elem.dispatch_event("click")
                            await asyncio.sleep(1.5)
                            # Re-localizar el input editable
                            input_elem = page.locator("input:not([readonly]), textarea:not([readonly])").filter(has_text=target).first.or_(
                                         page.locator("input:not([readonly]), textarea:not([readonly])").first)
                        
                        await input_elem.fill("")
                        await input_elem.type(valor_escribir, delay=100)
                        await asyncio.sleep(1.5)
                    else:
                        yield f"⚠️ No se encontró campo '{target}'"
                
                elif accion == "esperar":
                    yield "⏳ IA solicitó esperar..."
                    await asyncio.sleep(3)
            except Exception as e:
                yield f"❌ Error en acción: {str(e)}"

    async def _aplicar_filtro_inteligente(self, page, campo: str, valor: str, proveedor: str, modelo: str, api_key: str) -> AsyncGenerator[str, None]:
        """
        Aplica un filtro usando el bucle agentic guiado por IA.
        """
        async for step in self._ejecutar_con_ia(page, f"Filtrar el campo '{campo}' con el valor '{valor}'", proveedor, modelo, api_key):
            yield step

    async def buscar_inteligente(self, url_base: str, vehiculo: Any, filtros_reglas: List[Dict], proveedor: str = "ollama", modelo: str = "llama3.2", api_key: str = None) -> AsyncGenerator[Dict, None]:
    async def buscar_inteligente(self, url_base: str, vehiculo: Any, filtros_reglas: List[Dict], proveedor: str = "ollama", modelo: str = "llama3.2", api_key: str = None, motor: str = "playwright") -> AsyncGenerator[Dict, None]:
        """
        Navega autónomamente, aplica filtros y extrae URLs.
        Genera yields con el progreso para el frontend.
        Punto de entrada para la búsqueda inteligente. Despacha al motor seleccionado.
        """
        if motor == "stagehand":
            async for update in self._buscar_con_stagehand(url_base, vehiculo, filtros_reglas, proveedor, modelo, api_key):
                yield update
        else:
            async for update in self._buscar_con_playwright_agentic(url_base, vehiculo, filtros_reglas, proveedor, modelo, api_key):
                yield update

    async def _buscar_con_stagehand(self, url_base: str, vehiculo: Any, filtros_reglas: List[Dict], proveedor: str, modelo: str, api_key: str) -> AsyncGenerator[Dict, None]:
        """Implementación utilizando el framework Stagehand (Estructura base)"""
        yield {"step": "🚀 Iniciando motor Stagehand...", "status": "info"}
        yield {"step": "⚠️ Stagehand requiere un entorno Node.js o wrapper. Ejecutando via Bridge...", "status": "warning"}
        # Aquí iría la lógica de Stagehand: page.act(), page.extract(), etc.
        yield {"step": "❌ Motor Stagehand en desarrollo. Use Playwright por ahora.", "status": "error"}

    async def _buscar_con_playwright_agentic(self, url_base: str, vehiculo: Any, filtros_reglas: List[Dict], proveedor: str, modelo: str, api_key: str) -> AsyncGenerator[Dict, None]:
        """Navegación autónoma personalizada sobre Playwright (Lógica actual)"""
        # Verificación de seguridad para Windows
        if sys.platform == 'win32':
            loop = asyncio.get_running_loop()
            loop_type = type(loop).__name__
            if "Proactor" not in loop_type:
                yield {"step": f"❌ Error de Configuración: Se detectó {loop_type}. Playwright requiere ProactorEventLoop en Windows. Por favor, reinicie el servidor usando run_backend.py.", "status": "error"}
                return

        async with async_playwright() as p:
            yield {"step": f"🚀 Iniciando navegador para {url_base}...", "status": "info"}
            # headless=False permite ver la ventana. 
            # slow_mo añade un retraso entre acciones para que sea humano-perceptible.
            browser = await p.chromium.launch(headless=False, slow_mo=1000)
            context = await browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent=self.headers["User-Agent"])
            page = await context.new_page()

            try:
                yield {"step": f"🌐 Navegando a la home de la fuente...", "status": "info"}
                await page.goto(url_base, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                
                # Fase 0: Selección de país si la URL base lo sugiere
                match_pais = re.search(r'\.com/([a-z]{2})/|\.com\.([a-z]{2})/', url_base)
                if match_pais:
                    pais_code = match_pais.group(1) or match_pais.group(2)
                    pais_nombre = {"ar": "Argentina", "mx": "México", "cl": "Chile"}.get(pais_code, pais_code.upper())
                    
                    yield {"step": f"🌍 Detectado código de país '{pais_code}'. IA determinando navegación para '{pais_nombre}'...", "status": "info"}
                    async for step in self._ejecutar_con_ia(page, f"Asegurarse de que el sitio esté en la versión de '{pais_nombre}' (hacer click en el selector de país si aparece)", proveedor, modelo, api_key):
                        yield {"step": step, "status": "info"}
                    await page.wait_for_load_state("networkidle", timeout=10000)

                # 1. Buscar sección de usados/marketplace
                yield {"step": f"🔍 IA ({proveedor}) analizando cómo llegar al Marketplace de usados...", "status": "info"}
                marketplace_confirmado = False
                async for step in self._ejecutar_con_ia(page, "Navegar al catálogo de autos usados, Marketplace o sección de 'Comprar'", proveedor, modelo, api_key):
                    yield {"step": step, "status": "info"}
                    if "Objetivo verificado" in step:
                        marketplace_confirmado = True
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                if not marketplace_confirmado:
                    yield {"step": "🔍 IA no confirmó Marketplace. Realizando verificación técnica de seguridad...", "status": "info"}
                    # Verificación manual de seguridad: buscar símbolos de moneda o palabras clave de catálogo
                    content = await page.content()
                    precios_encontrados = len(re.findall(r'\$\s?[\d.]+', content))
                    if precios_encontrados < 3 and "usados" not in page.url.lower():
                        yield {"step": "❌ Error: No se detectó un listado de vehículos válido. La navegación falló.", "status": "error"}
                        return
                    yield {"step": "✨ Indicadores de datos detectados. Continuando con el proceso...", "status": "info"}
                
                # 2. Aplicar Filtros basados en Reglas
                yield {"step": "📋 Generando plan de filtrado inteligente...", "status": "info"}
                
                # Mapeo de campos de reglas a etiquetas comunes en portales
                mapeo_campos = {
                    "marca": vehiculo.marca,
                    "modelo": vehiculo.modelo,
                    "año": str(vehiculo.año)
                }

                for regla in filtros_reglas:
                    campo_regla = str(regla.get("parametros", {}).get("campo", "")).lower()
                    if campo_regla in mapeo_campos:
                        valor = mapeo_campos[campo_regla]
                        async for sub_step in self._aplicar_filtro_inteligente(page, campo, valor, proveedor, modelo, api_key):
                            yield {"step": sub_step, "status": "info"}

                yield {"step": "⏳ Esperando actualización final de la lista de resultados...", "status": "info"}
                await page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(2) 
                await page.mouse.wheel(0, 1000) # Scroll para cargar lazy items
                
                # 3. Extracción Final
                yield {"step": "📡 Extrayendo publicaciones mediante AXTree...", "status": "info"}
                client_final = await page.context.new_cdp_session(page)
                arbol_final = await client_final.send("Accessibility.getFullAXTree")
                resultados_sucios = self._limpiar_arbol(arbol_final)
                
                # Filtrar solo links que parezcan vehículos RELEVANTES (Heurística estricta)
                publicaciones = []
                vistos = set()
                
                # Palabras clave para ignorar secciones de publicidad o footer
                ignorar_keywords = ['vende tu', 'ayuda', 'contacto', 'términos', 'privacidad', 'sucursales', 'trabajá', 'blog', 'recomendados', 'publicidad']
                
                for res in resultados_sucios:
                    if res['tipo'] == 'link' and 'url' in res:
                        txt = res['texto'].lower()
                        
                        # Un resultado válido debe tener Precio Y (Marca o Modelo o Año)
                        tiene_precio = any(p in txt for p in ['$', 'ars', 'usd'])
                        tiene_info_auto = any(kw in txt for kw in [vehiculo.marca.lower(), vehiculo.modelo.lower(), str(vehiculo.año)])
                        es_publicidad = any(ik in txt for ik in ignorar_keywords)

                        if tiene_precio and tiene_info_auto and not es_publicidad:
                            full_url = res['url'] if res['url'].startswith('http') else f"{url_base.rstrip('/')}/{res['url'].lstrip('/')}"
                            if full_url not in vistos:
                                publicaciones.append({
                                    "titulo": res['texto'][:60],
                                    "url": full_url,
                                    "snippet": "Extraído vía Navegación Autónoma AXTree"
                                })
                                vistos.add(full_url)
                
                yield {"step": f"✅ ¡Éxito! Se hallaron {len(publicaciones)} publicaciones.", "status": "success", "data": publicaciones}

            except Exception as e:
                yield {"step": f"❌ Error en navegación: {str(e)}", "status": "error"}
            finally:
                await browser.close()