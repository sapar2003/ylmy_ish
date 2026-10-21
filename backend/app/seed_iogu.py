"""Ýagşygeldi Kakaýew adyndaky Halkara nebit we gaz uniwersiteti (HNGU) üçin başlangyç maglumatlar.

Fakultetler we kafedralar uniwersitetiň resmi sahypasyndan alyndy (iogu.edu.tm/articles/73, 2026-10-21).
Balkanabat bölümi bilkastlaýyn goşulmady. Hünärler kafedralaryň ugruna görä çaklanyp goşuldy
(magistratura: WHED). Toparlar, mugallymlar, otaglar we okuw meýilnamasy diňe synag üçin
oýlanyp tapyldy: olary UI-da hakyky maglumatlar bilen çalyşyň.
"""
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m

MORNING = [(1, time(8, 30), time(9, 50)), (2, time(10, 0), time(11, 20)), (3, time(11, 40), time(13, 0))]
EVENING = [(1, time(13, 30), time(14, 50)), (2, time(15, 0), time(16, 20)), (3, time(16, 30), time(17, 50))]

# Fakultet -> kafedralar (resmi sahypadan).
FACULTIES = {
    ("Nebit we gaz fakulteti", "NG"): [
        "Nebit we gaz guýularyny burawlamak kafedrasy",
        "Nebit we gaz ojaklaryny özleşdirmek kafedrasy",
        "Nebitgazgeçirijilerini we nebitgazyň saklanýan ýerlerini taslamak, gurmak we ulanmak kafedrasy",
        "Diller kafedrasy",
    ],
    ("Geologiýa fakulteti", "GL"): [
        "Peýdaly magdanlary gözlemegiň we barlamagyň geofiziki usullary kafedrasy",
        "Geologiýa we geohimiýa kafedrasy",
        "Gidrogeologiýa we inžener geologiýasy kafedrasy",
        "Dag işleri kafedrasy",
        "Geologik kartalaşdyrma we markşeýder işi kafedrasy",
        "Çyzuw we materiallaryň garşylygy kafedrasy",
    ],
    ("Energetika we inženerçilik desgalary fakulteti", "EI"): [
        "Senagat gurluşygy we geodeziýa kafedrasy",
        "Kompressorlar we sowadyjy desgalar kafedrasy",
        "Nebit we gaz känleriniň maşynlary we enjamlary kafedrasy",
        "Elektrik üpjünçiligi we awtomatika kafedrasy",
        "Fizika we elektronika kafedrasy",
        "Amaly mehanika kafedrasy",
    ],
    ("Himiýa tehnologiýasy we ekologiýa fakulteti", "HE"): [
        "Senagat ekologiýasy kafedrasy",
        "Nebiti, gazy gaýtadan işlemegiň himiki tehnologiýasy kafedrasy",
        "Jemgyýeti öwreniş ylymlary kafedrasy",
        "Umumy himiýa kafedrasy",
    ],
    ("Ykdysadyýet we dolandyryş fakulteti", "YD"): [
        "Nebit we gaz pudagynyň ykdysadyýeti we dolandyrylyşy kafedrasy",
        "Logistika kafedrasy",  # iňlisçe sahypada bar
        "Ýokary matematika kafedrasy",
        "Bedenterbiýe kafedrasy",
    ],
    ("Sanly tehnologiýalar we kiberhowpsuzlyk fakulteti", "SK"): [
        "Kiberhowpsuzlyk kafedrasy",
        "Informatika we maglumat tehnologiýalary kafedrasy",
        "Häzirki zaman kompýuter tehnologiýalary kafedrasy",
    ],
    ("Hünär derejesini ýokarlandyryş fakulteti", "HY"): [],
}

