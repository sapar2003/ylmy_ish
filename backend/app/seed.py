"""Demo maglumatlar: iki fakultet, iki smena, umumy mugallymlar, potok we bölünýän sapaklar.

Işletmek: `python -m app.seed` (baza boş bolmalydyr; `--reset` ähli maglumatlary pozup täzeden ýazýar).
`--dataset iogu`: Halkara nebit we gaz uniwersitetiniň fakultetleri we kafedralary (app/seed_iogu.py).
"""
import argparse
import sys
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.db.base import Base
from app.db.session import SessionLocal, engine

MORNING = [(1, time(8, 30), time(9, 50)), (2, time(10, 0), time(11, 20)), (3, time(11, 50), time(13, 10))]
EVENING = [(1, time(13, 30), time(14, 50)), (2, time(15, 0), time(16, 20)), (3, time(16, 30), time(17, 50))]


def seed(db: Session) -> None:
    add = lambda obj: (db.add(obj), db.flush(), obj)[2]  # noqa: E731

    # Gurluş
    inf = add(m.Faculty(name="Informatika we hasaplaýyş tehnikasy", short_name="IHT", code="IHT"))
    eco = add(m.Faculty(name="Ykdysadyýet", short_name="YK", code="YK"))
    d_prog = add(m.Department(name="Programmirleme", faculty=inf))
    d_math = add(m.Department(name="Ýokary matematika", faculty=inf))
    d_econ = add(m.Department(name="Ykdysady nazaryýet", faculty=eco))
    d_lang = add(m.Department(name="Daşary ýurt dilleri", faculty=eco))
    s_po = add(m.Specialty(name="Programma üpjünçiligi", code="PÜ", level=m.StudyLevel.bachelor, department=d_prog))
    s_ai = add(m.Specialty(
        name="Emeli aň", code="EA", level=m.StudyLevel.master, duration_years=2, department=d_prog
    ))
    s_fin = add(m.Specialty(name="Maliýe", code="ML", level=m.StudyLevel.bachelor, department=d_econ))

    morning = add(m.Shift(name="Irden", starts_at=time(8, 30), ends_at=time(13, 10)))
    evening = add(m.Shift(name="Öýlän", starts_at=time(13, 30), ends_at=time(17, 50)))
    for shift, periods in ((morning, MORNING), (evening, EVENING)):
        for day in range(1, 7):
            for number, start, end in periods:
                db.add(m.TimeSlot(shift_id=shift.id, weekday=day, number=number, starts_at=start, ends_at=end))
    db.flush()

    def group(name, specialty, course, count, shift):
        g = add(m.Group(name=name, specialty=specialty, course=course, student_count=count, shift_id=shift.id))
        for n in ("1", "2"):
            db.add(m.Subgroup(name=n, group=g, student_count=count // 2 + (int(n) - 1) * (count % 2)))
        db.flush()
        return g

    po101 = group("PÜ-101", s_po, 1, 24, morning)
    po102 = group("PÜ-102", s_po, 1, 22, morning)
    po201 = group("PÜ-201", s_po, 2, 20, evening)
    ea101 = group("EA-101", s_ai, 1, 12, evening)
    ml101 = group("ML-101", s_fin, 1, 26, morning)
    ml201 = group("ML-201", s_fin, 2, 25, evening)

    # Resurslar
    main = add(m.Building(name="Esasy bina", address="Bitarap Türkmenistan şaýoly"))
    second = add(m.Building(name="2-nji bina"))
    lecture = add(m.RoomType(name="Leksiýa zaly"))
    classroom = add(m.RoomType(name="Okuw otagy"))
    computer = add(m.RoomType(name="Kompýuter otagy"))
    for name, cap, bld, rt in [
        ("101", 80, main, lecture), ("102", 60, main, lecture),
        ("201", 30, main, classroom), ("202", 30, main, classroom), ("203", 28, second, classroom),
        ("204", 28, second, classroom), ("301", 15, main, computer), ("302", 15, main, computer),
        ("303", 15, second, computer),
    ]:
        db.add(m.Room(name=name, capacity=cap, building_id=bld.id, room_type_id=rt.id))
    db.flush()

    def teacher(name, dept, position="Mugallym", per_day=4):
        return add(m.Teacher(name=name, department_id=dept.id, position=position, max_lessons_per_day=per_day))

    t_annayev = teacher("A. Annaýew", d_math, "Dosent")  # iki fakultetde hem okadýar
    t_berdiyeva = teacher("B. Berdiýewa", d_prog, "Uly mugallym")
    t_charyyev = teacher("Ç. Çaryýew", d_prog)
    t_durdyyeva = teacher("D. Durdyýewa", d_prog)
    t_esenov = teacher("E. Esenow", d_econ, "Professor", per_day=3)
    t_gurbanova = teacher("G. Gurbanowa", d_lang)  # iňlis dili: ähli fakultetler
    t_hojayev = teacher("H. Hojaýew", d_econ)

    # Annaýew duşenbe güni irden işlemeýär, sişenbe öýlän işlemegi isleýär.
    for slot in db.scalars(select(m.TimeSlot)):
        if slot.weekday == 1 and slot.shift_id == morning.id:
            db.add(m.TeacherAvailability(teacher_id=t_annayev.id, time_slot_id=slot.id,
                                         status=m.AvailabilityStatus.unavailable))
        if slot.weekday == 2 and slot.shift_id == evening.id:
            db.add(m.TeacherAvailability(teacher_id=t_annayev.id, time_slot_id=slot.id,
                                         status=m.AvailabilityStatus.preferred))

    # Okuw meýilnamasy
    math = add(m.Subject(name="Ýokary matematika", department_id=d_math.id))
    prog = add(m.Subject(name="Programmirlemäniň esaslary", department_id=d_prog.id))
    db_ = add(m.Subject(name="Maglumatlar bazasy", department_id=d_prog.id))
    ml = add(m.Subject(name="Maşyn öwrenişi", department_id=d_prog.id))
    econ = add(m.Subject(name="Ykdysady nazaryýet", department_id=d_econ.id))
    fin = add(m.Subject(name="Maliýe hasabaty", department_id=d_econ.id))
    eng = add(m.Subject(name="Iňlis dili", department_id=d_lang.id))

    stream_po1 = add(m.Stream(name="PÜ 1-nji ýyl", groups=[po101, po102]))

    def item(subject, ltype, per_week, teacher_, group_=None, stream=None, room_type=None, split_teachers=None):
        ci = add(m.CurriculumItem(
            subject_id=subject.id, lesson_type=ltype, lessons_per_week=per_week, group_id=group_.id if group_ else None,
            stream_id=stream.id if stream else None, split=bool(split_teachers),
            room_type_id=room_type.id if room_type else None,
        ))
        if split_teachers:
            for sub, t in zip(sorted(group_.subgroups, key=lambda s: s.name), split_teachers, strict=True):
                db.add(m.TeachingAssignment(curriculum_item_id=ci.id, subgroup_id=sub.id, teacher_id=t.id))
        else:
            db.add(m.TeachingAssignment(curriculum_item_id=ci.id, teacher_id=teacher_.id))
        db.flush()

    L, P, LAB = m.LessonType.lecture, m.LessonType.practice, m.LessonType.lab
    # PÜ 1-nji ýyl: potok leksiýalary + toparlaýyn amaly + bölünýän tejribe
    item(math, L, 2, t_annayev, stream=stream_po1, room_type=lecture)
    item(prog, L, 1, t_berdiyeva, stream=stream_po1, room_type=lecture)
    for g in (po101, po102):
        item(math, P, 2, t_annayev, group_=g, room_type=classroom)
        item(prog, LAB, 2, None, group_=g, room_type=computer, split_teachers=[t_charyyev, t_durdyyeva])
        item(eng, P, 2, t_gurbanova, group_=g, room_type=classroom)
    # PÜ-201 (öýlän)
    item(db_, L, 1, t_berdiyeva, group_=po201, room_type=lecture)
    item(db_, LAB, 2, None, group_=po201, room_type=computer, split_teachers=[t_charyyev, t_charyyev])
    item(math, P, 2, t_annayev, group_=po201, room_type=classroom)
    item(eng, P, 2, t_gurbanova, group_=po201, room_type=classroom)
    # Magistratura (öýlän)
    item(ml, L, 2, t_durdyyeva, group_=ea101, room_type=classroom)
    item(ml, LAB, 2, t_durdyyeva, group_=ea101, room_type=computer)
    # Ykdysadyýet: Annaýew we Gurbanowa bu fakultetde hem okadýar
    item(econ, L, 2, t_esenov, group_=ml101, room_type=lecture)
    item(math, P, 2, t_annayev, group_=ml101, room_type=classroom)
    item(fin, P, 2, t_hojayev, group_=ml101, room_type=classroom)
    item(eng, P, 2, t_gurbanova, group_=ml101, room_type=classroom)
    item(fin, L, 2, t_esenov, group_=ml201, room_type=lecture)
    item(econ, P, 2, t_hojayev, group_=ml201, room_type=classroom)
    item(math, P, 2, t_annayev, group_=ml201, room_type=classroom)
    item(eng, P, 2, t_gurbanova, group_=ml201, room_type=classroom)
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="ähli tablisalary arassalap täzeden ýazmak")
    parser.add_argument("--dataset", choices=["demo", "iogu"], default="demo",
                        help="demo: kiçi synag maglumatlary; iogu: Halkara nebit we gaz uniwersiteti")
    parser.add_argument("--if-empty", action="store_true", help="baza boş bolsa ýazmak, bolmasa hiç zat etmezlik")
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.reset:
            for table in reversed(Base.metadata.sorted_tables):
                if table.name != "alembic_version":
                    db.execute(table.delete())
            db.commit()
        elif db.scalar(select(m.Faculty.id).limit(1)) is not None:
            if args.if_empty:
                return
            sys.exit("Bazada eýýäm maglumat bar. Täzeden ýazmak üçin: python -m app.seed --reset")
        if args.dataset == "iogu":
            from app.seed_iogu import seed_iogu

            seed_iogu(db)
        else:
            seed(db)
    print(f"Maglumatlar ýazyldy ({args.dataset}).")


if __name__ == "__main__":
    main()
