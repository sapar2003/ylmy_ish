# Raspisaniýe

Uniwersitetiň ähli fakultetleri üçin sapak raspisaniýesini awtomat düzýän ulgam.
Backend: FastAPI (Python), maglumat bazasy: PostgreSQL, frontend: Flutter, solwer: Google OR-Tools CP-SAT.

## Gurluş

```
backend/   FastAPI API (häzir: fakultet, kafedra, hünär, smena, topar, kiçi topar)
frontend/  Flutter programmasy (soňra)
solver/    Raspisaniýe algoritmi (soňra)
```

Ähli sanawlar ulanyjy tarapyndan dolandyrylýar: fakultetleri, kafedralary, toparlary we beýlekileri
islendik sanda goşup, üýtgedip, aýryp bolýar. Kodda hiç bir fakultet berkidilmeýär.

## Işe girizmek

```bash
docker compose up --build
```

API: http://localhost:8000, dokumentasiýa: http://localhost:8000/docs

## Docker-siz ösdürmek

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # DATABASE_URL-y öz PostgreSQL-iňe görä üýtget
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

## API (v1)

| Sanaw | Ýol | Süzgüçler |
| --- | --- | --- |
| Fakultetler | `/api/v1/faculties` | `q` |
| Kafedralar | `/api/v1/departments` | `q`, `faculty_id` |
| Hünärler | `/api/v1/specialties` | `q`, `department_id` |
| Smenalar | `/api/v1/shifts` | `q` |
| Toparlar | `/api/v1/groups` | `q`, `specialty_id`, `shift_id`, `course` |
| Kiçi toparlar | `/api/v1/subgroups` | `q`, `group_id` |

Her sanawda: `GET` (sanaw, `limit`/`offset`), `POST` (goşmak), `GET /{id}`, `PATCH /{id}` (üýtgetmek), `DELETE /{id}` (aýyrmak).
Içinde başga ýazgy bar bolan ýazgyny aýyrmak (meselem, kafedrasy bar fakultet) `409` gaýtarýar: ilki içindäkileri aýyrmaly.
Topar aýrylanda onuň kiçi toparlary hem aýrylýar.
