"""
Classes de pagination personnalisées pour Kendeya Backend.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Pagination standard pour toutes les listes de l'API.
    - Taille de page par défaut : 20
    - Taille de page maximale : 100
    - Paramètre de requête pour personnaliser la taille : page_size
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Retourne une réponse paginée au format standardisé.
        Format : {"success": true, "count": X, "next": ..., "previous": ..., "results": [...]}
        """
        return Response({
            'success': True,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
