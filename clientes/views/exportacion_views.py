"""
Exportación Views - Endpoints para exportar datos de clientes en múltiples formatos.
Soporta CSV, Excel y TXT con información completa del cliente y sus compras.
"""

import logging
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .base_views import BaseAPIView, ValidationMixin, SwaggerSchemaMixin, FileResponseMixin
from ..services import ExportacionService
from ..serializers import (
    ExportacionRequestSerializer,
    ErrorResponseSerializer,
    SuccessResponseSerializer
)


class ExportarClienteAPIView(BaseAPIView, ValidationMixin, FileResponseMixin, SwaggerSchemaMixin):
    """
    API para exportar datos completos de clientes en diferentes formatos.
    
    Permite exportar datos de clientes por tipo y número de documento
    en formatos CSV, Excel y TXT, con opciones personalizables para
    incluir historial de compras y detalle de productos.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.exportacion_service = ExportacionService()
    
    @extend_schema(
        summary="Exportar datos de cliente",
        description="""
        Exporta información completa de un cliente en el formato especificado.
        
        **Formatos disponibles:**
        - **CSV**: Archivo de valores separados por comas
        - **Excel**: Archivo Microsoft Excel (xlsx) con múltiples hojas
        - **TXT**: Archivo de texto plano con formato legible
        
        **Información incluida:**
        - Datos básicos del cliente
        - Estadísticas de compras (opcional)
        - Historial de compras (opcional)
        - Detalle de productos por compra (opcional)
        
        **Ejemplo de solicitud:**
        ```json
        {
            "tipo_documento": "CC",
            "numero_documento": "12345678",
            "formato": "excel",
            "incluir_compras": true,
            "incluir_productos": true,
            "nombre_archivo": "reporte_cliente_premium"
        }
        ```
        
        El archivo se genera para descarga directa con nombre personalizable.
        El Content-Type de la respuesta varía según el formato solicitado.
        """,
        request=ExportacionRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Archivo generado exitosamente para descarga",
                response=None  # Es un archivo para descarga, no un JSON
            ),
            400: SwaggerSchemaMixin.get_error_schema("Error de validación en los datos de entrada"),
            404: SwaggerSchemaMixin.get_error_schema("Cliente no encontrado"),
            500: SwaggerSchemaMixin.get_error_schema("Error interno del servidor")
        },
        tags=['Exportación'],
        operation_id='exportar_cliente'
    )
    def post(self, request: Request) -> Response:
        """
        Exporta datos de un cliente en el formato solicitado.
        
        Genera un archivo para descarga con la información completa
        del cliente según el formato y opciones especificadas.
        """
        try:
            # Validar datos del request
            serializer = ExportacionRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    message="Datos de exportación inválidos",
                    code="VALIDATION_ERROR",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    details={"validation_errors": serializer.errors}
                )
            
            # Obtener parámetros validados
            tipo_documento = serializer.validated_data['tipo_documento']
            numero_documento = serializer.validated_data['numero_documento']
            formato = serializer.validated_data.get('formato', 'csv')
            incluir_compras = serializer.validated_data.get('incluir_compras', True)
            incluir_productos = serializer.validated_data.get('incluir_productos', False)
            nombre_archivo = serializer.validated_data.get('nombre_archivo')
            
            # Validar formato del documento
            tipo_documento, numero_documento = self.validate_documento(
                tipo_documento, numero_documento
            )
            
            # Llamar al servicio de exportación
            response = self.exportacion_service.exportar_cliente(
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                formato=formato,
                incluir_compras=incluir_compras,
                incluir_productos=incluir_productos
            )
            
            # Personalizar nombre de archivo si se proporciona
            if nombre_archivo:
                extension = self._get_extension_for_format(formato)
                filename = f"{nombre_archivo}{extension}"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Registrar la exportación en logs
            self.logger.info(
                f"Archivo {formato} generado para cliente {tipo_documento}:{numero_documento}",
                extra={
                    "tipo_documento": tipo_documento,
                    "numero_documento": numero_documento,
                    "formato": formato,
                    "incluir_compras": incluir_compras,
                    "incluir_productos": incluir_productos
                }
            )
            
            return response
            
        except Exception as e:
            return self.handle_exception(e)
    
    @extend_schema(
        summary="Obtener formatos de exportación disponibles",
        description="""
        Lista todos los formatos de exportación disponibles con sus descripciones y capacidades.
        
        **Ejemplo de respuesta:**
        ```json
        {
            "success": true,
            "message": "Formatos de exportación obtenidos exitosamente",
            "data": [
                {
                    "codigo": "csv",
                    "nombre": "CSV (Comma Separated Values)",
                    "extension": ".csv",
                    "descripcion": "Archivo de texto con valores separados por comas",
                    "content_type": "text/csv",
                    "incluye_formato": false,
                    "soporta_multihoja": false
                },
                {
                    "codigo": "excel",
                    "nombre": "Microsoft Excel",
                    "extension": ".xlsx",
                    "descripcion": "Archivo de hoja de cálculo Excel con múltiples hojas",
                    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "incluye_formato": true,
                    "soporta_multihoja": true
                },
                {
                    "codigo": "txt",
                    "nombre": "Texto plano",
                    "extension": ".txt",
                    "descripcion": "Archivo de texto plano con formato legible",
                    "content_type": "text/plain",
                    "incluye_formato": false,
                    "soporta_multihoja": false
                }
            ],
            "meta": {
                "total_formatos": 3
            },
            "timestamp": "2025-09-28T14:35:40Z"
        }
        ```
        """,
        responses={
            200: OpenApiResponse(
                description="Lista de formatos disponibles obtenida exitosamente",
                response=SuccessResponseSerializer
            ),
            500: SwaggerSchemaMixin.get_error_schema("Error interno del servidor")
        },
        tags=['Exportación'],
        operation_id='formatos_exportacion'
    )
    def get(self, request: Request) -> Response:
        """
        Obtiene la lista de formatos de exportación disponibles.
        
        Útil para interfaces de usuario que necesitan mostrar
        las opciones disponibles de formatos de exportación.
        """
        try:
            # Obtener formatos disponibles del servicio
            formatos = self.exportacion_service.obtener_formatos_disponibles()
            
            # Preparar respuesta
            return self.success_response(
                data=formatos,
                message="Formatos de exportación obtenidos exitosamente",
                meta={
                    "total_formatos": len(formatos)
                }
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def _get_extension_for_format(self, formato: str) -> str:
        """Obtiene la extensión de archivo según el formato"""
        extensiones = {
            "csv": ".csv",
            "excel": ".xlsx",
            "txt": ".txt"
        }
        return extensiones.get(formato.lower(), ".csv")