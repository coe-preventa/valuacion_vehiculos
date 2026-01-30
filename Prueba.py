import asyncio
import json
import os
from playwright.async_api import async_playwright

def motor_determinista_limpieza(arbol_raw):
    nodos = arbol_raw.get("nodes", [])
    datos_limpios = []
    
    for nodo in nodos:
        if nodo.get("ignored"):
            continue
            
        rol = nodo.get("role", {}).get("value")
        nombre = nodo.get("name", {}).get("value")
        
        # --- NUEVA LÓGICA: Captura de URL ---
        url_destino = ""
        if rol == "link":
            for prop in nodo.get("properties", []):
                # Buscamos la propiedad 'url' dentro del árbol de accesibilidad
                if prop.get("name") in ["url", "href"]:
                    url_destino = prop.get("value", {}).get("value", "")

        if nombre and nombre.strip() and rol:
            texto = " ".join(nombre.split())
            
            if not datos_limpios or datos_limpios[-1]['texto'] != texto:
                item = {
                    "tipo": rol,
                    "texto": texto
                }
                # Si encontramos una URL, la agregamos al diccionario
                if url_destino:
                    item["url"] = url_destino
                    
                datos_limpios.append(item)
    return datos_limpios

async def captura_universal_cdp(url_objetivo):
    async with async_playwright() as p:
        print(f"🚀 Iniciando motor de captura en: {url_objetivo}")
        
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("🌐 Navegando...")
            await page.goto(url_objetivo, wait_until="domcontentloaded", timeout=60000)

            print("⏳ Esperando renderizado dinámico...")
            await asyncio.sleep(5) 

            # Scroll para asegurar que los nodos "lazy" entren al árbol
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(2)

            print("📡 Extrayendo AXTree vía CDP...")
            client = await page.context.new_cdp_session(page)
            arbol = await client.send("Accessibility.getFullAXTree")

            if arbol:
                # 1. Guardar Raw Data (Auditoría Técnica)
                with open("estructura_raw.json", "w", encoding="utf-8") as f:
                    json.dump(arbol, f, indent=2, ensure_ascii=False)
                
                # 2. Ejecutar Motor Determinístico de Limpieza
                print("🧹 Ejecutando limpieza determinística...")
                relevamiento_final = motor_determinista_limpieza(arbol)
                
                # 3. Guardar Datos Limpios (Para la Fuzzy Machine / IA)
                with open("relevamiento_limpio.json", "w", encoding="utf-8") as f:
                    json.dump(relevamiento_final, f, indent=2, ensure_ascii=False)
                
                print(f"✅ ¡ÉXITO!")
                print(f"📂 Archivo Crudo: estructura_raw.json ({os.path.getsize('estructura_raw.json')/1024:.1f} KB)")
                print(f"📂 Archivo Limpio: relevamiento_limpio.json ({os.path.getsize('relevamiento_limpio.json')/1024:.1f} KB)")
            
        except Exception as e:
            print(f"❌ Error durante el proceso: {e}")
        
        finally:
            print("🔒 Cerrando navegador...")
            await browser.close()

if __name__ == "__main__":
    URL_PRUEBA = "https://www.kavak.com/ar/usados?maker=chevrolet&model=agile&year=2011,2014,2015"
    asyncio.run(captura_universal_cdp(URL_PRUEBA))