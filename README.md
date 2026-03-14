# Kendeya Backend API

Backend Django REST Framework pour la plateforme de gestion médicale Kendeya (Guinée).

## 🏗️ Architecture

### Technologies
- **Framework**: Django 5.x + Django REST Framework
- **Base de données**: PostgreSQL
- **Cache & Queue**: Redis
- **Tasks asynchrones**: Celery + Celery Beat
- **WebSocket**: Django Channels
- **Authentification**: JWT (Simple JWT)

### Applications Django

1. **accounts** - Authentification et gestion des utilisateurs
2. **dossiers** - Dossiers médicaux et consultations
3. **maternite** - Suivi de grossesse et croissance enfants
4. **urgences** - Alertes d'urgence en temps réel
5. **reminders** - Rappels SMS automatiques

## 📊 Modèles de données

### Accounts (1 modèle)
- `User` - Utilisateurs (doctor, patient, secourist)

### Dossiers (6 modèles)
- `Patient` - Informations patients
- `MedicalRecord` - Dossiers médicaux avec QR codes
- `Consultation` - Consultations médicales
- `Prescription` - Ordonnances
- `LabTest` - Examens de laboratoire
- `Vaccination` - Vaccinations

### Maternité (8 modèles)
- `MaternityPatient` - Profil maternité
- `Pregnancy` - Grossesses
- `WeeklyCheckup` - Consultations hebdomadaires
- `PrenatalConsultation` - CPN
- `PrenatalExam` - Examens prénatals
- `Child` - Enfants
- `ChildGrowth` - Suivi de croissance
- `ChildVaccine` - Vaccins enfants

### Urgences (3 modèles)
- `EmergencyAlert` - Alertes d'urgence
- `Secourist` - Secouristes
- `Hospital` - Hôpitaux

### Reminders (1 modèle)
- `SmsReminder` - Rappels SMS

**Total: 18 modèles**

## 🚀 Installation

### Prérequis
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### Configuration locale

1. **Cloner le dépôt**
```bash
git clone <repository-url>
cd mybackend
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements/development.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

5. **Créer la base de données**
```bash
# Se connecter à PostgreSQL
psql -U postgres

# Créer la base de données et l'utilisateur
CREATE DATABASE kendeya_db;
CREATE USER kendeya_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE kendeya_db TO kendeya_user;
\q
```

6. **Appliquer les migrations**
```bash
python manage.py migrate
```

7. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

8. **Charger les données de test (optionnel)**
```bash
python manage.py seed_data
```

9. **Lancer le serveur**
```bash
python manage.py runserver
```

L'API sera accessible à `http://localhost:8000/`

### Lancer Celery (pour les tâches asynchrones)

Dans un terminal séparé:
```bash
# Worker Celery
celery -A config worker -l info

# Celery Beat (tâches périodiques)
celery -A config beat -l info
```

## 📖 Documentation API

L'API est documentée avec OpenAPI 3.0 (Swagger) grâce à drf-spectacular.

### Accéder à la documentation

- **Swagger UI** (interface interactive) : `http://localhost:8000/api/docs/`
- **ReDoc** (documentation lisible) : `http://localhost:8000/api/redoc/`
- **Schéma OpenAPI** (format YAML) : `http://localhost:8000/api/schema/`

### Générer le schéma OpenAPI

```bash
python manage.py spectacular --file schema.yml
```

## 📡 Endpoints API

### Authentification (`/api/v1/auth/`)
- `POST /register/` - Inscription
- `POST /login/` - Connexion
- `POST /logout/` - Déconnexion
- `GET /me/` - Profil utilisateur
- `PATCH /update-profile/` - Mise à jour profil
- `POST /change-password/` - Changement mot de passe
- `POST /token/refresh/` - Rafraîchir token JWT

