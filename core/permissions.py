"""
Permissions personnalisées pour Kendeya Backend.
Définit les permissions basées sur les rôles d'utilisateur.
"""

from rest_framework.permissions import BasePermission


class IsDoctor(BasePermission):
    """
    Permission pour vérifier que l'utilisateur est un médecin/soignant.
    Vérifie que user.role == 'doctor'.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'medecin'
        )


class IsPatient(BasePermission):
    """
    Permission pour vérifier que l'utilisateur est un patient.
    Vérifie que user.role == 'patient'.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'patient'
        )


class IsSecourist(BasePermission):
    """
    Permission pour vérifier que l'utilisateur est un secouriste.
    Vérifie que user.role == 'secourist'.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'secourist'
        )


class IsDoctorOrReadOnly(BasePermission):
    """
    Permission permettant aux médecins de modifier,
    mais autorisant la lecture à tous les utilisateurs authentifiés.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Méthodes de lecture autorisées pour tous
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Méthodes d'écriture réservées aux médecins
        return (
            hasattr(request.user, 'role') and
            request.user.role == 'medecin'
        )
