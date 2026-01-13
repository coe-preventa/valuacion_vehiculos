# 🚗 Sistema de Valuación de Vehículos Usados

Sistema completo para asistir a vendedores en la valuación de vehículos usados, con reglas de negocio configurables y auditoría completa.

## 📋 Características

### Gestión de Reglas
- ✅ CRUD completo de reglas de negocio
- ✅ Versionado automático de cada cambio
- ✅ Auditoría completa (quién, cuándo, qué cambió)
- ✅ Restauración a versiones anteriores
- ✅ Comparación entre versiones

### Tipos de Reglas
1. **Fuentes de Datos**: URLs de sitios de venta (Kavak, ML, etc.)
2. **Filtros de Búsqueda**: Criterios para filtrar resultados (año, km, etc.)
3. **Depuración**: Reglas para eliminar outliers y resultados no confiables
4. **Muestreo**: Cómo seleccionar la muestra de resultados
5. **Puntos de Control**: Umbrales y acciones cuando no hay suficientes datos
6. **Métodos de Valuación**: Promedio, mediana, ponderado, etc.
7. **Ajustes de Cálculo**: Inflación, márgenes, indexación

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

### Pasos

```bash
# 1. Clonar o copiar el proyecto
cd valuacion_vehiculos

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API key de Anthropic (para valuaciones)
export ANTHROPIC_API_KEY="tu-api-key"

# 5. Iniciar el backend
cd backend/api
uvicorn main:app --reload --port 8000

# 6. En otra terminal, iniciar el frontend
cd frontend
streamlit run app.py --server.port 8501
```

## 📁 Estructura del Proyecto

```
valuacion_vehiculos/
├── backend/
│   ├── models.py              # Modelos de datos (SQLAlchemy)
│   ├── services/
│   │   ├── reglas_service.py  # Lógica de gestión de reglas
│   │   └── agente_service.py  # Agente de valuación con Claude
│   └── api/
│       └── main.py            # API REST (FastAPI)
├── frontend/
│   └── app.py                 # Interfaz web (Streamlit)
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Reglas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/reglas` | Lista todas las reglas |
| GET | `/reglas/{id}` | Obtiene una regla |
| POST | `/reglas` | Crea una regla |
| PUT | `/reglas/{id}` | Modifica una regla |
| DELETE | `/reglas/{id}` | Elimina una regla |
| POST | `/reglas/{id}/restaurar` | Restaura una regla |

### Auditoría

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/reglas/{id}/historial` | Historial de versiones |
| GET | `/reglas/{id}/auditoria` | Auditoría de una regla |
| GET | `/auditoria` | Auditoría general |
| GET | `/reglas/{id}/comparar` | Compara dos versiones |

### Configuración

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/configuracion/actual` | Config activa en JSON |
| GET | `/configuracion/prompt` | Prompt generado |

## 📊 Ejemplos de Uso

### Crear una regla de filtro

```bash
curl -X POST "http://localhost:8000/reglas?usuario_id=xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": "FILTRO_KM_AMPLIADO",
    "nombre": "Filtro de km ampliado",
    "tipo": "filtro_busqueda",
    "parametros": {
      "campo": "kilometraje",
      "operador": "entre",
      "valor": [-15000, 15000],
      "relativo": true
    },
    "orden": 5
  }'
```

### Modificar una regla

```bash
curl -X PUT "http://localhost:8000/reglas/{regla_id}?usuario_id=xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "parametros": {"valor": [-20000, 20000]},
    "motivo_cambio": "Ampliando rango por baja oferta"
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

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO DE VALUACIÓN                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Vendedor ingresa datos del vehículo                     │
│           ↓                                                  │
│  2. Sistema carga reglas activas de la BD                   │
│           ↓                                                  │
│  3. Se construye prompt dinámico con las reglas             │
│           ↓                                                  │
│  4. Agente Claude ejecuta búsqueda web                      │
│           ↓                                                  │
│  5. Se aplican filtros y depuración según reglas            │
│           ↓                                                  │
│  6. Se calcula precio con métodos configurados              │
│           ↓                                                  │
│  7. Se guarda valuación con trazabilidad completa           │
│           ↓                                                  │
│  8. Vendedor recibe reporte + precio sugerido               │
│                                                              │
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
  "fecha": "2024-01-15T10:30:00",
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

1. Agregar valor en `TipoRegla` enum (models.py)
2. Agregar formateo en `agente_service.py`
3. Agregar plantilla en frontend

### Cambiar base de datos

Modificar `DATABASE_URL` en `api/main.py`:
```python
DATABASE_URL = "postgresql://user:pass@host/db"
```

## 📄 Licencia

MIT License

## 🤝 Contribuciones

PRs bienvenidos. Para cambios grandes, abrir issue primero.
