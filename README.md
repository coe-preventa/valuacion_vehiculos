# 🚗 Sistema de Valuación de Vehículos Usados v2.1

Sistema completo para asistir a vendedores en la valuación de vehículos usados, con reglas de negocio configurables, generación inteligente mediante IA y auditoría completa.

## 📋 Características

### Gestión de Reglas
- ✅ CRUD completo de reglas de negocio
- ✅ Versionado automático de cada cambio
- ✅ Auditoría completa (quién, cuándo, qué cambió)
- ✅ Restauración a versiones anteriores
- ✅ Comparación entre versiones

### 🤖 Generación Inteligente con IA
- ✅ **Traducción de lenguaje natural a JSON** técnico
- ✅ **Detección automática del tipo de regla** basada en el contexto
- ✅ **Múltiples proveedores de IA soportados:**
  - 🦙 **Ollama** (local, gratuito)
  - ⚡ **Groq** (cloud, gratuito con límites)
  - 🔷 **Google Gemini** (cloud, gratuito con límites)
- ✅ **Extracción exhaustiva** de marcas, modelos, porcentajes, montos, fechas, condiciones

### 📊 Selector Visual de Orden
- ✅ Visualización de reglas existentes por categoría
- ✅ Selección gráfica de posición para nueva regla
- ✅ Previsualización del ordenamiento final antes de guardar

### Tipos de Reglas (7)

| # | Tipo | Descripción | Ejemplo |
|---|------|-------------|---------|
| 1 | **📍 Fuente** | Portales de consulta de precios | Kavak, MercadoLibre, Autocosmos |
| 2 | **🔍 Filtro Búsqueda** | Parámetros de búsqueda | Marca, modelo, año ±2, km ±15000 |
| 3 | **💰 Ajuste Cálculo** | Modificación del precio final | +15%, -$50000, inflación, margen |
| 4 | **🧹 Depuración** | Eliminar publicaciones con ruido | Outliers, no verificados, antiguos |
| 5 | **📊 Muestreo** | Selección de muestra | 20 aleatorios, ordenados por precio |
| 6 | **⚠️ Punto Control** | Flujos condicionales | Si < 5 resultados, ampliar búsqueda |
| 7 | **📈 Método Valuación** | Cálculo de referencia | Mediana, promedio ponderado, percentil |

### Subtipos de Ajuste de Cálculo

| Subtipo | Descripción | Ejemplo de entrada |
|---------|-------------|-------------------|
| `ajuste_porcentual` | Porcentaje sobre el precio | "Aumentar 15% los Renault" |
| `ajuste_fijo` | Monto fijo en pesos | "Sumar $50000 a los Toyota" |
| `ajuste_fijo` (USD) | Monto fijo en dólares | "Restar 500 dólares" |
| `inflacion` | Ajuste por inflación | "Aplicar inflación del 5% mensual" |
| `margen_ganancia` | Margen de utilidad | "Margen del 12% mínimo $100000" |

### Trazabilidad
- 📝 Log de cada acción realizada
- 👤 Identificación del usuario en cada cambio
- 📅 Timestamps precisos
- 🔍 Comparación de versiones
- 💾 Snapshot completo de configuración en cada valuación

## 🚀 Instalación

### Requisitos
- Python 3.10+
- pip
- (Opcional) Ollama para IA local

### Pasos

```bash
# 1. Clonar o copiar el proyecto
cd valuacion_proyecto

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Opcional) Instalar Ollama para IA local
# Descargar de https://ollama.ai
ollama pull llama3.2  # o el modelo que prefieras

# 5. Iniciar el backend (desde la carpeta backend/api)
cd backend/api
uvicorn main:app --reload --port 8000

# 6. Cargar datos iniciales (en navegador o curl)
# http://localhost:8000/setup/inicial

# 7. En otra terminal, iniciar el frontend
cd frontend
streamlit run app.py --server.port 8501
```

### Configuración de Proveedores IA

