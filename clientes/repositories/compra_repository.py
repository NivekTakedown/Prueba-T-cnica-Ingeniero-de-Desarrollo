from typing import Optional, List, Dict, Any, Tuple
from django.db.models import QuerySet, Q, Sum, Count, Max, Min, Avg, F
from django.db import models  # Agregar esta importación
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone

from .base_repository import BaseRepository, ObjectNotFoundError, RepositoryValidationError
from ..models import Compra, DetalleCompra, Producto, Cliente, EstadoCompra


class CompraRepository(BaseRepository):
    """
    Repository específico para el modelo Compra.
    Maneja operaciones complejas de compras, reportes de fidelización y análisis de ventas.
    """
    
    def __init__(self):
        super().__init__(Compra)
    
    def get_queryset(self) -> QuerySet:
        """
        QuerySet optimizado para Compra con relaciones precargadas.
        """
        return super().get_queryset().select_related(
            'cliente', 'cliente__tipo_documento', 'estado'
        ).prefetch_related('detalles__producto')
    
    def get_compras_by_cliente(self, cliente_id: int, estado_codigo: Optional[str] = None) -> QuerySet:
        """
        Obtiene todas las compras de un cliente específico.
        
        Args:
            cliente_id: ID del cliente
            estado_codigo: Filtro opcional por estado de compra
            
        Returns:
            QuerySet con las compras del cliente
        """
        try:
            queryset = self.get_queryset().filter(cliente_id=cliente_id)
            
            if estado_codigo:
                queryset = queryset.filter(estado__codigo=estado_codigo.upper())
            
            self.logger.debug(f"Obteniendo compras del cliente {cliente_id}")
            return queryset.order_by('-fecha_compra')
            
        except Exception as e:
            self.logger.error(f"Error obteniendo compras del cliente: {e}")
            raise RepositoryValidationError(f"Error al obtener compras del cliente: {e}") from e
    
    def get_compras_ultimo_mes(self, fecha_inicio: Optional[date] = None) -> QuerySet:
        """
        Obtiene compras del último mes o desde una fecha específica.
        
        Args:
            fecha_inicio: Fecha desde la cual obtener compras. Si es None, usa último mes.
            
        Returns:
            QuerySet con compras del período
        """
        try:
            if fecha_inicio is None:
                fecha_inicio = timezone.now().date() - timedelta(days=30)
            
            queryset = self.get_queryset().filter(
                fecha_compra__date__gte=fecha_inicio
            )
            
            self.logger.debug(f"Obteniendo compras desde {fecha_inicio}")
            return queryset.order_by('-fecha_compra')
            
        except Exception as e:
            self.logger.error(f"Error obteniendo compras del último mes: {e}")
            raise RepositoryValidationError(f"Error al obtener compras recientes: {e}") from e
    
    def get_clientes_vip(self, monto_minimo: Decimal = Decimal('5000000'), 
                    fecha_inicio: Optional[date] = None) -> List[Cliente]:
        """
        Obtiene clientes VIP basado en sus compras completadas.
        
        Args:
            monto_minimo: Monto mínimo total de compras para ser VIP
            fecha_inicio: Filtro opcional por fecha de compras desde
            
        Returns:
            Lista de clientes VIP con sus totales anotados
        """
        try:
            # Filtrar compras completadas
            compras_query = Compra.objects.filter(estado__codigo='COMPLETADA')
            
            if fecha_inicio:
                compras_query = compras_query.filter(fecha_compra__date__gte=fecha_inicio)
            
            # Agrupar por cliente y calcular totales
            clientes_con_totales = compras_query.values('cliente').annotate(
                total_compras_periodo=Sum('monto_total'),
                numero_compras_periodo=Count('id'),
                ultima_compra_periodo=Max('fecha_compra')
            ).filter(
                total_compras_periodo__gte=monto_minimo
            ).order_by('-total_compras_periodo')
            
            # Obtener IDs de clientes VIP
            cliente_ids_vip = [item['cliente'] for item in clientes_con_totales]
            
            if not cliente_ids_vip:
                self.logger.debug(f"No hay clientes VIP con monto >= {monto_minimo}")
                return []
            
            # Obtener objetos Cliente
            from ..models import Cliente
            clientes_vip = Cliente.objects.filter(
                id__in=cliente_ids_vip,
                activo=True
            )
            
            # Crear diccionario para mapear totales
            totales_map = {
                item['cliente']: item for item in clientes_con_totales
            }
            
            # Anotar clientes con sus totales calculados
            clientes_anotados = []
            for cliente in clientes_vip:
                totales = totales_map.get(cliente.id, {})
                # Agregar atributos dinámicos al objeto cliente
                cliente.total_compras_periodo = totales.get('total_compras_periodo', Decimal('0'))
                cliente.numero_compras_periodo = totales.get('numero_compras_periodo', 0)
                cliente.ultima_compra_periodo = totales.get('ultima_compra_periodo', None)
                clientes_anotados.append(cliente)
            
            # Ordenar por total de compras (descendente)
            clientes_anotados.sort(
                key=lambda c: c.total_compras_periodo, 
                reverse=True
            )
            
            self.logger.debug(f"Encontrados {len(clientes_anotados)} clientes VIP con monto >= {monto_minimo}")
            return clientes_anotados
            
        except Exception as e:
            self.logger.error(f"Error obteniendo clientes VIP: {e}")
            raise RepositoryValidationError(f"Error al calcular clientes VIP: {e}") from e
            
    def get_reporte_ventas_periodo(self, fecha_inicio: date, fecha_fin: date) -> Dict[str, Any]:
        """
        Genera reporte completo de ventas para un período específico.
        
        Args:
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            
        Returns:
            Diccionario con métricas del período
        """
        try:
            # Filtrar compras del período
            compras_periodo = self.get_queryset().filter(
                fecha_compra__date__gte=fecha_inicio,
                fecha_compra__date__lte=fecha_fin,
                estado__codigo='COMPLETADA'
            )
            
            # Calcular métricas principales
            metricas = compras_periodo.aggregate(
                total_ventas=Sum('monto_total'),
                numero_compras=Count('id'),
                ticket_promedio=Avg('monto_total'),
                compra_maxima=Max('monto_total'),
                compra_minima=Min('monto_total'),
                clientes_unicos=Count('cliente', distinct=True)
            )
            
            # Calcular métricas adicionales
            metricas['total_ventas'] = metricas['total_ventas'] or Decimal('0')
            metricas['ticket_promedio'] = metricas['ticket_promedio'] or Decimal('0')
            metricas['compra_maxima'] = metricas['compra_maxima'] or Decimal('0')
            metricas['compra_minima'] = metricas['compra_minima'] or Decimal('0')
            
            # Top 10 productos más vendidos
            top_productos = DetalleCompra.objects.filter(
                compra__in=compras_periodo
            ).values(
                'producto__nombre',
                'producto__codigo'
            ).annotate(
                cantidad_vendida=Sum('cantidad'),
                ingresos_totales=Sum('subtotal_producto')
            ).order_by('-cantidad_vendida')[:10]
            
            # Top 10 clientes por compras
            top_clientes = compras_periodo.values(
                'cliente__nombre',
                'cliente__apellido',
                'cliente__numero_documento'
            ).annotate(
                total_compras=Sum('monto_total'),
                numero_ordenes=Count('id')
            ).order_by('-total_compras')[:10]
            
            # Ventas por día
            ventas_diarias = compras_periodo.extra(
                select={'dia': 'date(fecha_compra)'}
            ).values('dia').annotate(
                ventas_dia=Sum('monto_total'),
                ordenes_dia=Count('id')
            ).order_by('dia')
            
            reporte = {
                'periodo': {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'dias_totales': (fecha_fin - fecha_inicio).days + 1
                },
                'metricas_generales': metricas,
                'top_productos': list(top_productos),
                'top_clientes': list(top_clientes),
                'ventas_diarias': list(ventas_diarias)
            }
            
            self.logger.info(f"Reporte generado para período {fecha_inicio} - {fecha_fin}")
            return reporte
            
        except Exception as e:
            self.logger.error(f"Error generando reporte de ventas: {e}")
            raise RepositoryValidationError(f"Error al generar reporte: {e}") from e
    
    def crear_compra_completa(self, cliente_id: int, productos_data: List[Dict], 
                             observaciones: Optional[str] = None, 
                             metodo_pago: Optional[str] = None) -> Compra:
        """
        Crea una compra completa con sus detalles en una transacción.
        
        Args:
            cliente_id: ID del cliente
            productos_data: Lista de dict con 'producto_id' y 'cantidad'
            observaciones: Observaciones opcionales
            metodo_pago: Método de pago utilizado
            
        Returns:
            Compra creada con todos sus detalles
            
        Raises:
            RepositoryValidationError: Si hay errores de validación
        """
        try:
            with transaction.atomic():
                # Validar cliente
                cliente = Cliente.objects.get(id=cliente_id, activo=True)
                
                # Obtener estado pendiente
                estado_pendiente = EstadoCompra.objects.get(codigo='PENDIENTE')
                
                # Crear compra
                compra = Compra.objects.create(
                    cliente=cliente,
                    estado=estado_pendiente,
                    numero_factura=Compra.generar_numero_factura(),
                    fecha_compra=timezone.now(),
                    observaciones=observaciones,
                    metodo_pago=metodo_pago
                )
                
                # Agregar productos
                for item in productos_data:
                    producto = Producto.objects.get(
                        id=item['producto_id'],
                        activo=True
                    )
                    cantidad = item['cantidad']
                    
                    # Verificar stock
                    if not producto.tiene_stock_disponible(cantidad):
                        raise RepositoryValidationError(
                            f"Stock insuficiente para {producto.nombre}. "
                            f"Disponible: {producto.stock}, Solicitado: {cantidad}"
                        )
                    
                    # Crear detalle
                    DetalleCompra.crear_desde_producto(compra, producto, cantidad)
                    
                    # Reducir stock
                    producto.reducir_stock(cantidad)
                
                # Calcular totales
                compra.calcular_totales()
                
                self.logger.info(f"Compra creada exitosamente: {compra.numero_factura}")
                return compra
                
        except Cliente.DoesNotExist:
            raise RepositoryValidationError(f"Cliente {cliente_id} no encontrado o inactivo")
        except Producto.DoesNotExist:
            raise RepositoryValidationError("Uno o más productos no encontrados o inactivos")
        except EstadoCompra.DoesNotExist:
            raise RepositoryValidationError("Estado PENDIENTE no configurado en el sistema")
        except Exception as e:
            self.logger.error(f"Error creando compra completa: {e}")
            raise RepositoryValidationError(f"Error al crear compra: {e}") from e
    
    def completar_compra(self, compra_id: int) -> Compra:
        """
        Marca una compra como completada y actualiza estadísticas del cliente.
        
        Args:
            compra_id: ID de la compra a completar
            
        Returns:
            Compra completada
        """
        try:
            with transaction.atomic():
                compra = self.get_by_id_or_fail(compra_id)
                
                if compra.estado.codigo == 'COMPLETADA':
                    self.logger.warning(f"Compra {compra_id} ya está completada")
                    return compra
                
                # Cambiar estado
                estado_completada = EstadoCompra.objects.get(codigo='COMPLETADA')
                compra.estado = estado_completada
                compra.save()
                
                # Actualizar estadísticas del cliente
                compra.cliente.actualizar_estadisticas_compras()
                
                self.logger.info(f"Compra completada: {compra.numero_factura}")
                return compra
                
        except EstadoCompra.DoesNotExist:
            raise RepositoryValidationError("Estado COMPLETADA no configurado en el sistema")
        except Exception as e:
            self.logger.error(f"Error completando compra: {e}")
            raise RepositoryValidationError(f"Error al completar compra: {e}") from e
    
    def cancelar_compra(self, compra_id: int, motivo: Optional[str] = None) -> Compra:
        """
        Cancela una compra y devuelve el stock de productos.
        
        Args:
            compra_id: ID de la compra a cancelar
            motivo: Motivo opcional de cancelación
            
        Returns:
            Compra cancelada
        """
        try:
            with transaction.atomic():
                compra = self.get_by_id_or_fail(compra_id)
                
                if not compra.puede_cancelarse():
                    raise RepositoryValidationError(
                        f"La compra {compra.numero_factura} no puede ser cancelada en estado {compra.estado.nombre}"
                    )
                
                # Devolver stock
                for detalle in compra.detalles.all():
                    detalle.producto.aumentar_stock(detalle.cantidad)
                
                # Cambiar estado
                estado_cancelada = EstadoCompra.objects.get(codigo='CANCELADA')
                compra.estado = estado_cancelada
                
                if motivo:
                    compra.observaciones = f"{compra.observaciones or ''}\nCancelada: {motivo}".strip()
                
                compra.save()
                
                # Actualizar estadísticas del cliente si había compras completadas
                compra.cliente.actualizar_estadisticas_compras()
                
                self.logger.info(f"Compra cancelada: {compra.numero_factura}")
                return compra
                
        except EstadoCompra.DoesNotExist:
            raise RepositoryValidationError("Estado CANCELADA no configurado en el sistema")
        except Exception as e:
            self.logger.error(f"Error cancelando compra: {e}")
            raise RepositoryValidationError(f"Error al cancelar compra: {e}") from e
    
    def get_estadisticas_cliente(self, cliente_id: int) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas de compras de un cliente.
        
        Args:
            cliente_id: ID del cliente
            
        Returns:
            Diccionario con estadísticas del cliente
        """
        try:
            compras = self.get_compras_by_cliente(cliente_id, 'COMPLETADA')
            
            if not compras.exists():
                return {
                    'cliente_id': cliente_id,
                    'tiene_compras': False,
                    'estadisticas': {}
                }
            
            stats = compras.aggregate(
                total_gastado=Sum('monto_total'),
                numero_compras=Count('id'),
                ticket_promedio=Avg('monto_total'),
                primera_compra=Min('fecha_compra'),
                ultima_compra=Max('fecha_compra'),
                mayor_compra=Max('monto_total'),
                menor_compra=Min('monto_total')
            )
            
            # Productos más comprados
            productos_favoritos = DetalleCompra.objects.filter(
                compra__in=compras
            ).values(
                'producto__nombre',
                'producto__codigo'
            ).annotate(
                veces_comprado=Count('id'),
                cantidad_total=Sum('cantidad'),
                monto_total=Sum('subtotal_producto')
            ).order_by('-veces_comprado')[:5]
            
            # Frecuencia de compras (días entre compras)
            if stats['numero_compras'] > 1:
                primera_fecha = stats['primera_compra'].date()
                ultima_fecha = stats['ultima_compra'].date()
                dias_transcurridos = (ultima_fecha - primera_fecha).days
                frecuencia_promedio = dias_transcurridos / (stats['numero_compras'] - 1) if stats['numero_compras'] > 1 else 0
            else:
                frecuencia_promedio = 0
            
            resultado = {
                'cliente_id': cliente_id,
                'tiene_compras': True,
                'estadisticas': {
                    **stats,
                    'frecuencia_compra_dias': round(frecuencia_promedio, 1),
                    'productos_favoritos': list(productos_favoritos)
                }
            }
            
            self.logger.debug(f"Estadísticas calculadas para cliente {cliente_id}")
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas del cliente: {e}")
            raise RepositoryValidationError(f"Error al calcular estadísticas: {e}") from e
    
    def get_tendencias_ventas(self, dias: int = 30) -> Dict[str, Any]:
        """
        Analiza tendencias de ventas en los últimos N días.
        
        Args:
            dias: Número de días hacia atrás para analizar
            
        Returns:
            Diccionario con análisis de tendencias
        """
        try:
            fecha_inicio = timezone.now().date() - timedelta(days=dias)
            
            compras_periodo = self.get_queryset().filter(
                fecha_compra__date__gte=fecha_inicio,
                estado__codigo='COMPLETADA'
            )
            
            # Ventas por semana
            ventas_semanales = []
            fecha_actual = fecha_inicio
            while fecha_actual <= timezone.now().date():
                fecha_fin_semana = min(fecha_actual + timedelta(days=6), timezone.now().date())
                
                ventas_semana = compras_periodo.filter(
                    fecha_compra__date__gte=fecha_actual,
                    fecha_compra__date__lte=fecha_fin_semana
                ).aggregate(
                    total=Sum('monto_total'),
                    ordenes=Count('id')
                )
                
                ventas_semanales.append({
                    'semana_inicio': fecha_actual,
                    'semana_fin': fecha_fin_semana,
                    'ventas_total': ventas_semana['total'] or Decimal('0'),
                    'numero_ordenes': ventas_semana['ordenes'] or 0
                })
                
                fecha_actual = fecha_fin_semana + timedelta(days=1)
            
            # Categorías más vendidas
            from django.db.models import OuterRef
            categorias_top = DetalleCompra.objects.filter(
                compra__in=compras_periodo
            ).values(
                'producto__categoria__nombre'
            ).annotate(
                productos_vendidos=Sum('cantidad'),
                ingresos_categoria=Sum('subtotal_producto')
            ).order_by('-ingresos_categoria')[:10]
            
            # Crecimiento semanal
            crecimiento = []
            for i in range(1, len(ventas_semanales)):
                semana_anterior = ventas_semanales[i-1]['ventas_total']
                semana_actual = ventas_semanales[i]['ventas_total']
                
                if semana_anterior > 0:
                    crecimiento_porcentual = float((semana_actual - semana_anterior) / semana_anterior * 100)
                else:
                    crecimiento_porcentual = 0
                
                crecimiento.append({
                    'semana': i + 1,
                    'crecimiento_porcentual': round(crecimiento_porcentual, 2)
                })
            
            resultado = {
                'periodo_analisis': {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': timezone.now().date(),
                    'dias_analizados': dias
                },
                'ventas_semanales': ventas_semanales,
                'crecimiento_semanal': crecimiento,
                'categorias_top': list(categorias_top)
            }
            
            self.logger.info(f"Análisis de tendencias generado para {dias} días")
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error analizando tendencias: {e}")
            raise RepositoryValidationError(f"Error al analizar tendencias: {e}") from e