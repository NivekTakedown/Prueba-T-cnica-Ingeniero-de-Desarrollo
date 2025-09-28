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
        - CSV: Archivo de valores separados por comas
        - Excel: Archivo Microsoft Excel (xlsx)
        - TXT: Archivo de texto plano con formato legible
        
        **Información incluida:**
        - Datos básicos del cliente
        - Estadísticas de compras (opcional)
        - Historial de compras (opcional)
        - Detalle de productos por compra (opcional)
        
        El archivo se genera para descarga directa con nombre personalizable.
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
        description="Lista todos los formatos de exportación disponibles con sus descripciones",
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