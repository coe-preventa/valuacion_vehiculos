# backend/services/reglas_service.py
"""
Servicio para gestión de reglas de negocio con auditoría completa.
Permite CRUD de reglas con versionado y trazabilidad.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
import copy

from models import (
    Regla, HistorialRegla, AuditoriaRegla, Usuario, ConfiguracionGlobal,
    TipoRegla, TipoAccion
)


class ReglasService:
    """Servicio para gestionar reglas de negocio"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # CRUD DE REGLAS
    # ============================================
    
    def crear_regla(
        self,
        codigo: str,
        nombre: str,
        tipo: TipoRegla,
        parametros: Dict[str, Any],
        usuario_id: str,
        descripcion: Optional[str] = None,
        orden: int = 0,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        notas: Optional[str] = None
    ) -> Regla:
        """
        Crea una nueva regla y registra la auditoría.
        
        Args:
            codigo: Código único de la regla (ej: "FILTRO_AÑO_RANGO")
            nombre: Nombre descriptivo
            tipo: Tipo de regla (TipoRegla enum)
            parametros: Diccionario con la configuración de la regla
            usuario_id: ID del usuario que crea la regla
            descripcion: Descripción opcional
            orden: Orden de aplicación (menor = primero)
            ip_address: IP del usuario (para auditoría)
            user_agent: User agent del navegador (para auditoría)
            notas: Notas adicionales sobre la creación
        
        Returns:
            Regla creada
        """
        # Verificar que el código no exista
        existente = self.db.query(Regla).filter(Regla.codigo == codigo).first()
        if existente:
            raise ValueError(f"Ya existe una regla con código '{codigo}'")
        
        # Crear la regla
        regla = Regla(
            codigo=codigo,
            nombre=nombre,
            descripcion=descripcion,
            tipo=tipo,
            parametros=parametros,
            orden=orden,
            activo=True,
            version=1,
            creado_por=usuario_id,
            fecha_creacion=datetime.utcnow()
        )
        
        self.db.add(regla)
        self.db.flush()  # Para obtener el ID
        
        # Crear registro de auditoría
        auditoria = AuditoriaRegla(
            regla_id=regla.id,
            usuario_id=usuario_id,
            accion=TipoAccion.CREAR,
            fecha=datetime.utcnow(),
            valor_anterior=None,
            valor_nuevo=regla.to_dict(),
            campos_modificados=None,
            ip_address=ip_address,
            user_agent=user_agent,
            notas=notas or f"Creación de regla '{nombre}'"
        )
        self.db.add(auditoria)
        
        # Crear primera versión en historial
        historial = HistorialRegla(
            regla_id=regla.id,
            version=1,
            codigo=regla.codigo,
            nombre=regla.nombre,
            descripcion=regla.descripcion,
            tipo=regla.tipo,
            parametros=regla.parametros,
            activo=regla.activo,
            orden=regla.orden,
            modificado_por=usuario_id,
            fecha=datetime.utcnow(),
            motivo_cambio="Creación inicial"
        )
        self.db.add(historial)
        
        self.db.commit()
        self.db.refresh(regla)
        
        return regla
    
    def modificar_regla(
        self,
        regla_id: str,
        usuario_id: str,
        cambios: Dict[str, Any],
        motivo_cambio: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Regla:
        """
        Modifica una regla existente, guarda versión anterior y registra auditoría.
        
        Args:
            regla_id: ID de la regla a modificar
            usuario_id: ID del usuario que modifica
            cambios: Diccionario con los campos a cambiar
            motivo_cambio: Razón del cambio (opcional pero recomendado)
            ip_address: IP del usuario
            user_agent: User agent del navegador
        
        Returns:
            Regla modificada
        """
        regla = self.db.query(Regla).filter(Regla.id == regla_id).first()
        if not regla:
            raise ValueError(f"No existe regla con ID '{regla_id}'")
        
        # Guardar estado anterior
        valor_anterior = regla.to_dict()
        
        # Determinar qué campos cambiaron
        campos_modificados = []
        
        # Aplicar cambios permitidos
        campos_permitidos = ['nombre', 'descripcion', 'parametros', 'orden', 'activo']
        for campo, valor in cambios.items():
            if campo in campos_permitidos:
                valor_actual = getattr(regla, campo)
                if valor_actual != valor:
                    campos_modificados.append(campo)
                    setattr(regla, campo, valor)
        
        if not campos_modificados:
            return regla  # No hubo cambios reales
        
        # Incrementar versión
        regla.version += 1
        regla.modificado_por = usuario_id
        regla.fecha_modificacion = datetime.utcnow()
        
        # Crear registro en historial
        historial = HistorialRegla(
            regla_id=regla.id,
            version=regla.version,
            codigo=regla.codigo,
            nombre=regla.nombre,
            descripcion=regla.descripcion,
            tipo=regla.tipo,
            parametros=regla.parametros,
            activo=regla.activo,
            orden=regla.orden,
            modificado_por=usuario_id,
            fecha=datetime.utcnow(),
            motivo_cambio=motivo_cambio
        )
        self.db.add(historial)
        
        # Crear registro de auditoría
        auditoria = AuditoriaRegla(
            regla_id=regla.id,
            usuario_id=usuario_id,
            accion=TipoAccion.MODIFICAR,
            fecha=datetime.utcnow(),
            valor_anterior=valor_anterior,
            valor_nuevo=regla.to_dict(),
            campos_modificados=campos_modificados,
            ip_address=ip_address,
            user_agent=user_agent,
            notas=motivo_cambio
        )
        self.db.add(auditoria)
        
        self.db.commit()
        self.db.refresh(regla)
        
        return regla
    
    def eliminar_regla(
        self,
        regla_id: str,
        usuario_id: str,
        motivo: Optional[str] = None,
        eliminacion_fisica: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Elimina una regla (lógica o físicamente).
        
        Args:
            regla_id: ID de la regla a eliminar
            usuario_id: ID del usuario que elimina
            motivo: Razón de la eliminación
            eliminacion_fisica: Si True, elimina de la BD. Si False, solo desactiva.
            ip_address: IP del usuario
            user_agent: User agent del navegador
        
        Returns:
            True si se eliminó correctamente
        """
        regla = self.db.query(Regla).filter(Regla.id == regla_id).first()
        if not regla:
            raise ValueError(f"No existe regla con ID '{regla_id}'")
        
        valor_anterior = regla.to_dict()
        
        if eliminacion_fisica:
            # Eliminación física - guardar auditoría antes de eliminar
            auditoria = AuditoriaRegla(
                regla_id=regla.id,
                usuario_id=usuario_id,
                accion=TipoAccion.ELIMINAR,
                fecha=datetime.utcnow(),
                valor_anterior=valor_anterior,
                valor_nuevo=None,
                campos_modificados=None,
                ip_address=ip_address,
                user_agent=user_agent,
                notas=motivo or "Eliminación física de regla"
            )
            self.db.add(auditoria)
            self.db.delete(regla)
        else:
            # Eliminación lógica - desactivar
            regla.activo = False
            regla.version += 1
            regla.modificado_por = usuario_id
            regla.fecha_modificacion = datetime.utcnow()
            
            # Historial
            historial = HistorialRegla(
                regla_id=regla.id,
                version=regla.version,
                codigo=regla.codigo,
                nombre=regla.nombre,
                descripcion=regla.descripcion,
                tipo=regla.tipo,
                parametros=regla.parametros,
                activo=False,
                orden=regla.orden,
                modificado_por=usuario_id,
                fecha=datetime.utcnow(),
                motivo_cambio=motivo or "Eliminación lógica"
            )
            self.db.add(historial)
            
            # Auditoría
            auditoria = AuditoriaRegla(
                regla_id=regla.id,
                usuario_id=usuario_id,
                accion=TipoAccion.DESACTIVAR,
                fecha=datetime.utcnow(),
                valor_anterior=valor_anterior,
                valor_nuevo=regla.to_dict(),
                campos_modificados=["activo"],
                ip_address=ip_address,
                user_agent=user_agent,
                notas=motivo
            )
            self.db.add(auditoria)
        
        self.db.commit()
        return True
    
    def restaurar_regla(
        self,
        regla_id: str,
        usuario_id: str,
        version: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Regla:
        """
        Restaura una regla a una versión anterior o la reactiva si estaba eliminada.
        
        Args:
            regla_id: ID de la regla
            usuario_id: ID del usuario que restaura
            version: Versión específica a restaurar (None = solo reactivar)
            ip_address: IP del usuario
            user_agent: User agent del navegador
        
        Returns:
            Regla restaurada
        """
        regla = self.db.query(Regla).filter(Regla.id == regla_id).first()
        if not regla:
            raise ValueError(f"No existe regla con ID '{regla_id}'")
        
        valor_anterior = regla.to_dict()
        
        if version:
            # Restaurar a versión específica
            historial = self.db.query(HistorialRegla).filter(
                and_(
                    HistorialRegla.regla_id == regla_id,
                    HistorialRegla.version == version
                )
            ).first()
            
            if not historial:
                raise ValueError(f"No existe versión {version} de la regla")
            
            # Restaurar valores
            regla.nombre = historial.nombre
            regla.descripcion = historial.descripcion
            regla.parametros = historial.parametros
            regla.orden = historial.orden
            regla.activo = True  # Siempre activar al restaurar
        else:
            # Solo reactivar
            regla.activo = True
        
        regla.version += 1
        regla.modificado_por = usuario_id
        regla.fecha_modificacion = datetime.utcnow()
        
        # Historial
        historial_nuevo = HistorialRegla(
            regla_id=regla.id,
            version=regla.version,
            codigo=regla.codigo,
            nombre=regla.nombre,
            descripcion=regla.descripcion,
            tipo=regla.tipo,
            parametros=regla.parametros,
            activo=regla.activo,
            orden=regla.orden,
            modificado_por=usuario_id,
            fecha=datetime.utcnow(),
            motivo_cambio=f"Restauración a versión {version}" if version else "Reactivación"
        )
        self.db.add(historial_nuevo)
        
        # Auditoría
        auditoria = AuditoriaRegla(
            regla_id=regla.id,
            usuario_id=usuario_id,
            accion=TipoAccion.RESTAURAR,
            fecha=datetime.utcnow(),
            valor_anterior=valor_anterior,
            valor_nuevo=regla.to_dict(),
            campos_modificados=["restaurado"],
            ip_address=ip_address,
            user_agent=user_agent,
            notas=f"Restauración a versión {version}" if version else "Reactivación de regla"
        )
        self.db.add(auditoria)
        
        self.db.commit()
        self.db.refresh(regla)
        
        return regla
    
    # ============================================
    # CONSULTAS
    # ============================================
    
    def obtener_regla(self, regla_id: str) -> Optional[Regla]:
        """Obtiene una regla por ID"""
        return self.db.query(Regla).filter(Regla.id == regla_id).first()
    
    def obtener_regla_por_codigo(self, codigo: str) -> Optional[Regla]:
        """Obtiene una regla por código"""
        return self.db.query(Regla).filter(Regla.codigo == codigo).first()
    
    def listar_reglas(
        self,
        tipo: Optional[TipoRegla] = None,
        solo_activas: bool = True,
        ordenar_por: str = "orden"
    ) -> List[Regla]:
        """
        Lista reglas con filtros opcionales.
        
        Args:
            tipo: Filtrar por tipo de regla
            solo_activas: Si True, solo retorna reglas activas
            ordenar_por: Campo para ordenar (orden, nombre, fecha_creacion)
        
        Returns:
            Lista de reglas
        """
        query = self.db.query(Regla)
        
        if tipo:
            query = query.filter(Regla.tipo == tipo)
        
        if solo_activas:
            query = query.filter(Regla.activo == True)
        
        if ordenar_por == "orden":
            query = query.order_by(Regla.orden, Regla.nombre)
        elif ordenar_por == "nombre":
            query = query.order_by(Regla.nombre)
        elif ordenar_por == "fecha_creacion":
            query = query.order_by(Regla.fecha_creacion.desc())
        
        return query.all()
    
    def obtener_reglas_por_tipo(self) -> Dict[str, List[Dict]]:
        """
        Obtiene todas las reglas activas agrupadas por tipo.
        Formato útil para construir el prompt del agente.
        """
        reglas = self.listar_reglas(solo_activas=True)
        
        agrupadas = {}
        for regla in reglas:
            tipo_key = regla.tipo.value
            if tipo_key not in agrupadas:
                agrupadas[tipo_key] = []
            agrupadas[tipo_key].append(regla.to_dict())
        
        return agrupadas
    
    # ============================================
    # HISTORIAL Y AUDITORÍA
    # ============================================
    
    def obtener_historial_regla(self, regla_id: str) -> List[HistorialRegla]:
        """Obtiene el historial completo de versiones de una regla"""
        return self.db.query(HistorialRegla).filter(
            HistorialRegla.regla_id == regla_id
        ).order_by(HistorialRegla.version.desc()).all()
    
    def obtener_auditoria_regla(
        self,
        regla_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        accion: Optional[TipoAccion] = None,
        limit: int = 100
    ) -> List[AuditoriaRegla]:
        """
        Obtiene registros de auditoría con filtros.
        
        Args:
            regla_id: Filtrar por regla específica
            usuario_id: Filtrar por usuario
            fecha_desde: Fecha inicial
            fecha_hasta: Fecha final
            accion: Tipo de acción específica
            limit: Máximo de registros
        
        Returns:
            Lista de registros de auditoría
        """
        query = self.db.query(AuditoriaRegla)
        
        if regla_id:
            query = query.filter(AuditoriaRegla.regla_id == regla_id)
        
        if usuario_id:
            query = query.filter(AuditoriaRegla.usuario_id == usuario_id)
        
        if fecha_desde:
            query = query.filter(AuditoriaRegla.fecha >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(AuditoriaRegla.fecha <= fecha_hasta)
        
        if accion:
            query = query.filter(AuditoriaRegla.accion == accion)
        
        return query.order_by(AuditoriaRegla.fecha.desc()).limit(limit).all()
    
    def comparar_versiones(
        self,
        regla_id: str,
        version_a: int,
        version_b: int
    ) -> Dict[str, Any]:
        """
        Compara dos versiones de una regla y muestra las diferencias.
        
        Args:
            regla_id: ID de la regla
            version_a: Primera versión a comparar
            version_b: Segunda versión a comparar
        
        Returns:
            Diccionario con las diferencias
        """
        hist_a = self.db.query(HistorialRegla).filter(
            and_(
                HistorialRegla.regla_id == regla_id,
                HistorialRegla.version == version_a
            )
        ).first()
        
        hist_b = self.db.query(HistorialRegla).filter(
            and_(
                HistorialRegla.regla_id == regla_id,
                HistorialRegla.version == version_b
            )
        ).first()
        
        if not hist_a or not hist_b:
            raise ValueError("Una o ambas versiones no existen")
        
        diferencias = {
            "regla_id": regla_id,
            "version_a": version_a,
            "version_b": version_b,
            "cambios": []
        }
        
        campos_comparar = ['nombre', 'descripcion', 'parametros', 'activo', 'orden']
        
        for campo in campos_comparar:
            valor_a = getattr(hist_a, campo)
            valor_b = getattr(hist_b, campo)
            
            if valor_a != valor_b:
                diferencias["cambios"].append({
                    "campo": campo,
                    f"v{version_a}": valor_a,
                    f"v{version_b}": valor_b
                })
        
        return diferencias
    
    # ============================================
    # GENERADOR DE CONFIGURACIÓN PARA PROMPT
    # ============================================
    
    def generar_configuracion_prompt(self) -> Dict[str, Any]:
        """
        Genera la configuración completa formateada para el prompt del agente.
        Agrupa todas las reglas activas en un formato estructurado.
        """
        reglas_agrupadas = self.obtener_reglas_por_tipo()
        
        config = {
            "fuentes": [],
            "filtros_busqueda": [],
            "depuracion": [],
            "muestreo": [],
            "puntos_control": [],
            "metodos_valuacion": [],
            "ajustes_calculo": [],
            "metadata": {
                "generado_en": datetime.utcnow().isoformat(),
                "total_reglas": sum(len(v) for v in reglas_agrupadas.values())
            }
        }
        
        # Mapear tipos a keys de config
        mapeo = {
            "fuente": "fuentes",
            "filtro_busqueda": "filtros_busqueda",
            "depuracion": "depuracion",
            "muestreo": "muestreo",
            "punto_control": "puntos_control",
            "metodo_valuacion": "metodos_valuacion",
            "ajuste_calculo": "ajustes_calculo"
        }
        
        for tipo, reglas in reglas_agrupadas.items():
            key = mapeo.get(tipo)
            if key:
                config[key] = sorted(reglas, key=lambda x: x.get("orden", 0))
        
        return config
