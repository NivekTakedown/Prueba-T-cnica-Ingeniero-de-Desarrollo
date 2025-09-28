"""
Base Views - Clases base y utilidades comunes para todas las views.
Incluye manejo de errores, logging y response helpers.
"""

import logging
from typing import Dict, Any
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse
from drf_spectacular.openapi import AutoSchema

from ..services.base_service import ServiceException, ClienteNoEncontradoException, DocumentoInvalidoException

# Configurar logger específico para views
logger = logging.getLogger('clientes.views')


class BaseAPIView(APIView):
    """
    Clase base para todas las API Views con manejo común de errores y logging.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logger
    
    def dispatch(self, request: Request, *args, **kwargs):
        """
        Intercepta todas las requests para logging automático.
        """
        # Log de request entrante
        self.logger.info(
            f"API Request: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'ip_address': self.get_client_ip(request)
            }
        )
        
        try:
            # Ejecutar la view
            response = super().dispatch(request, *args, **kwargs)
            
            # Log de response exitoso
            self.logger.info(
                f"API Response: {request.method} {request.path} - Status: {response.status_code}",
                extra={
                    'status_code': response.status_code,
                    'response_size': len(str(response.data)) if hasattr(response, 'data') else 0
                }
            )
            
            return response
            
        except Exception as e:
            # Log de error y manejo
            self.logger.error(
                f"API Error: {request.method} {request.path} - Error: {str(e)}",
                extra={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            
            # Devolver error formateado
            return self.handle_exception(e)
    
    def handle_exception(self, exc: Exception) -> Response:
        """
        Maneja excepciones de forma consistente para todas las views.
        """
        # Errores específicos del negocio
        if isinstance(exc, ClienteNoEncontradoException):
            return self.error_response(
                message=exc.message,
                code="CLIENTE_NO_ENCONTRADO",
                status_code=status.HTTP_404_NOT_FOUND,
                details={"tipo_error": "cliente_no_encontrado"}
            )
        
        elif isinstance(exc, DocumentoInvalidoException):
            return self.error_response(
                message=exc.message,
                code="DOCUMENTO_INVALIDO",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"tipo_error": "documento_invalido"}
            )
        
        elif isinstance(exc, ServiceException):
            return self.error_response(
                message=exc.message,
                code="ERROR_SERVICIO",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"tipo_error": "servicio"}
            )
        
        # Errores de validación de DRF
        elif hasattr(exc, 'detail'):
            return self.error_response(
                message="Error de validación",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"validation_errors": exc.detail}
            )
        
        # Error genérico del servidor
        else:
            return self.error_response(
                message="Error interno del servidor",
                code="INTERNAL_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={"error_type": type(exc).__name__}
            )
    
    def success_response(self, data: Any = None, message: str = "Operación exitosa", 
                        status_code: int = status.HTTP_200_OK, 
                        meta: Dict = None) -> Response:
        """
        Helper para generar respuestas exitosas consistentes.
        """
        response_data = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": self.get_current_timestamp()
        }
        
        if meta:
            response_data["meta"] = meta
        
        return Response(response_data, status=status_code)
    
    def error_response(self, message: str, code: str = "ERROR", 
                      status_code: int = status.HTTP_400_BAD_REQUEST,
                      details: Dict = None) -> Response:
        """
        Helper para generar respuestas de error consistentes.
        """
        response_data = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "timestamp": self.get_current_timestamp()
            }
        }
        
        if details:
            response_data["error"]["details"] = details
        
        return Response(response_data, status=status_code)
    
    def paginated_response(self, queryset, serializer_class, request: Request,
                          message: str = "Datos obtenidos exitosamente") -> Response:
        """
        Helper para respuestas paginadas.
        """
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = serializer_class(queryset, many=True)
        return self.success_response(
            data=serializer.data,
            message=message,
            meta={"total_count": len(serializer.data)}
        )
    
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Obtiene la IP del cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'Unknown'
    
    @staticmethod
    def get_current_timestamp() -> str:
        """Retorna timestamp actual en formato ISO."""
        from datetime import datetime
        return datetime.now().isoformat()


class FileResponseMixin:
    """
    Mixin para views que retornan archivos para descarga.
    """
    
    def file_response(self, file_content: bytes, filename: str, 
                     content_type: str, attachment: bool = True) -> HttpResponse:
        """
        Genera una respuesta HTTP para descarga de archivos.
        """
        response = HttpResponse(file_content, content_type=content_type)
        
        if attachment:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        response['Content-Length'] = len(file_content)
        
        # Headers adicionales para mejor compatibilidad
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        self.logger.info(f"Archivo generado: {filename} ({len(file_content)} bytes)")
        
        return response


class ValidationMixin:
    """
    Mixin para validaciones comunes en las views.
    """
    
    def validate_required_fields(self, data: Dict, required_fields: list) -> Dict:
        """
        Valida que estén presentes los campos requeridos.
        """
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ServiceException(
                f"Campos requeridos faltantes: {', '.join(missing_fields)}"
            )
        
        return data
    
    def validate_documento(self, tipo_documento: str, numero_documento: str) -> tuple:
        """
        Validación básica de documentos.
        """
        if not tipo_documento or not numero_documento:
            raise DocumentoInvalidoException(
                "Tipo y número de documento son obligatorios"
            )
        
        # Limpiar espacios
        tipo_documento = tipo_documento.strip().upper()
        numero_documento = numero_documento.strip()
        
        # Validaciones básicas por tipo
        if tipo_documento == 'CC' and not numero_documento.isdigit():
            raise DocumentoInvalidoException(
                "La cédula debe contener solo números"
            )
        
        if len(numero_documento) < 5:
            raise DocumentoInvalidoException(
                "El número de documento debe tener al menos 5 caracteres"
            )
        
        return tipo_documento, numero_documento


class SwaggerSchemaMixin:
    """
    Mixin para esquemas de Swagger/OpenAPI comunes.
    """
    
    @staticmethod
    def get_success_schema(description: str = "Operación exitosa") -> OpenApiResponse:
        """Schema para respuestas exitosas."""
        return OpenApiResponse(
            response={
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': description},
                    'data': {'type': 'object'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            },
            description=description
        )
    
    @staticmethod
    def get_error_schema(description: str = "Error en la operación") -> OpenApiResponse:
        """Schema para respuestas de error."""
        return OpenApiResponse(
            response={
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {
                        'type': 'object',
                        'properties': {
                            'code': {'type': 'string', 'example': 'ERROR_CODE'},
                            'message': {'type': 'string', 'example': description},
                            'timestamp': {'type': 'string', 'format': 'date-time'},
                            'details': {'type': 'object'}
                        }
                    }
                }
            },
            description=description
        )
    
    @staticmethod
    def get_example_request(example_data: Dict) -> Dict:
        """
        Genera un ejemplo estandarizado de request para documentación.
        """
        return {
            'examples': {
                'request_example': {
                    'summary': 'Ejemplo de solicitud',
                    'value': example_data
                }
            }
        }
    
    @staticmethod
    def get_example_response(example_data: Dict) -> Dict:
        """
        Genera un ejemplo estandarizado de response para documentación.
        """
        return {
            'examples': {
                'response_example': {
                    'summary': 'Ejemplo de respuesta exitosa',
                    'value': {
                        'success': True,
                        'message': 'Operación completada exitosamente',
                        'data': example_data,
                        'timestamp': datetime.now().isoformat()
                    }
                }
            }
        }


class LoggingMiddleware:
    """
    Middleware personalizado para logging detallado.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('clientes.middleware')
    
    def __call__(self, request):
        # Pre-procesamiento
        start_time = self.get_current_time()
        
        response = self.get_response(request)
        
        # Post-procesamiento
        end_time = self.get_current_time()
        duration = end_time - start_time
        
        # Log de performance
        if duration > 1000:  # Mas de 1 segundo
            self.logger.warning(
                f"Slow request: {request.method} {request.path} took {duration}ms",
                extra={
                    'duration_ms': duration,
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code
                }
            )
        
        return response
    
    @staticmethod
    def get_current_time():
        """Retorna tiempo actual en millisegundos."""
        import time
        return int(time.time() * 1000)


# Decoradores útiles para views

def log_api_call(func):
    """
    Decorador para logging automático de calls a métodos de API.
    """
    def wrapper(self, request, *args, **kwargs):
        logger.info(f"API Call: {func.__name__} iniciado")
        try:
            result = func(self, request, *args, **kwargs)
            logger.info(f"API Call: {func.__name__} completado exitosamente")
            return result
        except Exception as e:
            logger.error(f"API Call: {func.__name__} falló - {str(e)}")
            raise
    return wrapper


def validate_content_type(content_type='application/json'):
    """
    Decorador para validar Content-Type de requests.
    """
    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            if request.content_type != content_type:
                return self.error_response(
                    message=f"Content-Type debe ser {content_type}",
                    code="INVALID_CONTENT_TYPE",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator