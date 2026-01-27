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


# ============================================
# ENDPOINTS - VEHÍCULOS
# ============================================

@app.post("/vehiculos", tags=["Vehículos"])
async def crear_vehiculo(vehiculo: VehiculoValuar, db: Session = Depends(get_db)):
    """Crea un vehículo para valuar"""
    nuevo = Vehiculo(
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        año=vehiculo.año,
        kilometraje=vehiculo.kilometraje,
        version=vehiculo.version,
        transmision=vehiculo.transmision,
        combustible=vehiculo.combustible
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {
        "id": nuevo.id,
        "marca": nuevo.marca,
        "modelo": nuevo.modelo,
        "año": nuevo.año,
        "kilometraje": nuevo.kilometraje
    }


@app.get("/vehiculos", tags=["Vehículos"])
async def listar_vehiculos(
    estado: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Lista vehículos"""
    query = db.query(Vehiculo)
    if estado:
        query = query.filter(Vehiculo.estado == estado)
    vehiculos = query.order_by(Vehiculo.fecha_creacion.desc()).limit(limit).all()
    return [{
        "id": v.id,
        "marca": v.marca,
        "modelo": v.modelo,
        "año": v.año,
        "kilometraje": v.kilometraje,
        "version": v.version,
        "estado": v.estado,
        "valuaciones_count": len(v.valuaciones)
    } for v in vehiculos]


@app.get("/vehiculos/{vehiculo_id}", tags=["Vehículos"])
async def obtener_vehiculo(vehiculo_id: str, db: Session = Depends(get_db)):
    """Obtiene un vehículo por ID"""
    vehiculo = db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return {
        "id": vehiculo.id,
        "marca": vehiculo.marca,
        "modelo": vehiculo.modelo,
        "año": vehiculo.año,
        "kilometraje": vehiculo.kilometraje,
        "version": vehiculo.version,
        "transmision": vehiculo.transmision,
        "combustible": vehiculo.combustible,
        "color": vehiculo.color,
        "estado": vehiculo.estado,
        "fecha_creacion": vehiculo.fecha_creacion
    }


# ============================================
# ENDPOINTS - VALUACIONES
# ============================================

class ValuacionRequest(BaseModel):
    vehiculo_id: Optional[str] = None
    # O datos directos del vehículo
    marca: Optional[str] = None
    modelo: Optional[str] = None
    año: Optional[int] = None
    kilometraje: Optional[int] = None
    version: Optional[str] = None
    transmision: Optional[str] = None
    combustible: Optional[str] = None
    # Proveedor IA
    proveedor_ia: str = "mock"  # mock, ollama, groq, gemini
    modelo_ia: Optional[str] = None
    api_key_ia: Optional[str] = None


class ValuacionResponse(BaseModel):
    id: str
    vehiculo: Dict[str, Any]
    precio_sugerido: Optional[float]
    precio_minimo: Optional[float]
    precio_maximo: Optional[float]
    confianza: Optional[str]
    analisis: Dict[str, Any]
    reglas_aplicadas: List[Dict]
    publicaciones: List[Dict]
    alertas: List[str]
    reporte: Optional[str]
    duracion_segundos: Optional[float]
    fecha: datetime


@app.post("/valuaciones", tags=["Valuaciones"])
async def crear_valuacion(
    request: ValuacionRequest,
    usuario_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Ejecuta una valuación completa.
    Puede recibir un vehiculo_id existente o los datos del vehículo directamente.
    """
    # Obtener o crear vehículo
    if request.vehiculo_id:
        vehiculo = db.query(Vehiculo).filter(Vehiculo.id == request.vehiculo_id).first()
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    elif request.marca and request.modelo and request.año and request.kilometraje:
        vehiculo = Vehiculo(
            marca=request.marca,
            modelo=request.modelo,
            año=request.año,
            kilometraje=request.kilometraje,
            version=request.version,
            transmision=request.transmision,
            combustible=request.combustible
        )
        db.add(vehiculo)
        db.flush()
    else:
        raise HTTPException(
            status_code=400, 
            detail="Debe proporcionar vehiculo_id o los datos del vehículo (marca, modelo, año, kilometraje)"
        )
    
    # Obtener configuración de reglas
    service = ReglasService(db)
    config = service.generar_configuracion_prompt()
    
    # Ejecutar valuación según proveedor
    import time
    inicio = time.time()
    
    if request.proveedor_ia == "mock":
        # Valuación de prueba/demo sin IA real
        resultado = ejecutar_valuacion_mock(vehiculo, config)
    else:
        # Valuación con IA real
        resultado = await ejecutar_valuacion_ia(
            vehiculo=vehiculo,
            config=config,
            proveedor=request.proveedor_ia,
            modelo=request.modelo_ia,
            api_key=request.api_key_ia
        )
    
    duracion = time.time() - inicio
    
    # Guardar valuación
    valuacion = Valuacion(
        vehiculo_id=vehiculo.id,
        usuario_id=usuario_id,
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
        duracion_segundos=duracion
    )
    
    db.add(valuacion)
    db.commit()
    db.refresh(valuacion)
    
    return {
        "id": valuacion.id,
        "vehiculo": {
            "id": vehiculo.id,
            "marca": vehiculo.marca,
            "modelo": vehiculo.modelo,
            "año": vehiculo.año,
            "kilometraje": vehiculo.kilometraje
        },
        "precio_sugerido": valuacion.precio_sugerido,
        "precio_minimo": valuacion.precio_minimo,
        "precio_maximo": valuacion.precio_maximo,
        "confianza": valuacion.confianza,
        "analisis": resultado.get("analisis", {}),
        "reglas_aplicadas": valuacion.reglas_aplicadas,
        "publicaciones": valuacion.publicaciones_analizadas,
        "alertas": resultado.get("alertas", []),
        "reporte": valuacion.reporte_completo,
        "duracion_segundos": valuacion.duracion_segundos,
        "fecha": valuacion.fecha
    }


@app.get("/valuaciones", tags=["Valuaciones"])
async def listar_valuaciones(
    vehiculo_id: Optional[str] = None,
    usuario_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Lista valuaciones con filtros"""
    query = db.query(Valuacion)
    if vehiculo_id:
        query = query.filter(Valuacion.vehiculo_id == vehiculo_id)
    if usuario_id:
        query = query.filter(Valuacion.usuario_id == usuario_id)
    
    valuaciones = query.order_by(Valuacion.fecha.desc()).limit(limit).all()
    
    return [{
        "id": v.id,
        "vehiculo": {
            "marca": v.vehiculo.marca,
            "modelo": v.vehiculo.modelo,
            "año": v.vehiculo.año
        } if v.vehiculo else None,
        "precio_sugerido": v.precio_sugerido,
        "confianza": v.confianza,
        "fecha": v.fecha,
        "duracion_segundos": v.duracion_segundos
    } for v in valuaciones]


@app.get("/valuaciones/{valuacion_id}", tags=["Valuaciones"])
async def obtener_valuacion(valuacion_id: str, db: Session = Depends(get_db)):
    """Obtiene detalle completo de una valuación"""
    valuacion = db.query(Valuacion).filter(Valuacion.id == valuacion_id).first()
    if not valuacion:
        raise HTTPException(status_code=404, detail="Valuación no encontrada")
    
    return {
        "id": valuacion.id,
        "vehiculo": {
            "id": valuacion.vehiculo.id,
            "marca": valuacion.vehiculo.marca,
            "modelo": valuacion.vehiculo.modelo,
            "año": valuacion.vehiculo.año,
            "kilometraje": valuacion.vehiculo.kilometraje,
            "version": valuacion.vehiculo.version
        } if valuacion.vehiculo else None,
        "precio_sugerido": valuacion.precio_sugerido,
        "precio_minimo": valuacion.precio_minimo,
        "precio_maximo": valuacion.precio_maximo,
        "confianza": valuacion.confianza,
        "analisis": {
            "fuentes_consultadas": valuacion.fuentes_consultadas,
            "resultados_encontrados": valuacion.resultados_encontrados,
            "resultados_filtrados": valuacion.resultados_filtrados,
            "precio_mercado_min": valuacion.precio_mercado_minimo,
            "precio_mercado_max": valuacion.precio_mercado_maximo,
            "precio_mercado_promedio": valuacion.precio_mercado_promedio,
            "precio_mercado_mediana": valuacion.precio_mercado_mediana
        },
        "reglas_aplicadas": valuacion.reglas_aplicadas,
        "configuracion_usada": valuacion.configuracion_usada,
        "publicaciones": valuacion.publicaciones_analizadas,
        "reporte": valuacion.reporte_completo,
        "duracion_segundos": valuacion.duracion_segundos,
        "fecha": valuacion.fecha
    }


# ============================================
# FUNCIONES DE VALUACIÓN
# ============================================

def ejecutar_valuacion_mock(vehiculo: Vehiculo, config: Dict) -> Dict[str, Any]:
    """
    Valuación de demostración sin IA real.
    Útil para testing y desarrollo.
    """
    import random
    
    # Precio base según año y marca (simplificado)
    precio_base = 15000000  # $15M base
    
    # Ajuste por año
    años_antiguedad = 2026 - vehiculo.año
    precio_base -= años_antiguedad * 1000000
    
    # Ajuste por km
    precio_base -= (vehiculo.kilometraje // 10000) * 200000
    
    # Variación aleatoria ±10%
    variacion = random.uniform(-0.1, 0.1)
    precio_base = int(precio_base * (1 + variacion))
    
    # Aplicar ajustes de config
    ajustes = config.get("ajustes_calculo", [])
    for ajuste in ajustes:
        params = ajuste.get("parametros", {})
        tipo = params.get("tipo", "")
        
        if tipo == "inflacion":
            porcentaje = params.get("porcentaje", 0)
            precio_base = int(precio_base * (1 + porcentaje / 100))
        elif tipo == "ajuste_porcentual":
            porcentaje = params.get("porcentaje", 0)
            operacion = params.get("operacion", "incrementar")
            if operacion == "incrementar":
                precio_base = int(precio_base * (1 + porcentaje / 100))
            else:
                precio_base = int(precio_base * (1 - porcentaje / 100))
        elif tipo == "ajuste_fijo":
            monto = params.get("monto", 0)
            operacion = params.get("operacion", "incrementar")
            if operacion == "incrementar":
                precio_base += monto
            else:
                precio_base -= monto
    
    precio_min = int(precio_base * 0.9)
    precio_max = int(precio_base * 1.1)
    
    # Generar publicaciones mock
    publicaciones = []
    fuentes = config.get("fuentes", [])
    for i, fuente in enumerate(fuentes[:3]):
        params = fuente.get("parametros", {})
        for j in range(random.randint(3, 7)):
            publicaciones.append({
                "fuente": params.get("url", f"fuente_{i}"),
                "precio": int(precio_base * random.uniform(0.85, 1.15)),
                "url": f"https://{params.get('url', 'example.com')}/auto/{j}",
                "incluida": j < 5
            })
    
    return {
        "precio_sugerido": precio_base,
        "precio_minimo": precio_min,
        "precio_maximo": precio_max,
        "confianza": "MEDIA",
        "analisis": {
            "fuentes_consultadas": len(fuentes),
            "resultados_iniciales": len(publicaciones),
            "resultados_tras_filtrado": len([p for p in publicaciones if p["incluida"]]),
            "resultados_tras_depuracion": len([p for p in publicaciones if p["incluida"]]),
            "precio_mercado_min": min([p["precio"] for p in publicaciones]) if publicaciones else 0,
            "precio_mercado_max": max([p["precio"] for p in publicaciones]) if publicaciones else 0,
            "precio_mercado_promedio": sum([p["precio"] for p in publicaciones]) // len(publicaciones) if publicaciones else 0,
            "precio_mercado_mediana": sorted([p["precio"] for p in publicaciones])[len(publicaciones)//2] if publicaciones else 0
        },
        "reglas_aplicadas": [
            {"codigo": r.get("codigo", ""), "resultado": f"Aplicado: {r.get('nombre', '')}"} 
            for r in config.get("ajustes_calculo", [])
        ],
        "publicaciones": publicaciones,
        "alertas": ["⚠️ Valuación MOCK - Solo para demostración"],
        "reporte_detallado": f"""
# Reporte de Valuación (DEMO)

## Vehículo
- **Marca:** {vehiculo.marca}
- **Modelo:** {vehiculo.modelo}
- **Año:** {vehiculo.año}
- **Kilometraje:** {vehiculo.kilometraje:,} km

## Resultado
- **Precio Sugerido:** ${precio_base:,}
- **Rango:** ${precio_min:,} - ${precio_max:,}
- **Confianza:** MEDIA

## Fuentes Consultadas
{len(fuentes)} fuentes configuradas

## Nota
Esta es una valuación de demostración. Para resultados reales, configure un proveedor de IA.
"""
    }


async def ejecutar_valuacion_ia(
    vehiculo: Vehiculo,
    config: Dict,
    proveedor: str,
    modelo: Optional[str],
    api_key: Optional[str]
) -> Dict[str, Any]:
    """
    Ejecuta valuación con IA real (Ollama, Groq, Gemini).
    """
    import httpx
    import json
    
    # Construir prompt
    prompt = construir_prompt_valuacion(vehiculo, config)
    
    try:
        if proveedor == "ollama":
            return await valuacion_ollama(prompt, modelo or "llama3.2")
        elif proveedor == "groq":
            return await valuacion_groq(prompt, modelo or "llama-3.3-70b-versatile", api_key)
        elif proveedor == "gemini":
            return await valuacion_gemini(prompt, modelo or "gemini-2.0-flash", api_key)
        else:
            raise ValueError(f"Proveedor no soportado: {proveedor}")
    except Exception as e:
        return {
            "precio_sugerido": None,
            "confianza": "BAJA",
            "alertas": [f"Error en valuación IA: {str(e)}"],
            "reporte_detallado": f"Error: {str(e)}"
        }


def construir_prompt_valuacion(vehiculo: Vehiculo, config: Dict) -> str:
    """Construye el prompt para la valuación"""
    
    fuentes = config.get("fuentes", [])
    fuentes_texto = "\n".join([
        f"  - {f.get('parametros', {}).get('url', 'N/A')}" 
        for f in fuentes
    ]) or "  - kavak.com.ar\n  - autos.mercadolibre.com.ar"
    
    ajustes = config.get("ajustes_calculo", [])
    ajustes_texto = "\n".join([
        f"  - {a.get('nombre', 'Ajuste')}: {a.get('parametros', {})}"
        for a in ajustes
    ]) or "  - Sin ajustes configurados"
    
    return f"""
Eres un experto en valuación de vehículos usados en Argentina. Tu tarea es buscar precios REALES y actuales.

VEHÍCULO A VALUAR:
- Marca: {vehiculo.marca}
- Modelo: {vehiculo.modelo}
- Año: {vehiculo.año}
- Kilometraje: {vehiculo.kilometraje:,} km
- Versión: {vehiculo.version or 'No especificada'}
- Transmisión: {vehiculo.transmision or 'No especificada'}
- Combustible: {vehiculo.combustible or 'No especificado'}

INSTRUCCIONES IMPORTANTES:
1. BUSCA en internet precios actuales de {vehiculo.marca} {vehiculo.modelo} {vehiculo.año} en Argentina
2. Consulta sitios como Kavak, MercadoLibre Autos, DeMotores, AutoCosmos
3. Busca publicaciones con características similares (año ±1, km similares)
4. Recopila al menos 5-10 precios de publicaciones reales
5. Calcula el precio promedio, mediana, mínimo y máximo del mercado

FUENTES PRIORITARIAS:
{fuentes_texto}

AJUSTES A APLICAR DESPUÉS DEL CÁLCULO:
{ajustes_texto}

PROCESO:
1. Buscar "{vehiculo.marca} {vehiculo.modelo} {vehiculo.año} precio Argentina"
2. Buscar en "kavak.com {vehiculo.marca} {vehiculo.modelo}"
3. Buscar en "autos.mercadolibre.com.ar {vehiculo.marca} {vehiculo.modelo} {vehiculo.año}"
4. Recopilar precios encontrados
5. Calcular estadísticas
6. Aplicar ajustes configurados

Responde ÚNICAMENTE con un JSON válido:

{{
    "precio_sugerido": <número entero en pesos argentinos>,
    "precio_minimo": <número entero>,
    "precio_maximo": <número entero>,
    "confianza": "ALTA|MEDIA|BAJA",
    "analisis": {{
        "fuentes_consultadas": <número de sitios consultados>,
        "resultados_iniciales": <número de publicaciones encontradas>,
        "resultados_tras_filtrado": <publicaciones que coinciden>,
        "precio_mercado_min": <precio más bajo encontrado>,
        "precio_mercado_max": <precio más alto encontrado>,
        "precio_mercado_promedio": <promedio de precios>,
        "precio_mercado_mediana": <mediana de precios>
    }},
    "reglas_aplicadas": [
        {{"codigo": "BUSQUEDA_WEB", "resultado": "Se buscaron precios en X sitios"}},
        {{"codigo": "FILTRO_AÑO", "resultado": "Se filtraron vehículos año {vehiculo.año} ±1"}},
        {{"codigo": "AJUSTE_APLICADO", "resultado": "descripción del ajuste"}}
    ],
    "publicaciones": [
        {{"fuente": "Kavak", "precio": 15000000, "url": "https://...", "titulo": "descripción", "incluida": true}},
        {{"fuente": "MercadoLibre", "precio": 14500000, "url": "https://...", "titulo": "descripción", "incluida": true}}
    ],
    "alertas": ["alertas o advertencias"],
    "reporte_detallado": "Resumen detallado del análisis realizado, fuentes consultadas y cómo se llegó al precio sugerido"
}}

IMPORTANTE: Incluye las publicaciones reales que encuentres con sus precios y URLs.
Responde SOLO con el JSON, sin texto adicional ni markdown.
"""


async def valuacion_ollama(prompt: str, modelo: str) -> Dict[str, Any]:
    """Ejecuta valuación con Ollama local"""
    import httpx
    import json
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": modelo,
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Error Ollama: {response.status_code}")
        
        data = response.json()
        texto = data.get("response", "")
        
        return extraer_json_respuesta(texto)


async def valuacion_groq(prompt: str, modelo: str, api_key: str) -> Dict[str, Any]:
    """Ejecuta valuación con Groq"""
    import httpx
    import json
    
    if not api_key:
        raise ValueError("API key de Groq requerida")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": modelo,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Error Groq: {response.status_code} - {response.text}")
        
        data = response.json()
        texto = data["choices"][0]["message"]["content"]
        
        return extraer_json_respuesta(texto)


async def valuacion_gemini(prompt: str, modelo: str, api_key: str) -> Dict[str, Any]:
    """Ejecuta valuación con Google Gemini + Google Search"""
    import httpx
    import json
    
    if not api_key:
        raise ValueError("API key de Gemini requerida")
    
    # Mapear nombres de modelos a los nombres correctos de la API
    modelos_map = {
        "gemini-2.0-flash": "gemini-2.0-flash",
        "gemini-2.0-flash-exp": "gemini-2.0-flash-exp", 
        "gemini-1.5-flash": "gemini-1.5-flash",
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-2.5-pro": "gemini-2.5-pro",
        "gemini-3-flash-preview": "gemini-3-flash-preview",
        "gemini-3-pro-preview": "gemini-3-pro-preview",
    }
    
    modelo_api = modelos_map.get(modelo, modelo)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Usar generateContent con Google Search grounding
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_api}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 4000
                    },
                    "tools": [{
                        "google_search": {}
                    }]
                }
            )
            
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("error", {}).get("message", response.text)
                except:
                    pass
                
                # Si falla con search, intentar sin search
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_api}:generateContent?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 4000
                        }
                    }
                )
                
                if response.status_code != 200:
                    return {
                        "precio_sugerido": None,
                        "confianza": "BAJA",
                        "alertas": [f"Error Gemini ({response.status_code}): {error_detail}"],
                        "reporte_detallado": f"Error al llamar a Gemini: {error_detail}"
                    }
            
            data = response.json()
            
            # Verificar si hay candidatos en la respuesta
            if not data.get("candidates"):
                return {
                    "precio_sugerido": None,
                    "confianza": "BAJA", 
                    "alertas": ["Gemini no devolvió respuesta válida"],
                    "reporte_detallado": f"Respuesta vacía de Gemini: {json.dumps(data)}"
                }
            
            # Extraer texto de la respuesta
            candidate = data["candidates"][0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            texto = ""
            for part in parts:
                if "text" in part:
                    texto += part["text"]
            
            # Extraer información de grounding (fuentes web) si existe
            grounding_metadata = candidate.get("groundingMetadata", {})
            search_results = grounding_metadata.get("groundingChunks", [])
            web_sources = grounding_metadata.get("webSearchQueries", [])
            
            resultado = extraer_json_respuesta(texto)
            
            # Agregar las fuentes web encontradas
            if search_results:
                publicaciones_web = []
                for chunk in search_results:
                    web_info = chunk.get("web", {})
                    if web_info:
                        publicaciones_web.append({
                            "fuente": web_info.get("title", "Fuente web"),
                            "url": web_info.get("uri", ""),
                            "precio": None,
                            "incluida": True
                        })
                
                if publicaciones_web:
                    resultado["publicaciones"] = publicaciones_web
                    resultado["alertas"] = resultado.get("alertas", [])
                    resultado["alertas"].append(f"✅ Se consultaron {len(publicaciones_web)} fuentes web via Google Search")
            
            # Agregar queries de búsqueda usadas
            if web_sources:
                resultado["busquedas_realizadas"] = web_sources
            
            return resultado
            
    except httpx.TimeoutException:
        return {
            "precio_sugerido": None,
            "confianza": "BAJA",
            "alertas": ["Timeout: Gemini tardó demasiado en responder"],
            "reporte_detallado": "La solicitud a Gemini excedió el tiempo límite (120s)"
        }
    except Exception as e:
        return {
            "precio_sugerido": None,
            "confianza": "BAJA",
            "alertas": [f"Error inesperado: {str(e)}"],
            "reporte_detallado": f"Error: {str(e)}"
        }


def extraer_json_respuesta(texto: str) -> Dict[str, Any]:
    """Extrae JSON de la respuesta de la IA"""
    import json
    import re
    
    # --- INICIO DEPURACIÓN ---
    print("\n" + "="*50)
    print("🤖 RESPUESTA CRUDA DE GEMINI:")
    print(texto)
    print("="*50 + "\n")
    # --- FIN DEPURACIÓN ---

    # Limpiar markdown
    texto = texto.replace("```json", "").replace("```", "").strip()
    
    # Buscar JSON en la respuesta
    try:
        json_match = re.search(r'\{[\s\S]*\}', texto)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    # Si no se puede parsear
    return {
        "precio_sugerido": None,
        "confianza": "BAJA",
        "alertas": ["No se pudo parsear la respuesta de la IA"],
        "reporte_detallado": texto
    }


# Para ejecutar: uvicorn main:app --reload --port 8000