"""
Vues pour l'application maternité.
Gère les grossesses, consultations prénatales et suivi des enfants.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsDoctor
from apps.dossiers.models import Patient
from .models import (
    MaternityPatient, Pregnancy, WeeklyCheckup,
    PrenatalConsultation, PrenatalExam, Child,
    ChildGrowth, ChildVaccine
)
from .serializers import (
    MaternityPatientSerializer, PregnancySerializer,
    WeeklyCheckupSerializer, PrenatalConsultationSerializer,
    PrenatalExamSerializer, ChildSerializer,
    ChildGrowthSerializer, ChildVaccineSerializer
)


# ========== MATERNITY PATIENTS ==========
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def maternity_patient_list_create(request):
    if request.method == 'GET':
        patients = Patient.objects.filter(doctor=request.user)
        return Response({
            'success': True,
            'count': patients.count(),
            'results': []
        })

    if request.method == 'POST':
        from datetime import date
        data = request.data
        year = date.today().year
        patient = Patient.objects.create(
            doctor=request.user,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
        )
        return Response({
            'success': True,
            'message': 'Patiente maternité créée.',
            'data': {
                'id': str(patient.id),
                'first_name': patient.first_name,
                'last_name': patient.last_name,
            }
        }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def maternity_patient_detail_simple(request, patient_id):
    """GET /api/v1/maternity/patients/:id/"""
    from apps.dossiers.models import Patient
    from django.shortcuts import get_object_or_404
    patient = get_object_or_404(Patient, id=patient_id)
    return Response({
        'success': True,
        'data': {
            'id': str(patient.id),
            'dossier_number': patient.dossier_number,
            'identity': patient.identity,
        }
    })

@api_view(['POST'])
@permission_classes([IsDoctor])
def maternity_patient_create(request, patient_id):
    """
    Crée un profil de maternité pour une patiente.

    POST /api/v1/maternite/patients/:id/maternity-profile/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)

    # Vérifier que le patient n'a pas déjà un profil de maternité
    if hasattr(patient, 'maternity_profile'):
        return Response({
            'success': False,
            'error': {
                'code': 'already_exists',
                'message': 'Cette patiente a déjà un profil de maternité.',
                'details': {}
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = MaternityPatientSerializer(data=request.data)

    if serializer.is_valid():
        maternity_patient = serializer.save(patient=patient)

        return Response({
            'success': True,
            'message': 'Profil de maternité créé avec succès.',
            'data': MaternityPatientSerializer(maternity_patient).data
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
def maternity_patient_detail(request, patient_id):
    """
    Récupère ou modifie le profil de maternité d'une patiente.

    GET /api/v1/maternite/patients/:id/maternity-profile/
    PATCH /api/v1/maternite/patients/:id/maternity-profile/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)

    if request.method == 'GET':
        serializer = MaternityPatientSerializer(maternity_patient)
        return Response({
            'success': True,
            'message': 'Profil de maternité récupéré avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = MaternityPatientSerializer(maternity_patient, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profil de maternité mis à jour avec succès.',
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


# ========== PREGNANCIES ==========

@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def pregnancy_list_create(request, patient_id):
    """
    Liste toutes les grossesses d'une patiente ou crée une nouvelle grossesse.

    GET /api/v1/maternite/patients/:id/pregnancies/
    POST /api/v1/maternite/patients/:id/pregnancies/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)

    if request.method == 'GET':
        pregnancies = Pregnancy.objects.filter(maternity_patient=maternity_patient)
        paginator = PageNumberPagination()
        paginated_pregnancies = paginator.paginate_queryset(pregnancies, request)
        serializer = PregnancySerializer(paginated_pregnancies, many=True)

        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = PregnancySerializer(data=request.data)

        if serializer.is_valid():
            pregnancy = serializer.save(doctor=request.user, maternity_patient=maternity_patient)

            return Response({
                'success': True,
                'message': 'Grossesse créée avec succès.',
                'data': PregnancySerializer(pregnancy).data
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
def pregnancy_detail(request, patient_id, pregnancy_id):
    """
    Récupère ou modifie une grossesse.

    GET /api/v1/maternite/patients/:id/pregnancies/:pid/
    PATCH /api/v1/maternite/patients/:id/pregnancies/:pid/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)

    if request.method == 'GET':
        serializer = PregnancySerializer(pregnancy)
        return Response({
            'success': True,
            'message': 'Grossesse récupérée avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = PregnancySerializer(pregnancy, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Grossesse mise à jour avec succès.',
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


# ========== WEEKLY CHECKUPS ==========

@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def weekly_checkup_list_create(request, patient_id, pregnancy_id):
    """
    Liste toutes les consultations hebdomadaires ou crée une nouvelle consultation.

    GET /api/v1/maternite/patients/:id/pregnancies/:pid/weekly-checkups/
    POST /api/v1/maternite/patients/:id/pregnancies/:pid/weekly-checkups/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)

    if request.method == 'GET':
        checkups = WeeklyCheckup.objects.filter(pregnancy=pregnancy)
        paginator = PageNumberPagination()
        paginated_checkups = paginator.paginate_queryset(checkups, request)
        serializer = WeeklyCheckupSerializer(paginated_checkups, many=True)

        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = WeeklyCheckupSerializer(data=request.data)

        if serializer.is_valid():
            checkup = serializer.save(doctor=request.user, pregnancy=pregnancy)

            return Response({
                'success': True,
                'message': 'Consultation hebdomadaire créée avec succès.',
                'data': WeeklyCheckupSerializer(checkup).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ========== PRENATAL CONSULTATIONS ==========

@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def prenatal_consultation_list_create(request, patient_id, pregnancy_id):
    """
    Liste toutes les consultations prénatales (CPN) ou crée une nouvelle CPN.

    GET /api/v1/maternite/patients/:id/pregnancies/:pid/prenatal-consultations/
    POST /api/v1/maternite/patients/:id/pregnancies/:pid/prenatal-consultations/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)

    if request.method == 'GET':
        consultations = PrenatalConsultation.objects.filter(pregnancy=pregnancy)
        paginator = PageNumberPagination()
        paginated_consultations = paginator.paginate_queryset(consultations, request)
        serializer = PrenatalConsultationSerializer(paginated_consultations, many=True)

        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = PrenatalConsultationSerializer(data=request.data)

        if serializer.is_valid():
            consultation = serializer.save(doctor=request.user, pregnancy=pregnancy)

            return Response({
                'success': True,
                'message': 'Consultation prénatale créée avec succès.',
                'data': PrenatalConsultationSerializer(consultation).data
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
def prenatal_consultation_detail(request, patient_id, pregnancy_id, consultation_id):
    """
    Récupère ou modifie une consultation prénatale.

    GET /api/v1/maternite/patients/:id/pregnancies/:pid/prenatal-consultations/:cid/
    PATCH /api/v1/maternite/patients/:id/pregnancies/:pid/prenatal-consultations/:cid/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)
    consultation = get_object_or_404(PrenatalConsultation, id=consultation_id, pregnancy=pregnancy)

    if request.method == 'GET':
        serializer = PrenatalConsultationSerializer(consultation)
        return Response({
            'success': True,
            'message': 'Consultation prénatale récupérée avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = PrenatalConsultationSerializer(consultation, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Consultation prénatale mise à jour avec succès.',
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


# ========== PRENATAL EXAMS ==========

@api_view(['POST'])
@permission_classes([IsDoctor])
def prenatal_exam_create(request, patient_id, pregnancy_id):
    """
    Ajoute un examen prénatal à une grossesse.

    POST /api/v1/maternite/patients/:id/pregnancies/:pid/prenatal-exams/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)

    serializer = PrenatalExamSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        exam = serializer.save(pregnancy=pregnancy)

        return Response({
            'success': True,
            'message': 'Examen prénatal ajouté avec succès.',
            'data': PrenatalExamSerializer(exam, context={'request': request}).data
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
def prenatal_exam_update(request, patient_id, pregnancy_id, exam_id):
    """
    Met à jour un examen prénatal (résultats, statut, etc.).

    PATCH /api/v1/maternite/patients/:id/pregnancies/:pid/prenatal-exams/:eid/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)
    exam = get_object_or_404(PrenatalExam, id=exam_id, pregnancy=pregnancy)

    serializer = PrenatalExamSerializer(exam, data=request.data, partial=True, context={'request': request})

    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': 'Examen prénatal mis à jour avec succès.',
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


# ========== CHILDREN ==========

@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def child_list_create(request, patient_id, pregnancy_id):
    """
    Liste tous les enfants d'une grossesse ou enregistre un nouveau-né.

    GET /api/v1/maternite/patients/:id/pregnancies/:pid/children/
    POST /api/v1/maternite/patients/:id/pregnancies/:pid/children/
    """
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)

    if request.method == 'GET':
        children = Child.objects.filter(pregnancy=pregnancy)
        serializer = ChildSerializer(children, many=True)

        return Response({
            'success': True,
            'count': children.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = ChildSerializer(data=request.data)

        if serializer.is_valid():
            child = serializer.save(pregnancy=pregnancy)

            return Response({
                'success': True,
                'message': 'Enfant enregistré avec succès.',
                'data': ChildSerializer(child).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


# ========== CHILD GROWTH ==========

@api_view(['POST'])
@permission_classes([IsDoctor])
def child_growth_create(request, child_id):
    """
    Ajoute un suivi de croissance pour un enfant.

    POST /api/v1/maternite/children/:id/growth/
    """
    child = get_object_or_404(Child, id=child_id)

    # Vérifier que le médecin a accès à cet enfant via la patiente
    if child.pregnancy.maternity_patient.patient.doctor != request.user:
        return Response({
            'success': False,
            'error': {
                'code': 'permission_denied',
                'message': 'Vous n\'avez pas accès à cet enfant.',
                'details': {}
            }
        }, status=status.HTTP_403_FORBIDDEN)

    serializer = ChildGrowthSerializer(data=request.data)

    if serializer.is_valid():
        growth = serializer.save(doctor=request.user, child=child)

        return Response({
            'success': True,
            'message': 'Suivi de croissance ajouté avec succès.',
            'data': ChildGrowthSerializer(growth).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


# ========== CHILD VACCINES ==========

@api_view(['POST'])
@permission_classes([IsDoctor])
def child_vaccine_create(request, child_id):
    """
    Ajoute un vaccin pour un enfant.

    POST /api/v1/maternite/children/:id/vaccines/
    """
    child = get_object_or_404(Child, id=child_id)

    # Vérifier que le médecin a accès à cet enfant via la patiente
    if child.pregnancy.maternity_patient.patient.doctor != request.user:
        return Response({
            'success': False,
            'error': {
                'code': 'permission_denied',
                'message': 'Vous n\'avez pas accès à cet enfant.',
                'details': {}
            }
        }, status=status.HTTP_403_FORBIDDEN)

    serializer = ChildVaccineSerializer(data=request.data)

    if serializer.is_valid():
        vaccine = serializer.save(doctor=request.user, child=child)

        return Response({
            'success': True,
            'message': 'Vaccin ajouté avec succès.',
            'data': ChildVaccineSerializer(vaccine).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)
