# PRIORITIES.md - cron-ui Chantier

## Progression Prioritaire

### Phase PROTOTYPE → ACTIVE → VEILLE

## P1 ✅ MVP LIVRÉ
- [x] Structure projet standard ✅
- [x] pyproject.toml métadonnées + dépendances ✅
- [x] Wrapper cron (collector.py) fonctionnel ✅
- [x] SQLite schema + migrations ✅
- [x] Première UI HTMX complète ✅

## P2 ✅ COMPLÉTÉ
- [x] Tests unitaires complets (96% coverage, 42 tests) ✅
- [x] Documentation technique complète (README) ✅
- [x] Configuration production (Dockerfile, docker-compose, script de validation) ✅
- [ ] Validation CI/CD pipeline
- [ ] Performance tuning

## P3 (ÉVOLUTIVITÉ V1→V2)
- [ ] Authentification utilisateur
- [ ] Thèmes custom
- [ ] Export/import données
- [ ] Alertes notifications
- [ ] Multi-instance support

## STATUT ACTUEL
- **Phase**: VEILLE
- **GitHub**: https://github.com/Mars375/cron-ui
- **Coverage**: 96% (42 tests)
- **Dernière validation**: Docker build + compose OK, dashboard et /health OK
- **Prochaine action**: Traiter les warnings pytest (FastAPI lifespan)
- **Readiness**: V1 fonctionnelle, self-hostable, en maintenance active

## TECH STACK VERIFIÉE
- ✅ Backend: FastAPI + SQLite
- ✅ Frontend: HTMX + Jinja2 templates
- ✅ API Client: httpx + graceful fallback
- ✅ Database: Schema + migrations + CRUD
- ✅ UI: Dashboard + jobs + détail job + filtres HTMX
- ✅ Déploiement: Dockerfile + docker-compose + health checks

## DEPENDANCES EXTERNES
- OpenClaw cron API (localhost:8905)
- Python: fastapi, uvicorn, httpx, jinja2
- Frontend: HTMX (CDN), TailwindCSS (CDN)
- Tests: pytest, pytest-cov
- Docker / Docker Compose pour le déploiement self-hosted