### Dossiers (`/api/v1/dossiers/`)
- `GET/POST /patients/` - Liste/Création patients
- `GET/PATCH/DELETE /patients/{id}/` - Détails patient
- `GET /patients/{id}/medical-record/` - Dossier médical avec QR
- `GET/POST /patients/{id}/consultations/` - Consultations
- `GET/PATCH /patients/{id}/consultations/{cid}/` - Détails consultation
- `POST /patients/{id}/consultations/{cid}/prescriptions/` - Prescriptions
- `POST /patients/{id}/consultations/{cid}/lab-tests/` - Examens labo
- `GET/POST /patients/{id}/vaccinations/` - Vaccinations

### Maternité (`/api/v1/maternity/`)
- `POST /patients/{id}/maternity-profile/` - Créer profil maternité
- `GET/PATCH /patients/{id}/maternity-profile/detail/` - Détails profil
- `GET/POST /patients/{id}/pregnancies/` - Grossesses
- `GET/PATCH /patients/{id}/pregnancies/{pid}/` - Détails grossesse
- `GET/POST /patients/{id}/pregnancies/{pid}/weekly-checkups/` - Consultations hebdo
- `GET/POST /patients/{id}/pregnancies/{pid}/prenatal-consultations/` - CPN
- `POST /patients/{id}/pregnancies/{pid}/prenatal-exams/` - Examens prénatals
- `GET/POST /patients/{id}/pregnancies/{pid}/children/` - Enfants
- `POST /children/{id}/growth/` - Suivi de croissance
- `POST /children/{id}/vaccines/` - Vaccins enfants

### Urgences (`/api/v1/emergency/`)
- `POST /secourist/profile/` - Créer profil secouriste
- `GET/PATCH /secourist/profile/detail/` - Détails profil secouriste
- `GET /secourists/` - Liste secouristes
- `GET /hospitals/` - Liste hôpitaux
- `GET /hospitals/{id}/` - Détails hôpital
- `POST /alerts/` - Créer alerte urgence
- `GET /alerts/list/` - Liste alertes
- `GET /alerts/pending/` - Alertes en attente
- `GET /alerts/{id}/` - Détails alerte
- `PATCH /alerts/{id}/assign/` - Assigner alerte
- `PATCH /alerts/{id}/status/` - Mettre à jour statut

### Rappels (`/api/v1/reminders/`)
- `GET/POST /sms/` - Liste/Création rappels SMS
- `GET/PATCH/DELETE /sms/{id}/` - Détails rappel SMS

### WebSocket
- `ws://localhost:8000/ws/urgences/alerts/` - Canal secouristes
- `ws://localhost:8000/ws/urgences/patient/alerts/` - Canal patients

## 🧪 Tests

### Lancer tous les tests
```bash
python manage.py test
```

### Lancer les tests d'une app spécifique
```bash
python manage.py test apps.accounts
python manage.py test apps.dossiers
```

### Avec coverage
```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # Génère un rapport HTML
```

## 🔐 Permissions

Le système utilise 3 rôles:
- **doctor** - Accès complet aux dossiers patients
- **patient** - Accès à ses propres données
- **secourist** - Accès aux alertes d'urgence

Les permissions personnalisées:
- `IsDoctor` - Réservé aux médecins
- `IsPatient` - Réservé aux patients
- `IsSecourist` - Réservé aux secouristes

## 📝 Administration

L'interface admin Django est accessible à `/admin/`

Fonctionnalités:
- Gestion complète de tous les modèles
- Filtres et recherche avancée
- Inlines pour relations (consultations, prescriptions, etc.)
- Export de données

## 🔄 Tâches Celery

### Tâches configurées
1. **send_sms_reminder** - Envoi d'un SMS de rappel
2. **process_pending_sms** - Traitement des SMS en attente (toutes les minutes)
3. **cleanup_old_sms** - Nettoyage des vieux SMS (quotidien)

## 🌍 Déploiement sur Railway

### Prérequis

- Compte GitHub avec le code poussé sur un repository
- Compte Railway (gratuit pour commencer)

