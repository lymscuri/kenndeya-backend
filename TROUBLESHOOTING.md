# Guide de dépannage - Déploiement Railway

## ✅ Changements effectués pour résoudre le healthcheck

1. **ALLOWED_HOSTS** - Valeur par défaut `['*']` si non configuré
2. **SECURE_SSL_REDIRECT** - Désactivé par défaut (Railway gère HTTPS)
3. **start.sh** - Script de démarrage robuste avec logs
4. **Healthcheck timeout** - Augmenté à 100s
5. **Procfile** - Simplifié pour utiliser start.sh

## 🔍 Comment déboguer sur Railway

### Voir les logs de l'application

1. Dans Railway Dashboard, cliquer sur votre service
2. Aller dans l'onglet "Deployments"
3. Cliquer sur le déploiement actuel
4. Voir les logs en temps réel

### Erreurs communes

#### 1. "DisallowedHost at /"

**Cause**: ALLOWED_HOSTS non configuré

**Solution**: Ajouter la variable dans Railway:
```
ALLOWED_HOSTS=votre-app.up.railway.app
```

#### 2. "Connection refused" (PostgreSQL)

**Cause**: DATABASE_URL non configuré

**Solution**:
- Vérifier que PostgreSQL est ajouté au projet
- Railway génère automatiquement DATABASE_URL
- Vérifier dans "Variables" du service

#### 3. "Connection refused" (Redis)

**Cause**: REDIS_URL non configuré

**Solution**:
- Vérifier que Redis est ajouté au projet
- Railway génère automatiquement REDIS_URL

#### 4. Healthcheck échoue après 30s

**Cause**: Migrations trop longues

**Solution**: Le timeout est maintenant à 100s. Si ça échoue encore:
- Vérifier les logs pour voir où ça bloque
- Les migrations peuvent prendre du temps la première fois

## 📝 Variables d'environnement requises

**Minimales** (pour que ça démarre):
```
DJANGO_SETTINGS_MODULE=config.settings.production
```

**Recommandées**:
```
DJANGO_SETTINGS_MODULE=config.settings.production
ALLOWED_HOSTS=votre-app.up.railway.app
DEBUG=False
```

**Optionnelles** (SMS):
```
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
```

## 🚀 Redéployer avec les nouveaux changements

```bash
git add .
git commit -m "Fix: Healthcheck avec ALLOWED_HOSTS par défaut et timeout augmenté"
git push origin main
```

## 💡 Astuces

- Les logs Gunicorn sont maintenant visibles dans Railway
- Le script start.sh affiche clairement chaque étape
- Si les migrations échouent, le déploiement s'arrête immédiatement
