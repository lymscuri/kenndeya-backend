"""
Limitation de débit par portée pour les vues @api_view anonymes.

ScopedRateThrottle de DRF lit `view.throttle_scope`, attribut qu'une vue
fonction décorée par @api_view ne porte pas : la limite n'est alors jamais
appliquée. Cette classe lit la portée sur elle-même et compte par adresse IP
(comme AnonRateThrottle), le taux venant de REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
"""

from rest_framework.throttling import SimpleRateThrottle


class ScopedAnonThrottle(SimpleRateThrottle):
    """À sous-classer avec `scope = '<clé de DEFAULT_THROTTLE_RATES>'`."""

    scope = None

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}