# (hünär, gysga kod, kafedra, dereje, smena, toparlar: [(kurs, talyp sany)])
SPECIALTIES = [
    ("Nebit we gaz guýularyny burawlamak", "BU", "Nebit we gaz guýularyny burawlamak kafedrasy", "bachelor", "irden", [(1, 24), (2, 22)]),
    ("Nebit we gaz ojaklaryny özleşdirmek", "OÖ", "Nebit we gaz ojaklaryny özleşdirmek kafedrasy", "bachelor", "irden", [(1, 25)]),
    ("Nebitgaz geçirijileri we saklaýyş desgalary", "NG", "Nebitgazgeçirijilerini we nebitgazyň saklanýan ýerlerini taslamak, gurmak we ulanmak kafedrasy", "bachelor", "öýlän", [(1, 20)]),
    ("Nebit we gaz inženerçiligi", "MNG", "Nebit we gaz ojaklaryny özleşdirmek kafedrasy", "master", "öýlän", [(1, 10)]),
    ("Nebit we gaz geologiýasy", "GG", "Geologiýa we geohimiýa kafedrasy", "bachelor", "irden", [(1, 22)]),
    ("Geofizika", "GF", "Peýdaly magdanlary gözlemegiň we barlamagyň geofiziki usullary kafedrasy", "bachelor", "öýlän", [(1, 18)]),
    ("Nebit we gaz känleriniň maşynlary we enjamlary", "ME", "Nebit we gaz känleriniň maşynlary we enjamlary kafedrasy", "bachelor", "öýlän", [(1, 22)]),
    ("Elektrik üpjünçiligi", "EÜ", "Elektrik üpjünçiligi we awtomatika kafedrasy", "bachelor", "irden", [(1, 24)]),
    ("Nebiti we gazy gaýtadan işlemegiň himiki tehnologiýasy", "HT", "Nebiti, gazy gaýtadan işlemegiň himiki tehnologiýasy kafedrasy", "bachelor", "irden", [(1, 24), (2, 20)]),
    ("Senagat ekologiýasy", "EK", "Senagat ekologiýasy kafedrasy", "bachelor", "öýlän", [(1, 18)]),
    ("Nebit we gaz pudagynyň ykdysadyýeti", "YK", "Nebit we gaz pudagynyň ykdysadyýeti we dolandyrylyşy kafedrasy", "bachelor", "öýlän", [(1, 26)]),
    ("Logistika", "LG", "Logistika kafedrasy", "bachelor", "öýlän", [(1, 22)]),
    ("Kiberhowpsuzlyk", "KH", "Kiberhowpsuzlyk kafedrasy", "bachelor", "irden", [(1, 20)]),
    ("Maglumat tehnologiýalary", "MT", "Informatika we maglumat tehnologiýalary kafedrasy", "bachelor", "irden", [(1, 22)]),
]

# Umumy dersler: kafedra, ders, sapak görnüşi, hepdede, bölünýärmi, otag görnüşi, mugallymlar.
# Bu mugallymlar ähli fakultetlere okadýar: algoritm olaryň sapaklaryny hiç haçan gabat getirmeýär.
COMMON = [
    ("Ýokary matematika kafedrasy", "Ýokary matematika", "practice", 2, False, "Okuw otagy",
     ["A. Annaýew", "M. Meredowa", "S. Saparow"]),
    ("Fizika we elektronika kafedrasy", "Fizika", "lab", 1, True, "Tejribehana",
     ["B. Baýramow", "G. Gylyjowa", "O. Orazow"]),
    ("Umumy himiýa kafedrasy", "Umumy himiýa", "practice", 1, False, "Okuw otagy",
     ["H. Hojamuradowa", "K. Kakajanow"]),
    ("Diller kafedrasy", "Iňlis dili", "practice", 2, True, "Okuw otagy",
     ["J. Jumaýewa", "L. Läheýewa", "N. Nurmuhammedowa", "T. Täçmyradowa"]),
    ("Informatika we maglumat tehnologiýalary kafedrasy", "Informatika", "lab", 1, True, "Kompýuter otagy",
     ["D. Durdyýew", "P. Pirmuhammedowa", "R. Rejepow"]),
    ("Bedenterbiýe kafedrasy", "Bedenterbiýe", "practice", 1, False, "Sport zaly",
     ["Ç. Çaryýew", "Ý. Ýazmuradow"]),
]

ROOMS = [
    # bina, otag, sygym, görnüş
    ("Esasy bina", "A-101", 120, "Leksiýa zaly"), ("Esasy bina", "A-102", 80, "Leksiýa zaly"),
    *[("Esasy bina", f"A-{n}", 30, "Okuw otagy") for n in range(201, 211)],
    *[("1-nji okuw binasy", f"B-{n}", 30, "Okuw otagy") for n in range(101, 107)],
    ("1-nji okuw binasy", "B-301", 15, "Tejribehana"), ("1-nji okuw binasy", "B-302", 15, "Tejribehana"),
    ("1-nji okuw binasy", "B-303", 15, "Tejribehana"),
    ("2-nji okuw binasy", "C-201", 15, "Kompýuter otagy"), ("2-nji okuw binasy", "C-202", 15, "Kompýuter otagy"),
    ("2-nji okuw binasy", "C-203", 15, "Kompýuter otagy"),
    ("Sport toplumy", "Sport zaly 1", 60, "Sport zaly"), ("Sport toplumy", "Sport zaly 2", 60, "Sport zaly"),
]


