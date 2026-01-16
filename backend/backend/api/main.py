# backend/api/main.py
"""
API REST para el sistema de valuación de vehículos.
Endpoints para gestión de reglas, usuarios y valuaciones.
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import sys
import os

# Agregar path del backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Usuario, Regla, HistorialRegla, AuditoriaRegla, 
    Vehiculo, Valuacion, TipoRegla, TipoAccion,
    crear_tablas
)
from services.reglas_service import ReglasService
from services.agente_service import AgenteValuacionService, GeneradorPromptDinamico


# ============================================
# CONFIGURACIÓN
# ============================================

DATABASE_URL = "sqlite:///./valuacion.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

crear_tablas(engine)

app = FastAPI(
    title="API Valuación de Vehículos",
    description="Sistema de valuación con reglas dinámicas y auditoría completa",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# SCHEMAS
# ============================================

class TipoReglaEnum(str, Enum):
    fuente = "fuente"
    filtro_busqueda = "filtro_busqueda"
    depuracion = "depuracion"
    muestreo = "muestreo"
    punto_control = "punto_control"
    metodo_valuacion = "metodo_valuacion"
    ajuste_calculo = "ajuste_calculo"


class ReglaCreate(BaseModel):
    codigo: str = Field(..., example="FILTRO_AÑO_RANGO")
    nombre: str = Field(..., example="Filtro de rango de años")
    tipo: TipoReglaEnum
    parametros: Dict[str, Any]
    descripcion: Optional[str] = None
    orden: int = 0


class ReglaUpdate(BaseModel):
    nombre: Optional[str] = None
    parametros: Optional[Dict[str, Any]] = None
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None
    motivo_cambio: Optional[str] = None


class ReglaResponse(BaseModel):
    id: str
    codigo: str
    nombre: str
    tipo: str
    parametros: Dict[str, Any]
    descripcion: Optional[str]
    activo: bool
    orden: int
    version: int
    creado_por: str
    fecha_creacion: datetime
    modificado_por: Optional[str]
    fecha_modificacion: Optional[datetime]

    class Config:
        from_attributes = True


class AuditoriaResponse(BaseModel):
    id: str
    regla_id: str
    usuario_id: str
    usuario_nombre: Optional[str]
    accion: str
    fecha: datetime
    campos_modificados: Optional[List[str]]
    valor_anterior: Optional[Dict]
    valor_nuevo: Optional[Dict]
    notas: Optional[str]


class UsuarioCreate(BaseModel):
    email: str
    nombre: str
    apellido: str
    rol: str = "vendedor"


class VehiculoValuar(BaseModel):
    marca: str
    modelo: str
    año: int = Field(..., ge=1990, le=2030)
    kilometraje: int = Field(..., ge=0)
    version: Optional[str] = None
    transmision: Optional[str] = None
    combustible: Optional[str] = None


# ============================================
# ENDPOINTS - REGLAS
# ============================================

@app.get("/")
async def root():
    return {"nombre": "API Valuación de Vehículos", "version": "1.0.0"}


@app.post("/reglas", response_model=ReglaResponse, tags=["Reglas"])
async def crear_regla(
    regla: ReglaCreate,
    request: Request,
    usuario_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Crea una nueva regla con auditoría"""
    service = ReglasService(db)
    
    try:
        nueva = service.crear_regla(
            codigo=regla.codigo,
            nombre=regla.nombre,
            tipo=TipoRegla(regla.tipo.value),
            parametros=regla.parametros,
            usuario_id=usuario_id,
            descripcion=regla.descripcion,
            orden=regla.orden,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        return ReglaResponse(
            id=nueva.id, codigo=nueva.codigo, nombre=nueva.nombre,
            tipo=nueva.tipo.value, parametros=nueva.parametros,
            descripcion=nueva.descripcion, activo=nueva.activo,
            orden=nueva.orden, version=nueva.version,
            creado_por=nueva.creado_por, fecha_creacion=nueva.fecha_creacion,
            modificado_por=nueva.modificado_por, fecha_modificacion=nueva.fecha_modificacion
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reglas", response_model=List[ReglaResponse], tags=["Reglas"])
async def listar_reglas(
    tipo: Optional[TipoReglaEnum] = None,
    solo_activas: bool = True,
    db: Session = Depends(get_db)
):
    """Lista reglas con filtros"""
    service = ReglasService(db)
    tipo_filtro = TipoRegla(tipo.value) if tipo else None
    reglas = service.listar_reglas(tipo=tipo_filtro, solo_activas=solo_activas)
    
    return [ReglaResponse(
        id=r.id, codigo=r.codigo, nombre=r.nombre, tipo=r.tipo.value,
        parametros=r.parametros, descripcion=r.descripcion, activo=r.activo,
        orden=r.orden, version=r.version, creado_por=r.creado_por,
        fecha_creacion=r.fecha_creacion, modificado_por=r.modificado_por,
        fecha_modificacion=r.fecha_modificacion
    ) for r in reglas]


@app.get("/reglas/{regla_id}", response_model=ReglaResponse, tags=["Reglas"])
async def obtener_regla(regla_id: str, db: Session = Depends(get_db)):
    """Obtiene una regla por ID"""
    service = ReglasService(db)
    regla = service.obtener_regla(regla_id)
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return ReglaResponse(
        id=regla.id, codigo=regla.codigo, nombre=regla.nombre, tipo=regla.tipo.value,
        parametros=regla.parametros, descripcion=regla.descripcion, activo=regla.activo,
        orden=regla.orden, version=regla.version, creado_por=regla.creado_por,
        fecha_creacion=regla.fecha_creacion, modificado_por=regla.modificado_por,
        fecha_modificacion=regla.fecha_modificacion
    )


@app.put("/reglas/{regla_id}", response_model=ReglaResponse, tags=["Reglas"])
async def modificar_regla(
    regla_id: str,
    cambios: ReglaUpdate,
    request: Request,
    usuario_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Modifica una regla (guarda versión anterior y auditoría)"""
    service = ReglasService(db)
    cambios_dict = {k: v for k, v in cambios.model_dump().items() if v is not None and k != "motivo_cambio"}
    
    if not cambios_dict:
        raise HTTPException(status_code=400, detail="No hay cambios")
    
    try:
        regla = service.modificar_regla(
            regla_id=regla_id,
            usuario_id=usuario_id,
            cambios=cambios_dict,
            motivo_cambio=cambios.motivo_cambio,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        return ReglaResponse(
            id=regla.id, codigo=regla.codigo, nombre=regla.nombre, tipo=regla.tipo.value,
            parametros=regla.parametros, descripcion=regla.descripcion, activo=regla.activo,
            orden=regla.orden, version=regla.version, creado_por=regla.creado_por,
            fecha_creacion=regla.fecha_creacion, modificado_por=regla.modificado_por,
            fecha_modificacion=regla.fecha_modificacion
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/reglas/{regla_id}", tags=["Reglas"])
async def eliminar_regla(
    regla_id: str,
    request: Request,
    usuario_id: str = Query(...),
    fisico: bool = False,
    motivo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Elimina una regla (lógica o física)"""
    service = ReglasService(db)
    try:
        service.eliminar_regla(
            regla_id=regla_id,
            usuario_id=usuario_id,
            motivo=motivo,
            eliminacion_fisica=fisico,
            ip_address=request.client.host if request.client else None
        )
        return {"mensaje": "Eliminada", "tipo": "física" if fisico else "lógica"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/reglas/{regla_id}/restaurar", response_model=ReglaResponse, tags=["Reglas"])
async def restaurar_regla(
    regla_id: str,
    request: Request,
    usuario_id: str = Query(...),
    version: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Restaura una regla a versión anterior"""
    service = ReglasService(db)
    try:
        regla = service.restaurar_regla(
            regla_id=regla_id,
            usuario_id=usuario_id,
            version=version,
            ip_address=request.client.host if request.client else None
        )
        return ReglaResponse(
            id=regla.id, codigo=regla.codigo, nombre=regla.nombre, tipo=regla.tipo.value,
            parametros=regla.parametros, descripcion=regla.descripcion, activo=regla.activo,
            orden=regla.orden, version=regla.version, creado_por=regla.creado_por,
            fecha_creacion=regla.fecha_creacion, modificado_por=regla.modificado_por,
            fecha_modificacion=regla.fecha_modificacion
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================
# ENDPOINTS - AUDITORÍA
# ============================================

@app.get("/reglas/{regla_id}/historial", tags=["Auditoría"])
async def obtener_historial(regla_id: str, db: Session = Depends(get_db)):
    """Historial de versiones de una regla"""
    service = ReglasService(db)
    historial = service.obtener_historial_regla(regla_id)
    return [{
        "version": h.version,
        "nombre": h.nombre,
        "parametros": h.parametros,
        "activo": h.activo,
        "modificado_por": h.modificado_por,
        "fecha": h.fecha.isoformat(),
        "motivo": h.motivo_cambio
    } for h in historial]


@app.get("/reglas/{regla_id}/auditoria", response_model=List[AuditoriaResponse], tags=["Auditoría"])
async def obtener_auditoria_regla(regla_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Auditoría de una regla específica"""
    service = ReglasService(db)
    auditorias = service.obtener_auditoria_regla(regla_id=regla_id, limit=limit)
    return [AuditoriaResponse(
        id=a.id, regla_id=a.regla_id, usuario_id=a.usuario_id,
        usuario_nombre=a.usuario.nombre_completo if a.usuario else None,
        accion=a.accion.value, fecha=a.fecha,
        campos_modificados=a.campos_modificados,
        valor_anterior=a.valor_anterior, valor_nuevo=a.valor_nuevo,
        notas=a.notas
    ) for a in auditorias]


@app.get("/auditoria", response_model=List[AuditoriaResponse], tags=["Auditoría"])
async def listar_auditoria_general(
    usuario_id: Optional[str] = None,
    accion: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Auditoría general del sistema"""
    service = ReglasService(db)
    accion_enum = TipoAccion(accion) if accion else None
    auditorias = service.obtener_auditoria_regla(
        usuario_id=usuario_id, accion=accion_enum,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, limit=limit
    )
    return [AuditoriaResponse(
        id=a.id, regla_id=a.regla_id, usuario_id=a.usuario_id,
        usuario_nombre=a.usuario.nombre_completo if a.usuario else None,
        accion=a.accion.value, fecha=a.fecha,
        campos_modificados=a.campos_modificados,
        valor_anterior=a.valor_anterior, valor_nuevo=a.valor_nuevo,
        notas=a.notas
    ) for a in auditorias]


@app.get("/reglas/{regla_id}/comparar", tags=["Auditoría"])
async def comparar_versiones(
    regla_id: str,
    version_a: int,
    version_b: int,
    db: Session = Depends(get_db)
):
    """Compara dos versiones de una regla"""
    service = ReglasService(db)
    try:
        return service.comparar_versiones(regla_id, version_a, version_b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================
# ENDPOINTS - CONFIGURACIÓN
# ============================================

@app.get("/configuracion/actual", tags=["Configuración"])
async def obtener_config_actual(db: Session = Depends(get_db)):
    """Configuración actual basada en reglas activas"""
    service = ReglasService(db)
    return service.generar_configuracion_prompt()


@app.get("/configuracion/prompt", tags=["Configuración"])
async def obtener_prompt(db: Session = Depends(get_db)):
    """Genera el prompt completo para el agente"""
    generador = GeneradorPromptDinamico(db)
    return {"prompt": generador.generar_prompt_completo()}


# ============================================
# ENDPOINTS - USUARIOS
# ============================================

@app.post("/usuarios", tags=["Usuarios"])
async def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Crea un usuario"""
    nuevo = Usuario(
        email=usuario.email, nombre=usuario.nombre,
        apellido=usuario.apellido, rol=usuario.rol
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"id": nuevo.id, "email": nuevo.email, "nombre_completo": nuevo.nombre_completo}


@app.get("/usuarios", tags=["Usuarios"])
async def listar_usuarios(db: Session = Depends(get_db)):
    """Lista usuarios"""
    usuarios = db.query(Usuario).all()
    return [{"id": u.id, "email": u.email, "nombre": u.nombre_completo, "rol": u.rol} for u in usuarios]


# ============================================
# SETUP INICIAL
# ============================================

@app.post("/setup/inicial", tags=["Setup"])
async def setup_inicial(db: Session = Depends(get_db)):
    """Carga configuración inicial de ejemplo"""
    
    # Verificar si ya existe
    if db.query(Usuario).first():
        return {"mensaje": "Ya existe configuración inicial"}
    
    # Crear admin
    admin = Usuario(email="admin@empresa.com", nombre="Admin", apellido="Sistema", rol="admin")
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    service = ReglasService(db)
    
    reglas_iniciales = [
        ("FUENTE_KAVAK", "Kavak", TipoRegla.FUENTE, {"url": "kavak.com", "prioridad": 1}, 1),
        ("FUENTE_ML", "Mercado Libre", TipoRegla.FUENTE, {"url": "autos.mercadolibre.com.ar", "prioridad": 2}, 2),
        ("FUENTE_AUTOCOSMOS", "Autocosmos", TipoRegla.FUENTE, {"url": "autocosmos.com.ar", "prioridad": 3}, 3),
        ("FILTRO_MARCA", "Marca exacta", TipoRegla.FILTRO_BUSQUEDA, {"campo": "marca", "operador": "igual"}, 1),
        ("FILTRO_MODELO", "Modelo exacto", TipoRegla.FILTRO_BUSQUEDA, {"campo": "modelo", "operador": "igual"}, 2),
        ("FILTRO_AÑO", "Año ±1", TipoRegla.FILTRO_BUSQUEDA, {"campo": "año", "operador": "entre", "valor": [-1, 1], "relativo": True}, 3),
        ("FILTRO_KM", "Km ±10000", TipoRegla.FILTRO_BUSQUEDA, {"campo": "km", "operador": "entre", "valor": [-10000, 10000], "relativo": True}, 4),
        ("DEPURAR_BAJOS", "Eliminar 5 más baratos", TipoRegla.DEPURACION, {"accion": "eliminar", "cantidad": 5, "extremo": "inferior"}, 1),
        ("DEPURAR_ALTOS", "Eliminar 5 más caros", TipoRegla.DEPURACION, {"accion": "eliminar", "cantidad": 5, "extremo": "superior"}, 2),
        ("DEPURAR_NO_VERIFICADOS", "Eliminar no verificados", TipoRegla.DEPURACION, {"accion": "eliminar", "criterio": "usuario_no_verificado"}, 3),
        ("MUESTREO_20", "Tomar 20 aleatorios", TipoRegla.MUESTREO, {"metodo": "aleatorio", "cantidad": 20}, 1),
        ("CONTROL_MIN_5", "Mínimo 5 resultados", TipoRegla.PUNTO_CONTROL, {"umbral_minimo": 5, "accion": "ampliar", "nuevos_parametros": {"año": [-2, 2], "km": [-15000, 15000]}}, 1),
        ("METODO_MEDIANA", "Usar mediana", TipoRegla.METODO_VALUACION, {"metodo": "mediana"}, 1),
        ("AJUSTE_INFLACION", "Inflación 5% a 30 días", TipoRegla.AJUSTE_CALCULO, {"tipo": "inflacion", "porcentaje": 5, "periodo_dias": 30}, 1),
    ]
    
    for codigo, nombre, tipo, params, orden in reglas_iniciales:
        try:
            service.crear_regla(
                codigo=codigo, nombre=nombre, tipo=tipo,
                parametros=params, usuario_id=admin.id, orden=orden,
                notas="Configuración inicial"
            )
        except:
            pass
    
    return {"mensaje": "Setup completado", "admin_id": admin.id}


@app.get("/health", tags=["General"])
async def health(db: Session = Depends(get_db)):
    """Health check"""
    count = db.query(Regla).filter(Regla.activo == True).count()
    return {"status": "ok", "reglas_activas": count, "timestamp": datetime.utcnow().isoformat()}


# Para ejecutar: uvicorn main:app --reload --port 8000
