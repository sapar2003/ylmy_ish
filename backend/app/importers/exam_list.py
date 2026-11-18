"""Synag sanawyny (ders, topar, maslahat berýän, uly we kiçi mugallym) TSV faýldan ulgama girizmek.

Kafedralaryň "synag kabul edýän mugallymlaryň sanawy" kagyzlaryndan (seneleri ýok) göçürilen sanaw üçin.
Setir: surat<TAB>ders<TAB>topar<TAB>maslahat<TAB>uly mugallym<TAB>kiçi mugallym<TAB>bellik(1/0)[<TAB>günler]
Mugallym: "u.m.A.Alçekow", "m-ö.A.Muhyýewa", "m.Çommadowa", "dos.R.Bekiýew", "prof.N.Suwhanow".
Günler: "6" = diňe şenbe (birnäçe bolsa "5,6"). Bellik 0 bolan setirler (beýleki fakultet ýa-da öçürilen) girizilmeýär.

Ulanylyşy:  python -m app.importers.exam_list sanaw.tsv --faculty "Ykdysadyýet we dolandyryş fakulteti"
            --session "Ýarymýyllyk synaglar 2026/2027 I (YDF)" --like "Ýarymýyllyk synaglar 2026/2027 I (STKF)"
"""
import argparse
import re
import sys
from collections import Counter
from datetime import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m

RANKS = {"u.m.": "Uly mugallym", "m.": "Mugallym", "m-ö.": "Mugallym-öwreniji", "dos.": "Dosent",
         "prof.": "Professor"}
TEACHER_RE = re.compile(r"^(u\.m\.|m-ö\.|m\.|dos\.|prof\.)\s*(?:([A-ZÇŞÜÖÄŇÝŽ])\.)?\s*(.+)$")
GROUP_RE = re.compile(r"^(Mag )?(\d) (NGPYD|ID|Logistika)(?: \(([A-ZÇ])\))?$")
SPECIALTIES = {  # kod -> (ady, derejeler)
    "NGPYD": "Nebitgaz pudagynyň ykdysadyýeti we dolandyrylyşy",
    "ID": "Işgärleri dolandyrmak",
    "Logistika": "Logistika",
}
DEPARTMENTS = {
    "NGPYD": "Nebitgaz pudagynyň ykdysadyýeti we dolandyrylyşy kafedrasy",
    "ID": "Nebitgaz pudagynyň ykdysadyýeti we dolandyrylyşy kafedrasy",
    "Logistika": "Logistika kafedrasy",
}
DEFAULT_SIZE = 24  # hakyky talyp sany berilmedi


def parse_teacher(text: str) -> tuple[str, str | None, str]:
    mt = TEACHER_RE.match(text.strip())
    if not mt:
        raise ValueError(f"Mugallym okalmady: {text!r}")
    return RANKS[mt.group(1)], mt.group(2), mt.group(3).strip()


