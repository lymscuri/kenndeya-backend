"""
Profil STAGING — environnement de test Railway (application installée sur le
téléphone du DG uniquement). Ce n'est PAS la production publique.

Strictement identique à production.py (sécurité, HTTPS, cookies, cache Redis,
WhiteNoise, Sentry…). Une seule différence : FIRSTAID_ALLOW_DRAFTS est lu
depuis l'environnement, pour que les protocoles de premiers secours encore
en brouillon (non validés par un médecin) soient servis à l'app de test.

NE JAMAIS utiliser ce profil pour le lancement public : au lancement, Railway
repasse sur DJANGO_SETTINGS_MODULE=config.settings.production, qui force
FIRSTAID_ALLOW_DRAFTS = False en dur sans lire l'environnement.
"""

from .production import *  # noqa: F401,F403 — même configuration que la production

# Seule différence avec production.py : brouillons firstaid servis si la
# variable d'environnement FIRSTAID_ALLOW_DRAFTS vaut True. Défaut : False.
FIRSTAID_ALLOW_DRAFTS = env.bool('FIRSTAID_ALLOW_DRAFTS', default=False)  # noqa: F405
