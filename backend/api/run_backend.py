import asyncio
import sys
import uvicorn

if __name__ == "__main__":
    # Configuración obligatoria para Playwright en Windows
    if sys.platform == 'win32':
        print("🔧 [SISTEMA] Configurando WindowsProactorEventLoopPolicy...")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Iniciamos uvicorn programáticamente
    # reload=False es recomendado en Windows cuando se usa Playwright para evitar conflictos de bucles
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        loop="asyncio",
        workers=1
    )