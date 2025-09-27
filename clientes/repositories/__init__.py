from .base_repository import (
    BaseRepository,
    RepositoryException,
    ObjectNotFoundError,
    RepositoryValidationError,
)
from .cliente_repository import ClienteRepository

__all__ = [
    'BaseRepository',
    'RepositoryException',
    'ObjectNotFoundError',
    'RepositoryValidationError',
    'ClienteRepository',
]