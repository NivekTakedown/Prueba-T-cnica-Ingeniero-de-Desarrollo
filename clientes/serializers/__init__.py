# Importar serializers de cliente
from .cliente_serializers import (
    ClienteSerializer,
    ClienteBusquedaSerializer,
    ClienteResponseSerializer,
    ClienteListSerializer,
    ClienteCreateSerializer,
    ClienteUpdateSerializer
)

# Importar serializers de compra
from .compra_serializers import (
    ProductoSerializer,
    ProductoListSerializer,
    CompraSerializer,
    CompraResumenSerializer,
    CompraCreateSerializer,
    DetalleCompraSerializer,
    CompraEstadisticasSerializer
)

# Importar serializers de referencia
from .reference_serializers import (
    TipoDocumentoSerializer,
    TipoDocumentoListSerializer,
    EstadoCompraSerializer,
    EstadoCompraListSerializer,
    CategoriaProductoSerializer,
    CategoriaProductoListSerializer,
    CategoriaProductoCreateSerializer,
    ApiResponseSerializer,
    TipoDocumentoResponseSerializer,
    EstadoCompraResponseSerializer,
    CategoriaProductoResponseSerializer
)

# Importar serializers de API
from .api_serializers import (
    BusquedaClienteRequestSerializer,
    BusquedaClienteResponseSerializer,
    ExportacionRequestSerializer,
    ReporteFidelizacionRequestSerializer,
    ReporteFidelizacionResponseSerializer,
    ErrorResponseSerializer,  # ✅ Este existe
    SuccessResponseSerializer,  # ✅ Este existe
    TiposDocumentoResponseSerializer,
    ValidacionDocumentoSerializer
)

__all__ = [
    # Cliente serializers
    'ClienteSerializer',
    'ClienteBusquedaSerializer', 
    'ClienteResponseSerializer',
    'ClienteListSerializer',
    'ClienteCreateSerializer',
    'ClienteUpdateSerializer',
    
    # Compra serializers
    'ProductoSerializer',
    'ProductoListSerializer',
    'CompraSerializer',
    'CompraResumenSerializer',
    'CompraCreateSerializer',
    'DetalleCompraSerializer',
    'CompraEstadisticasSerializer',
    
    # Reference serializers
    'TipoDocumentoSerializer',
    'TipoDocumentoListSerializer',
    'EstadoCompraSerializer',
    'EstadoCompraListSerializer',
    'CategoriaProductoSerializer',
    'CategoriaProductoListSerializer',
    'CategoriaProductoCreateSerializer',
    'ApiResponseSerializer',
    'TipoDocumentoResponseSerializer',
    'EstadoCompraResponseSerializer',
    'CategoriaProductoResponseSerializer',
    
    # API serializers
    'BusquedaClienteRequestSerializer',
    'BusquedaClienteResponseSerializer',
    'ExportacionRequestSerializer',
    'ReporteFidelizacionRequestSerializer',
    'ReporteFidelizacionResponseSerializer',
    'ErrorResponseSerializer',
    'SuccessResponseSerializer',
    'TiposDocumentoResponseSerializer',
    'ValidacionDocumentoSerializer'
]