### Étapes de déploiement

#### 1. Créer un nouveau projet Railway

1. Aller sur [railway.app](https://railway.app)
2. Cliquer sur "New Project"
3. Sélectionner "Deploy from GitHub repo"
4. Autoriser Railway à accéder à votre repository GitHub
5. Sélectionner le repository `mybackend`

#### 2. Ajouter les services nécessaires

**PostgreSQL:**
1. Dans votre projet Railway, cliquer sur "+ New"
2. Sélectionner "Database" → "PostgreSQL"
3. Railway créera automatiquement la variable `DATABASE_URL`

**Redis:**
1. Cliquer sur "+ New"
2. Sélectionner "Database" → "Redis"
3. Railway créera automatiquement la variable `REDIS_URL`

#### 3. Configurer les variables d'environnement

Dans les settings de votre service Django (web), ajouter les variables suivantes:

| Variable | Valeur | Note |
|----------|--------|------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | Obligatoire |
| `SECRET_KEY` | `%o8fjwdf+9jcc35b7q@(2e##ig@ky9x^(o8m7ir=3)5x-giq14` | Déjà configurée |
| `DATABASE_URL` | Auto-généré par Railway | Fourni automatiquement |
| `REDIS_URL` | Auto-généré par Railway | Fourni automatiquement |
| `ALLOWED_HOSTS` | Votre domaine Railway (ex: `your-app.up.railway.app`) | Mettre à jour après déploiement |
| `CORS_ALLOWED_ORIGINS` | URLs frontend (ex: `https://your-frontend.com`) | Optionnel |
| `TWILIO_ACCOUNT_SID` | Votre SID Twilio | Optionnel (pour SMS) |
| `TWILIO_AUTH_TOKEN` | Votre token Twilio | Optionnel (pour SMS) |
| `TWILIO_PHONE_NUMBER` | Votre numéro Twilio | Optionnel (pour SMS) |

#### 4. Déployer l'application

Railway déploiera automatiquement votre application dès que vous poussez du code sur GitHub. Le fichier `railway.json` contient la configuration de build:

```json
{
  "build": {
    "buildCommand": "pip install -r requirements/production.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput"
  },
  "deploy": {
    "startCommand": "gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 4"
  }
}
```

#### 5. Vérifier le déploiement

1. Aller dans l'onglet "Deployments" de votre service
2. Vérifier que le build s'est terminé sans erreur
3. Accéder à l'URL fournie par Railway (ex: `https://your-app.up.railway.app`)
4. Tester les endpoints:
   - `https://your-app.up.railway.app/health/` - Doit retourner `{"status": "healthy"}`
   - `https://your-app.up.railway.app/api/docs/` - Documentation Swagger
   - `https://your-app.up.railway.app/admin/` - Interface admin

#### 6. Créer un superutilisateur

Utiliser le Railway CLI ou l'interface web:

```bash
# Avec Railway CLI
railway run python manage.py createsuperuser

# Ou via l'interface web Railway
# Settings → Variables → + New Variable
# DJANGO_SUPERUSER_EMAIL=admin@kendeya.com
# DJANGO_SUPERUSER_PASSWORD=VotreMotDePasse
```

#### 7. Configurer les workers Celery (optionnel)

Pour les tâches asynchrones, créer un nouveau service dans Railway:

1. Dupliquer le service web
2. Changer la commande de démarrage en: `celery -A config worker -l info`
3. Pour Celery Beat, créer un autre service avec: `celery -A config beat -l info`

### Mise à jour du code

Pour déployer de nouvelles modifications:

```bash
git add .
git commit -m "Votre message"
git push origin main
```

Railway redéploiera automatiquement l'application.

## 📄 License

Propriétaire - Tous droits réservés

## 👥 Contributeurs

- Développé avec Claude Code

## 🆘 Support

Pour toute question ou problème, créer une issue sur le dépôt GitHub.
