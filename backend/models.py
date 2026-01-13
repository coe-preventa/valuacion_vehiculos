# backend/models.py
"""
Modelos de datos para el sistema de valuación de vehículos.
Incluye sistema completo de reglas con versionado y auditoría.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, Enum, JSON, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from enum import Enum as PyEnum
import uuid

Base = declarative_base()


# ============================================
# ENUMS
# ============================================

class TipoRegla(PyEnum):
    """Tipos de reglas de negocio"""
    FUENTE = "fuente"                    # Fuentes de datos (URLs)
    FILTRO_BUSQUEDA = "filtro_busqueda"  # Filtros de búsqueda
    DEPURACION = "depuracion"            # Reglas de eliminación de resultados
    MUESTREO = "muestreo"                # Cantidad y selección de resultados
    PUNTO_CONTROL = "punto_control"      # Umbrales y ampliaciones
    METODO_VALUACION = "metodo_valuacion"  # Métodos estadísticos
    AJUSTE_CALCULO = "ajuste_calculo"    # Ajustes de precio (inflación, márgenes)


class TipoAccion(PyEnum):
    """Tipos de acciones de auditoría"""
    CREAR = "crear"
    MODIFICAR = "modificar"
    ELIMINAR = "eliminar"
    ACTIVAR = "activar"
    DESACTIVAR = "desactivar"
    RESTAURAR = "restaurar"


class TipoComparacion(PyEnum):
    """Operadores de comparación para reglas"""
    IGUAL = "igual"
    DIFERENTE = "diferente"
    MAYOR = "mayor"
    MENOR = "menor"
    MAYOR_IGUAL = "mayor_igual"
    MENOR_IGUAL = "menor_igual"
    ENTRE = "entre"
    CONTIENE = "contiene"
    EN_LISTA = "en_lista"


# ============================================
# MODELOS DE USUARIO
# ============================================

class Usuario(Base):
    """Usuarios del sistema (vendedores, administradores)"""
    __tablename__ = "usuarios"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    nombre = Column(String(255), nullable=False)
    apellido = Column(String(255), nullable=False)
    rol = Column(String(50), default="vendedor")  # vendedor, supervisor, admin
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    ultimo_acceso = Column(DateTime, nullable=True)
    
    # Relaciones
    reglas_creadas = relationship("Regla", back_populates="creador", foreign_keys="Regla.creado_por")
    auditorias = relationship("AuditoriaRegla", back_populates="usuario")
    valuaciones = relationship("Valuacion", back_populates="usuario")
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def __repr__(self):
        return f"<Usuario {self.email}>"


# ============================================
# MODELOS DE REGLAS
# ============================================

class Regla(Base):
    """
    Regla de negocio configurable.
    Cada regla tiene un tipo, parámetros y puede estar activa o inactiva.
    """
    __tablename__ = "reglas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codigo = Column(String(50), unique=True, nullable=False)  # Ej: "FILTRO_AÑO_RANGO"
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(Enum(TipoRegla), nullable=False)
    
    # Configuración de la regla (estructura flexible en JSON)
    parametros = Column(JSON, nullable=False, default=dict)
    """
    Ejemplos de parametros según tipo:
    
    FUENTE:
        {"url": "kavak.com", "prioridad": 1, "verificado": true}
    
    FILTRO_BUSQUEDA:
        {"campo": "año", "operador": "entre", "valor": [-1, 1], "relativo": true}
    
    DEPURACION:
        {"accion": "eliminar_outliers", "cantidad": 5, "extremo": "inferior"}
    
    MUESTREO:
        {"metodo": "aleatorio", "cantidad": 20}
    
    PUNTO_CONTROL:
        {"umbral_minimo": 5, "accion": "ampliar_busqueda", 
         "nuevos_parametros": {"año": 2, "km": 15000}}
    
    METODO_VALUACION:
        {"metodo": "mediana", "peso": 1.0}
    
    AJUSTE_CALCULO:
        {"tipo": "inflacion", "porcentaje": 5, "periodo_dias": 30}
    """
    
    # Estado
    activo = Column(Boolean, default=True)
    orden = Column(Integer, default=0)  # Orden de aplicación
    
    # Versionado
    version = Column(Integer, default=1)
    
    # Auditoría básica
    creado_por = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    modificado_por = Column(String(36), ForeignKey("usuarios.id"), nullable=True)
    fecha_modificacion = Column(DateTime, nullable=True)
    
    # Relaciones
    creador = relationship("Usuario", back_populates="reglas_creadas", foreign_keys=[creado_por])
    historial = relationship("HistorialRegla", back_populates="regla", order_by="desc(HistorialRegla.version)")
    auditorias = relationship("AuditoriaRegla", back_populates="regla", order_by="desc(AuditoriaRegla.fecha)")
    
    def __repr__(self):
        return f"<Regla {self.codigo} v{self.version}>"
    
    def to_dict(self):
        """Convierte la regla a diccionario para el prompt"""
        return {
            "codigo": self.codigo,
            "nombre": self.nombre,
            "tipo": self.tipo.value,
            "parametros": self.parametros,
            "activo": self.activo,
            "orden": self.orden,
            "version": self.version
        }


class HistorialRegla(Base):
    """
    Historial de versiones de cada regla.
    Cada vez que se modifica una regla, se guarda una copia aquí.
    """
    __tablename__ = "historial_reglas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    regla_id = Column(String(36), ForeignKey("reglas.id"), nullable=False)
    version = Column(Integer, nullable=False)
    
    # Snapshot de la regla en esta versión
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(Enum(TipoRegla), nullable=False)
    parametros = Column(JSON, nullable=False)
    activo = Column(Boolean, nullable=False)
    orden = Column(Integer, nullable=False)
    
    # Quién y cuándo
    modificado_por = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    motivo_cambio = Column(Text, nullable=True)  # Opcional: por qué se cambió
    
    # Relaciones
    regla = relationship("Regla", back_populates="historial")
    usuario = relationship("Usuario")
    
    __table_args__ = (
        UniqueConstraint('regla_id', 'version', name='uix_regla_version'),
    )
    
    def __repr__(self):
        return f"<HistorialRegla {self.codigo} v{self.version}>"


class AuditoriaRegla(Base):
    """
    Registro de auditoría detallado de todas las acciones sobre reglas.
    """
    __tablename__ = "auditoria_reglas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    regla_id = Column(String(36), ForeignKey("reglas.id"), nullable=False)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    
    # Detalles de la acción
    accion = Column(Enum(TipoAccion), nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    
    # Estado antes y después (para poder ver exactamente qué cambió)
    valor_anterior = Column(JSON, nullable=True)  # Null si es creación
    valor_nuevo = Column(JSON, nullable=True)     # Null si es eliminación
    
    # Campos específicos que cambiaron
    campos_modificados = Column(JSON, nullable=True)  # ["parametros.rango", "activo"]
    
    # Contexto adicional
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    notas = Column(Text, nullable=True)
    
    # Relaciones
    regla = relationship("Regla", back_populates="auditorias")
    usuario = relationship("Usuario", back_populates="auditorias")
    
    def __repr__(self):
        return f"<Auditoria {self.accion.value} - {self.fecha}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "regla_id": self.regla_id,
            "usuario": self.usuario.nombre_completo if self.usuario else None,
            "accion": self.accion.value,
            "fecha": self.fecha.isoformat(),
            "campos_modificados": self.campos_modificados,
            "notas": self.notas
        }


# ============================================
# MODELOS DE CONFIGURACIÓN
# ============================================

class ConfiguracionGlobal(Base):
    """
    Configuración global del sistema.
    Permite guardar conjuntos de reglas activas como "perfiles".
    """
    __tablename__ = "configuracion_global"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    es_default = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    
    # IDs de reglas que componen esta configuración
    reglas_ids = Column(JSON, default=list)
    
    creado_por = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Configuracion {self.nombre}>"


# ============================================
# MODELOS DE VALUACIÓN
# ============================================

class Vehiculo(Base):
    """Vehículos en el inventario"""
    __tablename__ = "vehiculos"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    marca = Column(String(100), nullable=False)
    modelo = Column(String(100), nullable=False)
    año = Column(Integer, nullable=False)
    kilometraje = Column(Integer, nullable=False)
    version = Column(String(100), nullable=True)
    transmision = Column(String(50), nullable=True)
    combustible = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    patente = Column(String(20), nullable=True)
    
    # Datos de compra
    precio_compra = Column(Float, nullable=True)
    fecha_compra = Column(DateTime, nullable=True)
    
    # Estado
    estado = Column(String(50), default="en_stock")  # en_stock, vendido, reservado
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    valuaciones = relationship("Valuacion", back_populates="vehiculo")
    
    def __repr__(self):
        return f"<Vehiculo {self.marca} {self.modelo} {self.año}>"


class Valuacion(Base):
    """
    Registro de cada valuación realizada.
    Guarda el resultado y las reglas que se usaron.
    """
    __tablename__ = "valuaciones"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehiculo_id = Column(String(36), ForeignKey("vehiculos.id"), nullable=False)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    
    # Resultados
    precio_sugerido = Column(Float, nullable=True)
    precio_minimo = Column(Float, nullable=True)
    precio_maximo = Column(Float, nullable=True)
    confianza = Column(String(20), nullable=True)  # ALTA, MEDIA, BAJA
    
    # Datos del análisis
    fuentes_consultadas = Column(Integer, default=0)
    resultados_encontrados = Column(Integer, default=0)
    resultados_filtrados = Column(Integer, default=0)
    
    # Estadísticas de mercado
    precio_mercado_minimo = Column(Float, nullable=True)
    precio_mercado_maximo = Column(Float, nullable=True)
    precio_mercado_promedio = Column(Float, nullable=True)
    precio_mercado_mediana = Column(Float, nullable=True)
    
    # Trazabilidad completa
    reglas_aplicadas = Column(JSON, default=list)  # Snapshot de reglas usadas
    configuracion_usada = Column(JSON, default=dict)  # Config completa al momento
    publicaciones_analizadas = Column(JSON, default=list)  # URLs y precios
    
    # Reporte completo generado por el agente
    reporte_completo = Column(Text, nullable=True)
    
    # Metadata
    fecha = Column(DateTime, default=datetime.utcnow)
    duracion_segundos = Column(Float, nullable=True)
    tokens_usados = Column(JSON, default=dict)
    
    # Relaciones
    vehiculo = relationship("Vehiculo", back_populates="valuaciones")
    usuario = relationship("Usuario", back_populates="valuaciones")
    
    def __repr__(self):
        return f"<Valuacion {self.id[:8]} - ${self.precio_sugerido}>"


# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def crear_tablas(engine):
    """Crea todas las tablas en la base de datos"""
    Base.metadata.create_all(engine)


def obtener_session(database_url: str = "sqlite:///valuacion.db"):
    """Crea y retorna una sesión de base de datos"""
    engine = create_engine(database_url, echo=False)
    crear_tablas(engine)
    Session = sessionmaker(bind=engine)
    return Session()