class ListImporter:
    def __init__(self, db: Session, faculty_name: str):
        self.db = db
        self.faculty = db.scalar(select(m.Faculty).where(m.Faculty.name == faculty_name))
        if self.faculty is None:
            raise ValueError(f"Fakultet tapylmady: {faculty_name}")
        self.created = Counter()
        self.notes: list[str] = []
        self.teachers = list(db.scalars(select(m.Teacher)))
        self.cache: dict[tuple[str, str | None], m.Teacher] = {}
        self.subjects = {s.name.casefold(): s for s in db.scalars(select(m.Subject))}

    def department(self, name: str) -> m.Department:
        d = self.db.scalar(select(m.Department).where(m.Department.name == name,
                                                      m.Department.faculty_id == self.faculty.id))
        if d is None:
            d = m.Department(name=name, faculty_id=self.faculty.id)
            self.db.add(d)
            self.db.flush()
            self.created["kafedra"] += 1
        return d

    def specialty(self, code: str, master: bool) -> m.Specialty:
        level = m.StudyLevel.master if master else m.StudyLevel.bachelor
        dep = self.department(DEPARTMENTS[code])
        sp = self.db.scalar(select(m.Specialty).where(m.Specialty.code == code, m.Specialty.level == level,
                                                      m.Specialty.department_id == dep.id))
        if sp is None:
            sp = m.Specialty(name=SPECIALTIES[code], code=code, level=level, department_id=dep.id)
            self.db.add(sp)
            self.db.flush()
            self.created["hünär"] += 1
        return sp

    def group(self, name: str) -> m.Group:
        g = self.db.scalar(select(m.Group).where(m.Group.name == name))
        if g is not None:
            return g
        mg = GROUP_RE.match(name)
        if not mg:
            raise ValueError(f"Topar ady okalmady: {name!r}")
        sp = self.specialty(mg.group(3), bool(mg.group(1)))
        g = m.Group(name=name, course=int(mg.group(2)), student_count=DEFAULT_SIZE, specialty_id=sp.id)
        self.db.add(g)
        self.db.flush()
        self.created["topar"] += 1
        return g

    def teacher(self, text: str, dept_id: int) -> m.Teacher:
        position, initial, surname = parse_teacher(text)
        if initial is None:
            known = [k for k in self.cache if k[0] == surname]
            if len(known) == 1:
                return self.cache[known[0]]
        key = (surname, initial)
        if key in self.cache:
            return self.cache[key]
        hits = []
        for t in self.teachers:
            parts = t.name.replace(".", ". ").split()
            if parts and parts[0] == surname and (initial is None or (len(parts) > 1 and parts[1][0] == initial)):
                hits.append(t)
        exact = [t for t in hits if t.name == (f"{surname} {initial}." if initial else surname)]
        if len(hits) > 1 and len(exact) == 1:
            hits = exact  # öňki girizmede döredilen ýazgy
        if len(hits) == 1:
            obj = hits[0]
        else:
            if len(hits) > 1:
                self.notes.append(f"{text}: {len(hits)} sany meňzeş mugallym bar, täze ýazgy döredildi.")
            obj = m.Teacher(name=f"{surname} {initial}." if initial else surname, position=position,
                            department_id=dept_id)
            self.db.add(obj)
            self.db.flush()
            self.teachers.append(obj)
            self.created["mugallym"] += 1
        self.cache[key] = obj
        return obj

    def subject(self, name: str, dept_id: int) -> m.Subject:
        s = self.subjects.get(name.casefold())
        if s is None:
            s = m.Subject(name=name, department_id=dept_id)
            self.db.add(s)
            self.db.flush()
            self.subjects[name.casefold()] = s
            self.created["ders"] += 1
        return s

    def run(self, path: Path, session_name: str, like_name: str | None) -> m.ExamSession:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            rows.append(parts + [""] * (8 - len(parts)))
        skipped = [r for r in rows if r[6].strip() != "1"]
        for r in skipped:
            self.notes.append(f"Girizilmedi (bellenmedik): {r[2]} · {r[1]} ({r[4]}, {r[5]})")
        rows = [r for r in rows if r[6].strip() == "1"]

        like = self.db.scalar(select(m.ExamSession).where(m.ExamSession.name == like_name)) if like_name else None
        session = self.db.scalar(select(m.ExamSession).where(m.ExamSession.name == session_name))
        if session is not None:
            self.db.delete(session)
            self.db.flush()
        session = m.ExamSession(
            name=session_name, kind=m.ExamKind.final,
            starts_on=like.starts_on if like else None, ends_on=like.ends_on if like else None,
            weekdays=list(like.weekdays) if like else [1, 2, 3, 4, 5, 6], max_per_day=1, rest_days=1,
            consultations=True)
        self.db.add(session)
        self.db.flush()
        periods = [(p.number, p.starts_at, p.ends_at) for p in like.periods] if like else \
            [(1, time(8, 30), time(9, 50)), (2, time(10, 0), time(11, 20))]
        for n, a, b in periods:
            self.db.add(m.ExamPeriod(session_id=session.id, number=n, starts_at=a, ends_at=b))
        self.db.flush()

        seen = set()
        n = 0
        for img, subj, gname, consult, examiner, assistant, _, days in rows:
            g = self.group(gname)
            dept = self.db.get(m.Specialty, g.specialty_id).department_id
            if (subj, gname) in seen:
                self.notes.append(f"Gaýtalanýar, bir gezek alyndy: {gname} · {subj}")
                continue
            seen.add((subj, gname))
            ex = self.teacher(examiner, dept)
            asst = self.teacher(assistant, dept) if assistant else None
            if consult and consult != examiner:
                self.notes.append(f"{gname} · {subj}: maslahaty {consult} berýär, uly mugallym {examiner}.")
            wd = [int(x) for x in days.split(",") if x.strip()] or None
            self.db.add(m.Exam(session_id=session.id, subject_id=self.subject(subj, dept).id, group_id=g.id,
                               examiner_id=ex.id, assistant_id=asst.id if asst and asst.id != ex.id else None,
                               weekdays=wd))
            n += 1
        self.db.flush()
        self.summary = {"synag": n, "topar": len({r[2] for r in rows}),
                        "mugallym": len({t.id for t in self.cache.values()}), "täze": dict(self.created)}
        return session


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tsv", type=Path)
    ap.add_argument("--faculty", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--like", help="seneleri we wagtlary şu möwsümden almak")
    args = ap.parse_args(argv)
    from app.db.session import get_session_factory
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with get_session_factory()() as db:
        imp = ListImporter(db, args.faculty)
        s = imp.run(args.tsv, args.session, args.like)
        db.commit()
        print(f"Möwsüm: {s.name} (id={s.id}) {s.starts_on} – {s.ends_on}")
        print(f"Jemi: {imp.summary}")
        for note in dict.fromkeys(imp.notes):
            print("  •", note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
