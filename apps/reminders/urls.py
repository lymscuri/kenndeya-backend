"""
URLs pour l'application reminders.
Routes de gestion des rappels SMS.
"""

from django.urls import path
from . import views


urlpatterns = [
    # SMS Reminders
    path('sms/', views.sms_reminder_list_create, name='sms_reminder_list_create'),
    path('sms/<uuid:reminder_id>/', views.sms_reminder_detail, name='sms_reminder_detail'),
]
