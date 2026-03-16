# apps/notifications/urls.py

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # POST /api/v1/notifications/register/ - Enregistrer un token push
    path('register/', views.register_token, name='register_token'),

    # POST /api/v1/notifications/send/ - Envoyer une notification (médecins uniquement)
    path('send/', views.send_notification, name='send_notification'),
]