| Proveedor | Configuración | Obtener API Key |
|-----------|---------------|-----------------|
| **Ollama** | Local, no requiere API key | [ollama.ai](https://ollama.ai) |
| **Groq** | API key en sidebar | [console.groq.com](https://console.groq.com) |
| **Gemini** | API key en sidebar | [aistudio.google.com](https://aistudio.google.com/app/apikey) |

## 📁 Estructura del Proyecto

```
valuacion_proyecto/
├── backend/
│   ├── models.py                    # Modelos SQLAlchemy (374 líneas)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── reglas_service.py        # CRUD + Auditoría (596 líneas)
│   │   └── agente_service.py        # Agente de valuación con Claude
│   └── api/
│       ├── main.py                  # API REST FastAPI (487 líneas)
│       └── valuacion.db             # Base de datos SQLite
├── frontend/
│   ├── app.py                       # Interfaz Streamlit v2.1 (1385 líneas)
│   ├── componentes/
│   │   └── formulario_parametros.py
│   └── servicios/
│       └── ia_gratuita.py           # Proveedores IA
├── Documentación/
│   ├── README.md
│   └── requirements.txt
└── venv/                            # Entorno virtual
```

## 🔌 API Endpoints

### Reglas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/reglas` | Lista todas las reglas (filtrable por tipo) |
| GET | `/reglas/{id}` | Obtiene una regla por ID |
| POST | `/reglas?usuario_id=xxx` | Crea una regla |
| PUT | `/reglas/{id}?usuario_id=xxx` | Modifica una regla |
| DELETE | `/reglas/{id}?usuario_id=xxx` | Elimina una regla |
| POST | `/reglas/{id}/restaurar?usuario_id=xxx` | Restaura una regla |

### Auditoría

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/reglas/{id}/historial` | Historial de versiones |
| GET | `/reglas/{id}/auditoria` | Auditoría de una regla |
| GET | `/auditoria` | Auditoría general del sistema |
| GET | `/reglas/{id}/comparar?version_a=1&version_b=2` | Compara dos versiones |

### Configuración

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/configuracion/actual` | Configuración activa en JSON |
| GET | `/configuracion/prompt` | Prompt generado para el agente |

### Usuarios

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/usuarios` | Lista usuarios |
| POST | `/usuarios` | Crea un usuario |

### Sistema

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Info de la API |
| GET | `/health` | Health check con conteo de reglas |
| POST | `/setup/inicial` | Carga configuración inicial de ejemplo |

## 📊 Ejemplos de Uso

### Crear regla desde lenguaje natural (Frontend)

**Entrada:** "Aumentar en 20000$ el precio de los autos Renault solo por el mes de enero de 2026"

**JSON Generado:**
```json
{
  "tipo": "ajuste_fijo",
  "monto": 20000,
  "moneda": "ARS",
  "operacion": "incrementar",
  "condicion_marca": "Renault",
  "periodo_vigencia": {
    "tipo": "mes",
    "mes": "enero",
    "año": 2026
  }
}
```

### Crear regla via API

```bash
curl -X POST "http://localhost:8000/reglas?usuario_id=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": "AJUSTE_RENAULT_ENERO",
    "nombre": "Aumento Renault Enero 2026",
    "tipo": "ajuste_calculo",
    "parametros": {
      "tipo": "ajuste_fijo",
      "monto": 20000,
      "moneda": "ARS",
      "operacion": "incrementar",
      "condicion_marca": "Renault",
      "periodo_vigencia": {
        "tipo": "mes",
        "mes": "enero",
        "año": 2026
      }
    },
    "descripcion": "Aumentar $20000 a Renault en enero 2026",
    "orden": 10
  }'
```

### Modificar una regla

```bash
curl -X PUT "http://localhost:8000/reglas/{regla_id}?usuario_id=admin" \
  -H "Content-Type: application/json" \
  -d '{
    "parametros": {"monto": 25000},
    "motivo_cambio": "Ajuste por inflación"
  }'
```

### Ver historial de cambios

```bash
curl "http://localhost:8000/reglas/{regla_id}/historial"
```

### Comparar versiones

```bash
curl "http://localhost:8000/reglas/{regla_id}/comparar?version_a=1&version_b=3"
```

## 🔄 Flujo de Trabajo

### Flujo de Creación de Regla (Frontend)

```
┌─────────────────────────────────────────────────────────────┐
│              FLUJO DE CREACIÓN DE REGLA v2.1                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Usuario escribe descripción en lenguaje natural         │
│           ↓                                                 │
│  2. Selecciona proveedor IA (Ollama/Groq/Gemini)           │
│           ↓                                                 │
│  3. Click en "Generar"                                      │
│           ↓                                                 │
│  4. IA analiza y detecta tipo de regla                      │
│           ↓                                                 │
│  5. IA genera JSON con todos los parámetros                 │
│           ↓                                                 │
│  6. Usuario ve tabla de reglas existentes del mismo tipo    │
│           ↓                                                 │
│  7. Usuario selecciona posición (orden) visualmente         │
│           ↓                                                 │
│  8. Previsualización del nuevo ordenamiento                 │
│           ↓                                                 │
│  9. Click en "Guardar" → Regla creada con auditoría         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Valuación

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO DE VALUACIÓN                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Vendedor ingresa datos del vehículo                     │
│           ↓                                                 │
│  2. Sistema carga reglas activas de la BD                   │
│           ↓                                                 │
│  3. Se construye prompt dinámico con las reglas             │
│           ↓                                                 │
│  4. Agente Claude ejecuta búsqueda web                      │
│           ↓                                                 │
│  5. Se aplican filtros y depuración según reglas            │
│           ↓                                                 │
│  6. Se calcula precio con métodos configurados              │
│           ↓                                                 │
│  7. Se guarda valuación con trazabilidad completa           │
│           ↓                                                 │
│  8. Vendedor recibe reporte + precio sugerido               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📝 Modelo de Auditoría

Cada cambio en una regla genera:

```json
{
  "id": "uuid",
  "regla_id": "uuid de la regla",
  "usuario_id": "uuid del usuario",
  "accion": "crear|modificar|eliminar|activar|desactivar|restaurar",
  "fecha": "2026-01-15T10:30:00",
  "valor_anterior": { ... },
  "valor_nuevo": { ... },
  "campos_modificados": ["parametros", "nombre"],
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "notas": "Motivo del cambio"
}
```

## 🔐 Seguridad

- Cada acción requiere `usuario_id`
- Se registra IP y User-Agent
- Eliminación lógica por defecto (preserva historial)
- Versionado inmutable de cambios

## 🛠️ Personalización

### Agregar nuevo tipo de regla

1. Agregar valor en `TipoRegla` enum (`backend/models.py`)
2. Agregar formateo en `agente_service.py`
3. Agregar al `PROMPT_GENERADOR` en `frontend/app.py`
4. Agregar a `TIPO_REGLA_LABELS` y `TIPO_REGLA_DESCRIPCIONES`

### Agregar nuevo proveedor de IA

1. Agregar configuración en sidebar (`frontend/app.py`)
2. Agregar caso en `generar_con_ia_generico()`

### Cambiar base de datos

Modificar `DATABASE_URL` en `backend/api/main.py`:
```python
# SQLite (default)
DATABASE_URL = "sqlite:///./valuacion.db"

# PostgreSQL
DATABASE_URL = "postgresql://user:pass@host/db"

# MySQL
DATABASE_URL = "mysql://user:pass@host/db"
```

## 🐛 Troubleshooting

### "Ollama no detectado"
```bash
# Verificar si Ollama está corriendo
curl http://localhost:11434/api/tags

# Si no responde, iniciar Ollama
ollama serve
```

### "Error: listen tcp 127.0.0.1:11434: bind: Solo se permite un uso..."
Ollama ya está corriendo. No necesitás ejecutar `ollama serve` de nuevo.

### "No se cargan las reglas"
1. Verificar que el backend esté corriendo: `http://localhost:8000/health`
2. Ejecutar setup inicial: `http://localhost:8000/setup/inicial`
3. Verificar la ubicación de `valuacion.db`

### Base de datos vacía
```bash
# Cargar datos iniciales
curl -X POST http://localhost:8000/setup/inicial
```

## 📌 Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| v2.1 | 2026-01 | Prompt expandido con escenarios de negocio |
| v2.0 | 2026-01 | Selector visual de orden |
| v1.9 | 2026-01 | Distinción ajuste_fijo vs ajuste_porcentual |
| v1.8 | 2026-01 | Prioridad IA sobre heurística |
| v1.0 | 2025-12 | Versión inicial |

## 📄 Licencia

MIT License

## 🤝 Contribuciones

PRs bienvenidos. Para cambios grandes, abrir issue primero.