# SEO Analyzer API

API d'analyse SEO qui génère des captures d'écran des résultats d'analyse de sites web en utilisant l'API SEObserver.

## Fonctionnalités

- Analyse des métriques SEO via l'API SEObserver
- Génération de captures d'écran des résultats
- API RESTful simple à utiliser
- Déploiement facile sur Google Cloud Run
- Interface utilisateur moderne et réactive
- Affichage des recommandations personnalisées
- Support Docker pour un déploiement facile

## Déploiement sur Google Cloud Run

### Prérequis

1. Un compte Google Cloud Platform (GCP)
2. Google Cloud SDK installé localement
3. Docker installé localement (pour tester en local)
4. Une clé API SEObserver valide

### Configuration initiale

1. **Activer les API nécessaires** :
   ```bash
   gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
   ```

2. **Configurer le projet GCP** :
   ```bash
   gcloud config set project VOTRE_PROJET_ID
   gcloud config set run/region us-central1
   ```

### Déploiement manuel

1. **Construire et pousser l'image Docker** :
   ```bash
   gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/seo-analyzer
   ```

2. **Déployer sur Cloud Run** :
   ```bash
   gcloud run deploy seo-analyzer \
     --image gcr.io/$(gcloud config get-value project)/seo-analyzer \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars="SEOBSERVER_API_KEY=votre_cle_api" \
     --memory=2Gi \
     --cpu=1 \
     --timeout=300s \
     --concurrency=80
   ```

### Déploiement automatisé avec Cloud Build

1. **Créer un déclencheur Cloud Build** :
   - Allez dans Google Cloud Console > Cloud Build > Déclencheurs
   - Créez un nouveau déclencheur lié à votre dépôt
   - Configurez la substitution de variable `_SEOBSERVER_API_KEY` avec votre clé API

2. **Lancer le déploiement** :
   ```bash
   gcloud builds submit --config=cloudbuild.yaml \
     --substitutions=_SEOBSERVER_API_KEY=votre_cle_api
   ```

## Utilisation de l'API

### Endpoint principal

```
POST /api/analyze/screenshot
```

**Paramètres (JSON)** :
```json
{
  "domain": "exemple.com"
}
```

**Réponse** :
- Succès : Fichier image JPEG
- Erreur : Objet JSON avec les détails de l'erreur

### Exemple avec cURL

```bash
curl -X POST https://votre-service-run-abcdef-uc.a.run.app/api/analyze/screenshot \
  -H "Content-Type: application/json" \
  -d '{"domain": "exemple.com"}' \
  --output resultat_analyse.jpg
```

### Exemple avec Python

```python
import requests

response = requests.post(
    'https://votre-service-run-abcdef-uc.a.run.app/api/analyze/screenshot',
    json={'domain': 'exemple.com'}
)

if response.status_code == 200:
    with open('resultat_analyse.jpg', 'wb') as f:
        f.write(response.content)
    print("Capture d'écran enregistrée avec succès !")
else:
    print("Erreur:", response.json())
```

## Configuration avancée

### Variables d'environnement

| Variable | Description | Requis | Valeur par défaut |
|----------|-------------|--------|------------------|
| `PORT` | Port d'écoute du serveur | Non | 8080 |
| `SEOBSERVER_API_KEY` | Clé API pour SEObserver | Oui | - |
| `DEBUG` | Mode débogage | Non | False |

### Évolutivité

L'application est configurée pour s'adapter automatiquement à la charge sur Cloud Run. Vous pouvez ajuster :
- `--memory` : Mémoire allouée (1Gi à 8Gi)
- `--cpu` : Nombre de CPU (1-4)
- `--concurrency` : Nombre de requêtes simultanées par conteneur

## Dépannage

### Erreurs courantes

- **401 Unauthorized** : Vérifiez que la clé API SEObserver est correcte
- **Timeout** : Augmentez le timeout avec `--timeout` (max 900s)
- **Mémoire insuffisante** : Augmentez la mémoire avec `--memory`

### Journaux

Les journaux sont disponibles dans Google Cloud Console > Cloud Run > Votre service > Journaux

## Prérequis

- Docker et Docker Compose
- Clé API SEObserver valide

## Installation

1. Clonez le dépôt :
   ```bash
   git clone [URL_DU_DEPOT]
   cd windsurf-project
   ```

2. Créez un fichier `.env` à partir de l'exemple :
   ```bash
   cp .env.example .env
   ```

3. Modifiez le fichier `.env` pour y ajouter votre clé API SEObserver :
   ```
   SEOBSERVER_API_KEY=votre_cle_api_ici
   ```

## Démarrage

1. Construisez et démarrez les conteneurs :
   ```bash
   docker-compose up --build -d
   ```

2. Accédez à l'application dans votre navigateur :
   ```
   http://localhost:5000
   ```

## Structure du projet

```
.
├── .env.example           # Exemple de fichier de configuration
├── .gitignore            # Fichiers à ignorer par Git
├── Dockerfile            # Configuration Docker
├── README.md             # Ce fichier
├── app.py                # Application Flask principale
├── docker-compose.yml    # Configuration Docker Compose
├── requirements.txt      # Dépendances Python
└── templates/
    └── index.html       # Interface utilisateur
```

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `SEOBSERVER_API_KEY` | Clé API pour accéder à SEObserver (requise) |
| `FLASK_ENV` | Environnement d'exécution (production/development) |
| `PORT` | Port sur lequel l'application écoute (par défaut: 5000) |

## Licence

Ce projet est sous licence MIT.
