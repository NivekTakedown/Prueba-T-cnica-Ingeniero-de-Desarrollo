"""
URLs Configuration para la app clientes
"""

from django.urls import path, include
from .views.cliente_views import (
    BuscarClienteAPIView,
    TiposDocumentoListAPIView,
    ClienteInfoCompletaAPIView
)
from .views.exportacion_views import ExportarClienteAPIView

app_name = 'clientes'

# URLs v1 de la API
v1_patterns = [
    # Cliente endpoints
    path('buscar-cliente/', BuscarClienteAPIView.as_view(), name='buscar-cliente'),
    path('cliente/<int:cliente_id>/', ClienteInfoCompletaAPIView.as_view(), name='info-completa-cliente'),
    
    # Exportación endpoints
    path('exportar/', ExportarClienteAPIView.as_view(), name='exportar-cliente'),
    
    # Referencias
    path('tipos-documento/', TiposDocumentoListAPIView.as_view(), name='tipos-documento'),
]

urlpatterns = [
    path('v1/', include((v1_patterns, 'v1'), namespace='v1')),
]