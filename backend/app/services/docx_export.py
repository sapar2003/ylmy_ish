"""Raspisaniýeleri uniwersitetiň Word nusgasy boýunça (.docx) çykarmak.

Hepdelik raspisaniýe — "OKUW SAPAKLARYNYŇ TERTIBI": günler dik ýazylýar, jübütler 1-2, 3-4, 5-6;
potok leksiýasy birnäçe toparyň sütünini birleşdirýär, kiçi toparlar toparyň sütünini bölýär,
sanawjy/maýdalawjy hepdäniň sapaklary jübüt öýjüginiň ýokarky/aşaky setirinde.
Synag raspisaniýesi — "ARA SYNAGLARYŇ GÜN TERTIBI": setirler seneler, sütünler toparlar.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.services.docx_writer import Cell, Page, Para, Row, Run, Table, build_docx, p

LESSON_ABBR = {"lecture": "u.o.", "practice": "a.s.", "lab": "t.s.", "seminar": "s.s."}
POSITION_ABBR = {
    "uly mugallym": "uly mug.", "mugallym": "mug.", "mugallym-öwreniji": "mug.-öwr.",
    "professor": "prof.", "dosent": "dos.",
}
WEEKDAYS = ["Duşenbe", "Sişenbe", "Çarşenbe", "Penşenbe", "Anna", "Şenbe", "Ýekşenbe"]
LEVEL_WORD = {"bachelor": "bakalawr", "master": "magistr"}
LEVEL_TITLE = {"bachelor": "Bakalawr", "master": "Magistr"}
EXAM_KIND = {
    "midterm": ("ARA SYNAGLARYŇ", "Ara synaglaryň"),
    "final": ("SYNAGLARYŇ", "Synaglaryň"),
    "retake": ("GAÝTADAN TABŞYRMALARYŇ", "Gaýtadan tabşyrmalaryň"),
    "state": ("DÖWLET SYNAGLARYNYŇ", "Döwlet synaglarynyň"),
    "other": ("SYNAGLARYŇ", "Synaglaryň"),
}


@dataclass
class DocOptions:
    """Resminamanyň goşmaça maglumatlary (adaty bahalar STKF-iň Word faýllaryndan)."""
    academic_year: str = "2026/2027"
    semester: str = "I"
    prorector: str = "S. Hudaýwerenow"
    rector: str = "B. Atamanow"
    dean_title: str = "Fakultetiň dekanynyň w.ý.ý."
    dean: str = "D. Tejenow"
    office_head: str = "M. Babaýew"
    mini: bool = False  # ykjam çap: kiçi şrift we gyralar


# --- umumy kömekçiler ---
def short_teacher(t: m.Teacher | None) -> str:
    """"Arrykowa Güljemal Kerimnazarowna" + "Uly mugallym" -> "uly mug.G.Arrykowa"."""
    if t is None:
        return ""
    parts = t.name.split()
    if len(parts) >= 2 and parts[1].endswith("."):  # "Hudaýgulyýewa G."
        name = f"{parts[1]}{parts[0]}"
    elif len(parts) >= 2:
        name = f"{parts[1][0]}.{parts[0]}"
    else:
        name = t.name
    return POSITION_ABBR.get((t.position or "").strip().lower(), "") + name


def spaced(text: str) -> str:
    """"Ara synaglaryň" -> "A r a   s y n a g l a r y ň" (Word faýllaryndaky ýaly)."""
    return "   ".join(" ".join(word) for word in text.split())


@dataclass
class GroupInfo:
    group: m.Group
    specialty: m.Specialty
    faculty: m.Faculty


def group_infos(db: Session, group_ids: list[int]) -> list[GroupInfo]:
    rows = db.execute(
        select(m.Group, m.Specialty, m.Faculty)
        .join(m.Specialty, m.Specialty.id == m.Group.specialty_id)
        .join(m.Department, m.Department.id == m.Specialty.department_id)
        .join(m.Faculty, m.Faculty.id == m.Department.faculty_id)
        .where(m.Group.id.in_(group_ids))
    ).all()
    by_id = {g.id: GroupInfo(g, s, f) for g, s, f in rows}
    return [by_id[g] for g in group_ids if g in by_id]


def courses_text(infos: list[GroupInfo]) -> str:
    return "-".join(str(c) for c in sorted({i.group.course for i in infos}))


def specialties(infos: list[GroupInfo]) -> list[m.Specialty]:
    seen, out = set(), []
    for i in infos:
        if i.specialty.id not in seen:
            seen.add(i.specialty.id)
            out.append(i.specialty)
    return out


def spec_name(s: m.Specialty) -> str:
    return f"{s.name} ({s.code})" if s.code else s.name


def faculty_upper(infos: list[GroupInfo]) -> str:
    name = infos[0].faculty.name if infos else ""
    base = name[: -len(" fakulteti")] if name.lower().endswith(" fakulteti") else name
    return base.upper()


def first_year(o: DocOptions) -> str:
    return o.academic_year.split("/")[0].strip()


def approval_header(title_lines: list[str], subtitle: str | None, o: DocOptions) -> Table:
    """Ýokarky üç bölek: prorektor (çep), at (orta), "Tassyklaýaryn" rektor (sag)."""
    sz = 10 if o.mini else 14
    big = 12 if o.mini else 16
    year = first_year(o)
    blank = " " * 22
    left = [
        Para([Run("Okuw işleri boýunça", bold=True)], size=sz),
        Para([Run("prorektor ", bold=True), Run(blank, bold=True, underline=True), Run(f" {o.prorector}", bold=True)],
             size=sz),
        Para([Run(f"{year}-njy ýylyň ", bold=True), Run("            ", bold=True, underline=True),
              Run(" aýynyň ___ -i (y)", bold=True)], size=sz),
    ]
    center = [Para([Run(line, bold=True)], align="center", size=big) for line in title_lines]
    if subtitle:
        center.append(Para([Run(subtitle, bold=True)], align="center", size=sz))
    right = [
        Para([Run("“Tassyklaýaryn”", bold=True)], align="center", size=sz),
        Para([Run("Rektor ", bold=True), Run(blank, bold=True, underline=True), Run(f" {o.rector}", bold=True)],
             align="center", size=sz),
        Para([Run(f"{year}-njy ýylyň ", bold=True), Run("            ", bold=True, underline=True),
              Run(" aýynyň ___ -i (y)", bold=True)], align="center", size=sz),
    ]
    return Table(widths=[5670, 4772, 6095], borders=False,
                 rows=[Row([Cell(left, valign="top"), Cell(center, valign="top"), Cell(right, valign="top")])])


def signatures(note: str, o: DocOptions) -> list[Para]:
    sz = 9 if o.mini else 13
    small = 7 if o.mini else 8
    gap = " " * 10
    return [
        Para([Run(note)], size=sz, space_after=60),
        Para([Run(f"{o.dean_title}{gap}{o.dean}{gap}_________{gap}Okuw bölüminiň başlygy{gap}"
                  f"{o.office_head}{gap}_________")], size=sz - 3 if not o.mini else sz),
        Para([Run(f"{' ' * 40}(familiýasy, ady we atasynyň ady){' ' * 8}(goly){' ' * 70}"
                  f"(familiýasy, ady we atasynyň ady){' ' * 8}(goly)")], size=small),
    ]


def merge_row(keys: list) -> list[tuple[int, int, object]]:
    """Bir setirdäki yzygiderli birmeňzeş açarly sütünleri birleşdirýär: [(başy, giňligi, açar)]."""
    segs = []
    for col, key in enumerate(keys):
        if segs and key is not None and segs[-1][2] == key and segs[-1][0] + segs[-1][1] == col:
            start, span, _ = segs[-1]
            segs[-1] = (start, span + 1, key)
        else:
            segs.append((col, 1, key))
    return segs


# --- hepdelik raspisaniýe ---
@dataclass
class Lesson:
    key: tuple
    groups: list[int]
    subgroup: m.Subgroup | None
    subject: str
    kind: str
    teacher: m.Teacher
    room: str | None
    week: int | None
    weekday: int
    start: str
    number: int


def timetable_lessons(db: Session, tt: m.Timetable) -> list[Lesson]:
    rows = db.execute(
        select(m.TimetableEntry, m.TeachingAssignment, m.CurriculumItem, m.TimeSlot)
        .join(m.TeachingAssignment, m.TeachingAssignment.id == m.TimetableEntry.assignment_id)
        .join(m.CurriculumItem, m.CurriculumItem.id == m.TeachingAssignment.curriculum_item_id)
        .join(m.TimeSlot, m.TimeSlot.id == m.TimetableEntry.time_slot_id)
        .where(m.TimetableEntry.timetable_id == tt.id)
    ).all()
    names = lambda model: {o.id: o for o in db.scalars(select(model))}  # noqa: E731
    subjects, teachers, rooms = names(m.Subject), names(m.Teacher), names(m.Room)
    subgroups, streams = names(m.Subgroup), names(m.Stream)
    out = []
    for e, a, item, slot in rows:
        groups = [g.id for g in streams[item.stream_id].groups] if item.stream_id else [item.group_id]
        out.append(Lesson(
            key=(a.id, slot.id, e.week), groups=groups,
            subgroup=subgroups.get(a.subgroup_id) if a.subgroup_id else None,
            subject=subjects[item.subject_id].name, kind=item.lesson_type.value, teacher=teachers[a.teacher_id],
            room=rooms[e.room_id].name if e.room_id in rooms else None, week=e.week, weekday=slot.weekday,
            start=slot.starts_at.strftime("%H:%M"), number=slot.number,
        ))
    return out


def lesson_paras(lesson: Lesson, size: float) -> list[Para]:
    first = f"{lesson.subject} ({LESSON_ABBR[lesson.kind]})" + (f"  {lesson.room}" if lesson.room else "")
    return [Para([Run(first)], align="center", size=size), Para([Run(short_teacher(lesson.teacher))],
                                                                align="center", size=size)]


def timetable_page(db: Session, tt: m.Timetable, lessons: list[Lesson], group_ids: list[int],
                   o: DocOptions) -> list:
    infos = group_infos(db, group_ids)
    page_groups = [i.group.id for i in infos]
    mine = [l for l in lessons if set(l.groups) & set(page_groups)]
    sz = 7 if o.mini else 9

    # Sütünler: her topar üçin 1, kiçi toparlara bölünýän bolsa kiçi topar sany.
    subs_of = defaultdict(list)
    for l in mine:
        if l.subgroup and l.subgroup.id not in [s.id for s in subs_of[l.subgroup.group_id]]:
            subs_of[l.subgroup.group_id].append(l.subgroup)
    cols, group_cols, sub_col = 0, {}, {}
    for g in page_groups:
        subs = sorted(subs_of.get(g, []), key=lambda s: s.name)
        group_cols[g] = list(range(cols, cols + max(1, len(subs))))
        for i, s in enumerate(subs):
            sub_col[s.id] = cols + i
        cols += max(1, len(subs))

    # Setirler: gün × jübüt wagty; sanawjy/maýdalawjy sapak bar bolsa jübüt iki setir.
    times = sorted({l.start for l in mine}) or ["08:30"]
    days = sorted({l.weekday for l in mine} | set(range(1, 7)))
    grid: dict[tuple, list] = {}
    row_keys = []
    for d in days:
        used = [t for t in times if any(l.weekday == d and l.start == t for l in mine)]
        for t in times:
            here = [l for l in mine if l.weekday == d and l.start == t]
            if not here and (t != times[0] or used):  # sapaksyz jübütler görkezilmeýär (boş gün bir setir)
                continue
            parts = [1, 2] if any(l.week for l in here) else [None]
            for w in parts:
                row_keys.append((d, t, w))
                grid[d, t, w] = [None] * cols
            for l in here:
                targets = [sub_col[l.subgroup.id]] if l.subgroup else [c for g in l.groups if g in group_cols
                                                                     for c in group_cols[g]]
                for w in parts:
                    if l.week is None or l.week == w:
                        for c in targets:
                            grid[d, t, w][c] = l.key
    by_key = {l.key: l for l in mine}

    # Boş öýjükler: bir toparyň boş kiçi sütünleri birleşsin.
    def keys_of(rk):
        out = list(grid[rk])
        for g, cs in group_cols.items():
            for c in cs:
                if out[c] is None:
                    out[c] = ("empty", g)
        return out

    total = 15894
    first_w, label_w = 425, 690
    group_w = (total - first_w - label_w) / max(1, len(page_groups))
    widths = [first_w, label_w]
    for g in page_groups:
        n = len(group_cols[g])
        widths += [round(group_w / n)] * n

    header_cells = [Cell([Para([Run("Günler", bold=True)], align="center", size=sz)], vmerge="restart",
                         vertical=True),
                    Cell([Para([Run("Topar", bold=True)], align="center", size=sz)])]
    for i in infos:
        header_cells.append(Cell([
            Para([Run(i.group.name, bold=True)], align="center", size=sz),
            Para([Run(f"({i.group.student_count}-talyp)", bold=True)], align="center", size=sz),
        ], span=len(group_cols[i.group.id]), vmerge="restart"))
    rows = [Row(header_cells, height=397, header=True),
            Row([Cell(vmerge="continue", vertical=True),
                 Cell([Para([Run("Sapak", bold=True)], align="center", size=sz)])]
                + [Cell(span=len(group_cols[g]), vmerge="continue") for g in page_groups], header=True)]

    for ri, rk in enumerate(row_keys):
        d, t, w = rk
        first_of_day = ri == 0 or row_keys[ri - 1][0] != d
        first_of_pair = w in (None, 1)
        cells = [Cell([Para([Run(WEEKDAYS[d - 1], bold=True)], align="center", size=sz)] if first_of_day else [],
                      vmerge="restart" if first_of_day else "continue", vertical=True)]
        if first_of_pair:
            k = times.index(t) + 1
            label = [Para([Run(f"{2 * k - 1}-{2 * k}")], align="center", size=sz),
                     Para([Run(f"({t})")], align="center", size=sz - 2)]
            cells.append(Cell(label, vmerge="restart" if w else None))
        else:
            cells.append(Cell(vmerge="continue"))
        segs = merge_row(keys_of(rk))
        prev = merge_row(keys_of(row_keys[ri - 1])) if w == 2 else []
        nxt = merge_row(keys_of(row_keys[ri + 1])) if w == 1 else []
        for start, span, key in segs:
            vm = None
            if w == 2 and (start, span, key) in prev:
                vm = "continue"
            elif w == 1 and (start, span, key) in nxt:
                vm = "restart"
            paras = lesson_paras(by_key[key], sz) if key in by_key and vm != "continue" else []
            cells.append(Cell(paras, span=span, vmerge=vm))
        rows.append(Row(cells, height=None))

    specs = specialties(infos)
    level = LEVEL_WORD.get(infos[0].specialty.level.value, "") if infos else ""
    many = len(specs) > 1
    spec_line = (", ".join(spec_name(s) for s in specs)
                 + f" {level} taýýarlyk {'ugurlarynyň' if many else 'ugrunyň'} {courses_text(infos)} okuw ýyly")
    title_sz = 10 if o.mini else 14
    return [
        approval_header(["OKUW SAPAKLARYNYŇ", "T E R T I B I"], None, o),
        p(f"{faculty_upper(infos)} fakulteti", size=title_sz, align="center"),
        p(spec_line, size=title_sz, align="center"),
        p(f"{o.academic_year}-nji okuw ýylynyň {o.semester} ýarymýyllygy", size=title_sz, align="center", after=80),
        Table(widths=widths, rows=rows),
        p("", size=4),
        *signatures("Bellik: Okuw dersiniň ady, sapagyň görnüşi, mugallymyň alymlyk derejesi, familiýasy we ady, "
                    "okuw otagynyň belgisi doly görkezilmelidir.", o),
    ]


def timetable_docx(db: Session, tt: m.Timetable, pages: list[list[int]], o: DocOptions) -> bytes:
    lessons = timetable_lessons(db, tt)
    blocks = []
    for i, group_ids in enumerate(pages):
        if i:
            blocks.append("PAGE_BREAK")
        blocks += timetable_page(db, tt, lessons, group_ids, o)
    margins = (284, 284, 567, 567) if o.mini else (568, 1135, 709, 720)
    return build_docx(blocks, Page(margins=margins))


# --- synag raspisaniýesi ---
@dataclass
class ExamLesson:
    key: int
    groups: list[int]
    subject: str
    examiner: m.Teacher
    assistant: m.Teacher | None
    room: str | None
    day: date
    start: str


def exam_lessons(db: Session, sch: m.ExamSchedule) -> list[ExamLesson]:
    rows = db.execute(
        select(m.ExamEntry, m.Exam, m.ExamPeriod)
        .join(m.Exam, m.Exam.id == m.ExamEntry.exam_id)
        .join(m.ExamPeriod, m.ExamPeriod.id == m.ExamEntry.period_id)
        .where(m.ExamEntry.schedule_id == sch.id)
    ).all()
    names = lambda model: {o.id: o for o in db.scalars(select(model))}  # noqa: E731
    subjects, teachers, rooms, streams = names(m.Subject), names(m.Teacher), names(m.Room), names(m.Stream)
    return [
        ExamLesson(
            key=e.id, groups=[g.id for g in streams[ex.stream_id].groups] if ex.stream_id else [ex.group_id],
            subject=subjects[ex.subject_id].name, examiner=teachers[ex.examiner_id],
            assistant=teachers.get(ex.assistant_id), room=rooms[e.room_id].name if e.room_id in rooms else None,
            day=e.day, start=period.starts_at.strftime("%H:%M"),
        )
        for e, ex, period in rows
    ]


def exam_paras(x: ExamLesson, size: float) -> list[Para]:
    hh, mm = x.start.split(":")
    paras = [Para([Run(f"Synag {hh}", bold=True), Run(mm, bold=True, superscript=True)], align="center", size=size),
             Para([Run(x.subject)], align="center", size=size)]
    if x.room:
        paras.append(Para([Run(x.room)], align="center", size=size))
    paras.append(Para([Run(short_teacher(x.examiner))], align="center", size=size))
    if x.assistant:
        paras.append(Para([Run(short_teacher(x.assistant))], align="center", size=size))
    return paras


def exam_page(db: Session, session: m.ExamSession, exams: list[ExamLesson], days: list[date],
              group_ids: list[int], o: DocOptions) -> list:
    infos = group_infos(db, group_ids)
    page_groups = [i.group.id for i in infos]
    col_of = {g: i for i, g in enumerate(page_groups)}
    mine = [x for x in exams if set(x.groups) & set(page_groups)]
    sz = 8 if o.mini else 10
    banner_sz = 10 if o.mini else 14
    kind_upper, kind_word = EXAM_KIND.get(session.kind.value, EXAM_KIND["other"])

    total = 15134
    date_w = 1384
    widths = [date_w] + [round((total - date_w) / max(1, len(page_groups)))] * len(page_groups)
    n = len(page_groups)
    rows = [
        Row([Cell([Para([Run("Topar", bold=True)], align="center", size=sz)])]
            + [Cell([Para([Run(f"{i.group.name} ({i.group.student_count}-talyp)", bold=True)], align="center",
                         size=sz)], vmerge="restart") for i in infos], height=488, header=True),
        Row([Cell([Para([Run("Günler", bold=True)], align="center", size=sz)])]
            + [Cell(vmerge="continue") for _ in infos], height=425, header=True),
    ]

    def banner(text):
        return Cell([Para([Run(spaced(text), bold=True)], align="center", size=banner_sz)], span=n)

    for di, d in enumerate(days):
        per_group = {g: sorted([x for x in mine if x.day == d and g in x.groups], key=lambda x: x.start)
                     for g in page_groups}
        k = max([1] + [len(v) for v in per_group.values()])
        day_rows = []
        if di == 0:
            day_rows.append(("banner", f"{kind_word} başlanýan güni"))
        day_rows += [("exam", i) for i in range(k)]
        if di == len(days) - 1:
            day_rows.append(("banner", f"{kind_word} tamamlanýan güni"))
        for ri, (kind, val) in enumerate(day_rows):
            date_cell = Cell([Para([Run(d.strftime("%d.%m.%Y") + "ý.", bold=True)], align="center", size=sz)]
                             if ri == 0 else [], vmerge=("restart" if ri == 0 else "continue") if len(day_rows) > 1
                             else None)
            if kind == "banner":
                rows.append(Row([date_cell, banner(val)], height=425))
                continue
            keys = []
            for g in page_groups:
                lst = per_group[g]
                keys.append(lst[val].key if val < len(lst) else ("empty", g, len(lst)))
            cells = [date_cell]
            for start, span, key in merge_row(keys):
                g = page_groups[start]
                lst = per_group[g]
                # Toparyň şol günki soňky synagy (ýa-da boş öýjük) galan setirlere çenli uzaldylýar.
                last = max(len(lst) - 1, 0)
                if val > last and k > 1:
                    cells.append(Cell(span=span, vmerge="continue"))
                    continue
                vm = "restart" if (val == last and k - 1 > last) else None
                x = next((e for e in lst if e.key == key), None)
                cells.append(Cell(exam_paras(x, sz) if x else [], span=span, vmerge=vm))
            rows.append(Row(cells, height=683 if not o.mini else None))

    specs = specialties(infos)
    level = infos[0].specialty.level.value if infos else "bachelor"
    title_sz = 10 if o.mini else 14
    many = len(specs) > 1
    return [
        approval_header([*kind_upper.split(), "GÜN", "TERTIBI"], f"({LEVEL_TITLE.get(level, '')} taýýarlygy)", o),
        p(f"{faculty_upper(infos)} fakultetiniň", size=title_sz, align="center", bold=True),
        p(", ".join(spec_name(s) for s in specs), size=title_sz, align="center", bold=True),
        p(f"taýýarlygyň {'ugurlary' if many else 'ugry'} boýunça {courses_text(infos)} okuw ýyly", size=title_sz,
          align="center"),
        p(f"{o.academic_year}-nji okuw ýylynyň {o.semester} ýarymýyllygy", size=title_sz, align="center", after=80),
        Table(widths=widths, rows=rows),
        p("", size=4),
        *signatures("Bellik:  Hasaplar we synaglar gün tertibinde görkezilen wagtda başlanýar.", o),
    ]


def exam_docx(db: Session, sch: m.ExamSchedule, days: list[date], pages: list[list[int]], o: DocOptions) -> bytes:
    session = db.get(m.ExamSession, sch.session_id)
    exams = exam_lessons(db, sch)
    blocks = []
    for i, group_ids in enumerate(pages):
        if i:
            blocks.append("PAGE_BREAK")
        blocks += exam_page(db, session, exams, days, group_ids, o)
    margins = (284, 284, 709, 709) if o.mini else (426, 284, 1134, 1134)
    return build_docx(blocks, Page(margins=margins))
