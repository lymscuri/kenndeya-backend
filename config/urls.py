"""
Configuration des URLs principales pour Kendeya Backend.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint de santé pour vérifier que l'API est en ligne.
    Utilisé par Railway et les outils de monitoring.
    """
    return Response({
        'status': 'healthy',
        'service': 'Kendeya Backend API',
        'version': '1.0.0'
    })


urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),

    # Health check
    path('health/', health_check, name='health_check'),

    # Documentation API (OpenAPI/Swagger)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API v1
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/dossiers/', include('apps.dossiers.urls')),
    path('api/v1/maternity/', include('apps.maternite.urls')),
    path('api/v1/emergency/', include('apps.urgences.urls')),
    path('api/v1/reminders/', include('apps.reminders.urls')),
]

# Servir les fichiers médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
