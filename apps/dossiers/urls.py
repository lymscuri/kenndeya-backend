"""
URLs pour l'application dossiers.
Routes de gestion des dossiers médicaux.
"""

from django.urls import path
from . import views


urlpatterns = [
    # Mon dossier médical (patient connecté)
    path('my-record/', views.my_medical_record, name='my_medical_record'),

    # Patients
    path('patients/', views.patient_list_create, name='patient_list_create'),
    path('patients/<uuid:patient_id>/', views.patient_detail, name='patient_detail'),

    # Dossier médical (avec QR code)
    path('patients/<uuid:patient_id>/medical-record/', views.medical_record_detail, name='medical_record_detail'),

    # Consultations
    path('patients/<uuid:patient_id>/consultations/', views.consultation_list_create, name='consultation_list_create'),
    path('patients/<uuid:patient_id>/consultations/<uuid:consultation_id>/', views.consultation_detail, name='consultation_detail'),

    # Prescriptions
    path('patients/<uuid:patient_id>/consultations/<uuid:consultation_id>/prescriptions/', views.prescription_create, name='prescription_create'),

    # Examens de laboratoire
    path('patients/<uuid:patient_id>/consultations/<uuid:consultation_id>/lab-tests/', views.lab_test_create, name='lab_test_create'),
    path('patients/<uuid:patient_id>/consultations/<uuid:consultation_id>/lab-tests/<uuid:lab_test_id>/', views.lab_test_update, name='lab_test_update'),
    path('patients/<uuid:patient_id>/lab-tests/', views.lab_test_direct_create, name='lab_test_direct_create'),

    # Vaccinations
    path('patients/<uuid:patient_id>/vaccinations/', views.vaccination_list_create, name='vaccination_list_create'),

    # Chirurgies
    path('patients/<uuid:patient_id>/chirurgies/', views.ChirurgieListCreateView.as_view(), name='chirurgie_list_create'),

    # Hospitalisations
    path('patients/<uuid:patient_id>/hospitalisations/', views.HospitalisationListCreateView.as_view(), name='hospitalisation_list_create'),
]
