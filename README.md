# Assistant de connaissances Safran

Cet outil est une solution interne, hors ligne et orientée R&D pour rechercher des documents techniques Safran. Il ingère des fichiers PDF, Word et PowerPoint depuis un dossier local ou SharePoint, stocke le texte extrait dans SQLite, construit un index BM25 et affiche des résultats triés avec une réponse justifiée dans une interface Streamlit.

Aucune API externe n'est utilisée au runtime. La recherche vectorielle optionnelle nécessite un modèle local compatible déjà présent sur le réseau d'entreprise.

## Architecture

```text
SharePoint / dossier local
        |
        v
IngestPipeline -> extracteurs PDF/DOCX/PPTX -> SQLite projects/chunks/keywords
        |                                      |
        v                                      v
 index BM25                      index vectoriel optionnel
        \                                      /
         \                                    /
          v                                  v
 HybridEngine -> Ranker -> AnswerGenerator -> ResponseBuilder -> UI Streamlit
```

## Démarrage rapide

```bash
cd safran-knowledge-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/create_sample_docs.py
python scripts/ingest_local.py --path ./sample_docs --reset
streamlit run ui/app.py
```

Sur Windows, utilisez `.venv\\Scripts\\activate` à la place de `source .venv/bin/activate`.

## Local LLM / Ollama

Si vous souhaitez accélérer la génération de réponses avec un service LLM local, configurez Ollama en tant que service HTTP.

1. Installer Ollama et charger un modèle local compatible.
2. Exécuter le service sur le port 11434 :

```bash
ollama serve
```

3. Activer l'URL du service dans `.env` :

```text
LOCAL_LLM_SERVICE_URL=http://127.0.0.1:11434
LOCAL_LLM_SERVICE_MODEL=llama3.2:3b
LOCAL_LLM_TIMEOUT=20
```

Si `LOCAL_LLM_SERVICE_URL` n'est pas configuré, l'application retombera sur les réponses extractives justifiées.

## Configuration SharePoint

Renseignez ces valeurs dans `.env` :

```text
SHAREPOINT_URL=https://votre-site-sharepoint
SHAREPOINT_USERNAME=DOMAINE\\utilisateur
SHAREPOINT_PASSWORD=votre-mot-de-passe
SHAREPOINT_LIBRARY=Documents
```

Puis exécutez :

```bash
python scripts/ingest_sharepoint.py --check
python scripts/ingest_sharepoint.py
```

Le paramètre `--check` permet de valider les identifiants et de lister les premiers fichiers trouvés. Les échecs sont enregistrés et ignorés pour ne pas bloquer l'ingestion complète.

## Recherche vectorielle

La recherche vectorielle est désactivée par défaut. Pour l'activer hors ligne :

1. Téléchargez un modèle compatible sur une machine connectée à Internet.
2. Copiez le dossier du modèle sur le réseau d'entreprise.
3. Installez les dépendances optionnelles depuis le miroir interne : `sentence-transformers`, `faiss-cpu`.
4. Définissez :

```text
EMBEDDING_MODEL_PATH=./models/all-MiniLM-L6-v2
USE_VECTOR_SEARCH=true
```

Puis reconstruisez les index :

```bash
python scripts/rebuild_index.py
```

## Structure du projet

```text
config.py                  paramètres via variables d'environnement
db/                        schéma SQLite, modèles et accès aux données
ingest/                    ingestion locale/SharePoint et extracteurs
search/                    BM25, recherche vectorielle optionnelle, fusion hybride
assistant/                 traitement des requêtes, résumé, génération de réponses
ui/app.py                  application Streamlit
scripts/                   scripts opérationnels
tests/                     tests Pytest
```

## Tests

```bash
pytest
```

Les tests génèrent des documents DOCX/PPTX synthétiques et valident l'ingestion locale et la recherche BM25.

## Limites connues et prochaines étapes

- Les pages PDF purement images sont ignorées ; une OCR hors ligne peut être ajoutée plus tard.
- Les métadonnées SharePoint varient selon l'environnement ; l'ingestion locale utilise la date de modification du système de fichiers.
- Le générateur de réponses est encore extrait et justifié à partir des fragments récupérés.
- La recherche vectorielle dépend de dépendances optionnelles et d'un modèle local.
- Le filtrage des droits d'accès n'est pas encore implémenté ; il faut le renforcer avant un déploiement large.

## Format de réponse actuel

L'interface affiche désormais une réponse directe justifiée en premier, puis la confiance, les limites, les citations de sources et les fragments de preuve détaillés.

Utilisez `python scripts/create_sample_docs.py` pour générer des documents de démonstration en français couvrant le radar FPGA, la navigation UAV et la fusion inertielle/GNSS.
