# cron-ui - V1 Scope Plan

## Objectif Principal
Dashboard self-hostable pour visualiser l'historique et le statut des cron jobs OpenClaw

## V1 Minimal Scope

### Core Components
1. **Cron Data Collector** (`collector.py`)
   - Wrapper pour interroger l'API OpenClaw cron
   - Extraction des jobs: actifs, désactivés, erreurs, exécutions
   - Enrichissement avec métadonnées (dernière exécution, prochain run, etc.)

2. **SQLite Backend** (`database.py`)
   - Schéma: `cron_jobs`, `executions`, `errors`
   - Migration automatique
   - Méthodes CRUD principales
   - Indexing pour performance

3. **Web UI** (`ui/`)
   - Frontend statique avec HTMX + Alpine.js
   - Pages principales:
     - Dashboard (stats globales, jobs récents)
     - Job list (filtrable, searchable)
     - Job detail (historique, logs, métadonnées)
     - Settings (refresh interval, thème)
   - Design responsive

### Technologies Stack
- **Backend**: Python 3.11+ (FastAPI + SQLite)
- **Frontend**: HTMX 1.9+ + Alpine.js 3.13+ + TailwindCSS
- **Database**: SQLite (auto-gérée)
- **Déploiement**: Single binary + SQLite file

### Endpoints API V1
```python
# GET /api/jobs - Liste tous les jobs
# GET /api/jobs/{job_id} - Détail d'un job
# GET /api/executions - Historique des exécutions
# GET /api/stats - Statistiques globales
# GET /api/health - Health check
```

### Architecture
```
cron-ui/
├── app.py              # FastAPI app
├── collector.py        # OpenClaw API client
├── database.py         # SQLite operations
├── migrations/         # DB migrations
├── ui/
│   ├── index.html      # Main dashboard
│   ├── jobs.html       # Job listing
│   ├── job-detail.html # Job detail
│   └── static/
│       ├── css/        # Tailwind styles
│       └── js/         # Alpine.js + custom
├── config.py           # Configuration
├── requirements.txt   # Python deps
└── Dockerfile         # Container option
```

### Critères de Success V1
1. ✅ Dashboard fonctionnel avec 3 pages principales
2. ✅ Connexion stable à l'API OpenClaw cron
3. ✅ Données persistantes en SQLite
4. ✅ Interface responsive mobile/tablet
5. ✅ Documentation README complète
6. ✅ Tests unitaires (>80% coverage)

### Prochaines Étapes
1. Créer structure projet
2. Implémenter collector.py
3. Configurer SQLite schema
4. Développer UI avec HTMX
5. Intégrer backend/frontend
6. Tests et documentation

### Dépendances Externes
- OpenClaw API (localhost:8905 pour router)
- Python: fastapi, uvicorn, httpx, pydantic
- Frontend: HTMX, Alpine.js, TailwindCSS (CDN)

### Évolutivité V1→V2
- Authentification utilisateur
- Thèmes custom
- Export/import données
- Alertes notifications
- Multi-instance support