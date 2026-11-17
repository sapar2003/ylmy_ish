"""Okuw bölüminiň "SYNAGLARYŇ GÜN TERTIBI" Word faýllaryny ulgama girizmek.

Her faýl: ýokarda tassyklama, soň esasy tablisa — sütünler toparlar ("1 KUPÜ (A) (23-talyp) V (bina)-301"),
setirler seneler, öýjüklerde "Maslahat 08:30 ..." ýa-da "Synag 10:00 <ders> <uly mugallym> <kiçi mugallym> (otag)".

Girizilýär: toparlaryň talyp sany we öz otagy, mugallymlar (wezipesi bilen), dersler, otaglar, synag möwsümi,
synaglar (ders + topar + uly we kiçi mugallym) we faýldaky tertip "Asyl tertip" diýen synag raspisaniýesi hökmünde.

Ulanylyşy:  python -m app.importers.exam_docx "C:\\...\\New folder" [--report hasabat.txt]
"""
import argparse
import re
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, time
from pathlib import Path
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
UP = "A-ZÇŞÜÖÄŇÝŽ"
LO = "a-zçşüöäňýž"
RANK_RE = rf"(uly\s*mug\.|mug\.\s*-\s*öwr\.|mug\.|prof\.|dos\.)"
TEACHER_RE = re.compile(rf"{RANK_RE}\s*(?:MUG\.\s*)?(?:([{UP}])\.\s*)?([{UP}][{LO}]+?)(?=uly\s*mug\.|mug\.|prof\.|[^{LO}]|$)")
ROOM_RE = re.compile(r"\(?\s*\b((?:V|MTO)\s*-\s*\d+)\s*\)?")
ENTRY_RE = re.compile(r"(Maslahat|Synag)\s*(\d{2})\s*:?\s*(\d{2})")
GROUP_RE = re.compile(rf"(\d)\s*([{UP}]+)\s*(?:\(([{UP}])\))?\s*\((\d+)\s*-\s*talyp\)\s*V\s*\(bina\)\s*-\s*(\d+)")
DATE_RE = re.compile(r"(\d{2})\.\s*(\d{2})\.\s*(\d{4})")
RANK_POSITION = {"uly mug.": "Uly mugallym", "mug.": "Mugallym", "mug.-öwr.": "Mugallym-öwreniji",
                 "prof.": "Professor", "dos.": "Dosent"}
SUBJECT_FIX = {"usulary": "usullary", "tehnikanynyň": "tehnikanyň"}
SECONDARY_FILES = ("2 MUT,KUPÜ", "2 MUT,MH")  # 2-nji ýyl üçin goşmaça (gabat gelmeýän) nusgalar
SESSION_NAME = "Ýarymýyllyk synaglar 2026/2027 I (STKF)"
PERIODS = [(1, time(8, 30), time(9, 50)), (2, time(10, 0), time(11, 20))]


