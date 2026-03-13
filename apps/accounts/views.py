"""
Vues pour l'application accounts.
Gère l'authentification et la gestion des utilisateurs.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login as django_login

from .models import User
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    ChangePasswordSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Inscription d'un nouvel utilisateur.

    POST /api/v1/auth/register/
    Body: {
        "email": "user@example.com",
        "password": "securepassword",
        "password_confirm": "securepassword",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+224XXXXXXXXX",
        "role": "patient"
    }
    """
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            'success': True,
            'message': 'Inscription réussie.',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Connexion d'un utilisateur existant.

    POST /api/v1/auth/login/
    Body: {
        "email": "user@example.com",
        "password": "securepassword"
    }
    """
    serializer = LoginSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        user = serializer.validated_data['user']

        # Connecter l'utilisateur
        django_login(request, user)

        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            'success': True,
            'message': 'Connexion réussie.',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        }, status=status.HTTP_200_OK)

    return Response({
        'success': False,
        'error': {
            'code': 'authentication_failed',
            'message': 'Échec de l\'authentification.',
            'details': serializer.errors
        }
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Déconnexion d'un utilisateur (blacklist du refresh token).

    POST /api/v1/auth/logout/
    Body: {
        "refresh": "refresh_token_here"
    }
    """
    try:
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response({
                'success': False,
                'error': {
                    'code': 'validation_error',
                    'message': 'Le refresh token est requis.',
                    'details': {}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Blacklist le refresh token
        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({
            'success': True,
            'message': 'Déconnexion réussie.',
            'data': {}
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'error': {
                'code': 'error',
                'message': 'Une erreur est survenue lors de la déconnexion.',
                'details': {'detail': str(e)}
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Récupère les informations de l'utilisateur connecté.

    GET /api/v1/auth/me/
    """
    serializer = UserSerializer(request.user)

    return Response({
        'success': True,
        'message': 'Informations utilisateur récupérées.',
        'data': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Met à jour le profil de l'utilisateur connecté.

    PATCH /api/v1/auth/profile/
    Body: {
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+224XXXXXXXXX"
    }
    """
    serializer = UserSerializer(
        request.user,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()

        return Response({
            'success': True,
            'message': 'Profil mis à jour avec succès.',
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change le mot de passe de l'utilisateur connecté.

    POST /api/v1/auth/change-password/
    Body: {
        "old_password": "oldpassword",
        "new_password": "newpassword",
        "new_password_confirm": "newpassword"
    }
    """
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={'request': request}
    )

    if serializer.is_valid():
        serializer.save()

        return Response({
            'success': True,
            'message': 'Mot de passe changé avec succès.',
            'data': {}
        }, status=status.HTTP_200_OK)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)
