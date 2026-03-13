"""
Gestionnaire d'exceptions personnalisé pour Kendeya Backend.
Formate toutes les erreurs selon le format standardisé de l'API.
"""

from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotAuthenticated, PermissionDenied, NotFound
from django.http import Http404


def custom_exception_handler(exc, context):
    """
    Gestionnaire d'exceptions personnalisé pour formater les erreurs.
    Format de sortie : {"success": false, "error": {"code": "...", "message": "...", "details": {...}}}
    """
    # Appeler le gestionnaire par défaut de DRF
    response = exception_handler(exc, context)

    if response is not None:
        # Déterminer le code d'erreur en fonction du type d'exception
        error_code = get_error_code(exc)
        error_message = get_error_message(exc)
        error_details = response.data if isinstance(response.data, dict) else {'detail': response.data}

        # Formater la réponse selon notre standard
        response.data = {
            'success': False,
            'error': {
                'code': error_code,
                'message': error_message,
                'details': error_details
            }
        }

    return response


def get_error_code(exc):
    """Détermine le code d'erreur en fonction du type d'exception."""
    if isinstance(exc, ValidationError):
        return 'validation_error'
    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return 'authentication_failed'
    elif isinstance(exc, PermissionDenied):
        return 'permission_denied'
    elif isinstance(exc, (NotFound, Http404)):
        return 'not_found'
    else:
        return 'error'


def get_error_message(exc):
    """Retourne un message d'erreur en français en fonction du type d'exception."""
    if isinstance(exc, ValidationError):
        return "Les données fournies sont invalides."
    elif isinstance(exc, AuthenticationFailed):
        return "Échec de l'authentification."
    elif isinstance(exc, NotAuthenticated):
        return "Authentification requise."
    elif isinstance(exc, PermissionDenied):
        return "Vous n'avez pas la permission d'effectuer cette action."
    elif isinstance(exc, (NotFound, Http404)):
        return "Ressource introuvable."
    else:
        # Essayer d'extraire le message de l'exception
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                # Si c'est un dict, prendre la première valeur
                first_key = list(exc.detail.keys())[0] if exc.detail else 'error'
                return str(exc.detail[first_key])
            return str(exc.detail)
        return "Une erreur est survenue."
