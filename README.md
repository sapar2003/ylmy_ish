# Raspisaniýe

Uniwersitetiň ähli fakultetleri üçin sapak raspisaniýesini awtomat düzýän ulgam.
Backend: FastAPI (Python), maglumat bazasy: PostgreSQL, frontend: Flutter, solwer: Google OR-Tools CP-SAT.

## Gurluş

```
backend/   FastAPI API (gurluş, resurslar, okuw meýilnamasy)
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
| Mugallymlar | `/api/v1/teachers` | `q`, `department_id` |
| Wagt slotlary | `/api/v1/time-slots` | `shift_id`, `weekday` |
| Binalar | `/api/v1/buildings` | `q` |
| Otag görnüşleri | `/api/v1/room-types` | `q` |
| Otaglar | `/api/v1/rooms` | `q`, `building_id`, `room_type_id` |
| Dersler | `/api/v1/subjects` | `q`, `department_id` |
| Potoklar | `/api/v1/streams` | `q` |
| Okuw meýilnamasy | `/api/v1/curriculum` | `group_id`, `stream_id`, `subject_id` |
| Mugallym bellemek | `/api/v1/assignments` | `curriculum_item_id`, `teacher_id` |

Her sanawda: `GET` (sanaw, `limit`/`offset`), `POST` (goşmak), `GET /{id}`, `PATCH /{id}` (üýtgetmek), `DELETE /{id}` (aýyrmak).
Içinde başga ýazgy bar bolan ýazgyny aýyrmak (meselem, kafedrasy bar fakultet) `409` gaýtarýar: ilki içindäkileri aýyrmaly.
Topar aýrylanda onuň kiçi toparlary hem aýrylýar.

Goşmaça endpointler:

- `POST /api/v1/time-slots/generate`: bir smena üçin ähli günleriň slotlaryny bir gezekde döredýär
  (meselem, 6 gün × 3 jübüt = 18 slot).
- `GET/PUT /api/v1/teachers/{id}/availability`: mugallymyň boş wagty. Her slot üçin `available`,
  `preferred` ýa-da `unavailable`; bellenmedik slotda mugallym boş hasaplanýar.

Okuw meýilnamasynyň düzgünleri:

- Ýazgy ýa bir topara (`group_id`), ýa bir potoga (`stream_id`) degişli bolýar, ikisine birden däl.
- `split: true` bolsa sapak kiçi toparlara bölünýär: her kiçi topar üçin aýratyn mugallym bellenýär
  (mugallym şol bir adam ýa-da dürli bolup biler). Potok sapagy bölünmeýär.
- Bölünmeýän sapaga diňe bir mugallym bellenýär.

## Testler

```bash
cd backend
pytest                                            # in-memory SQLite
TEST_DATABASE_URL=postgresql+psycopg://... pytest # PostgreSQL bilen
```
