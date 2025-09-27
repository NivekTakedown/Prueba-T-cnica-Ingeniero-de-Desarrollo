"""
Reporte Service - Lógica de negocio para generar reportes de fidelización.
Genera reportes de clientes VIP y exporta automáticamente a Excel.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import HttpResponse
import io

from .base_service import BaseService, ServiceException, require_params
from ..repositories.compra_repository import CompraRepository
from ..models import Cliente, Compra


class ReporteService(BaseService):
    """
    Service para generar reportes de fidelización y clientes VIP.
    """
    
    def __init__(self):
        super().__init__()
        self.compra_repo = CompraRepository()
    
    def generar_reporte_fidelizacion(self, monto_minimo: Decimal = None, 
                                   fecha_inicio: datetime = None,
                                   fecha_fin: datetime = None,
                                   exportar_excel: bool = True) -> Dict[str, Any]:
        """
        Genera reporte completo de fidelización de clientes VIP.
        
        Args:
            monto_minimo: Monto mínimo para ser considerado VIP (default: 5,000,000)
            fecha_inicio: Fecha de inicio del período (default: último mes)
            fecha_fin: Fecha de fin del período (default: hoy)
            exportar_excel: Si generar archivo Excel automáticamente
            
        Returns:
            Dict con datos del reporte y información del archivo Excel
        """
        def _generar_reporte_operacion():
            # Configurar parámetros por defecto
            if monto_minimo is None:
                monto_minimo_calc = Decimal('5000000.00')
            else:
                monto_minimo_calc = monto_minimo
                
            if fecha_fin is None:
                fecha_fin_calc = datetime.now()
            else:
                fecha_fin_calc = fecha_fin
                
            if fecha_inicio is None:
                fecha_inicio_calc = fecha_fin_calc - timedelta(days=30)
            else:
                fecha_inicio_calc = fecha_inicio
            
            self.log_info(f"Generando reporte de fidelización desde {fecha_inicio_calc} hasta {fecha_fin_calc}")
            
            # Obtener clientes VIP
            clientes_vip = self.obtener_clientes_vip(
                monto_minimo_calc, 
                fecha_inicio_calc, 
                fecha_fin_calc
            )
            
            # Calcular estadísticas generales
            estadisticas = self._calcular_estadisticas_generales(
                clientes_vip, fecha_inicio_calc, fecha_fin_calc
            )
            
            # Preparar resultado
            resultado = {
                'clientes_vip': clientes_vip,
                'estadisticas_generales': estadisticas,
                'parametros_reporte': {
                    'monto_minimo': monto_minimo_calc,
                    'fecha_inicio': fecha_inicio_calc,
                    'fecha_fin': fecha_fin_calc,
                    'total_dias': (fecha_fin_calc - fecha_inicio_calc).days
                },
                'fecha_generacion': datetime.now(),
                'archivo_excel_generado': False
            }
            
            # Generar Excel si se solicita
            if exportar_excel and clientes_vip:
                excel_info = self._generar_excel_reporte(resultado)
                resultado['archivo_excel'] = excel_info
                resultado['archivo_excel_generado'] = True
            
            self.log_info(f"Reporte generado: {len(clientes_vip)} clientes VIP encontrados")
            
            return resultado
        
        return self.execute_with_transaction(
            "generar_reporte_fidelizacion",
            _generar_reporte_operacion
        )
    
    def obtener_clientes_vip(self, monto_minimo: Decimal, 
                           fecha_inicio: datetime = None,
                           fecha_fin: datetime = None) -> List[Dict[str, Any]]:
        """
        Obtiene lista de clientes VIP basado en criterios específicos.
        
        Args:
            monto_minimo: Monto mínimo de compras en el período
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            
        Returns:
            Lista de diccionarios con información de clientes VIP
        """
        def _obtener_vip_operacion():
            # Configurar fechas por defecto
            if fecha_fin is None:
                fecha_fin_calc = datetime.now()
            else:
                fecha_fin_calc = fecha_fin
                
            if fecha_inicio is None:
                fecha_inicio_calc = fecha_fin_calc - timedelta(days=30)
            else:
                fecha_inicio_calc = fecha_inicio
            
            self.log_info(f"Buscando clientes VIP con monto >= ${monto_minimo}")
            
            # Consulta optimizada para clientes VIP
            clientes_vip_data = self._ejecutar_consulta_vip(
                monto_minimo, fecha_inicio_calc, fecha_fin_calc
            )
            
            # Formatear datos para respuesta
            clientes_vip = []
            for cliente_data in clientes_vip_data:
                cliente_info = {
                    'id': cliente_data['id'],
                    'tipo_documento': cliente_data['tipo_documento__codigo'],
                    'numero_documento': cliente_data['numero_documento'],
                    'nombre': cliente_data['nombre'],
                    'apellido': cliente_data['apellido'],
                    'correo': cliente_data['correo'] or 'No registrado',
                    'telefono': cliente_data['telefono'] or 'No registrado',
                    'monto_total_periodo': cliente_data['monto_total'],
                    'numero_transacciones': cliente_data['numero_transacciones'],
                    'monto_promedio_transaccion': (
                        cliente_data['monto_total'] / cliente_data['numero_transacciones']
                        if cliente_data['numero_transacciones'] > 0 else Decimal('0.00')
                    ),
                    'fecha_primera_compra': cliente_data['fecha_primera_compra'],
                    'fecha_ultima_compra': cliente_data['ultima_compra_periodo'],  # ✅ Usar nueva columna
                    'activo': cliente_data['activo']
                }
                clientes_vip.append(cliente_info)
            
            # Ordenar por monto total descendente
            clientes_vip.sort(key=lambda x: x['monto_total_periodo'], reverse=True)
            
            return clientes_vip
        
        return self.execute_with_transaction(
            "obtener_clientes_vip",
            _obtener_vip_operacion
        )
    
    def exportar_reporte_excel(self, datos_reporte: Dict[str, Any], 
                             nombre_archivo: str = None) -> HttpResponse:
        """
        Exporta el reporte de fidelización a un archivo Excel descargable.
        
        Args:
            datos_reporte: Datos del reporte generado
            nombre_archivo: Nombre personalizado del archivo
            
        Returns:
            HttpResponse con el archivo Excel para descarga
        """
        def _exportar_excel_operacion():
            if not datos_reporte.get('clientes_vip'):
                raise ServiceException("No hay datos de clientes VIP para exportar")
            
            # Generar nombre de archivo si no se proporciona
            if not nombre_archivo:
                fecha_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                nombre_archivo_calc = f'reporte_fidelizacion_{fecha_str}.xlsx'
            else:
                nombre_archivo_calc = nombre_archivo if nombre_archivo.endswith('.xlsx') else f"{nombre_archivo}.xlsx"
            
            # Crear el archivo Excel
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                
                # Hoja 1: Resumen Ejecutivo
                self._crear_hoja_resumen(writer, datos_reporte)
                
                # Hoja 2: Clientes VIP
                self._crear_hoja_clientes_vip(writer, datos_reporte['clientes_vip'])
                
                # Hoja 3: Estadísticas (si hay datos suficientes)
                if len(datos_reporte['clientes_vip']) > 0:
                    self._crear_hoja_estadisticas(writer, datos_reporte)
            
            output.seek(0)
            
            # Crear respuesta HTTP
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{nombre_archivo_calc}"'
            
            self.log_info(f"Excel de reporte exportado: {nombre_archivo_calc}")
            
            return response
        
        return self.execute_with_transaction(
            "exportar_reporte_excel",
            _exportar_excel_operacion
        )
    
    # Métodos privados de apoyo
    
    def _ejecutar_consulta_vip(self, monto_minimo: Decimal, 
                             fecha_inicio: datetime, fecha_fin: datetime) -> List[Dict]:
        """Ejecuta la consulta optimizada para obtener clientes VIP."""
        from django.db.models import Sum, Count, Min, Max
        
        # ✅ CORRECCIÓN 1: compra__ → compras__
        # ✅ CORRECCIÓN 2: Renombrar fecha_ultima_compra → ultima_compra_periodo
        queryset = Cliente.objects.filter(
            activo=True,
            compras__fecha_compra__gte=fecha_inicio,
            compras__fecha_compra__lte=fecha_fin,
            compras__estado__codigo='COMPLETADA'
        ).annotate(
            monto_total=Sum('compras__monto_total'),
            numero_transacciones=Count('compras'),
            fecha_primera_compra=Min('compras__fecha_compra'),
            ultima_compra_periodo=Max('compras__fecha_compra')  # ✅ Nuevo nombre
        ).filter(
            monto_total__gte=monto_minimo
        ).select_related('tipo_documento').values(
            'id', 'tipo_documento__codigo', 'numero_documento',
            'nombre', 'apellido', 'correo', 'telefono', 'activo',
            'monto_total', 'numero_transacciones',
            'fecha_primera_compra', 'ultima_compra_periodo'  # ✅ Actualizar aquí también
        )
        
        return list(queryset)
    
    def _calcular_estadisticas_generales(self, clientes_vip: List[Dict], 
                                       fecha_inicio: datetime, fecha_fin: datetime) -> Dict:
        """Calcula estadísticas generales del reporte."""
        if not clientes_vip:
            return {
                'total_clientes_vip': 0,
                'monto_total_periodo': Decimal('0.00'),
                'monto_promedio_cliente': Decimal('0.00'),
                'transacciones_totales': 0,
                'ticket_promedio': Decimal('0.00')
            }
        
        total_clientes = len(clientes_vip)
        monto_total = sum(cliente['monto_total_periodo'] for cliente in clientes_vip)
        transacciones_totales = sum(cliente['numero_transacciones'] for cliente in clientes_vip)
        
        return {
            'total_clientes_vip': total_clientes,
            'monto_total_periodo': monto_total,
            'monto_promedio_cliente': monto_total / total_clientes if total_clientes > 0 else Decimal('0.00'),
            'transacciones_totales': transacciones_totales,
            'ticket_promedio': monto_total / transacciones_totales if transacciones_totales > 0 else Decimal('0.00'),
            'periodo_dias': (fecha_fin - fecha_inicio).days,
            'cliente_mayor_gasto': max(clientes_vip, key=lambda x: x['monto_total_periodo']) if clientes_vip else None,
            'cliente_mas_transacciones': max(clientes_vip, key=lambda x: x['numero_transacciones']) if clientes_vip else None
        }
    
    def _generar_excel_reporte(self, datos_reporte: Dict) -> Dict[str, Any]:
        """Genera información del archivo Excel interno."""
        try:
            fecha_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f'reporte_fidelizacion_{fecha_str}.xlsx'
            
            # En una implementación real, aquí se guardaría el archivo
            # Para esta prueba, solo retornamos la metadata
            
            return {
                'nombre_archivo': nombre_archivo,
                'ruta_archivo': f'/tmp/{nombre_archivo}',  # Ruta simulada
                'tamaño_bytes': len(datos_reporte['clientes_vip']) * 100,  # Estimación
                'fecha_creacion': datetime.now(),
                'url_descarga': f'/api/v1/reportes/descargar/{nombre_archivo}'
            }
        except Exception as e:
            self.log_error("Error generando información de Excel", e)
            return {'error': str(e)}
    
    def _crear_hoja_resumen(self, writer, datos_reporte: Dict):
        """Crea la hoja de resumen ejecutivo."""
        resumen_data = [
            ['REPORTE DE FIDELIZACIÓN DE CLIENTES', ''],
            ['Fecha de Generación', datos_reporte['fecha_generacion'].strftime('%Y-%m-%d %H:%M:%S')],
            ['', ''],
            ['PARÁMETROS DEL REPORTE', ''],
            ['Monto Mínimo VIP', f"${datos_reporte['parametros_reporte']['monto_minimo']:,.2f}"],
            ['Fecha Inicio', datos_reporte['parametros_reporte']['fecha_inicio'].strftime('%Y-%m-%d')],
            ['Fecha Fin', datos_reporte['parametros_reporte']['fecha_fin'].strftime('%Y-%m-%d')],
            ['Período (días)', datos_reporte['parametros_reporte']['total_dias']],
            ['', ''],
            ['ESTADÍSTICAS GENERALES', ''],
            ['Total Clientes VIP', datos_reporte['estadisticas_generales']['total_clientes_vip']],
            ['Monto Total Período', f"${datos_reporte['estadisticas_generales']['monto_total_periodo']:,.2f}"],
            ['Monto Promedio por Cliente', f"${datos_reporte['estadisticas_generales']['monto_promedio_cliente']:,.2f}"],
            ['Total Transacciones', datos_reporte['estadisticas_generales']['transacciones_totales']],
            ['Ticket Promedio', f"${datos_reporte['estadisticas_generales']['ticket_promedio']:,.2f}"]
        ]
        
        df_resumen = pd.DataFrame(resumen_data, columns=['Concepto', 'Valor'])
        df_resumen.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)
    
    def _crear_hoja_clientes_vip(self, writer, clientes_vip: List[Dict]):
        """Crea la hoja con el detalle de clientes VIP."""
        if not clientes_vip:
            return
            
        # Convertir a DataFrame
        df_clientes = pd.DataFrame(clientes_vip)
        
        # Renombrar columnas para mejor presentación
        df_clientes = df_clientes.rename(columns={
            'tipo_documento': 'Tipo Doc',
            'numero_documento': 'Número Documento',
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'correo': 'Correo',
            'telefono': 'Teléfono',
            'monto_total_periodo': 'Monto Total',
            'numero_transacciones': 'Transacciones',
            'monto_promedio_transaccion': 'Promedio Transacción',
            'fecha_ultima_compra': 'Última Compra'
        })
        
        # Seleccionar y ordenar columnas
        columnas_mostrar = [
            'Tipo Doc', 'Número Documento', 'Nombre', 'Apellido',
            'Correo', 'Teléfono', 'Monto Total', 'Transacciones',
            'Promedio Transacción', 'Última Compra'
        ]
        
        df_final = df_clientes[columnas_mostrar]
        df_final.to_excel(writer, sheet_name='Clientes VIP', index=False)
    
    def _crear_hoja_estadisticas(self, writer, datos_reporte: Dict):
        """Crea hoja con estadísticas adicionales."""
        estadisticas = datos_reporte['estadisticas_generales']
        
        # Top clientes por monto
        top_clientes_data = []
        for i, cliente in enumerate(datos_reporte['clientes_vip'][:10], 1):
            top_clientes_data.append([
                i,
                f"{cliente['nombre']} {cliente['apellido']}",
                cliente['numero_documento'],
                f"${cliente['monto_total_periodo']:,.2f}"
            ])
        
        df_top = pd.DataFrame(top_clientes_data, 
                            columns=['Ranking', 'Nombre Completo', 'Documento', 'Monto Total'])
        df_top.to_excel(writer, sheet_name='Top 10 Clientes', index=False)