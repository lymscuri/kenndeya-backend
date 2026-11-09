# CLAUDE.md — Kendeya Backend
## Instructions pour Claude Code

---

## 🔴 RÈGLE ABSOLUE — UNE TÂCHE À LA FOIS + TEST OBLIGATOIRE

**Ne jamais construire plusieurs sprints ou plusieurs fichiers en une seule fois.**
**Ne jamais passer au fichier suivant sans avoir testé le fichier courant.**

---

### 🔁 Protocole obligatoire pour CHAQUE fichier

```
ÉTAPE 1 — Annonce
  → "Je vais créer apps/xxx/models.py. Voici ce qu'il contiendra : ..."

ÉTAPE 2 — Création
  → Écrire le fichier

ÉTAPE 3 — Test syntaxe Django (OBLIGATOIRE)
  → python manage.py check --settings=config.settings.development
  → Résultat attendu : "System check identified no issues (0 silenced)."
  → Si erreur : corriger AVANT de continuer

ÉTAPE 4 — Test spécifique au type de fichier (voir tableau ci-dessous)

ÉTAPE 5 — Rapport
  → Afficher : ✅ Fichier créé + résultat des tests
  → Mettre à jour la case [ ] → [x] dans ce CLAUDE.md

ÉTAPE 6 — Pause
  → "apps/xxx/models.py ✅ testé et validé. Prêt pour apps/xxx/serializers.py ?"
  → ATTENDRE confirmation avant de continuer
```

---

### 🧪 Tests par type de fichier

| Fichier | Tests à exécuter |
|---|---|
| `models.py` | `manage.py check` + `manage.py makemigrations --check --dry-run` |
| `serializers.py` | `manage.py check` + import test : `python -c "from apps.xxx.serializers import *; print('OK')"` |
| `views.py` | `manage.py check` + import test : `python -c "from apps.xxx.views import *; print('OK')"` |
| `urls.py` | `manage.py check` + `manage.py show_urls` (si django-extensions) ou vérification manuelle |
| `admin.py` | `manage.py check` |
| `tasks.py` | `manage.py check` + import test |
| `consumers.py` | `manage.py check` + import test |

---

### 🧪 Tests de sprint (fin de chaque sprint complet)

À la fin de chaque sprint, avant de passer au sprint suivant :

```bash
# 1. Vérification globale Django
python manage.py check --settings=config.settings.development

# 2. Générer + vérifier les migrations
python manage.py makemigrations --settings=config.settings.development
python manage.py migrate --settings=config.settings.development

# 3. Lancer les tests unitaires du sprint
python manage.py test apps.<module>.tests --settings=config.settings.development -v 2

# 4. Vérifier que le serveur démarre
python manage.py runserver --settings=config.settings.development &
sleep 3
curl -s http://localhost:8000/health/ | python -m json.tool
kill %1
```

Tous ces tests doivent passer avant de déclarer le sprint **TERMINÉ ✅**.

---

## 📋 Contexte du projet

