"""
URL configuration for rios_desierto_sac project.
Configura las rutas principales del proyecto y la documentación OpenAPI.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),
    
    # Redirección desde la raíz a la documentación Swagger
    path('', RedirectView.as_view(url='/swagger/', permanent=False), name='index'),
    
    # API endpoints - Todos bajo el prefijo 'api'
    path('api/', include('clientes.urls')),
    
    # Swagger/OpenAPI documentación
    path('api/schema/', 
         SpectacularAPIView.as_view(), 
         name='schema'),
    
    path('swagger/', 
         SpectacularSwaggerView.as_view(url_name='schema'), 
         name='swagger-ui'),
    
    path('redoc/', 
         SpectacularRedocView.as_view(url_name='schema'), 
         name='redoc'),
]

# Configuración para servir archivos estáticos en desarrollo
if settings.DEBUG:
    # Servir archivos estáticos en desarrollo
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Servir archivos media en desarrollo (para uploads)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
