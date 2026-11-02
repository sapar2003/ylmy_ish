from fastapi import APIRouter, Depends

from app import models as m
from app.api import scope as sc
from app.api.auth import require_staff
from app.api.crud import build_crud_router
from app.api.v1 import curriculum, docx, exams, journal, resources, timetables, users
from app.schemas import structure as s

api_router = APIRouter(prefix="/api/v1")

# Maglumatlar: admin hemmesini, dekan diňe öz fakultetiniňkini (`app.api.scope`).
# Raspisaniýe düzmek, çap etmek we umumy sanawlary üýtgetmek — diňe admin (endpointleriň öz barlagy).
admin_router = APIRouter(dependencies=[Depends(require_staff)])
admin_router.include_router(build_crud_router(
    model=m.Faculty, create_schema=s.FacultyCreate, update_schema=s.FacultyUpdate,
    read_schema=s.FacultyRead, prefix="/faculties", tag="Fakultetler",
))
admin_router.include_router(build_crud_router(
    model=m.Department, create_schema=s.DepartmentCreate, update_schema=s.DepartmentUpdate,
    read_schema=s.DepartmentRead, prefix="/departments", tag="Kafedralar", filters=("faculty_id",),
    scope=sc.DEPARTMENT,
))
admin_router.include_router(build_crud_router(
    model=m.Specialty, create_schema=s.SpecialtyCreate, update_schema=s.SpecialtyUpdate,
    read_schema=s.SpecialtyRead, prefix="/specialties", tag="Hünärler", filters=("department_id",),
    scope=sc.SPECIALTY,
))
admin_router.include_router(build_crud_router(
    model=m.Shift, create_schema=s.ShiftCreate, update_schema=s.ShiftUpdate,
    read_schema=s.ShiftRead, prefix="/shifts", tag="Smenalar",
))
admin_router.include_router(build_crud_router(
    model=m.Group, create_schema=s.GroupCreate, update_schema=s.GroupUpdate,
    read_schema=s.GroupRead, prefix="/groups", tag="Toparlar", filters=("specialty_id", "shift_id", "course"),
    scope=sc.GROUP,
))
admin_router.include_router(build_crud_router(
    model=m.Subgroup, create_schema=s.SubgroupCreate, update_schema=s.SubgroupUpdate,
    read_schema=s.SubgroupRead, prefix="/subgroups", tag="Kiçi toparlar", filters=("group_id",),
    scope=sc.SUBGROUP,
))
admin_router.include_router(resources.router)
admin_router.include_router(curriculum.router)
admin_router.include_router(timetables.router)
admin_router.include_router(exams.router)
admin_router.include_router(docx.router)

api_router.include_router(admin_router)
# Giriş (açyk), hasaplar we çap etmek (admin), "meniň raspisaniýäm" (mugallym) — öz barlaglary bilen.
api_router.include_router(users.router)
api_router.include_router(journal.router)
