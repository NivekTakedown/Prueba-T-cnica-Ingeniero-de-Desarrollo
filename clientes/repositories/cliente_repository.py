from typing import Optional, List, Dict, Any
from django.db.models import QuerySet, Q, Sum, Count, Max
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, date

from .base_repository import BaseRepository, ObjectNotFoundError, RepositoryValidationError
from ..models import Cliente, TipoDocumento


class ClienteRepository(BaseRepository):
    """
    Repository específico para el modelo Cliente.
    Proporciona métodos especializados para operaciones con clientes.
    """
    
    def __init__(self):
        super().__init__(Cliente)
    
    def get_queryset(self) -> QuerySet:
        """
        QuerySet optimizado para Cliente con relaciones precargadas.
        """
        return super().get_queryset().select_related('tipo_documento')
    
    def get_by_documento(self, tipo_documento: str, numero_documento: str) -> Optional[Cliente]:
        """
        Busca un cliente por tipo y número de documento.
        
        Args:
            tipo_documento: Código del tipo de documento (ej: 'CC', 'NIT', 'PA')
            numero_documento: Número del documento
            
        Returns:
            Cliente encontrado o None si no existe
            
        Raises:
            RepositoryValidationError: Si los parámetros son inválidos
        """
        try:
            if not tipo_documento or not numero_documento:
                raise RepositoryValidationError("Tipo y número de documento son requeridos")
            
            # Normalizar datos
            tipo_documento = tipo_documento.strip().upper()
            numero_documento = numero_documento.strip().upper()
            
            self.logger.debug(f"Buscando cliente por documento: {tipo_documento} - {numero_documento}")
            
            cliente = self.get_queryset().filter(
                tipo_documento__codigo=tipo_documento,
                numero_documento=numero_documento,
                activo=True
            ).first()
            
            if cliente:
                self.logger.info(f"Cliente encontrado: {cliente.get_nombre_completo()}")
            else:
                self.logger.warning(f"Cliente no encontrado con documento: {tipo_documento} - {numero_documento}")
            
            return cliente
            
        except Exception as e:
            self.logger.error(f"Error buscando cliente por documento: {e}")
            raise RepositoryValidationError(f"Error al buscar cliente por documento: {e}") from e
    
    def get_by_documento_or_fail(self, tipo_documento: str, numero_documento: str) -> Cliente:
        """
        Busca un cliente por documento o lanza excepción si no existe.
        
        Args:
            tipo_documento: Código del tipo de documento
            numero_documento: Número del documento
            
        Returns:
            Cliente encontrado
            
        Raises:
            ObjectNotFoundError: Si el cliente no existe
        """
        cliente = self.get_by_documento(tipo_documento, numero_documento)
        if cliente is None:
            raise ObjectNotFoundError(f"Cliente no encontrado con documento {tipo_documento}: {numero_documento}")
        return cliente
    
    def get_by_correo(self, correo: str) -> Optional[Cliente]:
        """
        Busca un cliente por correo electrónico.
        
        Args:
            correo: Correo electrónico del cliente
            
        Returns:
            Cliente encontrado o None si no existe
        """
        try:
            if not correo:
                return None
            
            correo = correo.strip().lower()
            self.logger.debug(f"Buscando cliente por correo: {correo}")
            
            cliente = self.get_queryset().filter(
                correo=correo,
                activo=True
            ).first()
            
            if cliente:
                self.logger.info(f"Cliente encontrado por correo: {cliente.get_nombre_completo()}")
            
            return cliente
            
        except Exception as e:
            self.logger.error(f"Error buscando cliente por correo: {e}")
            raise RepositoryValidationError(f"Error al buscar cliente por correo: {e}") from e
    
    def search_clientes(self, filters: Dict[str, Any]) -> QuerySet:
        """
        Búsqueda avanzada de clientes con múltiples filtros.
        
        Args:
            filters: Diccionario con filtros de búsqueda:
                - search_term (str): Término de búsqueda en nombre, apellido, correo
                - tipo_documento (str): Código del tipo de documento
                - activo (bool): Estado del cliente
                - fecha_creacion_desde (date): Fecha desde
                - fecha_creacion_hasta (date): Fecha hasta
                - es_vip (bool): Si es cliente VIP
                - monto_minimo (Decimal): Monto mínimo de compras
                
        Returns:
            QuerySet con clientes que coinciden con los filtros
        """
        try:
            queryset = self.get_queryset()
            
            # Filtro por término de búsqueda en múltiples campos
            search_term = filters.get('search_term')
            if search_term:
                search_term = search_term.strip()
                search_query = Q(
                    Q(nombre__icontains=search_term) |
                    Q(apellido__icontains=search_term) |
                    Q(correo__icontains=search_term) |
                    Q(numero_documento__icontains=search_term)
                )
                queryset = queryset.filter(search_query)
            
            # Filtro por tipo de documento
            tipo_documento = filters.get('tipo_documento')
            if tipo_documento:
                queryset = queryset.filter(tipo_documento__codigo=tipo_documento.upper())
            
            # Filtro por estado activo
            activo = filters.get('activo')
            if activo is not None:
                queryset = queryset.filter(activo=activo)
            
            # Filtros por fechas
            fecha_desde = filters.get('fecha_creacion_desde')
            if fecha_desde:
                queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
            
            fecha_hasta = filters.get('fecha_creacion_hasta')
            if fecha_hasta:
                queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)
            
            # Filtro por monto mínimo de compras
            monto_minimo = filters.get('monto_minimo')
            if monto_minimo:
                queryset = queryset.filter(total_compras__gte=monto_minimo)
            
            # Filtro por clientes VIP
            es_vip = filters.get('es_vip')
            if es_vip is not None:
                vip_monto = filters.get('vip_monto_minimo', Decimal('5000000'))
                if es_vip:
                    queryset = queryset.filter(total_compras__gte=vip_monto)
                else:
                    queryset = queryset.filter(total_compras__lt=vip_monto)
            
            self.logger.debug(f"Búsqueda de clientes con filtros: {filters}")
            return queryset.order_by('-fecha_creacion')
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda de clientes: {e}")
            raise RepositoryValidationError(f"Error en búsqueda de clientes: {e}") from e
    
    def get_clientes_vip(self, monto_minimo: Decimal = Decimal('5000000'), 
                        fecha_ultima_compra_desde: Optional[date] = None) -> QuerySet:
        """
        Obtiene clientes VIP basado en el total de compras.
        
        Args:
            monto_minimo: Monto mínimo para ser considerado VIP
            fecha_ultima_compra_desde: Filtro opcional por fecha de última compra
            
        Returns:
            QuerySet con clientes VIP ordenados por total de compras
        """
        try:
            queryset = self.get_queryset().filter(
                total_compras__gte=monto_minimo,
                activo=True
            )
            
            if fecha_ultima_compra_desde:
                queryset = queryset.filter(fecha_ultima_compra__gte=fecha_ultima_compra_desde)
            
            self.logger.debug(f"Obteniendo clientes VIP con monto >= {monto_minimo}")
            return queryset.order_by('-total_compras')
            
        except Exception as e:
            self.logger.error(f"Error obteniendo clientes VIP: {e}")
            raise RepositoryValidationError(f"Error al obtener clientes VIP: {e}") from e
    
    def get_clientes_activos_recientes(self, dias: int = 30) -> QuerySet:
        """
        Obtiene clientes que han estado activos en los últimos N días.
        
        Args:
            dias: Número de días hacia atrás para considerar actividad reciente
            
        Returns:
            QuerySet con clientes activos recientemente
        """
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            fecha_limite = timezone.now() - timedelta(days=dias)
            
            queryset = self.get_queryset().filter(
                fecha_ultima_compra__gte=fecha_limite,
                activo=True
            )
            
            self.logger.debug(f"Obteniendo clientes activos últimos {dias} días")
            return queryset.order_by('-fecha_ultima_compra')
            
        except Exception as e:
            self.logger.error(f"Error obteniendo clientes activos recientes: {e}")
            raise RepositoryValidationError(f"Error al obtener clientes activos: {e}") from e
    
    def get_estadisticas_generales(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de los clientes.
        
        Returns:
            Diccionario con estadísticas generales
        """
        try:
            queryset = self.get_queryset().filter(activo=True)
            
            stats = queryset.aggregate(
                total_clientes=Count('id'),
                total_ventas=Sum('total_compras'),
                promedio_ventas=Sum('total_compras') / Count('id'),
                clientes_con_compras=Count('id', filter=Q(numero_compras__gt=0)),
                clientes_vip=Count('id', filter=Q(total_compras__gte=Decimal('5000000')))
            )
            
            # Calcular algunos valores adicionales
            stats['total_ventas'] = stats['total_ventas'] or Decimal('0')
            stats['promedio_ventas'] = stats['promedio_ventas'] or Decimal('0')
            stats['porcentaje_con_compras'] = (
                (stats['clientes_con_compras'] / stats['total_clientes'] * 100) 
                if stats['total_clientes'] > 0 else 0
            )
            stats['porcentaje_vip'] = (
                (stats['clientes_vip'] / stats['total_clientes'] * 100) 
                if stats['total_clientes'] > 0 else 0
            )
            
            self.logger.debug(f"Estadísticas generales calculadas: {stats['total_clientes']} clientes")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error calculando estadísticas: {e}")
            raise RepositoryValidationError(f"Error al calcular estadísticas: {e}") from e
    
    def create_cliente(self, data: Dict[str, Any]) -> Cliente:
        """
        Crea un nuevo cliente con validaciones específicas.
        
        Args:
            data: Datos del cliente incluyendo tipo_documento_codigo
            
        Returns:
            Cliente creado
            
        Raises:
            RepositoryValidationError: Si hay errores de validación
        """
        try:
            # Obtener tipo de documento si se proporciona código
            tipo_documento_codigo = data.pop('tipo_documento_codigo', None)
            if tipo_documento_codigo:
                try:
                    tipo_documento = TipoDocumento.objects.get(
                        codigo=tipo_documento_codigo.upper(),
                        activo=True
                    )
                    data['tipo_documento'] = tipo_documento
                except TipoDocumento.DoesNotExist:
                    raise RepositoryValidationError(f"Tipo de documento '{tipo_documento_codigo}' no válido")
            
            # Validar que no exista otro cliente con el mismo documento
            if 'numero_documento' in data and 'tipo_documento' in data:
                existe = self.exists(
                    tipo_documento=data['tipo_documento'],
                    numero_documento=data['numero_documento'],
                    activo=True
                )
                if existe:
                    raise RepositoryValidationError(
                        f"Ya existe un cliente activo con documento "
                        f"{data['tipo_documento'].codigo}: {data['numero_documento']}"
                    )
            
            # Crear cliente usando el método base
            cliente = self.create(**data)
            self.logger.info(f"Cliente creado exitosamente: {cliente}")
            return cliente
            
        except RepositoryValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error creando cliente: {e}")
            raise RepositoryValidationError(f"Error al crear cliente: {e}") from e
    
    def update_cliente(self, cliente_id: int, data: Dict[str, Any]) -> Cliente:
        """
        Actualiza un cliente con validaciones específicas.
        
        Args:
            cliente_id: ID del cliente a actualizar
            data: Datos a actualizar
            
        Returns:
            Cliente actualizado
        """
        try:
            # Manejar cambio de tipo de documento si se proporciona
            tipo_documento_codigo = data.pop('tipo_documento_codigo', None)
            if tipo_documento_codigo:
                try:
                    tipo_documento = TipoDocumento.objects.get(
                        codigo=tipo_documento_codigo.upper(),
                        activo=True
                    )
                    data['tipo_documento'] = tipo_documento
                except TipoDocumento.DoesNotExist:
                    raise RepositoryValidationError(f"Tipo de documento '{tipo_documento_codigo}' no válido")
            
            # Actualizar usando el método base
            cliente = self.update(cliente_id, **data)
            self.logger.info(f"Cliente actualizado exitosamente: {cliente}")
            return cliente
            
        except RepositoryValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error actualizando cliente: {e}")
            raise RepositoryValidationError(f"Error al actualizar cliente: {e}") from e
    
    def desactivar_cliente(self, cliente_id: int, razon: Optional[str] = None) -> Cliente:
        """
        Desactiva un cliente (soft delete).
        
        Args:
            cliente_id: ID del cliente a desactivar
            razon: Razón opcional para la desactivación
            
        Returns:
            Cliente desactivado
        """
        try:
            cliente = self.get_by_id_or_fail(cliente_id)
            
            if not cliente.activo:
                self.logger.warning(f"Cliente {cliente_id} ya estaba desactivado")
                return cliente
            
            cliente.desactivar(razon)
            self.logger.info(f"Cliente desactivado: {cliente}")
            return cliente
            
        except Exception as e:
            self.logger.error(f"Error desactivando cliente: {e}")
            raise RepositoryValidationError(f"Error al desactivar cliente: {e}") from e
    
    def reactivar_cliente(self, cliente_id: int) -> Cliente:
        """
        Reactiva un cliente previamente desactivado.
        
        Args:
            cliente_id: ID del cliente a reactivar
            
        Returns:
            Cliente reactivado
        """
        try:
            cliente = self.get_by_id_or_fail(cliente_id)
            
            if cliente.activo:
                self.logger.warning(f"Cliente {cliente_id} ya estaba activo")
                return cliente
            
            cliente.reactivar()
            self.logger.info(f"Cliente reactivado: {cliente}")
            return cliente
            
        except Exception as e:
            self.logger.error(f"Error reactivando cliente: {e}")
            raise RepositoryValidationError(f"Error al reactivar cliente: {e}") from e
    
    def get_tipos_documento_disponibles(self) -> QuerySet:
        """
        Obtiene los tipos de documento disponibles para crear clientes.
        
        Returns:
            QuerySet con tipos de documento activos
        """
        try:
            return TipoDocumento.objects.filter(activo=True).order_by('nombre')
        except Exception as e:
            self.logger.error(f"Error obteniendo tipos de documento: {e}")
            raise RepositoryValidationError(f"Error al obtener tipos de documento: {e}") from e