**Nom** : Kendeya Backend
**Description** : Backend Django pour l'application de santé Kendeya — dossiers médicaux, maternité, urgences temps réel, rappels SMS.
**Stack** : Django 5.x + DRF + SimpleJWT + PostgreSQL + Redis + Celery + Django Channels
**Déploiement** : Railway
**Langue** : Français (commentaires, messages d'erreur, réponses)

---

## 🗂️ Structure du projet

```
kendeya_backend/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── accounts/       # Auth JWT + User custom
│   ├── dossiers/       # Dossier médical
│   ├── maternite/      # Suivi grossesse
│   ├── urgences/       # Alertes + WebSocket
│   └── reminders/      # SMS + Celery
├── core/
│   ├── permissions.py
│   ├── pagination.py
│   ├── exceptions.py
│   └── utils.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── .env                # Ne pas commiter
├── .env.example
├── .gitignore
├── Procfile
├── railway.json
├── runtime.txt
└── manage.py
```

---

## 🚦 Sprints — État d'avancement

### ✅ SPRINT 0 — Fichiers de base (TERMINÉ)
Tous les fichiers ci-dessous existent déjà. **Ne pas les recréer.**

- `config/settings/base.py` ✅
- `config/settings/development.py` ✅
- `config/settings/production.py` ✅
- `config/urls.py` ✅
- `config/asgi.py` ✅
- `config/wsgi.py` ✅
- `config/celery.py` ✅
- `config/__init__.py` ✅
- `core/permissions.py` ✅
- `core/pagination.py` ✅
- `core/exceptions.py` ✅
- `core/utils.py` ✅
- `requirements/base.txt` ✅
- `requirements/development.txt` ✅
- `requirements/production.txt` ✅
- `.env.example` ✅
- `.gitignore` ✅
- `Procfile` ✅
- `railway.json` ✅
- `runtime.txt` ✅
- `manage.py` ✅

---

### ✅ SPRINT 1 — Auth + Accounts (TERMINÉ)
- `apps/accounts/models.py` ✅
- `apps/accounts/serializers.py` ✅
- `apps/accounts/views.py` ✅
- `apps/accounts/urls.py` ✅
- `apps/accounts/admin.py` ✅

---

### ✅ SPRINT 2 — Dossier Médical (TERMINÉ)
- `apps/dossiers/models.py` ✅
- `apps/dossiers/serializers.py` ✅
- `apps/dossiers/views.py` ✅
- `apps/dossiers/urls.py` ✅
- `apps/dossiers/admin.py` ✅

---

### 🔲 SPRINT 3 — Maternité (À FAIRE)

**Ordre d'implémentation — un fichier à la fois, tester avant de passer au suivant :**

- [ ] `apps/maternite/models.py` → test : `check` + `makemigrations --dry-run`
- [ ] `apps/maternite/serializers.py` → test : `check` + import test
- [ ] `apps/maternite/views.py` → test : `check` + import test
- [ ] `apps/maternite/urls.py` → test : `check` + reverse URLs
- [ ] `apps/maternite/admin.py` → test : `check`
- [ ] `apps/maternite/tests.py` → test : `manage.py test apps.maternite`

**Modèles à implémenter :**
- `MaternityPatient` — patiente maternité liée à un soignant
- `Pregnancy` — grossesse (calcul auto due_date + current_week)
- `WeeklyCheckup` — suivi hebdomadaire
- `PrenatalConsultation` — consultations prénatales planifiées
- `PrenatalExam` — examens prénataux
- `Child` — enfant né
- `ChildGrowth` — mesures de croissance
- `ChildVaccine` — vaccins PEV enfant (calendrier guinéen)

**Endpoints à implémenter :**
```
POST   /api/v1/maternity/patients/
GET    /api/v1/maternity/patients/
GET    /api/v1/maternity/patients/:id/
POST   /api/v1/maternity/patients/:id/weekly-checkups/
GET    /api/v1/maternity/patients/:id/weekly-checkups/
POST   /api/v1/maternity/patients/:id/prenatal-exams/
GET    /api/v1/maternity/patients/:id/prenatal-exams/
PATCH  /api/v1/maternity/patients/:id/consultations/:cid/schedule/
PATCH  /api/v1/maternity/patients/:id/consultations/:cid/done/
POST   /api/v1/maternity/patients/:id/children/
GET    /api/v1/maternity/patients/:id/children/
POST   /api/v1/maternity/children/:id/growth/
GET    /api/v1/maternity/children/:id/growth/
PATCH  /api/v1/maternity/children/vaccines/:id/done/
```

---

### 🔲 SPRINT 4 — Urgences + WebSocket (À FAIRE)

**Ordre d'implémentation — un fichier à la fois, tester avant de passer au suivant :**

- [ ] `apps/urgences/models.py` → test : `check` + `makemigrations --dry-run`
- [ ] `apps/urgences/serializers.py` → test : `check` + import test
- [ ] `apps/urgences/views.py` → test : `check` + import test
- [ ] `apps/urgences/urls.py` → test : `check`
- [ ] `apps/urgences/consumers.py` → test : `check` + import test
- [ ] `apps/urgences/routing.py` → test : `check`
- [ ] `apps/urgences/admin.py` → test : `check`
- [ ] `apps/urgences/tests.py` → test : `manage.py test apps.urgences`

**Modèles à implémenter :**
- `EmergencyAlert` — alerte urgence avec géolocalisation
- `Secourist` — secouriste disponible avec position GPS
- `Hospital` — hôpitaux et pharmacies avec coordonnées

**Endpoints à implémenter :**
```
POST   /api/v1/emergency/alerts/
GET    /api/v1/emergency/alerts/
PATCH  /api/v1/emergency/alerts/:id/take/
PATCH  /api/v1/emergency/alerts/:id/resolve/
GET    /api/v1/emergency/secourists/
PATCH  /api/v1/emergency/secourists/me/location/
GET    /api/v1/emergency/hospitals/
WS     /ws/emergency/
```

---

### 🔲 SPRINT 5 — Rappels SMS + Celery (À FAIRE)

**Ordre d'implémentation — un fichier à la fois, tester avant de passer au suivant :**

- [ ] `apps/reminders/models.py` → test : `check` + `makemigrations --dry-run`
- [ ] `apps/reminders/serializers.py` → test : `check` + import test
- [ ] `apps/reminders/tasks.py` → test : `check` + import test
- [ ] `apps/reminders/views.py` → test : `check` + import test
- [ ] `apps/reminders/urls.py` → test : `check`
- [ ] `apps/reminders/admin.py` → test : `check`
- [ ] `apps/reminders/tests.py` → test : `manage.py test apps.reminders`

**Modèles à implémenter :**
- `SmsReminder` — rappel SMS planifié (vaccination, RDV, etc.)

**Endpoints à implémenter :**
```
POST   /api/v1/reminders/
GET    /api/v1/reminders/
PATCH  /api/v1/reminders/:id/status/
POST   /api/v1/reminders/test-send/   (dev only)
```

---

### 🔲 SPRINT 6 — Migrations + Seed data (À FAIRE)

- [ ] Générer toutes les migrations (`makemigrations`)
- [ ] Appliquer les migrations (`migrate`)
- [ ] Créer un script de données initiales (`fixtures/` ou `management/commands/seed.py`)
  - Hôpitaux de Guinée (Conakry)
  - Calendrier vaccinal PEV guinéen pour enfants
  - Un médecin et un patient de test

---

### 🔲 SPRINT 7 — Tests (À FAIRE)

- [ ] `tests/test_accounts.py` — Register, Login, Me, Logout
- [ ] `tests/test_dossiers.py` — CRUD patients, consultations, QR code
- [ ] `tests/test_maternite.py` — Grossesse, suivis, enfants
- [ ] `tests/test_urgences.py` — Alertes, WebSocket
- [ ] `tests/test_reminders.py` — Création rappels, tâches Celery

---

### 🔲 SPRINT 8 — Deploy Railway (À FAIRE)

- [ ] Vérifier `Procfile` + `railway.json`
- [ ] Configurer variables d'environnement Railway
- [ ] Tester `collectstatic`
- [ ] Premier déploiement + vérification `/health/`
- [ ] Tester les endpoints en production

---

### 🟡 SPRINT 9 — Premiers secours grand public (`apps/firstaid`) — EN COURS

**Principe** : aucune consigne n'est produite par un modèle de langage. Chaque phrase vient d'un
protocole YAML sous `apps/firstaid/protocols/`, cité page par page (IFRC 2025 EN pour le contenu,
IFRC 2020 FR pour la terminologie) et signé par un médecin avant publication.

- [x] `config/settings/base.py` → `EMERGENCY_NUMBER` (défaut 442), `FIRSTAID_ALLOW_DRAFTS` (défaut False)
- [x] `config/settings/production.py` → `FIRSTAID_ALLOW_DRAFTS = False` forcé en dur
- [x] `apps/firstaid/schema.py` → structures + règles de validation (15 mots, source_page, signataires…)
- [x] `apps/firstaid/loader.py` → YAML avec lignes, registre, `all_protocols()` / `publishable_protocols()`
- [x] `apps/firstaid/apps.py` → refus de démarrer si un protocole est invalide
- [x] `apps/firstaid/protocols/unconscious_breathing.yaml` → brouillon non validé, bilingue, 33 étapes sourcées
- [x] `apps/firstaid/protocols/cardiac_arrest.yaml` → brouillon non validé, bilingue, 3 variantes, RCP avec/sans insufflations, DAE
- [x] `apps/firstaid/tests.py` → 30 tests (`manage.py test apps.firstaid`)
- [ ] Validation médicale (`validated_by` + `status: validated`) avant tout endpoint public
- [ ] Endpoints publics (n'appellent QUE `publishable_protocols()`)

---

## 📐 Conventions de code

### Format des réponses API

**Succès :**
```json
{
  "success": true,
  "message": "Description de l'action.",
  "data": { ... }
}
```

**Liste :**
```json
{
  "success": true,
  "count": 42,
  "results": [ ... ]
}
```

**Erreur :**
```json
{
  "success": false,
  "error": {
    "code": "not_found",
    "message": "Patient introuvable.",
    "details": { ... }
  }
}
```

### Modèles

- Toujours utiliser `UUID` comme PK
- Toujours ajouter `created_at` (auto_now_add) et `updated_at` (auto_now) sur les modèles principaux
- Toujours définir `db_table`, `ordering`, `verbose_name`
- Les champs optionnels : `blank=True` + `default=''` (CharField) ou `null=True, blank=True` (ForeignKey, DateField)

### Serializers

- Toujours marquer `id`, `created_at`, `updated_at` en `read_only_fields`
- Créer une version `List` allégée et une version `Detail` complète pour les modèles importants
- Validation métier dans `validate_<field>` ou `validate()`

### Views

- Utiliser `@api_view` + `@permission_classes` (pas de CBV sauf cas justifié)
- Toujours utiliser `get_object_or_404`
- Toujours vérifier les permissions manuellement si la logique est complexe
- Le `doctor` / `soignant` est toujours injecté depuis `request.user`, jamais depuis le body

### Permissions

- Routes création/modification dossier → `IsDoctor`
- Routes lecture dossier → `IsAuthenticated` + vérification manuelle
- Routes urgences → `IsAuthenticated`
- Utiliser les permissions du `core/permissions.py`

---

## ⚙️ Commandes utiles

```bash
# Démarrer en dev
python manage.py runserver --settings=config.settings.development

# Migrations
python manage.py makemigrations
python manage.py migrate

# Créer superuser
python manage.py createsuperuser

# Vérification Django
python manage.py check

# Collecte fichiers statiques (prod)
python manage.py collectstatic --noinput

# Lancer Celery worker
celery -A config worker --loglevel=info

# Lancer Celery beat
celery -A config beat --loglevel=info
```

---

## 🌍 Variables d'environnement requises

| Variable | Obligatoire | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Clé secrète Django |
| `DEBUG` | ✅ | True (dev) / False (prod) |
| `ALLOWED_HOSTS` | ✅ | Hosts autorisés |
| `DATABASE_URL` | ✅ | URL PostgreSQL |
| `REDIS_URL` | ✅ | URL Redis |
| `CORS_ALLOWED_ORIGINS` | ✅ | Origines frontend |
| `TWILIO_ACCOUNT_SID` | ⚠️ prod | SMS Twilio |
| `TWILIO_AUTH_TOKEN` | ⚠️ prod | SMS Twilio |
| `TWILIO_PHONE_NUMBER` | ⚠️ prod | Numéro Twilio |
| `SENTRY_DSN` | ⚠️ prod | Monitoring erreurs |

---

## ✅ Ce que Claude Code DOIT faire

- ✅ Toujours lire ce fichier en premier avant de commencer
- ✅ Annoncer ce qu'il va faire avant de le faire
- ✅ Coder UN SEUL fichier à la fois
- ✅ Après chaque fichier : exécuter les tests du tableau "Tests par type de fichier"
- ✅ Afficher le résultat complet des tests (pas juste "ça marche")
- ✅ Si un test échoue : corriger immédiatement, ne pas passer au suivant
- ✅ Après chaque fichier validé : mettre à jour `[ ]` → `[x]` dans ce CLAUDE.md
- ✅ Après chaque sprint complet : exécuter les tests de sprint complets
- ✅ Respecter les conventions de code définies ci-dessus
- ✅ Écrire les commentaires et messages en français
- ✅ Garder le code propre, lisible, production-ready dès le départ

---

## 🚫 Ce que Claude Code NE doit PAS faire

- ❌ Ne pas recréer les fichiers déjà marqués ✅
- ❌ Ne pas faire plusieurs fichiers d'un coup sans confirmation
- ❌ Ne pas passer au fichier suivant sans avoir testé le fichier courant
- ❌ Ne pas déclarer un test réussi sans avoir affiché sa sortie
- ❌ Ne pas faire plusieurs sprints en une seule session
- ❌ Ne pas mettre de logique dans les migrations
- ❌ Ne pas hardcoder de secrets (utiliser toujours `env()`)
- ❌ Ne pas utiliser `username` — l'identifiant est toujours `email`
- ❌ Ne pas injecter `doctor` / `soignant` depuis le body de la requête
