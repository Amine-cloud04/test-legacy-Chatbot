# Assistant de connaissances Safran

Cet outil est une solution interne, hors ligne et orientée R&D pour rechercher des documents techniques Safran. Il ingère des fichiers PDF, Word et PowerPoint depuis un dossier local ou SharePoint, stocke le texte extrait dans SQLite, construit un index BM25 et un index vectoriel optionnel, puis affiche des résultats triés avec une réponse justifiée dans une interface Streamlit.

Aucune API externe n'est utilisée au runtime. La recherche vectorielle optionnelle nécessite un modèle local compatible déjà présent sur le réseau d'entreprise.

## Architecture

```mermaid
flowchart TD
    A[Documents locaux / SharePoint] --> B[Ingestion]
    B --> C[Extraction texte PDF / DOCX / PPTX]
    C --> D[Nettoyage + métadonnées]
    D --> E[Chunking 640 chars / overlap 100]
    E --> F[SQLite projects / chunks / keywords]
    E --> G[Index BM25]
    E --> H[Index vectoriel optionnel]
    G --> I[Cache disque + mémoire]
    H --> I

    J[Question utilisateur en français] --> K[Streamlit UI]
    K --> L[Query Processor]
    L --> M[Hybrid Retrieval]
    M --> G
    M --> H
    M --> N[Fusion RRF]
    N --> O[Reranking local]
    O --> P[Construction du contexte]
    P --> Q[Ollama local llama3.2:3b]
    Q --> R[Réponse en français]
    R --> K

    F --> M
```

### Lecture du pipeline

1. **Ingestion**
   - Les documents sont lus depuis un dossier local ou SharePoint.
   - Les extracteurs récupèrent le texte des fichiers PDF, DOCX et PPTX.
   - Le contenu est découpé en chunks courts avec chevauchement.
   - Les métadonnées et le texte sont persistés dans SQLite.
   - Les index BM25 et vectoriel sont construits une seule fois à l'ingestion.

2. **Recherche**
   - La question de l'utilisateur est analysée en français.
   - Le moteur lance une recherche hybride BM25 + vecteurs.
   - Les résultats sont fusionnés avec Reciprocal Rank Fusion.
   - Un reranker local garde les meilleurs candidats.

3. **Génération**
   - Le contexte utile est reconstruit à partir des meilleurs fragments.
   - Les doublons sont réduits avant envoi au modèle.
   - Ollama `llama3.2:3b` génère une réponse en français.
   - Streamlit affiche la réponse en streaming avec les sources et les preuves.

### Résumé en une ligne

```text
Documents -> extraction -> chunking -> indexation -> hybrid retrieval -> rerank -> contexte -> Ollama -> réponse française sourcée -> UI
```

## Pack USB Windows (PC personnel → PC entreprise sans Internet)

Le PC entreprise n'a **rien** à installer depuis le web. Tout est sur la clé.

Sur votre **PC personnel** (avec Internet) :

```bash
./pack_usb.sh
```

Cela prépare `dist/safran-usb/` (~4 Go) avec :
- l'application
- Python Windows portable
- toutes les bibliothèques Python
- Ollama Windows + modèle `llama3.2:3b`

Copiez **tout** le dossier `dist/safran-usb` sur une clé USB chiffrée (8 Go minimum).

Sur le **PC entreprise** :

1. `install_offline.bat` (une fois — installe depuis la clé uniquement)
2. Ouvrir SharePoint dans le navigateur → synchroniser/télécharger les dossiers projets
3. `demarrer.bat` → synchroniser ce dossier local → lancer la revue

Détails : `USB_LIRE_MOI.txt`.

## Démarrage rapide (développement local)

```bash
cd safran-knowledge-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./setup_offline.sh
python scripts/create_sample_docs.py --scale 3
./sync_from_folder.sh ./sample_docs --reset
./check_ready.sh
./run_review.sh
```

Sur Windows : `.venv\Scripts\activate`, puis les `.bat` équivalents (`setup_offline.bat`, `demarrer.bat`, …).

Menu guidé (recommandé sur PC entreprise) :

```bash
./demarrer.sh
```

## Workflow recommandé (PC entreprise + SharePoint navigateur)

Sur un PC entreprise, SharePoint Online s'ouvre déjà dans le navigateur (SSO). Ne stockez pas de mot de passe SharePoint sur la clé USB.

```text
1. ./setup_offline.sh
   → crée .env.review (sans secrets SharePoint)

2. Ouvrir la bibliothèque SharePoint dans le navigateur
   → Synchroniser avec OneDrive, ou télécharger le dossier projets

3. ./sync_from_folder.sh "/chemin/vers/OneDrive/Bibliothèque" --reset
   → écrit data/knowledge_base.db + data/bm25_index.pkl + data/sync_manifest.json

4. ./check_ready.sh
   → vérifie base, index, manifeste, Ollama

5. ./run_review.sh
   → revue hors ligne sur 127.0.0.1
```