# --- Word faýlyny okamak ---
def _norm(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(rf"\bC\.(?=\s*[{UP}])", "Ç.", text)  # latyn C
    text = re.sub(r"\bMUG\.\s*(?=Çüriýew)", "M.", text)
    return re.sub(r"\s+", " ", text).strip()


def _cell_text(tc) -> str:
    paras = []
    for p in tc.iter(W + "p"):
        t = "".join(x.text or "" for x in p.iter(W + "t"))
        if t.strip():
            paras.append(t)
    return _norm(" ".join(paras))


def _cells(tr) -> list[tuple[str, int]]:
    out = []
    for tc in tr.findall(W + "tc"):
        span = tc.find(f"{W}tcPr/{W}gridSpan")
        out.append((_cell_text(tc), int(span.get(W + "val")) if span is not None else 1))
    return out


@dataclass
class Teacher:
    rank: str
    initial: str | None
    surname: str


@dataclass
class Entry:
    day: date
    kind: str  # "consult" | "exam"
    start: time
    subject: str
    teachers: list[Teacher]
    room: str | None


@dataclass
class DocGroup:
    course: int
    code: str
    letter: str | None
    size: int
    room: str
    entries: list[Entry] = field(default_factory=list)


@dataclass
class Doc:
    path: Path
    master: bool
    groups: list[DocGroup]
    session_days: list[date]


def parse_entries(text: str, day: date) -> list[Entry]:
    out = []
    marks = list(ENTRY_RE.finditer(text))
    for i, mk in enumerate(marks):
        body = text[mk.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        teachers = [Teacher(re.sub(r"\s+", "", t.group(1)).replace("ulymug.", "uly mug."), t.group(2), t.group(3))
                    for t in TEACHER_RE.finditer(body)]
        rooms = [re.sub(r"\s+", "", r.group(1)) for r in ROOM_RE.finditer(body)]
        cut = min([t.start() for t in TEACHER_RE.finditer(body)] + [r.start() for r in ROOM_RE.finditer(body)]
                  + [len(body)])
        subject = body[:cut].strip(" ,.")
        for a, b in SUBJECT_FIX.items():
            subject = subject.replace(a, b)
        subject = re.sub(r"\s+", " ", subject)
        out.append(Entry(day=day, kind="consult" if mk.group(1) == "Maslahat" else "exam",
                         start=time(int(mk.group(2)), int(mk.group(3))), subject=subject,
                         teachers=teachers, room=rooms[0] if rooms else None))
    return out


def parse_doc(path: Path) -> Doc:
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    text_all = _norm(" ".join(t.text or "" for t in root.iter(W + "t")))
    master = "magistr" in path.stem.lower() or "Magistr" in text_all
    table = next(t for t in root.iter(W + "tbl") if _cells(t.find(W + "tr"))[0][0].startswith("Topar"))
    rows = table.findall(W + "tr")
    header = _cells(rows[0])[1:]
    groups = []
    for text, _ in header:
        g = GROUP_RE.search(text)
        if not g:
            raise ValueError(f"{path.name}: topar ady okalmady: {text!r}")
        groups.append(DocGroup(course=int(g.group(1)), code=g.group(2), letter=g.group(3), size=int(g.group(4)),
                               room=f"V-{g.group(5)}"))
    days, current = [], None
    for tr in rows[2:]:
        cells = _cells(tr)
        dm = DATE_RE.search(cells[0][0])
        if dm:
            current = date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)))
            days.append(current)
        if current is None or len(cells) == 2:  # başlanýan/tamamlanýan güni setiri
            continue
        col = 0
        for text, span in cells[1:]:
            for k in range(span):
                if col + k < len(groups) and text:
                    groups[col + k].entries += parse_entries(text, current)
            col += span
    return Doc(path=path, master=master, groups=groups, session_days=days)


