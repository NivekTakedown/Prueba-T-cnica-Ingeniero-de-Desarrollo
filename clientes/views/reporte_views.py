"""
Reporte Views - Endpoints para generación de reportes y análisis de datos.
Incluye reportes de fidelización de clientes VIP con exportación automática.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .base_views import BaseAPIView, ValidationMixin, SwaggerSchemaMixin, FileResponseMixin
from ..services import ReporteService
from ..serializers import (
    ReporteFidelizacionRequestSerializer,
    ReporteFidelizacionResponseSerializer,
    ErrorResponseSerializer
)


class ReporteFidelizacionAPIView(BaseAPIView, ValidationMixin, FileResponseMixin, SwaggerSchemaMixin):
    """
    API para generar reportes de fidelización de clientes VIP.
    
    Permite generar reportes con clientes que superan un monto mínimo 
    de compras en un período específico, con opciones para filtrar 
    por fechas y exportar automáticamente a Excel.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reporte_service = ReporteService()
    
    @extend_schema(
        summary="Generar reporte de fidelización",
        description="""
        Genera un reporte de clientes VIP que han superado un monto mínimo de compras 
        en un período específico, con opción de exportación automática a Excel.
        
        **Información incluida:**
        - Datos básicos de los clientes VIP
        - Estadísticas de compras por cliente
        - Métricas de fidelización
        - Resumen ejecutivo del período
        
        **Parámetros opcionales:**
        - `fecha_inicio`: Fecha de inicio del período (formato YYYY-MM-DD)
        - `fecha_fin`: Fecha de fin del período (formato YYYY-MM-DD)
        - `monto_minimo`: Monto mínimo para considerar cliente VIP (default: 5000000)
        - `exportar_excel`: Si generar archivo Excel directamente (default: true)
        
        **URL de ejemplo:**
        ```
        GET /api/v1/reportes/fidelizacion/?fecha_inicio=2025-08-01&fecha_fin=2025-08-31&monto_minimo=5000000&exportar_excel=false
        ```
        
        **Ejemplo de respuesta JSON:**
        ```json
        {
            "success": true,
            "message": "Reporte de fidelización generado exitosamente",
            "data": {
                "clientes_vip": [
                    {
                        "id": 4,
                        "tipo_documento": "CC",
                        "numero_documento": "12345678",
                        "nombre_completo": "Juan Pérez",
                        "correo": "juan.perez@ejemplo.com",
                        "monto_total_periodo": 8500000.00,
                        "numero_transacciones": 5,
                        "fecha_ultima_compra": "2025-08-28T10:15:30Z"
                    },
                    {
                        "id": 7,
                        "tipo_documento": "NIT",
                        "numero_documento": "9001234567",
                        "nombre_completo": "Empresa ABC",
                        "correo": "contacto@empresaabc.com",
                        "monto_total_periodo": 12750000.00,
                        "numero_transacciones": 8,
                        "fecha_ultima_compra": "2025-08-30T16:45:20Z"
                    }
                ],
                "estadisticas_generales": {
                    "total_clientes_vip": 2,
                    "monto_total_periodo": 21250000.00,
                    "monto_promedio_cliente": 10625000.00,
                    "transacciones_totales": 13,
                    "ticket_promedio": 1634615.38,
                    "periodo_dias": 31,
                    "cliente_mayor_gasto": "Empresa ABC (NIT: 9001234567)"
                }
            },
            "meta": {
                "fecha_generacion": "2025-09-28T14:40:22Z",
                "total_clientes_vip": 2,
                "parametros": {
                    "fecha_inicio": "2025-08-01",
                    "fecha_fin": "2025-08-31",
                    "monto_minimo": 5000000.00
                }
            },
            "timestamp": "2025-09-28T14:40:22Z"
        }
        ```
        
        **Notas:**
        - Si `exportar_excel=true`, la respuesta será un archivo Excel para descarga
        - Por defecto, analiza el último mes completo
        """,
        parameters=[
            OpenApiParameter(
                name='fecha_inicio',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Fecha de inicio del período (por defecto: último mes)',
                required=False
            ),
            OpenApiParameter(
                name='fecha_fin',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Fecha de fin del período (por defecto: hoy)',
                required=False
            ),
            OpenApiParameter(
                name='monto_minimo',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Monto mínimo para considerar cliente VIP',
                default="5000000.00",
                required=False
            ),
            OpenApiParameter(
                name='exportar_excel',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Generar archivo Excel automáticamente',
                default=True,
                required=False
            )
        ],
        responses={
            200: OpenApiResponse(
                response=ReporteFidelizacionResponseSerializer,
                description="Reporte generado exitosamente"
            ),
            # Si exportar_excel=True, la respuesta será un archivo Excel en lugar de JSON
            # DRF Spectacular no soporta bien responses condicionales, así que documentamos ambas
            # posibilidades
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": OpenApiResponse(
                description="Archivo Excel con el reporte de fidelización"
            ),
            400: SwaggerSchemaMixin.get_error_schema("Error de validación en los parámetros"),
            500: SwaggerSchemaMixin.get_error_schema("Error interno del servidor")
        },
        tags=['Reportes'],
        operation_id='reporte_fidelizacion'
    )
    def get(self, request: Request) -> Response:
        """
        Genera reporte de fidelización de clientes VIP por método GET.
        
        Los parámetros se reciben como query parameters.
        """
        try:
            # Extraer parámetros de query
            params = {
                'fecha_inicio': request.query_params.get('fecha_inicio'),
                'fecha_fin': request.query_params.get('fecha_fin'),
                'monto_minimo': request.query_params.get('monto_minimo'),
                'exportar_excel': request.query_params.get('exportar_excel', 'true').lower() in ('true', 't', 'yes', 'y', '1')
            }
            
            # Procesar parámetros
            return self._procesar_reporte(params)
            
        except Exception as e:
            return self.handle_exception(e)
    
    @extend_schema(
        summary="Generar reporte de fidelización (POST)",
        description="""
        Versión POST del generador de reportes de fidelización.
        Permite especificar parámetros en el cuerpo de la petición.
        
        **Ejemplo de solicitud:**
        ```json
        {
            "fecha_inicio": "2025-08-01",
            "fecha_fin": "2025-09-30",
            "monto_minimo": 5000000,
            "exportar_excel": true,
            "nombre_archivo": "reporte_vip_q3_2025"
        }
        ```
        
        Útil para interfaces complejas o para integración con otros sistemas
        que necesitan enviar parámetros detallados.
        """,
        request=ReporteFidelizacionRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=ReporteFidelizacionResponseSerializer,
                description="Reporte generado exitosamente"
            ),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": OpenApiResponse(
                description="Archivo Excel con el reporte de fidelización"
            ),
            400: SwaggerSchemaMixin.get_error_schema("Error de validación en los parámetros"),
            500: SwaggerSchemaMixin.get_error_schema("Error interno del servidor")
        },
        tags=['Reportes'],
        operation_id='reporte_fidelizacion_post'
    )
    def post(self, request: Request) -> Response:
        """
        Genera reporte de fidelización de clientes VIP por método POST.
        
        Los parámetros se reciben en el cuerpo de la petición.
        """
        try:
            # Validar datos del request con serializer
            serializer = ReporteFidelizacionRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    message="Parámetros de reporte inválidos",
                    code="VALIDATION_ERROR",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    details={"validation_errors": serializer.errors}
                )
            
            # Procesar parámetros validados
            return self._procesar_reporte(serializer.validated_data)
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _procesar_reporte(self, params: dict) -> Response:
        """
        Procesa los parámetros y genera el reporte de fidelización.
        
        Args:
            params: Diccionario con parámetros del reporte
                - fecha_inicio: Fecha de inicio del período (opcional)
                - fecha_fin: Fecha de fin del período (opcional)
                - monto_minimo: Monto mínimo para considerar cliente VIP (opcional)
                - exportar_excel: Si generar archivo Excel (opcional, default=True)
        
        Returns:
            Response con el reporte (JSON o Excel dependiendo de exportar_excel)
        """
        # Extraer y procesar parámetros
        fecha_inicio = params.get('fecha_inicio')
        fecha_fin = params.get('fecha_fin')
        
        # Convertir monto_minimo a Decimal si existe
        monto_minimo = params.get('monto_minimo')
        if monto_minimo is not None:
            if isinstance(monto_minimo, str):
                monto_minimo = Decimal(monto_minimo)
        else:
            monto_minimo = Decimal('5000000.00')
        
        # Determinar si exportar a Excel
        exportar_excel = params.get('exportar_excel', True)
        
        # Generar el reporte
        self.logger.info(
            f"Generando reporte de fidelización: "
            f"fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, "
            f"monto_minimo={monto_minimo}, exportar_excel={exportar_excel}"
        )
        
        # Llamar al servicio de reportes
        datos_reporte = self.reporte_service.generar_reporte_fidelizacion(
            monto_minimo=monto_minimo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            exportar_excel=exportar_excel
        )
        
        # Si se solicitó exportar a Excel, devolver el archivo
        if exportar_excel:
            # Obtener el nombre personalizado o generar uno por defecto
            nombre_archivo = params.get('nombre_archivo')
            if not nombre_archivo:
                hoy = datetime.now().strftime('%Y%m%d')
                nombre_archivo = f"reporte_fidelizacion_{hoy}"
            
            # El servicio devuelve una respuesta HTTP con el archivo Excel
            excel_response = self.reporte_service.exportar_reporte_excel(
                datos_reporte, nombre_archivo
            )
            
            # Registrar exportación en logs
            self.logger.info(
                f"Exportado reporte de fidelización a Excel: {nombre_archivo}.xlsx"
            )
            
            return excel_response
        
        # Si no se exporta a Excel, devolver datos en JSON
        return self.success_response(
            data=datos_reporte,
            message="Reporte de fidelización generado exitosamente",
            meta={
                "fecha_generacion": datetime.now().isoformat(),
                "total_clientes_vip": len(datos_reporte.get('clientes_vip', [])),
                "parametros": {
                    "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else None,
                    "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
                    "monto_minimo": float(monto_minimo)
                }
            }
        )