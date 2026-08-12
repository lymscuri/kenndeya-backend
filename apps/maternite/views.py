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
    ChildGrowthSerializer, ChildVaccineSerializer,
    MyMaternityRecordSerializer
)


# ========== MATERNITY PATIENTS ==========
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def maternity_patient_list_create(request):
    if request.method == 'GET':
        # Récupérer les MaternityPatients liés aux patients du médecin
        maternity_patients = MaternityPatient.objects.filter(
            patient__doctor=request.user
        ).select_related('patient').prefetch_related(
            'pregnancies',
            'pregnancies__weekly_checkups',
            'pregnancies__prenatal_consultations',
            'pregnancies__prenatal_exams',
            'pregnancies__children',
            'pregnancies__children__growth_records',
            'pregnancies__children__vaccines',
        )

        from .alerts import evaluate_pregnancy

        results = []
        for mp in maternity_patients:
            patient = mp.patient
            # Itère sur la relation prefetchée pour éviter de relancer un
            # SELECT — .filter().first() casserait le cache prefetch.
            prefetched_pregnancies = list(mp.pregnancies.all())
            pregnancy = next(
                (p for p in prefetched_pregnancies if p.status == 'ongoing'),
                prefetched_pregnancies[0] if prefetched_pregnancies else None,
            )
            weekly_checkups = []
            prenatal_consultations = []
            prenatal_exams = []
            children = []
            child_growth = []
            child_vaccines = []
            alert_level, alert_reasons = evaluate_pregnancy(pregnancy)

            if pregnancy:
                # WeeklyCheckup : on ne renvoie que les champs qui existent réellement
                # dans le modèle. Le modèle n'a NI "fetal_movements" (seulement
                # fetal_heart_rate = BCF) NI "symptoms" (le champ voisin est
                # "complaints" = plaintes textuelles). "observations" n'est pas
                # l'humeur ("mood") mais une note clinique du médecin.
                weekly_checkups = [{
                    'id': str(wc.id),
                    'week_number': wc.week_number,
                    'checkup_date': str(wc.checkup_date),
                    'weight': float(wc.weight) if wc.weight is not None else None,
                    'blood_pressure_systolic': wc.blood_pressure_systolic,
                    'blood_pressure_diastolic': wc.blood_pressure_diastolic,
                    'uterine_height': float(wc.uterine_height) if wc.uterine_height is not None else None,
                    'fetal_heart_rate': wc.fetal_heart_rate,
                    'fetal_movements': wc.fetal_movements or None,
                    'symptoms': wc.symptoms or [],
                    'mood': wc.mood or None,
                    'complaints': wc.complaints,
                    'observations': wc.observations,
                    'recommendations': wc.recommendations,
                    'next_appointment': str(wc.next_appointment) if wc.next_appointment else None,
                } for wc in pregnancy.weekly_checkups.all()]

                prenatal_consultations = [{
                    'id': str(c.id),
                    'consultation_number': c.consultation_number,
                    'week_of_gestation': c.week_of_gestation,
                    'status': c.status,
                    'scheduled_date': str(c.scheduled_date) if c.scheduled_date else None,
                    'consultation_date': str(c.consultation_date) if c.consultation_date else None,
                } for c in pregnancy.prenatal_consultations.all()]

                prenatal_exams = [{
                    'id': str(e.id),
                    'exam_name': e.exam_name,
                    'exam_type': e.exam_type,
                    'status': e.status,
                    'ordered_date': str(e.ordered_date),
                    'completed_date': str(e.completed_date) if e.completed_date else None,
                    'results': e.results,
                    'interpretation': e.interpretation,
                    'prenatal_consultation': str(e.prenatal_consultation_id) if e.prenatal_consultation_id else None,
                } for e in pregnancy.prenatal_exams.all()]

                for child in pregnancy.children.all():
                    children.append({
                        'id': str(child.id),
                        'first_name': child.first_name,
                        'last_name': child.last_name,
                        'gender': child.gender,
                        'birth_date': str(child.birth_date),
                        'birth_weight': float(child.birth_weight) if child.birth_weight is not None else None,
                        'birth_height': float(child.birth_height) if child.birth_height is not None else None,
                        'head_circumference': float(child.head_circumference) if child.head_circumference is not None else None,
                        'apgar_score_1min': child.apgar_score_1min,
                        'apgar_score_5min': child.apgar_score_5min,
                        'complications': child.complications,
                        'notes': child.notes,
                    })

                    for g in child.growth_records.all():
                        child_growth.append({
                            'id': str(g.id),
                            'child': str(child.id),
                            'checkup_date': str(g.checkup_date),
                            'age_in_months': g.age_in_months,
                            'weight': float(g.weight) if g.weight is not None else None,
                            'height': float(g.height) if g.height is not None else None,
                            'head_circumference': float(g.head_circumference) if g.head_circumference is not None else None,
                            'nutritional_status': g.nutritional_status,
                            'developmental_milestones': g.developmental_milestones,
                            'observations': g.observations,
                            'recommendations': g.recommendations,
                            'next_appointment': str(g.next_appointment) if g.next_appointment else None,
                        })

                    for v in child.vaccines.all():
                        child_vaccines.append({
                            'id': str(v.id),
                            'child': str(child.id),
                            'vaccine_name': v.vaccine_name,
                            'vaccine_type': v.vaccine_type,
                            'dose_number': v.dose_number,
                            'date_administered': str(v.date_administered),
                            'next_dose_date': str(v.next_dose_date) if v.next_dose_date else None,
                            'batch_number': v.batch_number,
                            'manufacturer': v.manufacturer,
                            'site': v.site,
                            'notes': v.notes,
                        })

            results.append({
                'id': str(patient.id),
                'maternity_id': str(mp.id),
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'full_name': patient.full_name,
                'age': patient.age,
                'date_of_birth': str(patient.date_of_birth),
                'gender': patient.gender,
                'phone': patient.phone,
                'email': patient.email,
                'doctor': str(patient.doctor_id),
                'linked_email': patient.email,
                'created_at': str(patient.created_at),
                'pregnancy': {
                    'id': str(pregnancy.id),
                    'is_active': pregnancy.status == 'ongoing',
                    'current_week': pregnancy.weeks_of_gestation or 0,
                    'due_date': str(pregnancy.expected_delivery_date) if pregnancy.expected_delivery_date else None,
                    'last_period_date': str(pregnancy.last_menstrual_period) if pregnancy.last_menstrual_period else None,
                    'gravidity': mp.number_of_pregnancies,
                    'parity': mp.number_of_deliveries,
                } if pregnancy else None,
                'weekly_checkups': weekly_checkups,
                'prenatal_consultations': prenatal_consultations,
                'prenatal_exams': prenatal_exams,
                'children': children,
                'child_growth': child_growth,
                'child_vaccines': child_vaccines,
                'alert_level': alert_level,
                'alert_reasons': alert_reasons,
            })
        
        return Response({
            'success': True,
            'count': len(results),
            'results': results
        })

    if request.method == 'POST':
        from datetime import date
        data = request.data
        patient = Patient.objects.create(
            doctor=request.user,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
            date_of_birth=data.get('date_of_birth', '1990-01-01'),
            email=data.get('linked_email', ''),
        )
        # Créer aussi le profil MaternityPatient lié
        maternity = MaternityPatient.objects.create(
            patient=patient,
        )

        # Créer automatiquement la grossesse si DDR fournie
        pregnancy = None
        ddr_str = data.get('last_menstrual_period') or data.get('last_period_date')
        if ddr_str:
            try:
                from datetime import datetime, timedelta
                ddr = datetime.strptime(ddr_str, '%Y-%m-%d').date()
                dpa_str = data.get('expected_delivery_date')
                if dpa_str:
                    dpa = datetime.strptime(dpa_str, '%Y-%m-%d').date()
                else:
                    dpa = ddr + timedelta(days=280)

                pregnancy = Pregnancy.objects.create(
                    maternity_patient=maternity,
                    doctor=request.user,
                    pregnancy_number=int(data.get('pregnancy_number', 1)),
                    status='ongoing',
                    last_menstrual_period=ddr,
                    expected_delivery_date=dpa,
                    weeks_of_gestation=data.get('weeks_of_gestation') or None,
                )
            except Exception as e:
                print(f"[Warning] Pregnancy auto-create failed: {e}")

        return Response({
            'success': True,
            'message': 'Patiente maternité créée.',
            'data': {
                'id': str(patient.id),
                'maternity_id': str(maternity.id),
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'pregnancy_id': str(pregnancy.id) if pregnancy else None,
            }
        }, status=201)


