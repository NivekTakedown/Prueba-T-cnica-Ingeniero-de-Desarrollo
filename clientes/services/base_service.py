"""
Base Service - Clase base para todos los services del sistema.
Proporciona funcionalidad común como logging y manejo de errores.
"""

import logging
from typing import Any, Dict, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status


# Configurar logger específico para services
logger = logging.getLogger('clientes.services')


class ServiceException(Exception):
    """
    Excepción personalizada para errores de services.
    """
    def __init__(self, message: str, error_code: str = None, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.error_code = error_code or 'SERVICE_ERROR'
        self.status_code = status_code
        super().__init__(self.message)


class ClienteNoEncontradoException(ServiceException):
    """Excepción específica cuando no se encuentra un cliente."""
    def __init__(self, mensaje: str = "Cliente no encontrado"):
        super().__init__(
            message=mensaje,
            error_code='CLIENTE_NO_ENCONTRADO',
            status_code=status.HTTP_404_NOT_FOUND
        )


class DocumentoInvalidoException(ServiceException):
    """Excepción específica para documentos inválidos."""
    def __init__(self, mensaje: str = "Documento inválido"):
        super().__init__(
            message=mensaje,
            error_code='DOCUMENTO_INVALIDO',
            status_code=status.HTTP_400_BAD_REQUEST
        )


class BaseService:
    """
    Clase base para todos los services del sistema.
    Proporciona funcionalidad común y estándares de manejo de errores.
    """
    
    def __init__(self):
        """Inicializa el service con logging."""
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.logger.info(f"Inicializando {self.__class__.__name__}")
    
    def log_info(self, message: str, extra_data: Dict = None):
        """Log de información con datos adicionales."""
        if extra_data:
            self.logger.info(f"{message} - Data: {extra_data}")
        else:
            self.logger.info(message)
    
    def log_error(self, message: str, exception: Exception = None, extra_data: Dict = None):
        """Log de errores con información detallada."""
        error_msg = f"{message}"
        if exception:
            error_msg += f" - Exception: {str(exception)}"
        if extra_data:
            error_msg += f" - Data: {extra_data}"
        
        self.logger.error(error_msg, exc_info=exception is not None)
    
    def log_warning(self, message: str, extra_data: Dict = None):
        """Log de advertencias."""
        if extra_data:
            self.logger.warning(f"{message} - Data: {extra_data}")
        else:
            self.logger.warning(message)
    
    @transaction.atomic
    def execute_with_transaction(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Ejecuta una operación dentro de una transacción de base de datos.
        
        Args:
            operation_name: Nombre descriptivo de la operación
            operation_func: Función a ejecutar
            *args, **kwargs: Argumentos para la función
            
        Returns:
            Resultado de la operación
            
        Raises:
            ServiceException: Si hay errores en la operación
        """
        try:
            self.log_info(f"Iniciando operación: {operation_name}")
            
            result = operation_func(*args, **kwargs)
            
            self.log_info(f"Operación completada exitosamente: {operation_name}")
            return result
            
        except ValidationError as e:
            self.log_error(f"Error de validación en {operation_name}", e)
            raise ServiceException(
                message=f"Error de validación: {str(e)}",
                error_code='VALIDATION_ERROR',
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        except ServiceException:
            # Re-lanzar excepciones de service sin modificar
            raise
            
        except Exception as e:
            self.log_error(f"Error inesperado en {operation_name}", e)
            raise ServiceException(
                message=f"Error interno del sistema en {operation_name}",
                error_code='INTERNAL_ERROR',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def validate_required_params(self, params: Dict[str, Any], required_fields: list):
        """
        Valida que los parámetros requeridos estén presentes.
        
        Args:
            params: Diccionario con parámetros
            required_fields: Lista de campos requeridos
            
        Raises:
            ServiceException: Si faltan parámetros requeridos
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in params or params[field] is None or params[field] == '':
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Campos requeridos faltantes: {', '.join(missing_fields)}"
            self.log_error(error_msg, extra_data={'missing_fields': missing_fields})
            raise ServiceException(
                message=error_msg,
                error_code='MISSING_REQUIRED_FIELDS',
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def create_success_response(self, data: Any = None, message: str = "Operación exitosa") -> Dict:
        """
        Crea una respuesta estándar exitosa.
        
        Args:
            data: Datos a incluir en la respuesta
            message: Mensaje de éxito
            
        Returns:
            Diccionario con formato de respuesta estándar
        """
        response = {
            'success': True,
            'message': message,
            'timestamp': self._get_current_timestamp()
        }
        
        if data is not None:
            response['data'] = data
            
        return response
    
    def create_error_response(self, exception: ServiceException) -> Dict:
        """
        Crea una respuesta estándar de error.
        
        Args:
            exception: Excepción del service
            
        Returns:
            Diccionario con formato de error estándar
        """
        return {
            'success': False,
            'error': True,
            'message': exception.message,
            'error_code': exception.error_code,
            'status_code': exception.status_code,
            'timestamp': self._get_current_timestamp()
        }
    
    def _get_current_timestamp(self) -> str:
        """Obtiene timestamp actual en formato ISO."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def handle_service_exception(self, operation_name: str, exception: Exception) -> ServiceException:
        """
        Maneja excepciones y las convierte en ServiceException estándar.
        
        Args:
            operation_name: Nombre de la operación que falló
            exception: Excepción original
            
        Returns:
            ServiceException estandarizada
        """
        if isinstance(exception, ServiceException):
            return exception
        
        # Log del error original
        self.log_error(f"Error en {operation_name}", exception)
        
        # Convertir a ServiceException
        if isinstance(exception, ValidationError):
            return ServiceException(
                message=f"Error de validación en {operation_name}: {str(exception)}",
                error_code='VALIDATION_ERROR',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Error genérico
        return ServiceException(
            message=f"Error interno en {operation_name}",
            error_code='INTERNAL_ERROR',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Funciones helper para usar en otros services
def require_params(params: Dict, *required_fields) -> None:
    """
    Helper function para validar parámetros requeridos.
    
    Usage:
        require_params(request_data, 'tipo_documento', 'numero_documento')
    """
    service = BaseService()
    service.validate_required_params(params, list(required_fields))


def log_service_operation(service_name: str, operation: str, data: Dict = None):
    """
    Helper function para logging de operaciones.
    
    Usage:
        log_service_operation('ClienteService', 'buscar_cliente', {'documento': '12345'})
    """
    logger.info(f"{service_name}.{operation} - Data: {data or 'No data'}")