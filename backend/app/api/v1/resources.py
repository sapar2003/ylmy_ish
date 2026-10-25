from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from app import models as m
from app.api.crud import DbSession, build_crud_router, commit_or_raise, get_or_404
from app.schemas import resources as s

router = APIRouter()

# --- Mugallymlar we olaryň boş wagty ---
teachers = APIRouter(prefix="/teachers", tags=["Mugallymlar"])


@teachers.get("/{teacher_id}/availability", response_model=list[s.AvailabilityItem])
def get_availability(teacher_id: int, db: DbSession):
    """Diňe bellenen slotlar gaýtarylýar; galan slotlarda mugallym boş hasaplanýar."""
    get_or_404(db, m.Teacher, teacher_id, "Mugallym")
    rows = db.scalars(
        select(m.TeacherAvailability)
        .where(m.TeacherAvailability.teacher_id == teacher_id)
        .order_by(m.TeacherAvailability.time_slot_id)
    )
    return [s.AvailabilityItem(time_slot_id=r.time_slot_id, status=r.status) for r in rows]


@teachers.put("/{teacher_id}/availability", response_model=list[s.AvailabilityItem])
def replace_availability(teacher_id: int, items: list[s.AvailabilityItem], db: DbSession):
    """Mugallymyň ähli belliklerini täze sanaw bilen çalyşýar."""
    get_or_404(db, m.Teacher, teacher_id, "Mugallym")
    slot_ids = [i.time_slot_id for i in items]
    if len(set(slot_ids)) != len(slot_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Bir slot iki gezek görkezilipdir.")
    db.execute(delete(m.TeacherAvailability).where(m.TeacherAvailability.teacher_id == teacher_id))
    db.add_all(m.TeacherAvailability(teacher_id=teacher_id, **i.model_dump()) for i in items)
    commit_or_raise(db)
    return sorted(items, key=lambda i: i.time_slot_id)


build_crud_router(
    model=m.Teacher, create_schema=s.TeacherCreate, update_schema=s.TeacherUpdate,
    read_schema=s.TeacherRead, prefix="/teachers", tag="Mugallym", filters=("department_id",),
    router=teachers,
)
router.include_router(teachers)

# --- Wagt slotlary ---
time_slots = APIRouter(prefix="/time-slots", tags=["Wagt slotlary"])


@time_slots.post("/generate", response_model=list[s.TimeSlotRead], status_code=status.HTTP_201_CREATED)
def generate_time_slots(payload: s.TimeSlotGenerate, db: DbSession):
    """Smena üçin ähli günleriň slotlaryny döredýär (meselem, 6 gün × 3 jübüt = 18 slot)."""
    get_or_404(db, m.Shift, payload.shift_id, "Smena")
    slots = [
        m.TimeSlot(shift_id=payload.shift_id, weekday=day, **period.model_dump())
        for day in sorted(set(payload.weekdays))
        for period in payload.periods
    ]
    db.add_all(slots)
    commit_or_raise(db)
    for slot in slots:
        db.refresh(slot)
    return slots


build_crud_router(
    model=m.TimeSlot, create_schema=s.TimeSlotCreate, update_schema=s.TimeSlotUpdate,
    read_schema=s.TimeSlotRead, prefix="/time-slots", tag="Wagt sloty", filters=("shift_id", "weekday"),
    search_field=None, order_by=("shift_id", "weekday", "number"), router=time_slots,
)
router.include_router(time_slots)

# --- Binalar, otag görnüşleri, otaglar ---
router.include_router(build_crud_router(
    model=m.Building, create_schema=s.BuildingCreate, update_schema=s.BuildingUpdate,
    read_schema=s.BuildingRead, prefix="/buildings", tag="Binalar",
))
router.include_router(build_crud_router(
    model=m.RoomType, create_schema=s.RoomTypeCreate, update_schema=s.RoomTypeUpdate,
    read_schema=s.RoomTypeRead, prefix="/room-types", tag="Otag görnüşleri",
))
router.include_router(build_crud_router(
    model=m.Room, create_schema=s.RoomCreate, update_schema=s.RoomUpdate,
    read_schema=s.RoomRead, prefix="/rooms", tag="Otaglar", filters=("building_id", "room_type_id", "faculty_id"),
))
