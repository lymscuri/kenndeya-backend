"""
Configuration de l'app firstaid.

Au démarrage, tous les protocoles YAML sont chargés et validés. Une seule
erreur (fichier malformé, page source manquante, 'validated' sans signataire,
étape trop longue, bascule vers un scénario absent…) empêche Django de démarrer :
mieux vaut un déploiement refusé qu'une consigne de secours douteuse affichée.
"""

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class FirstaidConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.firstaid'
    verbose_name = 'Premiers secours'

    def ready(self):
        from .loader import registry
        from .schema import ProtocolValidationError

        try:
            registry.load()
        except ProtocolValidationError as exc:
            # ImproperlyConfigured stoppe net manage.py / gunicorn avec le détail.
            raise ImproperlyConfigured(str(exc)) from exc
