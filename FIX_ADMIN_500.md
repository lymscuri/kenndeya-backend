# Fix Admin 500 Error

## Changements effectués

1. ✅ **STORAGES** - Utilisation de `CompressedStaticFilesStorage` au lieu de `CompressedManifestStaticFilesStorage`
2. ✅ **start.sh** - Vérification que collectstatic réussit (exit 1 si échec)
3. ✅ **Logging** - Level INFO pour voir les erreurs
4. ✅ **static/.gitkeep** - S'assurer que le dossier static existe

## Pour déployer

```bash
git add .
git commit -m "Fix: Admin 500 - Configuration staticfiles améliorée"
git push origin main
```

## Après le redéploiement

1. **Vérifier les logs** sur Railway pour voir:
   - "Collecting static files..."
   - "Static files collected successfully in /app/staticfiles/"
   - Liste des fichiers collectés

2. **Tester l'admin**:
   - `https://kenndeya-backend-production.up.railway.app/admin/`

## Si l'erreur 500 persiste

Sur Railway, vérifier les logs pour voir l'erreur exacte. Les logs détaillés sont maintenant activés.

Erreurs possibles:
- **Fichiers statiques manquants** → Vérifier dans les logs que collectstatic a réussi
- **CSRF token missing** → Ajouter `CSRF_TRUSTED_ORIGINS`
- **Database error** → Vérifier que les migrations ont réussi

## Variables Railway à vérifier

Assurez-vous que ces variables sont configurées:
```
DJANGO_SETTINGS_MODULE=config.settings.production
ALLOWED_HOSTS=kenndeya-backend-production.up.railway.app
DATABASE_URL=<auto-généré>
REDIS_URL=<auto-généré>
```

## Créer un superutilisateur

Une fois l'admin accessible:

```bash
# Avec Railway CLI
railway run python manage.py createsuperuser

# Ou via variables d'environnement Railway
DJANGO_SUPERUSER_EMAIL=admin@kendeya.com
DJANGO_SUPERUSER_PASSWORD=VotreMotDePasse
```