@api_view(['GET'])
@permission_classes([IsDoctor])
def maternity_patient_detail_simple(request, patient_id):
    """GET /api/v1/maternity/patients/:id/"""
    from apps.dossiers.models import Patient
    from django.shortcuts import get_object_or_404
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
    return Response({
        'success': True,
        'data': {
            'id': str(patient.id),
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
@permission_classes([IsAuthenticated])
def weekly_checkup_list_create(request, patient_id, pregnancy_id):
    """
    Liste toutes les consultations hebdomadaires ou crée une nouvelle consultation.

    GET /api/v1/maternite/patients/:id/pregnancies/:pid/weekly-checkups/
    POST /api/v1/maternite/patients/:id/pregnancies/:pid/weekly-checkups/

    Contrôle d'accès :
    - Médecin (role in doctor/medecin) : accès uniquement si patient.doctor == request.user.
    - Patiente (role == 'patient') : accès uniquement si patient.email == request.user.email
      (même critère que my_maternity_record). Ne peut donc écrire QUE sur sa
      propre grossesse.
    - Tout autre rôle (secouriste, etc.) : 403.

    Le doctor enregistré sur le checkup reste celui de la grossesse
    (pregnancy.doctor), y compris quand c'est la patiente elle-même qui
    remplit le suivi — c'est la même personne qui la suit.
    """
    patient = get_object_or_404(Patient, id=patient_id)
    maternity_patient = get_object_or_404(MaternityPatient, patient=patient)
    pregnancy = get_object_or_404(Pregnancy, id=pregnancy_id, maternity_patient=maternity_patient)

    user = request.user
    user_role = getattr(user, 'role', None)
    is_doctor = user_role in ('doctor', 'medecin') and patient.doctor_id == user.id
    is_owner_patient = (
        user_role == 'patient'
        and patient.email
        and patient.email.lower() == (user.email or '').lower()
    )

    if not (is_doctor or is_owner_patient):
        return Response({
            'success': False,
            'error': {
                'code': 'permission_denied',
                'message': "Vous n'avez pas accès à cette grossesse.",
            }
        }, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        checkups = WeeklyCheckup.objects.filter(pregnancy=pregnancy)
        paginator = PageNumberPagination()
        paginated_checkups = paginator.paginate_queryset(checkups, request)
        serializer = WeeklyCheckupSerializer(paginated_checkups, many=True)

        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = WeeklyCheckupSerializer(data=request.data)

        if serializer.is_valid():
            checkup = serializer.save(doctor=pregnancy.doctor, pregnancy=pregnancy)

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


# ========== MY MATERNITY RECORD ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_maternity_record(request):
    """
    Retourne le dossier maternité complet de la patiente connectée.
    Accessible aux patientes et médecins.

    GET /api/v1/maternity/my-record/
    """
    # Chercher la patiente maternité dont l'email du patient correspond à l'utilisateur connecté
    # Optimisation : select_related pour patient et doctor, prefetch_related pour relations many
    maternity_patient = MaternityPatient.objects.select_related(
        'patient'
    ).prefetch_related(
        'pregnancies',
        'pregnancies__doctor',
        'pregnancies__prenatal_consultations',
        'pregnancies__children',
        'pregnancies__children__vaccines'
    ).filter(
        patient__email=request.user.email
    ).first()

    if not maternity_patient:
        return Response({
            'success': False,
            'error': {
                'code': 'not_found',
                'message': 'Aucun dossier maternité trouvé pour cet utilisateur.',
                'details': {
                    'email': request.user.email,
                    'suggestion': 'Veuillez contacter votre médecin pour créer votre dossier maternité.'
                }
            }
        }, status=status.HTTP_404_NOT_FOUND)

    # Sérialiser le dossier complet
    serializer = MyMaternityRecordSerializer(maternity_patient)

    return Response({
        'success': True,
        'message': 'Dossier maternité récupéré avec succès.',
        'data': serializer.data
    }, status=status.HTTP_200_OK)
