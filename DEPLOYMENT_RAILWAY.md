# Guide de déploiement sur Railway

## ✅ Fichiers de configuration prêts

- ✓ `requirements.txt` - Toutes les dépendances
- ✓ `runtime.txt` - Python 3.11.9
- ✓ `Procfile` - Commandes de démarrage
- ✓ `railway.json` - Configuration Railway
- ✓ `.env.example` - Template avec SECRET_KEY

## 🚀 Étapes de déploiement

### 1. Pousser le code sur GitHub

```bash
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

### 2. Créer le projet Railway

1. Aller sur https://railway.app
2. Cliquer sur "New Project"
3. Sélectionner "Deploy from GitHub repo"
4. Choisir le repository `kenndeya-backend`

### 3. Ajouter PostgreSQL

1. Dans le projet Railway, cliquer "+ New"
2. Sélectionner "Database" → "PostgreSQL"
3. Railway générera automatiquement `DATABASE_URL`

### 4. Ajouter Redis

1. Cliquer "+ New"
2. Sélectionner "Database" → "Redis"
3. Railway générera automatiquement `REDIS_URL`

### 5. Configurer les variables d'environnement

Dans le service Django (web), ajouter:

```
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=%o8fjwdf+9jcc35b7q@(2e##ig@ky9x^(o8m7ir=3)5x-giq14
ALLOWED_HOSTS=<votre-domaine-railway>
```

**IMPORTANT**: Remplacer `<votre-domaine-railway>` par votre URL Railway.
Exemple: `myapp.up.railway.app`

### 6. Variables optionnelles (SMS)

```
TWILIO_ACCOUNT_SID=votre_sid
TWILIO_AUTH_TOKEN=votre_token
TWILIO_PHONE_NUMBER=votre_numero
```

### 7. Vérifier le déploiement

Une fois déployé, tester:

- Health check: `https://votre-app.up.railway.app/health/`
- API Docs: `https://votre-app.up.railway.app/api/docs/`
- Admin: `https://votre-app.up.railway.app/admin/`

### 8. Créer un superutilisateur

Utiliser le CLI Railway:

```bash
railway login
railway link
railway run python manage.py createsuperuser
```

Ou ajouter ces variables:
```
DJANGO_SUPERUSER_EMAIL=admin@kendeya.com
DJANGO_SUPERUSER_PASSWORD=VotreMotDePasse
```

### 9. Services Celery (optionnel)

Pour les tâches asynchrones:

1. Dupliquer le service web
2. Renommer en "celery-worker"
3. Changer la variable `RAILWAY_SERVICE_NAME=worker`
4. Pour Celery Beat, créer un autre service avec `RAILWAY_SERVICE_NAME=beat`

## 🔒 SÉCURITÉ IMPORTANTE

⚠️ **TOKEN GITHUB COMPROMIS**: Le token que vous avez partagé doit être révoqué immédiatement:

1. Aller sur https://github.com/settings/tokens
2. Trouver le token et cliquer "Delete"
3. Créer un nouveau token si nécessaire

## 📝 Notes

- Le Procfile gère automatiquement les migrations et collectstatic
- Les logs sont accessibles dans Railway Dashboard
- Les redéploiements se font automatiquement à chaque push