# --- bazada tapmak ýa-da döretmek ---
def _key(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


class Importer:
    def __init__(self, db: Session, log=print):
        self.db, self.log = db, log
        self.notes: list[str] = []
        self.created = Counter()
        self.subjects = {_key(s.name): s for s in db.scalars(select(m.Subject))}
        self.rooms = {r.name: r for r in db.scalars(select(m.Room))}
        self.teachers_db = list(db.scalars(select(m.Teacher)))
        self.teacher_cache: dict[tuple[str, str | None], m.Teacher] = {}

    def group_name(self, d: Doc, g: DocGroup) -> str:
        base = f"{g.course} {g.code}" + (f" ({g.letter})" if g.letter else "")
        return f"Mag {base}" if d.master else base

    def specialty(self, code: str, master: bool) -> m.Specialty:
        level = m.StudyLevel.master if master else m.StudyLevel.bachelor
        sp = self.db.scalar(select(m.Specialty).where(m.Specialty.code == code, m.Specialty.level == level))
        if sp is None:
            raise ValueError(f"Hünär tapylmady: {code} ({level.value}). Ilki hünäri goşuň.")
        return sp

    def room(self, name: str, size: int) -> m.Room:
        r = self.rooms.get(name)
        if r is None:
            building = self.db.scalar(select(m.Building).order_by(m.Building.id))
            rtype = self.db.scalar(select(m.RoomType).where(m.RoomType.name == "Okuw otagy")) or \
                self.db.scalar(select(m.RoomType).order_by(m.RoomType.id))
            r = m.Room(name=name, capacity=max(30, size), building_id=building.id, room_type_id=rtype.id)
            self.db.add(r)
            self.db.flush()
            self.rooms[name] = r
            self.created["otag"] += 1
        elif r.capacity < size:
            self.notes.append(f"Otag {name}: sygymy {r.capacity}, ýöne {size} talyp üçin ulanylýar.")
        return r

    def subject(self, name: str, department_id: int) -> m.Subject:
        s = self.subjects.get(_key(name))
        if s is None:
            s = m.Subject(name=name, department_id=department_id)
            self.db.add(s)
            self.db.flush()
            self.subjects[_key(name)] = s
            self.created["ders"] += 1
        return s

    def teacher(self, t: Teacher, department_id: int, ranks: Counter) -> m.Teacher:
        surname = t.surname
        initial = t.initial
        if initial is None:  # "mug.Agajykowa": şol familiýaly ýeke-täk mugallymy alýarys
            known = [k for k in self.teacher_cache if k[0] == surname]
            if len(known) == 1:
                return self.teacher_cache[known[0]]
        key = (surname, initial)
        if key in self.teacher_cache:
            return self.teacher_cache[key]
        hits = [x for x in self.teachers_db
                if x.name.split()[0] == surname and (initial is None or len(x.name.split()) > 1
                                                     and x.name.split()[1][0] == initial)]
        if len(hits) == 1:
            obj = hits[0]
        else:
            obj = m.Teacher(name=f"{surname} {initial}." if initial else surname,
                            position=RANK_POSITION.get(ranks.most_common(1)[0][0]) if ranks else None,
                            department_id=department_id)
            self.db.add(obj)
            self.db.flush()
            self.teachers_db.append(obj)
            self.created["mugallym"] += 1
        self.teacher_cache[key] = obj
        return obj

    def run(self, folder: Path) -> m.ExamSession:
        files = sorted(p for p in folder.glob("*.docx") if not p.name.startswith("~$"))
        files.sort(key=lambda p: p.stem in SECONDARY_FILES)  # esasy faýllar öňürti
        docs = []
        for p in files:
            docs.append(parse_doc(p))
            self.log(f"Okaldy: {p.name} ({len(docs[-1].groups)} topar)")

        # mugallymlaryň iň köp ulanylýan wezipesi
        ranks: dict[tuple[str, str | None], Counter] = defaultdict(Counter)
        for d in docs:
            for g in d.groups:
                for e in g.entries:
                    for t in e.teachers:
                        ranks[t.surname, t.initial][t.rank] += 1

        all_days = sorted({day for d in docs for day in d.session_days})
        session = self.db.scalar(select(m.ExamSession).where(m.ExamSession.name == SESSION_NAME))
        if session is not None:  # gaýtadan girizmek: köne synaglary we tertipleri pozýarys
            self.db.delete(session)
            self.db.flush()
        session = m.ExamSession(name=SESSION_NAME, kind=m.ExamKind.final, starts_on=all_days[0],
                                ends_on=all_days[-1], weekdays=[1, 2, 3, 4, 5, 6], max_per_day=1, rest_days=1,
                                consultations=True)
        self.db.add(session)
        self.db.flush()
        periods = []
        for n, a, b in PERIODS:
            pr = m.ExamPeriod(session_id=session.id, number=n, starts_at=a, ends_at=b)
            self.db.add(pr)
            periods.append(pr)
        self.db.flush()
        period_of = lambda t: min(periods, key=lambda pr: abs(  # noqa: E731
            pr.starts_at.hour * 60 + pr.starts_at.minute - t.hour * 60 - t.minute))
        original = m.ExamSchedule(session_id=session.id, name="Asyl tertip (Word faýllaryndan)",
                                  status=m.TimetableStatus.done, solver_status="imported", issues=[])
        self.db.add(original)
        self.db.flush()

        seen: dict[str, tuple[Doc, DocGroup]] = {}
        conflicts: list[str] = []
        exams_n = 0
        for d in docs:
            for g in d.groups:
                name = self.group_name(d, g)
                if name in seen:  # 2-nji ýyl: goşmaça faýldaky nusga — tapawutlaryny ýazýarys
                    conflicts += self.compare(name, seen[name], (d, g))
                    continue
                seen[name] = (d, g)
                sp = self.specialty(g.code, d.master)
                group = self.db.scalar(select(m.Group).where(m.Group.name == name))
                if group is None:
                    group = m.Group(name=name, course=g.course, specialty_id=sp.id)
                    self.db.add(group)
                    self.created["topar"] += 1
                if group.student_count != g.size:
                    self.notes.append(f"{name}: talyp sany {group.student_count} → {g.size}")
                group.student_count = g.size
                group.home_room_id = self.room(g.room, g.size).id
                self.db.flush()
                dept = sp.department_id
                exams_of = [e for e in g.entries if e.kind == "exam"]
                last = {}
                for e in exams_of:  # bir ders iki gezek "Synag" bolsa, soňkusy synag, öňküsi ýalňyşlyk
                    if e.subject in last:
                        self.notes.append(f"{name}: '{e.subject}' iki gezek synag ({last[e.subject].day:%d.%m} we "
                                          f"{e.day:%d.%m}); {e.day:%d.%m} alyndy.")
                    last[e.subject] = e
                for e in exams_of:
                    if last.get(e.subject) is not e:
                        continue
                    if not e.teachers or not e.subject:
                        self.notes.append(f"{name} {e.day:%d.%m}: synag okalmady (ders ýa-da mugallym ýok).")
                        continue
                    ts = [self.teacher(t, dept, ranks[t.surname, t.initial]) for t in e.teachers[:2]]
                    exam = m.Exam(session_id=session.id, subject_id=self.subject(e.subject, dept).id,
                                  group_id=group.id, examiner_id=ts[0].id,
                                  assistant_id=ts[1].id if len(ts) > 1 and ts[1].id != ts[0].id else None)
                    self.db.add(exam)
                    self.db.flush()
                    room = self.room(e.room, g.size) if e.room else self.rooms[g.room]
                    self.db.add(m.ExamEntry(schedule_id=original.id, exam_id=exam.id, day=e.day,
                                            period_id=period_of(e.start).id, room_id=room.id))
                    exams_n += 1
        self.db.flush()
        self.summary = {
            "faýl": len(docs), "topar": len(seen), "synag": exams_n,
            "mugallym": len({t.id for t in self.teacher_cache.values()}),
            "täze": dict(self.created),
        }
        self.conflicts = conflicts
        return session

    def compare(self, name: str, primary: tuple[Doc, DocGroup], other: tuple[Doc, DocGroup]) -> list[str]:
        (d1, g1), (d2, g2) = primary, other
        out = []
        if g1.size != g2.size:
            out.append(f"{name}: talyp sany {d1.path.stem}: {g1.size}, {d2.path.stem}: {g2.size}")
        if g1.room != g2.room:
            out.append(f"{name}: otag {d1.path.stem}: {g1.room}, {d2.path.stem}: {g2.room}")
        sig = lambda g: {(e.day, e.subject, e.teachers[0].surname if e.teachers else "")  # noqa: E731
                         for e in g.entries if e.kind == "exam"}
        a, b = sig(g1), sig(g2)
        for day, subj, t in sorted(a - b):
            out.append(f"{name}: diňe {d1.path.stem}-de: {day:%d.%m} {subj} ({t})")
        for day, subj, t in sorted(b - a):
            out.append(f"{name}: diňe {d2.path.stem}-de: {day:%d.%m} {subj} ({t})")
        return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--report", type=Path, help="hasabaty şu faýla ýazmak")
    args = ap.parse_args(argv)
    from app.db.session import get_session_factory
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with get_session_factory()() as db:
        imp = Importer(db)
        session = imp.run(args.folder)
        db.commit()
        lines = [f"Synag möwsümi: {session.name} (id={session.id}), {session.starts_on} – {session.ends_on}",
                 f"Jemi: {imp.summary}", "", "2-nji ýylyň faýllaryndaky gabat gelmezlikler:"]
        lines += [f"  • {c}" for c in imp.conflicts] or ["  ýok"]
        lines += ["", "Bellikler:"] + ([f"  • {n}" for n in dict.fromkeys(imp.notes)] or ["  ýok"])
        text = "\n".join(lines)
        print(text)
        if args.report:
            args.report.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
