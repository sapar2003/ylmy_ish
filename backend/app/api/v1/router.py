from fastapi import APIRouter

from app import models as m
from app.api.crud import build_crud_router
from app.api.v1 import curriculum, resources
from app.schemas import structure as s

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(build_crud_router(
    model=m.Faculty, create_schema=s.FacultyCreate, update_schema=s.FacultyUpdate,
    read_schema=s.FacultyRead, prefix="/faculties", tag="Fakultetler",
))
api_router.include_router(build_crud_router(
    model=m.Department, create_schema=s.DepartmentCreate, update_schema=s.DepartmentUpdate,
    read_schema=s.DepartmentRead, prefix="/departments", tag="Kafedralar", filters=("faculty_id",),
))
api_router.include_router(build_crud_router(
    model=m.Specialty, create_schema=s.SpecialtyCreate, update_schema=s.SpecialtyUpdate,
    read_schema=s.SpecialtyRead, prefix="/specialties", tag="Hünärler", filters=("department_id",),
))
api_router.include_router(build_crud_router(
    model=m.Shift, create_schema=s.ShiftCreate, update_schema=s.ShiftUpdate,
    read_schema=s.ShiftRead, prefix="/shifts", tag="Smenalar",
))
api_router.include_router(build_crud_router(
    model=m.Group, create_schema=s.GroupCreate, update_schema=s.GroupUpdate,
    read_schema=s.GroupRead, prefix="/groups", tag="Toparlar", filters=("specialty_id", "shift_id", "course"),
))
api_router.include_router(build_crud_router(
    model=m.Subgroup, create_schema=s.SubgroupCreate, update_schema=s.SubgroupUpdate,
    read_schema=s.SubgroupRead, prefix="/subgroups", tag="Kiçi toparlar", filters=("group_id",),
))
api_router.include_router(resources.router)
api_router.include_router(curriculum.router)