def seed_iogu(db: Session) -> None:
    def add(obj):
        db.add(obj)
        db.flush()
        return obj

    departments: dict[str, m.Department] = {}
    for (name, code), dept_names in FACULTIES.items():
        faculty = add(m.Faculty(name=name, short_name=code, code=code))
        for d in dept_names:
            departments[d] = add(m.Department(name=d, faculty_id=faculty.id))

    shifts = {
        "irden": add(m.Shift(name="Irden", starts_at=time(8, 30), ends_at=time(13, 0))),
        "öýlän": add(m.Shift(name="Öýlän", starts_at=time(13, 30), ends_at=time(17, 50))),
    }
    for key, periods in (("irden", MORNING), ("öýlän", EVENING)):
        for day in range(1, 7):
            for number, start, end in periods:
                db.add(m.TimeSlot(shift_id=shifts[key].id, weekday=day, number=number, starts_at=start, ends_at=end))

    buildings: dict[str, m.Building] = {}
    room_types: dict[str, m.RoomType] = {}
    for bld, name, cap, rtype in ROOMS:
        if bld not in buildings:
            buildings[bld] = add(m.Building(name=bld, address="Aşgabat" if "Sport" not in bld else None))
        if rtype not in room_types:
            room_types[rtype] = add(m.RoomType(name=rtype))
        db.add(m.Room(name=name, capacity=cap, building_id=buildings[bld].id, room_type_id=room_types[rtype].id))
    db.flush()

    # Umumy dersleriň mugallymlary
    common_teachers: dict[str, list[m.Teacher]] = {}
    common_subjects: dict[str, m.Subject] = {}
    for dept, subject, *_rest, teachers in COMMON:
        common_subjects[subject] = add(m.Subject(name=subject, department_id=departments[dept].id))
        common_teachers[subject] = [
            add(m.Teacher(name=t, department_id=departments[dept].id, position="Mugallym", max_lessons_per_day=4))
            for t in teachers
        ]

    def assign(item: m.CurriculumItem, group: m.Group, teachers: list[m.Teacher], cursor: list[int]) -> None:
        """Mugallymlary nobat bilen paýlaýar, ýüki deňleşdirmek üçin."""
        if item.split:
            for sub in sorted(group.subgroups, key=lambda s: s.name):
                t = teachers[cursor[0] % len(teachers)]
                cursor[0] += 1
                db.add(m.TeachingAssignment(curriculum_item_id=item.id, subgroup_id=sub.id, teacher_id=t.id))
        else:
            t = teachers[cursor[0] % len(teachers)]
            cursor[0] += 1
            db.add(m.TeachingAssignment(curriculum_item_id=item.id, teacher_id=t.id))

    cursors = {subject: [0] for subject in common_teachers}
    for name, code, dept_name, level, shift, groups in SPECIALTIES:
        dept = departments[dept_name]
        sp = add(m.Specialty(
            name=name, code=code, level=m.StudyLevel(level), department_id=dept.id,
            duration_years=2 if level == "master" else 4,
        ))
        # Hünär dersleri: kafedranyň öz mugallymy
        head = add(m.Teacher(name=f"{code} kafedrasynyň mugallymy", department_id=dept.id,
                             position="Uly mugallym", max_lessons_per_day=4))
        lecture = add(m.Subject(name=f"{name}: esaslar", department_id=dept.id))

        for course, students in groups:
            g = add(m.Group(name=f"{code}-{course}01", specialty_id=sp.id, course=course,
                            student_count=students, shift_id=shifts[shift].id))
            for half in ("1", "2"):
                db.add(m.Subgroup(name=half, group_id=g.id, student_count=(students + (half == "1")) // 2))
            db.flush()
            db.refresh(g)

            item = add(m.CurriculumItem(subject_id=lecture.id, lesson_type=m.LessonType.lecture,
                                        lessons_per_week=2, group_id=g.id,
                                        room_type_id=room_types["Leksiýa zaly"].id))
            db.add(m.TeachingAssignment(curriculum_item_id=item.id, teacher_id=head.id))

            for _dept, subject, ltype, per_week, split, rtype, _t in COMMON:
                if level == "master" and subject in ("Bedenterbiýe", "Umumy himiýa", "Fizika"):
                    continue
                item = add(m.CurriculumItem(
                    subject_id=common_subjects[subject].id, lesson_type=m.LessonType(ltype),
                    lessons_per_week=per_week, group_id=g.id, split=split, room_type_id=room_types[rtype].id,
                ))
                assign(item, g, common_teachers[subject], cursors[subject])
    db.commit()


def has_data(db: Session) -> bool:
    return db.scalar(select(m.Faculty.id).limit(1)) is not None
