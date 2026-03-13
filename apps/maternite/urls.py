"""
URLs pour l'application maternité.
Routes de gestion de maternité et suivi de grossesse.
"""

from django.urls import path
from . import views


urlpatterns = [
    # Maternity Profile
    path('patients/<uuid:patient_id>/maternity-profile/', views.maternity_patient_create, name='maternity_patient_create'),
    path('patients/<uuid:patient_id>/maternity-profile/detail/', views.maternity_patient_detail, name='maternity_patient_detail'),

    # Pregnancies
    path('patients/<uuid:patient_id>/pregnancies/', views.pregnancy_list_create, name='pregnancy_list_create'),
    path('patients/<uuid:patient_id>/pregnancies/<uuid:pregnancy_id>/', views.pregnancy_detail, name='pregnancy_detail'),

    # Weekly Checkups
    path('patients/<uuid:patient_id>/pregnancies/<uuid:pregnancy_id>/weekly-checkups/', views.weekly_checkup_list_create, name='weekly_checkup_list_create'),

    # Prenatal Consultations
    path('patients/<uuid:patient_id>/pregnancies/<uuid:pregnancy_id>/prenatal-consultations/', views.prenatal_consultation_list_create, name='prenatal_consultation_list_create'),
    path('patients/<uuid:patient_id>/pregnancies/<uuid:pregnancy_id>/prenatal-consultations/<uuid:consultation_id>/', views.prenatal_consultation_detail, name='prenatal_consultation_detail'),

    # Prenatal Exams
    path('patients/<uuid:patient_id>/pregnancies/<uuid:pregnancy_id>/prenatal-exams/', views.prenatal_exam_create, name='prenatal_exam_create'),
    path('patients/<uuid:patient_id>/pregnancies/<uuid:pregnancy_id>/prenatal-exams/<uuid:exam_id>/', views.prenatal_exam_update, name='prenatal_exam_update'),

    # Children
    path('patients/<uuid:patient_id>/pregnancies/<uuid:pregnancy_id>/children/', views.child_list_create, name='child_list_create'),

    # Child Growth & Vaccines
    path('children/<uuid:child_id>/growth/', views.child_growth_create, name='child_growth_create'),
    path('children/<uuid:child_id>/vaccines/', views.child_vaccine_create, name='child_vaccine_create'),
]
