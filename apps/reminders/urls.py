"""
apps/reminders/urls.py — Routes SMS Kendeya
"""

from django.urls import path
from . import views

urlpatterns = [
    # CRUD rappels
    path('sms/',                         views.sms_reminder_list_create,    name='sms_list_create'),
    path('sms/<uuid:reminder_id>/',      views.sms_reminder_detail,         name='sms_detail'),
    path('sms/<uuid:reminder_id>/send/', views.send_reminder_now,           name='sms_send_now'),

    # Création rapide avec message automatique
    path('vaccination/',                 views.create_vaccination_reminder, name='reminder_vaccination'),
    path('prenatal/',                    views.create_prenatal_reminder,    name='reminder_prenatal'),
    path('appointment/',                 views.create_appointment_reminder, name='reminder_appointment'),

    # Stats
    path('stats/',                       views.reminders_stats,             name='reminders_stats'),
]