Ou enchaîner via `./demarrer.sh` (menu 1 → 2 → 3 → 4).

Le panneau latéral affiche la date de dernière synchro et le chemin source.

## LLM Local

L'assistant utilise le service local Ollama, avec le modèle `llama3.2:3b`:

```text
LOCAL_LLM_SERVICE_URL=http://127.0.0.1:11434
LOCAL_LLM_SERVICE_MODEL=llama3.2:3b
LOCAL_LLM_TIMEOUT=20
```

Si Ollama n'est pas disponible, l'application revient automatiquement aux réponses extractives justifiées. Dans tous les cas, le prompt demande une réponse en français.

La réponse est streamée dans l'interface dès que le modèle commence à générer le texte.

## Fallback API SharePoint (optionnel)

Souvent bloqué par MFA / Conditional Access. Préférez le workflow dossier ci-dessus.

Si votre environnement autorise encore login/mot de passe API :

```text
SHAREPOINT_URL=https://votre-site-sharepoint
SHAREPOINT_USERNAME=user@entreprise.com
SHAREPOINT_PASSWORD=...
SHAREPOINT_LIBRARY=Documents
```

```bash
python scripts/ingest_sharepoint.py --check
python scripts/ingest_sharepoint.py
```

Le paramètre `--check` valide la connexion et liste les premiers fichiers. Les échecs sont enregistrés et ignorés pour ne pas bloquer l'ingestion complète.

## Recherche vectorielle

La recherche vectorielle est désactivée par défaut. Pour l'activer hors ligne :

1. Téléchargez un modèle compatible sur une machine connectée à Internet.
2. Copiez le dossier du modèle sur le réseau d'entreprise.
3. Installez les dépendances optionnelles depuis le miroir interne : `sentence-transformers`, `faiss-cpu`.
4. Définissez :

```text
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
USE_VECTOR_SEARCH=true
```

Le code essaie d'abord `BAAI/bge-m3`, puis `paraphrase-multilingual-mpnet-base-v2`, puis `multilingual-e5-base`, en restant strictement local si le modèle est déjà présent en cache ou sur disque.

Puis reconstruisez les index :

```bash
python scripts/rebuild_index.py
```

## Structure du projet

```text
config.py                  paramètres via variables d'environnement
.env.review.example        config hors ligne (sans secrets SharePoint)
demarrer.sh|.bat           menu guidé (config → sync → check → revue)
setup_offline.sh|.bat      créer .env.review et le dossier data/
check_ready.sh|.bat        vérifier base, index, Ollama
sync_from_folder.sh|.bat   indexer un dossier OneDrive/SharePoint local
run_review.sh|.bat         lancer l'UI en mode revue hors ligne
db/                        schéma SQLite, modèles et accès aux données
ingest/                    ingestion locale/SharePoint, manifeste de synchro
search/                    BM25, recherche vectorielle optionnelle, fusion hybride
assistant/                 traitement des requêtes, résumé, génération de réponses
ui/app.py                  application Streamlit
scripts/                   setup_offline, check_ready, sync_from_folder, ingest_*
tests/                     tests Pytest
```

## Tests

```bash
pytest
```

Les tests génèrent des documents DOCX/PPTX synthétiques et valident l'ingestion locale, la recherche BM25, la fusion hybride, le générateur de réponses, et le branchement Ollama.

## Limites connues et prochaines étapes

- Les pages PDF purement images sont ignorées ; une OCR hors ligne peut être ajoutée plus tard.
- Le workflow principal est dossier local (OneDrive/téléchargement navigateur) ; l'API SharePoint login/mot de passe est un fallback souvent incompatible avec MFA.
- Les réponses sont générées par Ollama local, avec streaming dans l'interface.
- La recherche vectorielle dépend de dépendances optionnelles et d'un modèle local.
- Le filtrage des droits d'accès n'est pas encore implémenté ; il faut le renforcer avant un déploiement large.
- Pour une clé USB : chiffrez le volume (BitLocker To Go / VeraCrypt) ; ne laissez pas de mots de passe SharePoint sur la clé.

## Format de réponse actuel

L'interface affiche désormais une réponse directe en français en premier, puis la confiance, les limites, les citations de sources et les fragments de preuve détaillés.

Utilisez `python scripts/create_sample_docs.py --scale 3` pour générer un corpus de démonstration plus volumineux couvrant le radar FPGA, la navigation UAV, la fusion inertielle/GNSS, la vérification avionique, la cybersécurité et le traitement IA embarqué.
