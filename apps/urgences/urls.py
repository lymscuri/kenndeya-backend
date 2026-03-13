"""
URLs pour l'application urgences.
Routes de gestion des urgences, secouristes et hôpitaux.
"""

from django.urls import path
from . import views


urlpatterns = [
    # Secourist Profile
    path('secourist/profile/', views.secourist_profile_create, name='secourist_profile_create'),
    path('secourist/profile/detail/', views.secourist_profile_detail, name='secourist_profile_detail'),
    path('secourists/', views.secourist_list, name='secourist_list'),

    # Hospitals
    path('hospitals/', views.hospital_list, name='hospital_list'),
    path('hospitals/<uuid:hospital_id>/', views.hospital_detail, name='hospital_detail'),

    # Emergency Alerts
    path('alerts/', views.emergency_alert_create, name='emergency_alert_create'),
    path('alerts/list/', views.emergency_alert_list, name='emergency_alert_list'),
    path('alerts/pending/', views.emergency_alert_pending, name='emergency_alert_pending'),
    path('alerts/<uuid:alert_id>/', views.emergency_alert_detail, name='emergency_alert_detail'),
    path('alerts/<uuid:alert_id>/assign/', views.emergency_alert_assign, name='emergency_alert_assign'),
    path('alerts/<uuid:alert_id>/status/', views.emergency_alert_update_status, name='emergency_alert_update_status'),
]
