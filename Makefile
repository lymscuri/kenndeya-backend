# Makefile pour Kendeya Backend
# Simplifie les commandes Docker et Django courantes

.PHONY: help build up down restart logs shell test migrate createsuperuser seed clean

help: ## Afficher cette aide
	@echo "Commandes disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Commandes Docker de base
build: ## Construire les images Docker
	docker-compose build

up: ## Démarrer tous les services en mode détaché
	docker-compose up -d

down: ## Arrêter tous les services
	docker-compose down

restart: ## Redémarrer tous les services
	docker-compose restart

logs: ## Afficher les logs de tous les services
	docker-compose logs -f

# Commandes de développement
dev-up: ## Démarrer en mode développement
	docker-compose -f docker-compose.dev.yml up

dev-down: ## Arrêter le mode développement
	docker-compose -f docker-compose.dev.yml down

dev-build: ## Construire les images en mode développement
	docker-compose -f docker-compose.dev.yml build

# Commandes Django
shell: ## Ouvrir un shell Django
	docker-compose exec web python manage.py shell

migrate: ## Exécuter les migrations
	docker-compose exec web python manage.py migrate

makemigrations: ## Créer de nouvelles migrations
	docker-compose exec web python manage.py makemigrations

createsuperuser: ## Créer un superutilisateur
	docker-compose exec web python manage.py createsuperuser

seed: ## Charger les données de test
	docker-compose exec web python manage.py seed_data

collectstatic: ## Collecter les fichiers statiques
	docker-compose exec web python manage.py collectstatic --noinput

# Tests
test: ## Exécuter tous les tests
	docker-compose exec web python manage.py test

test-coverage: ## Exécuter les tests avec coverage
	docker-compose exec web coverage run --source='.' manage.py test
	docker-compose exec web coverage report
	docker-compose exec web coverage html

# Logs par service
logs-web: ## Logs du service web
	docker-compose logs -f web

logs-celery: ## Logs du worker Celery
	docker-compose logs -f celery_worker

logs-beat: ## Logs de Celery Beat
	docker-compose logs -f celery_beat

logs-db: ## Logs de PostgreSQL
	docker-compose logs -f db

# Nettoyage
clean: ## Nettoyer les conteneurs, volumes et images
	docker-compose down -v
	docker system prune -f

clean-all: ## Nettoyer TOUT (conteneurs, volumes, images, cache)
	docker-compose down -v --rmi all
	docker system prune -af --volumes

# Commandes de production
prod-build: ## Construire pour production
	docker-compose -f docker-compose.yml build

prod-up: ## Démarrer en production
	docker-compose -f docker-compose.yml up -d

prod-down: ## Arrêter la production
	docker-compose -f docker-compose.yml down

prod-logs: ## Logs de production
	docker-compose -f docker-compose.yml logs -f

# Backup et restore
backup-db: ## Sauvegarder la base de données
	docker-compose exec db pg_dump -U kendeya_user kendeya_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restaurer la base de données (utiliser BACKUP_FILE=fichier.sql)
	docker-compose exec -T db psql -U kendeya_user kendeya_db < $(BACKUP_FILE)
