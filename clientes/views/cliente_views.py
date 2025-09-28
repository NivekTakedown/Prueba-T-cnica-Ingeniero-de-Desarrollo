"""
Cliente Views - Endpoints para búsqueda de clientes y tipos de documento.
Incluye documentación Swagger completa.
"""

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes

from .base_views import BaseAPIView, ValidationMixin, SwaggerSchemaMixin
from ..services import ClienteService
from ..serializers import (
    BusquedaClienteRequestSerializer,
    BusquedaClienteResponseSerializer,
    TipoDocumentoSerializer
)
from ..models import TipoDocumento


class BuscarClienteAPIView(BaseAPIView, ValidationMixin, SwaggerSchemaMixin):
    """
    API para buscar cliente por tipo y número de documento.
    
    Retorna información completa del cliente incluyendo:
    - Datos básicos del cliente
    - Estadísticas de compras
    - Historial de compras recientes
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cliente_service = ClienteService()
    
    @extend_schema(
        summary="Buscar cliente por documento",
        description="""
        Busca un cliente específico por su tipo y número de documento.
        
        **Funcionalidades:**
        - Búsqueda exacta por documento
        - Información completa del cliente
        - Estadísticas de compras
        - Historial de compras recientes
        - Validaciones de formato de documento
        
        **Ejemplos de uso:**
        ```json
        {
            "tipo_documento": "CC",
            "numero_documento": "12345678",
            "incluir_compras": true,
            "limite_compras": 5
        }
        ```
        
        **Respuesta exitosa:**
        ```json
        {
            "success": true,
            "message": "Cliente encontrado exitosamente",
            "data": {
                "cliente": {
                    "id": 4,
                    "tipo_documento": {"codigo": "CC", "nombre": "Cédula de Ciudadanía"},
                    "numero_documento": "12345678",
                    "nombre": "Juan",
                    "apellido": "Pérez",
                    "correo": "juan.perez@ejemplo.com"
                },
                "estadisticas_compras": {
                    "total_compras": 3,
                    "monto_total_historico": 1250000.00,
                    "monto_promedio": 416666.67
                },
                "compras": [
                    {
                        "id": 12,
                        "fecha_compra": "2025-08-15T10:30:00Z",
                        "monto_total": 450000.00,
                        "estado": "COMPLETADA"
                    }
                ]
            },
            "timestamp": "2025-09-28T14:30:45Z"
        }
        ```
        """,
        request=BusquedaClienteRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=BusquedaClienteResponseSerializer,
                description="Cliente encontrado exitosamente"
            ),
            400: SwaggerSchemaMixin.get_error_schema("Error de validación"),
            404: SwaggerSchemaMixin.get_error_schema("Cliente no encontrado"),
            500: SwaggerSchemaMixin.get_error_schema("Error interno del servidor")
        },
        tags=['Clientes'],
        operation_id='buscar_cliente'
    )
    def post(self, request: Request) -> Response:
        """
        Busca un cliente por tipo y número de documento.
        """
        # Validar datos del request
        serializer = BusquedaClienteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Datos de entrada inválidos",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"validation_errors": serializer.errors}
            )
        
        # Extraer y validar parámetros
        tipo_documento = serializer.validated_data['tipo_documento']
        numero_documento = serializer.validated_data['numero_documento']
        incluir_compras = serializer.validated_data.get('incluir_compras', True)
        limite_compras = serializer.validated_data.get('limite_compras', 10)
        
        try:
            # Validar formato de documento
            tipo_documento, numero_documento = self.validate_documento(
                tipo_documento, numero_documento
            )
            
            # Buscar cliente
            resultado_busqueda = self.cliente_service.buscar_cliente_por_documento(
                tipo_documento, numero_documento
            )
            
            # Obtener información completa si se encuentra el cliente
            if resultado_busqueda:
                cliente = resultado_busqueda['cliente']
                
                info_completa = self.cliente_service.obtener_informacion_completa(
                    cliente.id,
                    incluir_compras=incluir_compras,
                    limite_compras=limite_compras
                )
                
                # Preparar respuesta
                response_data = {
                    'cliente': {
                        'id': cliente.id,
                        'tipo_documento': cliente.tipo_documento.codigo,
                        'numero_documento': cliente.numero_documento,
                        'nombre': cliente.nombre,
                        'apellido': cliente.apellido,
                        'nombre_completo': f"{cliente.nombre} {cliente.apellido}",
                        'correo': cliente.correo,
                        'telefono': cliente.telefono,
                        'activo': cliente.activo,
                        'fecha_registro': cliente.fecha_creacion
                    },
                    'estadisticas_compras': info_completa['estadisticas_compras'],
                    'compras_recientes': []
                }
                
                # Agregar compras si están disponibles
                if incluir_compras and 'compras_recientes' in info_completa:
                    response_data['compras_recientes'] = [
                        {
                            'numero_factura': compra.numero_factura,
                            'fecha_compra': compra.fecha_compra,
                            'monto_total': compra.monto_total,
                            'estado': compra.estado.nombre if compra.estado else 'N/A',
                            'cantidad_productos': len(compra.detalles.all()) if hasattr(compra, 'detalles') else 0
                        }
                        for compra in info_completa['compras_recientes']
                    ]
                
                # Metadata adicional
                meta_info = {
                    'total_compras': response_data['estadisticas_compras'].get('total_compras', 0),
                    'compras_mostradas': len(response_data['compras_recientes']),
                    'incluir_compras': incluir_compras,
                    'documento_buscado': f"{tipo_documento} {numero_documento}"
                }
                
                return self.success_response(
                    data=response_data,
                    message=f"Cliente encontrado: {cliente.nombre} {cliente.apellido}",
                    meta=meta_info
                )
        
        except Exception as e:
            # El manejo de excepciones se hace en BaseAPIView.handle_exception
            return self.handle_exception(e)


class TiposDocumentoListAPIView(BaseAPIView, SwaggerSchemaMixin):
    """
    API para listar tipos de documento disponibles.
    
    Endpoint de apoyo para interfaces de usuario que necesitan
    mostrar los tipos de documento válidos para búsquedas.
    """
    
    @extend_schema(
        summary="Listar tipos de documento",
        description="""
        Obtiene la lista completa de tipos de documento disponibles en el sistema.
        
        **Información retornada:**
        - Código del tipo de documento (ej: CC, NIT, PA)
        - Nombre descriptivo completo
        - Descripción detallada cuando aplica
        - Estado de disponibilidad
        
        **Ejemplos de respuesta:**
        ```json
        {
            "success": true,
            "message": "Tipos de documento obtenidos exitosamente",
            "data": [
                {
                    "id": 1,
                    "codigo": "CC",
                    "nombre": "Cédula de Ciudadanía",
                    "descripcion": "Documento de identificación para ciudadanos colombianos",
                    "activo": true
                },
                {
                    "id": 2,
                    "codigo": "NIT", 
                    "nombre": "Número de Identificación Tributaria",
                    "descripcion": "Documento para empresas y personas jurídicas",
                    "activo": true
                }
            ],
            "meta": {
                "total_tipos": 2,
                "solo_activos": true
            },
            "timestamp": "2025-09-28T14:31:22Z"
        }
        ```
        
        **Casos de uso:**
        - Poblar dropdowns en interfaces
        - Validación del lado del cliente
        - Documentación de API
        """,
        responses={
            200: OpenApiResponse(
                response=TipoDocumentoSerializer(many=True),
                description="Lista de tipos de documento obtenida exitosamente"
            ),
            500: SwaggerSchemaMixin.get_error_schema("Error interno del servidor")
        },
        tags=['Referencias'],
        operation_id='listar_tipos_documento'
    )
    def get(self, request: Request) -> Response:
        """
        Retorna la lista de tipos de documento disponibles.
        """
        try:
            # Obtener tipos de documento activos
            tipos_documento = TipoDocumento.objects.filter(activo=True).order_by('codigo')
            
            # Crear datos manualmente para evitar problemas de serialización
            datos = []
            for tipo in tipos_documento:
                datos.append({
                    'id': tipo.id,
                    'codigo': tipo.codigo,
                    'nombre': tipo.nombre,
                    'descripcion': getattr(tipo, 'descripcion', ''),
                    'activo': tipo.activo
                })
            
            # Preparar metadata
            meta_info = {
                'total_tipos': len(datos),
                'solo_activos': True
            }
            
            return self.success_response(
                data=datos,
                message="Tipos de documento obtenidos exitosamente",
                meta=meta_info
            )
            
        except Exception as e:
            self.logger.error(f"Error al obtener tipos de documento: {str(e)}", exc_info=True)
            return self.error_response(
                message="Error al obtener tipos de documento",
                code="DATABASE_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error_type": type(e).__name__, "error_message": str(e)}
            )


class ClienteInfoCompletaAPIView(BaseAPIView, ValidationMixin, SwaggerSchemaMixin):
    """
    API para obtener información completa de un cliente por ID.
    
    Endpoint auxiliar para cuando ya se conoce el ID del cliente
    y se necesita información detallada.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cliente_service = ClienteService()
    
    @extend_schema(
        summary="Obtener información completa del cliente",
        description="""
        Obtiene información detallada de un cliente específico por su ID.
    
        **Parámetros de consulta:**
        - `incluir_compras`: Si incluir historial de compras (default: true)
        - `limite_compras`: Número máximo de compras a incluir (default: 10)
    
        **URL de ejemplo:**
        ```
        GET /api/v1/cliente/4/?incluir_compras=true&limite_compras=5
        ```
    
        **Respuesta exitosa:**
        ```json
        {
            "success": true,
            "message": "Información del cliente obtenida exitosamente",
            "data": {
                "cliente": {
                    "id": 4,
                    "tipo_documento": {"codigo": "CC", "nombre": "Cédula de Ciudadanía"},
                    "numero_documento": "12345678",
                    "nombre": "Juan",
                    "apellido": "Pérez",
                    "correo": "juan.perez@ejemplo.com",
                    "telefono": "+57 3001234567",
                    "direccion": "Calle 123 #45-67",
                    "ciudad": "Bogotá",
                    "es_vip": true
                },
                "estadisticas": {
                    "total_compras": 15,
                    "monto_total": 8500000.00,
                    "compras_ultimo_mes": 3
                },
                "compras": [
                    {
                        "id": 102,
                        "fecha": "2025-09-20T15:30:45Z",
                        "monto": 1250000.00,
                        "productos": ["Televisor LED 50\"", "Soundbar 2.1"]
                    }
                ]
            },
            "timestamp": "2025-09-28T14:32:10Z"
        }
        ```
        """,
        parameters=[
            OpenApiParameter(
                name='incluir_compras',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Incluir historial de compras en la respuesta',
                default=True
            ),
            OpenApiParameter(
                name='limite_compras',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Número máximo de compras a incluir',
                default=10
            )
        ],
        responses={
            200: SwaggerSchemaMixin.get_success_schema("Información del cliente obtenida exitosamente"),
            404: SwaggerSchemaMixin.get_error_schema("Cliente no encontrado"),
            500: SwaggerSchemaMixin.get_error_schema("Error interno del servidor")
        },
        tags=['Clientes'],
        operation_id='info_completa_cliente'
    )
    def get(self, request: Request, cliente_id: int) -> Response:
        """
        Obtiene información completa de un cliente por ID.
        """
        try:
            # Obtener parámetros de query
            incluir_compras = request.query_params.get('incluir_compras', 'true').lower() == 'true'
            limite_compras = int(request.query_params.get('limite_compras', 10))
            
            # Validar límite
            if limite_compras < 0:
                limite_compras = 10
            elif limite_compras > 100:  # Límite máximo para rendimiento
                limite_compras = 100
            
            # Obtener información completa
            info_completa = self.cliente_service.obtener_informacion_completa(
                cliente_id,
                incluir_compras=incluir_compras,
                limite_compras=limite_compras
            )
            
            # El service ya maneja el caso de cliente no encontrado
            cliente = info_completa['cliente']
            
            # Preparar respuesta similar a BuscarClienteAPIView
            response_data = {
                'cliente': {
                    'id': cliente.id,
                    'tipo_documento': cliente.tipo_documento.codigo,
                    'numero_documento': cliente.numero_documento,
                    'nombre': cliente.nombre,
                    'apellido': cliente.apellido,
                    'nombre_completo': f"{cliente.nombre} {cliente.apellido}",
                    'correo': cliente.correo,
                    'telefono': cliente.telefono,
                    'activo': cliente.activo,
                    'fecha_registro': cliente.fecha_creacion
                },
                'estadisticas_compras': info_completa['estadisticas_compras'],
                'compras_recientes': []
            }
            
            # Agregar compras si están disponibles
            if incluir_compras and 'compras_recientes' in info_completa:
                response_data['compras_recientes'] = [
                    {
                        'numero_factura': compra.numero_factura,
                        'fecha_compra': compra.fecha_compra,
                        'monto_total': compra.monto_total,
                        'estado': compra.estado.nombre if compra.estado else 'N/A'
                    }
                    for compra in info_completa['compras_recientes']
                ]
            
            meta_info = {
                'cliente_id': cliente_id,
                'incluir_compras': incluir_compras,
                'limite_aplicado': limite_compras,
                'compras_encontradas': len(response_data['compras_recientes'])
            }
            
            return self.success_response(
                data=response_data,
                message=f"Información completa obtenida para {cliente.nombre} {cliente.apellido}",
                meta=meta_info
            )
            
        except Exception as e:
            return self.handle_exception(e)