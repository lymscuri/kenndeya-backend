"""
Vues pour l'application dossiers.
Gère les dossiers médicaux, patients, consultations, etc.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404

from core.permissions import IsDoctor
from .models import Patient, MedicalRecord, Consultation, Prescription, LabTest, Vaccination
from .serializers import (
    PatientListSerializer,
    PatientSerializer,
    MedicalRecordSerializer,
    ConsultationListSerializer,
    ConsultationSerializer,
    PrescriptionSerializer,
    LabTestSerializer,
    VaccinationSerializer,
    MyMedicalRecordSerializer
)


# ========== PATIENTS ==========

@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def patient_list_create(request):
    """
    Liste tous les patients du médecin connecté ou crée un nouveau patient.

    GET /api/v1/dossiers/patients/
    POST /api/v1/dossiers/patients/
    """
    if request.method == 'GET':
        patients = Patient.objects.filter(doctor=request.user)
        paginator = PageNumberPagination()
        paginated_patients = paginator.paginate_queryset(patients, request)
        serializer = PatientListSerializer(paginated_patients, many=True)

        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = PatientSerializer(data=request.data)

        if serializer.is_valid():
            # Injecter le médecin depuis request.user
            patient = serializer.save(doctor=request.user)

            # Créer automatiquement le dossier médical
            MedicalRecord.objects.create(patient=patient)

            return Response({
                'success': True,
                'message': 'Patient créé avec succès.',
                'data': PatientSerializer(patient).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsDoctor])
def patient_detail(request, patient_id):
    """
    Récupère, modifie ou supprime un patient.

    GET /api/v1/dossiers/patients/:id/
    PATCH /api/v1/dossiers/patients/:id/
    DELETE /api/v1/dossiers/patients/:id/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)

    if request.method == 'GET':
        serializer = PatientSerializer(patient)
        return Response({
            'success': True,
            'message': 'Patient récupéré avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = PatientSerializer(patient, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Patient mis à jour avec succès.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        patient.delete()
        return Response({
            'success': True,
            'message': 'Patient supprimé avec succès.',
            'data': {}
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def medical_record_detail(request, patient_id):
    """
    Récupère le dossier médical d'un patient avec le QR code.

    GET /api/v1/dossiers/patients/:id/medical-record/
    """
    patient = get_object_or_404(Patient, id=patient_id)

    # Vérifier que l'utilisateur est le médecin du patient
    if patient.doctor != request.user:
        return Response({
            'success': False,
            'error': {
                'code': 'permission_denied',
                'message': 'Vous n\'avez pas accès à ce dossier médical.',
                'details': {}
            }
        }, status=status.HTTP_403_FORBIDDEN)

    medical_record = get_object_or_404(MedicalRecord, patient=patient)
    serializer = MedicalRecordSerializer(medical_record, context={'request': request})

    return Response({
        'success': True,
        'message': 'Dossier médical récupéré avec succès.',
        'data': serializer.data
    }, status=status.HTTP_200_OK)


# ========== CONSULTATIONS ==========

@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def consultation_list_create(request, patient_id):
    """
    Liste toutes les consultations d'un patient ou crée une nouvelle consultation.

    GET /api/v1/dossiers/patients/:id/consultations/
    POST /api/v1/dossiers/patients/:id/consultations/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)

    if request.method == 'GET':
        consultations = Consultation.objects.filter(patient=patient)
        paginator = PageNumberPagination()
        paginated_consultations = paginator.paginate_queryset(consultations, request)
        serializer = ConsultationListSerializer(paginated_consultations, many=True)

        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = ConsultationSerializer(data=request.data)

        if serializer.is_valid():
            # Injecter le médecin et le patient
            consultation = serializer.save(doctor=request.user, patient=patient)

            return Response({
                'success': True,
                'message': 'Consultation créée avec succès.',
                'data': ConsultationSerializer(consultation).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH'])
@permission_classes([IsDoctor])
def consultation_detail(request, patient_id, consultation_id):
    """
    Récupère ou modifie une consultation.

    GET /api/v1/dossiers/patients/:id/consultations/:cid/
    PATCH /api/v1/dossiers/patients/:id/consultations/:cid/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    consultation = get_object_or_404(Consultation, id=consultation_id, patient=patient)

    if request.method == 'GET':
        serializer = ConsultationSerializer(consultation)
        return Response({
            'success': True,
            'message': 'Consultation récupérée avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = ConsultationSerializer(consultation, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Consultation mise à jour avec succès.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ========== PRESCRIPTIONS ==========

@api_view(['POST'])
@permission_classes([IsDoctor])
def prescription_create(request, patient_id, consultation_id):
    """
    Ajoute une prescription à une consultation.

    POST /api/v1/dossiers/patients/:id/consultations/:cid/prescriptions/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    consultation = get_object_or_404(Consultation, id=consultation_id, patient=patient)

    serializer = PrescriptionSerializer(data=request.data)

    if serializer.is_valid():
        prescription = serializer.save(consultation=consultation)

        return Response({
            'success': True,
            'message': 'Prescription ajoutée avec succès.',
            'data': PrescriptionSerializer(prescription).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


# ========== EXAMENS DE LABORATOIRE ==========

@api_view(['POST'])
@permission_classes([IsDoctor])
def lab_test_create(request, patient_id, consultation_id):
    """
    Ajoute un examen de laboratoire à une consultation.

    POST /api/v1/dossiers/patients/:id/consultations/:cid/lab-tests/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    consultation = get_object_or_404(Consultation, id=consultation_id, patient=patient)

    serializer = LabTestSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        lab_test = serializer.save(consultation=consultation)

        return Response({
            'success': True,
            'message': 'Examen de laboratoire ajouté avec succès.',
            'data': LabTestSerializer(lab_test, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsDoctor])
def lab_test_update(request, patient_id, consultation_id, lab_test_id):
    """
    Met à jour un examen de laboratoire (résultats, statut, etc.).

    PATCH /api/v1/dossiers/patients/:id/consultations/:cid/lab-tests/:lid/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    consultation = get_object_or_404(Consultation, id=consultation_id, patient=patient)
    lab_test = get_object_or_404(LabTest, id=lab_test_id, consultation=consultation)

    serializer = LabTestSerializer(lab_test, data=request.data, partial=True, context={'request': request})

    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Examen de laboratoire mis à jour avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


# ========== VACCINATIONS ==========

@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def vaccination_list_create(request, patient_id):
    """
    Liste toutes les vaccinations d'un patient ou ajoute une vaccination.

    GET /api/v1/dossiers/patients/:id/vaccinations/
    POST /api/v1/dossiers/patients/:id/vaccinations/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)

    if request.method == 'GET':
        vaccinations = Vaccination.objects.filter(patient=patient)
        serializer = VaccinationSerializer(vaccinations, many=True)

        return Response({
            'success': True,
            'count': vaccinations.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = VaccinationSerializer(data=request.data)

        if serializer.is_valid():
            vaccination = serializer.save(doctor=request.user, patient=patient)

            return Response({
                'success': True,
                'message': 'Vaccination ajoutée avec succès.',
                'data': VaccinationSerializer(vaccination).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ========== MY MEDICAL RECORD ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_medical_record(request):
    """
    Retourne le dossier médical complet du patient connecté.
    Accessible aux patients et médecins.

    GET /api/v1/dossiers/my-record/
    """
    # Chercher le patient dont l'email correspond à l'utilisateur connecté
    try:
        patient = Patient.objects.prefetch_related(
            'consultations',
            'consultations__doctor',
            'vaccinations',
            'vaccinations__doctor'
        ).filter(email=request.user.email).first()
    except Patient.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'code': 'not_found',
                'message': 'Aucun dossier médical trouvé pour cet utilisateur.',
                'details': {
                    'email': request.user.email,
                    'suggestion': 'Veuillez contacter votre médecin pour créer votre dossier médical.'
                }
            }
        }, status=status.HTTP_404_NOT_FOUND)

    # Sérialiser le dossier complet
    serializer = MyMedicalRecordSerializer(patient)

    return Response({
        'success': True,
        'message': 'Dossier médical récupéré avec succès.',
        'data': serializer.data
    }, status=status.HTTP_200_OK)
