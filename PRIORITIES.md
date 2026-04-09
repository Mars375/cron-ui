# PRIORITIES.md - cron-ui Chantier

## Progression Prioritaire

### Phase PROTOTYPE → ACTIVE → VEILLE

## P1 PRIORITÉ (EN COURS)
- [x] Structure projet standard ✅
- [x] pyproject.toml métadonnées + dépendances ✅
- [x] Wrapper cron (collector.py) fonctionnel ✅
- [x] SQLite schema + migrations ✅
- [ ] **PREMIERE UI HTMX complète**
  - [x] Template base (ui/templates/base.html)
  - [x] Dashboard (ui/templates/index.html)
  - [x] Jobs list (ui/templates/jobs.html)
  - [x] Job detail (ui/templates/job_detail.html)
  - [ ] Intégration backend/frontend complète
  - [ ] Tests UI + automatisation
  - [ ] Documentation utilisateur

## P2 (À COMPLÉTER APRÈS P1)
- [ ] Tests unitaires complets (>80% coverage)
- [ ] Documentation technique complète
- [ ] Configuration production (Docker, environment variables)
- [ ] Validation CI/CD pipeline
- [ ] Performance tuning

## P3 (ÉVOLUTIVITÉ V1→V2)
- [ ] Authentification utilisateur
- [ ] Thèmes custom
- [ ] Export/import données
- [ ] Alertes notifications
- [ ] Multi-instance support

## CRITÈRES DE PROMOTION V1
- [ ] Dashboard fonctionnel avec 3 pages principales
- [ ] Connexion stable à l'API OpenClaw cron
- [ ] Données persistantes en SQLite
- [ ] Interface responsive mobile/tablet
- [ ] Documentation README complète
- [ ] Tests unitaires (>80% coverage)

## STATUT ACTUEL
- **Phase**: PROTOTYPE
- **Prochaine action**: Finaliser intégration backend/frontend UI HTMX
- **Progression**: 4/5 P1 complétés, 1 P1 en cours
- **Readiness**: Près de promotion ACTIVE - tests et docs restantes

## TECH STACK VERIFIÉE
- ✅ Backend: FastAPI + SQLite
- ✅ Frontend: HTMX + Jinja2 templates
- ✅ API Client: httpx + graceful fallback
- ✅ Database: Schema + migrations + CRUD
- ⏳ UI: Templates existent, intégration en cours

## DEPENDANCES EXTERNES
- OpenClaw cron API (localhost:8905)
- Python: fastapi, uvicorn, httpx, jinja2
- Frontend: HTMX (CDN), TailwindCSS (CDN)
- Tests: pytest, pytest-cov