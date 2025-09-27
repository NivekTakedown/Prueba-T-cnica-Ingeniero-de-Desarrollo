"""
Exportación Service - Lógica de negocio para exportar datos de clientes.
Soporta CSV, Excel y TXT con información completa del cliente y sus compras.
"""

import csv
import io
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from django.http import HttpResponse

from .base_service import BaseService, ServiceException, require_params
from .cliente_service import ClienteService
from ..models import Cliente, Compra, DetalleCompra


class ExportacionService(BaseService):
    """
    Service para manejo de exportación de datos de clientes en múltiples formatos.
    """
    
    def __init__(self):
        super().__init__()
        self.cliente_service = ClienteService()
    
    def exportar_cliente(self, tipo_documento: str, numero_documento: str, 
                        formato: str = 'csv', incluir_compras: bool = True,
                        incluir_productos: bool = False) -> HttpResponse:
        """
        Exporta información completa de un cliente en el formato especificado.
        
        Args:
            tipo_documento: Tipo de documento del cliente
            numero_documento: Número de documento del cliente
            formato: Formato de exportación ('csv', 'excel', 'txt')
            incluir_compras: Si incluir historial de compras
            incluir_productos: Si incluir detalle de productos
            
        Returns:
            HttpResponse con el archivo para descarga
        """
        def _exportar_operacion():
            # Validar parámetros
            require_params({
                'tipo_documento': tipo_documento,
                'numero_documento': numero_documento,
                'formato': formato
            }, 'tipo_documento', 'numero_documento', 'formato')
            
            # Validar formato
            if formato not in ['csv', 'excel', 'txt']:
                raise ServiceException("Formato no soportado. Use: csv, excel, txt")
            
            # Obtener datos del cliente
            resultado_cliente = self.cliente_service.buscar_cliente_por_documento(
                tipo_documento, numero_documento
            )
            
            cliente = resultado_cliente['cliente']
            
            # Obtener información completa
            info_completa = self.cliente_service.obtener_informacion_completa(
                cliente.id, incluir_compras=incluir_compras
            )
            
            # Preparar datos para exportación
            datos_exportacion = self._preparar_datos_exportacion(
                info_completa, incluir_productos
            )
            
            # Generar archivo según formato
            if formato == 'csv':
                return self._generar_csv(datos_exportacion, numero_documento)
            elif formato == 'excel':
                return self._generar_excel(datos_exportacion, numero_documento)
            elif formato == 'txt':
                return self._generar_txt(datos_exportacion, numero_documento)
        
        return self.execute_with_transaction(
            "exportar_cliente", 
            _exportar_operacion
        )
    
    def _preparar_datos_exportacion(self, info_completa: Dict, incluir_productos: bool = False) -> Dict:
        """Prepara los datos en estructura optimizada para exportación."""
        cliente = info_completa['cliente']
        estadisticas = info_completa['estadisticas_compras']
        
        # ✅ Obtener descripción del tipo de documento de forma segura
        try:
            if hasattr(cliente.tipo_documento, 'descripcion'):
                tipo_doc_desc = cliente.tipo_documento.descripcion
            elif hasattr(cliente.tipo_documento, 'nombre'):
                tipo_doc_desc = cliente.tipo_documento.nombre
            else:
                tipo_doc_desc = cliente.tipo_documento.codigo
        except AttributeError:
            tipo_doc_desc = str(cliente.tipo_documento)
        
        # Información básica del cliente
        datos = {
            'cliente_info': {
                'tipo_documento': tipo_doc_desc,
                'numero_documento': cliente.numero_documento,
                'nombre_completo': f"{cliente.nombre} {cliente.apellido}",
                'correo': cliente.correo or 'No registrado',
                'telefono': cliente.telefono or 'No registrado',
                'fecha_registro': cliente.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
                'activo': 'Sí' if cliente.activo else 'No'
            },
            'estadisticas': {
                'total_compras': estadisticas.get('total_compras', 0),
                'monto_total_historico': float(estadisticas.get('monto_total_historico', 0)),
                'monto_promedio': float(estadisticas.get('monto_promedio', 0)),
                'compras_ultimo_mes': estadisticas.get('compras_ultimo_mes', 0),
                'monto_ultimo_mes': float(estadisticas.get('monto_ultimo_mes', 0)),
                'cliente_vip': 'Sí' if estadisticas.get('cliente_vip', False) else 'No',
                'ultima_compra': estadisticas.get('ultima_compra', 'Nunca')
            },
            'compras': [],
            'productos': []
        }
        
        # Agregar compras si están disponibles
        if 'compras_recientes' in info_completa and info_completa['compras_recientes']:
            for compra in info_completa['compras_recientes']:
                compra_info = {
                    'numero_factura': compra.numero_factura,
                    'fecha_compra': compra.fecha_compra.strftime('%Y-%m-%d %H:%M:%S'),
                    'monto_total': float(compra.monto_total),
                    'estado': compra.estado.nombre if compra.estado else 'N/A',
                    'subtotal': float(compra.subtotal),
                    'descuento_total': float(compra.descuento_total),
                    'iva_total': float(compra.iva_total)
                }
                datos['compras'].append(compra_info)
                
                # Agregar productos si se solicita
                if incluir_productos:
                    detalles = DetalleCompra.objects.filter(compra=compra).select_related('producto')
                    for detalle in detalles:
                        producto_info = {
                            'factura': compra.numero_factura,
                            'producto_codigo': detalle.producto.codigo,
                            'producto_nombre': detalle.producto.nombre,
                            'cantidad': detalle.cantidad,
                            'precio_unitario': float(detalle.precio_unitario),
                            'subtotal_producto': float(detalle.subtotal_producto),
                            'descuento_aplicado': float(detalle.descuento_aplicado),
                            'iva_aplicado': float(detalle.iva_aplicado)
                        }
                        datos['productos'].append(producto_info)
        
        return datos
    
    def _generar_csv(self, datos: Dict, numero_documento: str) -> HttpResponse:
        """Genera archivo CSV con los datos del cliente."""
        output = io.StringIO()
        
        # Información del cliente
        output.write("=== INFORMACIÓN DEL CLIENTE ===\n")
        for key, value in datos['cliente_info'].items():
            output.write(f"{key.replace('_', ' ').title()},{value}\n")
        
        # Estadísticas
        output.write("\n=== ESTADÍSTICAS DE COMPRAS ===\n")
        for key, value in datos['estadisticas'].items():
            output.write(f"{key.replace('_', ' ').title()},{value}\n")
        
        # Compras
        if datos['compras']:
            output.write("\n=== HISTORIAL DE COMPRAS ===\n")
            
            # Headers
            compra_headers = ['Número Factura', 'Fecha Compra', 'Monto Total', 'Estado', 'Subtotal', 'Descuento', 'IVA']
            output.write(','.join(compra_headers) + '\n')
            
            # Datos
            for compra in datos['compras']:
                row = [
                    compra['numero_factura'],
                    compra['fecha_compra'],
                    f"${compra['monto_total']:,.2f}",
                    compra['estado'],
                    f"${compra['subtotal']:,.2f}",
                    f"${compra['descuento_total']:,.2f}",
                    f"${compra['iva_total']:,.2f}"
                ]
                output.write(','.join(map(str, row)) + '\n')
        
        # Productos (si están incluidos)
        if datos['productos']:
            output.write("\n=== DETALLE DE PRODUCTOS ===\n")
            
            # Headers
            producto_headers = ['Factura', 'Código Producto', 'Nombre Producto', 'Cantidad', 'Precio Unit.', 'Subtotal', 'Descuento', 'IVA']
            output.write(','.join(producto_headers) + '\n')
            
            # Datos
            for producto in datos['productos']:
                row = [
                    producto['factura'],
                    producto['producto_codigo'],
                    producto['producto_nombre'],
                    producto['cantidad'],
                    f"${producto['precio_unitario']:,.2f}",
                    f"${producto['subtotal_producto']:,.2f}",
                    f"${producto['descuento_aplicado']:,.2f}",
                    f"${producto['iva_aplicado']:,.2f}"
                ]
                output.write(','.join(map(str, row)) + '\n')
        
        # Crear respuesta HTTP
        response = HttpResponse(
            output.getvalue(),
            content_type='text/csv',
            charset='utf-8-sig'  # Para caracteres especiales
        )
        
        filename = f"cliente_{numero_documento}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        self.log_info(f"Archivo CSV generado: {filename}")
        return response
    
    def _generar_excel(self, datos: Dict, numero_documento: str) -> HttpResponse:
        """Genera archivo Excel con los datos del cliente."""
        output = io.BytesIO()
        
        # Crear Excel con pandas
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Hoja 1: Información del cliente
            cliente_df = pd.DataFrame(list(datos['cliente_info'].items()), 
                                    columns=['Campo', 'Valor'])
            cliente_df.to_excel(writer, sheet_name='Información Cliente', index=False)
            
            # Hoja 2: Estadísticas
            stats_df = pd.DataFrame(list(datos['estadisticas'].items()), 
                                  columns=['Estadística', 'Valor'])
            stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)
            
            # Hoja 3: Compras (si existen)
            if datos['compras']:
                compras_df = pd.DataFrame(datos['compras'])
                compras_df.to_excel(writer, sheet_name='Historial Compras', index=False)
            
            # Hoja 4: Productos (si existen)
            if datos['productos']:
                productos_df = pd.DataFrame(datos['productos'])
                productos_df.to_excel(writer, sheet_name='Detalle Productos', index=False)
        
        output.seek(0)
        
        # Crear respuesta HTTP
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f"cliente_{numero_documento}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        self.log_info(f"Archivo Excel generado: {filename}")
        return response
    
    def _generar_txt(self, datos: Dict, numero_documento: str) -> HttpResponse:
        """Genera archivo TXT con los datos del cliente."""
        output = io.StringIO()
        
        # Header del reporte
        output.write("=" * 80 + "\n")
        output.write("REPORTE DE CLIENTE - RÍOS DEL DESIERTO SAC\n")
        output.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write("=" * 80 + "\n\n")
        
        # Información del cliente
        output.write("INFORMACIÓN DEL CLIENTE\n")
        output.write("-" * 40 + "\n")
        for key, value in datos['cliente_info'].items():
            label = key.replace('_', ' ').title().ljust(20)
            output.write(f"{label}: {value}\n")
        
        # Estadísticas
        output.write(f"\nESTADÍSTICAS DE COMPRAS\n")
        output.write("-" * 40 + "\n")
        for key, value in datos['estadisticas'].items():
            label = key.replace('_', ' ').title().ljust(25)
            if isinstance(value, (int, float)) and 'monto' in key:
                output.write(f"{label}: ${value:,.2f}\n")
            else:
                output.write(f"{label}: {value}\n")
        
        # Compras
        if datos['compras']:
            output.write(f"\nHISTORIAL DE COMPRAS ({len(datos['compras'])} compras)\n")
            output.write("-" * 80 + "\n")
            
            for i, compra in enumerate(datos['compras'], 1):
                output.write(f"\n{i}. Factura: {compra['numero_factura']}\n")
                output.write(f"   Fecha: {compra['fecha_compra']}\n")
                output.write(f"   Monto Total: ${compra['monto_total']:,.2f}\n")
                output.write(f"   Estado: {compra['estado']}\n")
                output.write(f"   Subtotal: ${compra['subtotal']:,.2f} | ")
                output.write(f"Descuento: ${compra['descuento_total']:,.2f} | ")
                output.write(f"IVA: ${compra['iva_total']:,.2f}\n")
        
        # Productos
        if datos['productos']:
            output.write(f"\nDETALLE DE PRODUCTOS ({len(datos['productos'])} productos)\n")
            output.write("-" * 80 + "\n")
            
            for i, producto in enumerate(datos['productos'], 1):
                output.write(f"\n{i}. {producto['producto_nombre']} ({producto['producto_codigo']})\n")
                output.write(f"   Factura: {producto['factura']}\n")
                output.write(f"   Cantidad: {producto['cantidad']} | ")
                output.write(f"Precio Unit.: ${producto['precio_unitario']:,.2f}\n")
                output.write(f"   Subtotal: ${producto['subtotal_producto']:,.2f} | ")
                output.write(f"Descuento: ${producto['descuento_aplicado']:,.2f}\n")
        
        # Footer
        output.write(f"\n" + "=" * 80 + "\n")
        output.write("Fin del reporte\n")
        
        # Crear respuesta HTTP
        response = HttpResponse(
            output.getvalue(),
            content_type='text/plain',
            charset='utf-8'
        )
        
        filename = f"cliente_{numero_documento}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        self.log_info(f"Archivo TXT generado: {filename}")
        return response
    
    def obtener_formatos_disponibles(self) -> List[Dict[str, str]]:
        """Retorna lista de formatos de exportación disponibles."""
        return [
            {'codigo': 'csv', 'nombre': 'CSV - Comma Separated Values', 'extension': '.csv'},
            {'codigo': 'excel', 'nombre': 'Excel - Microsoft Excel', 'extension': '.xlsx'},
            {'codigo': 'txt', 'nombre': 'TXT - Texto plano', 'extension': '.txt'}
        ]