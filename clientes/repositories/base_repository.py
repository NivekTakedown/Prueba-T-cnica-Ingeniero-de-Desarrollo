from abc import ABC, abstractmethod
from typing import Type, Optional, List, Dict, Any, Union
from django.db import models
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet, Q
import logging

logger = logging.getLogger(__name__)


class RepositoryException(Exception):
    """Excepción base para errores en repositories"""
    pass


class ObjectNotFoundError(RepositoryException):
    """Error cuando no se encuentra un objeto"""
    pass


class RepositoryValidationError(RepositoryException):
    """Error de validación en repository"""
    pass


class BaseRepository(ABC):
    """
    Clase base para todos los repositories.
    Proporciona operaciones CRUD básicas y métodos de utilidad comunes.
    """
    
    def __init__(self, model_class: Type[models.Model]):
        """
        Inicializa el repository con la clase del modelo.
        
        Args:
            model_class: La clase del modelo Django a gestionar
        """
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_queryset(self) -> QuerySet:
        """
        Retorna el QuerySet base para este repository.
        Puede ser sobrescrito para agregar filtros por defecto, select_related, etc.
        """
        return self.model_class.objects.all()
    
    def get_by_id(self, obj_id: Union[int, str]) -> Optional[models.Model]:
        """
        Obtiene un objeto por su ID.
        
        Args:
            obj_id: ID del objeto a buscar
            
        Returns:
            El objeto encontrado o None si no existe
            
        Raises:
            ObjectNotFoundError: Si el objeto no existe y se requiere
        """
        try:
            self.logger.debug(f"Buscando {self.model_class.__name__} con ID: {obj_id}")
            return self.get_queryset().get(pk=obj_id)
        except self.model_class.DoesNotExist:
            self.logger.warning(f"{self.model_class.__name__} con ID {obj_id} no encontrado")
            return None
        except Exception as e:
            self.logger.error(f"Error buscando {self.model_class.__name__} por ID {obj_id}: {e}")
            raise RepositoryException(f"Error al buscar por ID: {e}") from e
    
    def get_by_id_or_fail(self, obj_id: Union[int, str]) -> models.Model:
        """
        Obtiene un objeto por su ID o lanza excepción si no existe.
        
        Args:
            obj_id: ID del objeto a buscar
            
        Returns:
            El objeto encontrado
            
        Raises:
            ObjectNotFoundError: Si el objeto no existe
        """
        obj = self.get_by_id(obj_id)
        if obj is None:
            raise ObjectNotFoundError(f"{self.model_class.__name__} con ID {obj_id} no encontrado")
        return obj
    
    def get_all(self, **filters) -> QuerySet:
        """
        Obtiene todos los objetos, opcionalmente filtrados.
        
        Args:
            **filters: Filtros adicionales para aplicar
            
        Returns:
            QuerySet con los objetos
        """
        try:
            queryset = self.get_queryset()
            if filters:
                queryset = queryset.filter(**filters)
            self.logger.debug(f"Obteniendo todos los {self.model_class.__name__} con filtros: {filters}")
            return queryset
        except Exception as e:
            self.logger.error(f"Error obteniendo todos los {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al obtener todos los objetos: {e}") from e
    
    def filter_by(self, **filters) -> QuerySet:
        """
        Filtra objetos por criterios específicos.
        
        Args:
            **filters: Diccionario de filtros a aplicar
            
        Returns:
            QuerySet filtrado
        """
        try:
            queryset = self.get_queryset().filter(**filters)
            self.logger.debug(f"Filtrando {self.model_class.__name__} con: {filters}")
            return queryset
        except Exception as e:
            self.logger.error(f"Error filtrando {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al filtrar: {e}") from e
    
    def search(self, search_fields: List[str], search_term: str) -> QuerySet:
        """
        Realiza búsqueda de texto en campos específicos.
        
        Args:
            search_fields: Lista de campos donde buscar
            search_term: Término a buscar
            
        Returns:
            QuerySet con resultados de búsqueda
        """
        if not search_term or not search_fields:
            return self.get_queryset().none()
        
        try:
            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__icontains": search_term})
            
            queryset = self.get_queryset().filter(query)
            self.logger.debug(f"Buscando '{search_term}' en campos {search_fields}")
            return queryset
        except Exception as e:
            self.logger.error(f"Error en búsqueda de {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error en búsqueda: {e}") from e
    
    def create(self, **data) -> models.Model:
        """
        Crea un nuevo objeto.
        
        Args:
            **data: Datos para crear el objeto
            
        Returns:
            El objeto creado
            
        Raises:
            RepositoryValidationError: Si hay errores de validación
        """
        try:
            with transaction.atomic():
                self.logger.debug(f"Creando {self.model_class.__name__} con datos: {data}")
                obj = self.model_class(**data)
                obj.full_clean()  # Ejecutar validaciones
                obj.save()
                self.logger.info(f"{self.model_class.__name__} creado con ID: {obj.pk}")
                return obj
        except ValidationError as e:
            self.logger.warning(f"Error de validación creando {self.model_class.__name__}: {e}")
            raise RepositoryValidationError(f"Error de validación: {e}") from e
        except Exception as e:
            self.logger.error(f"Error creando {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al crear objeto: {e}") from e
    
    def update(self, obj_id: Union[int, str], **data) -> models.Model:
        """
        Actualiza un objeto existente.
        
        Args:
            obj_id: ID del objeto a actualizar
            **data: Datos para actualizar
            
        Returns:
            El objeto actualizado
            
        Raises:
            ObjectNotFoundError: Si el objeto no existe
            RepositoryValidationError: Si hay errores de validación
        """
        try:
            with transaction.atomic():
                obj = self.get_by_id_or_fail(obj_id)
                self.logger.debug(f"Actualizando {self.model_class.__name__} ID {obj_id} con: {data}")
                
                for key, value in data.items():
                    setattr(obj, key, value)
                
                obj.full_clean()  # Ejecutar validaciones
                obj.save()
                self.logger.info(f"{self.model_class.__name__} ID {obj_id} actualizado")
                return obj
        except ValidationError as e:
            self.logger.warning(f"Error de validación actualizando {self.model_class.__name__}: {e}")
            raise RepositoryValidationError(f"Error de validación: {e}") from e
        except ObjectNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error actualizando {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al actualizar objeto: {e}") from e
    
    def delete(self, obj_id: Union[int, str]) -> bool:
        """
        Elimina un objeto por su ID.
        
        Args:
            obj_id: ID del objeto a eliminar
            
        Returns:
            True si se eliminó exitosamente
            
        Raises:
            ObjectNotFoundError: Si el objeto no existe
        """
        try:
            with transaction.atomic():
                obj = self.get_by_id_or_fail(obj_id)
                self.logger.debug(f"Eliminando {self.model_class.__name__} ID {obj_id}")
                obj.delete()
                self.logger.info(f"{self.model_class.__name__} ID {obj_id} eliminado")
                return True
        except ObjectNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error eliminando {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al eliminar objeto: {e}") from e
    
    def soft_delete(self, obj_id: Union[int, str], field_name: str = 'activo') -> models.Model:
        """
        Realiza eliminación lógica marcando un campo como False.
        
        Args:
            obj_id: ID del objeto a "eliminar"
            field_name: Nombre del campo booleano a marcar como False
            
        Returns:
            El objeto actualizado
            
        Raises:
            ObjectNotFoundError: Si el objeto no existe
        """
        try:
            obj = self.get_by_id_or_fail(obj_id)
            
            if not hasattr(obj, field_name):
                raise RepositoryException(f"El modelo no tiene el campo '{field_name}'")
            
            self.logger.debug(f"Soft delete de {self.model_class.__name__} ID {obj_id}")
            setattr(obj, field_name, False)
            obj.save(update_fields=[field_name])
            self.logger.info(f"{self.model_class.__name__} ID {obj_id} desactivado")
            return obj
        except ObjectNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error en soft delete de {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al desactivar objeto: {e}") from e
    
    def bulk_create(self, objects_data: List[Dict[str, Any]]) -> List[models.Model]:
        """
        Crea múltiples objetos en una sola operación.
        
        Args:
            objects_data: Lista de diccionarios con datos para crear objetos
            
        Returns:
            Lista de objetos creados
        """
        try:
            with transaction.atomic():
                objects = [self.model_class(**data) for data in objects_data]
                
                # Validar todos los objetos primero
                for obj in objects:
                    obj.full_clean()
                
                created_objects = self.model_class.objects.bulk_create(objects)
                self.logger.info(f"Creados {len(created_objects)} objetos de {self.model_class.__name__}")
                return created_objects
        except ValidationError as e:
            self.logger.warning(f"Error de validación en bulk_create: {e}")
            raise RepositoryValidationError(f"Error de validación en creación masiva: {e}") from e
        except Exception as e:
            self.logger.error(f"Error en bulk_create de {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error en creación masiva: {e}") from e
    
    def count(self, **filters) -> int:
        """
        Cuenta objetos que coinciden con los filtros.
        
        Args:
            **filters: Filtros a aplicar
            
        Returns:
            Número de objetos que coinciden
        """
        try:
            count = self.filter_by(**filters).count()
            self.logger.debug(f"Contando {self.model_class.__name__} con filtros {filters}: {count}")
            return count
        except Exception as e:
            self.logger.error(f"Error contando {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al contar objetos: {e}") from e
    
    def exists(self, **filters) -> bool:
        """
        Verifica si existe al menos un objeto que coincida con los filtros.
        
        Args:
            **filters: Filtros a aplicar
            
        Returns:
            True si existe al menos un objeto
        """
        try:
            exists = self.filter_by(**filters).exists()
            self.logger.debug(f"Verificando existencia de {self.model_class.__name__} con {filters}: {exists}")
            return exists
        except Exception as e:
            self.logger.error(f"Error verificando existencia de {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error al verificar existencia: {e}") from e
    
    def get_or_create(self, defaults: Optional[Dict] = None, **kwargs) -> tuple[models.Model, bool]:
        """
        Obtiene un objeto o lo crea si no existe.
        
        Args:
            defaults: Valores por defecto para la creación
            **kwargs: Criterios de búsqueda
            
        Returns:
            Tupla (objeto, created) donde created es True si se creó
        """
        try:
            with transaction.atomic():
                obj, created = self.model_class.objects.get_or_create(
                    defaults=defaults,
                    **kwargs
                )
                action = "creado" if created else "encontrado"
                self.logger.debug(f"{self.model_class.__name__} {action} con criterios: {kwargs}")
                return obj, created
        except ValidationError as e:
            self.logger.warning(f"Error de validación en get_or_create: {e}")
            raise RepositoryValidationError(f"Error de validación: {e}") from e
        except Exception as e:
            self.logger.error(f"Error en get_or_create de {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error en get_or_create: {e}") from e
    
    def paginate(self, page: int = 1, page_size: int = 20, **filters) -> Dict[str, Any]:
        """
        Pagina resultados con filtros opcionales.
        
        Args:
            page: Número de página (base 1)
            page_size: Tamaño de página
            **filters: Filtros adicionales
            
        Returns:
            Diccionario con resultados paginados y metadata
        """
        try:
            queryset = self.filter_by(**filters)
            total_count = queryset.count()
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            objects = list(queryset[start_index:end_index])
            
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            result = {
                'objects': objects,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'next_page': page + 1 if has_next else None,
                    'previous_page': page - 1 if has_previous else None,
                }
            }
            
            self.logger.debug(f"Paginación de {self.model_class.__name__}: página {page}, {len(objects)} objetos")
            return result
            
        except Exception as e:
            self.logger.error(f"Error en paginación de {self.model_class.__name__}: {e}")
            raise RepositoryException(f"Error en paginación: {e}") from e