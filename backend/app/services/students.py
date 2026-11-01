"""Synag talyplary: hakyky sanaw ýok wagty her topara talyp sanyna görä türkmen atlary bilen talyp döredýär.

Kiçi toparlary bar bolan toparda talyplar kiçi toparlaryň sanyna görä paýlanýar.
Hakyky sanaw gelende admin panelinde üýtgedip ýa-da pozup bolýar.
"""
import random

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m

MALE = ["Aman", "Batyr", "Döwlet", "Merdan", "Myrat", "Serdar", "Atajan", "Kakajan", "Rustam", "Begenç",
        "Maksat", "Arslan", "Dowran", "Ylýas", "Nurmuhammet", "Şatlyk", "Gurbanguly", "Ata", "Perhat", "Begmyrat",
        "Yhlas", "Azat", "Kerim", "Meret", "Orazgeldi", "Sapar", "Resul", "Jumamyrat", "Hojamyrat", "Agajan"]
FEMALE = ["Aýna", "Bahar", "Gülälek", "Jeren", "Leýli", "Maýsa", "Ogulgerek", "Selbi", "Sona", "Täzegül",
          "Mähri", "Nurjahan", "Aýgül", "Dünýägözel", "Enejan", "Gözel", "Jemal", "Läle", "Ogulşat", "Mähek"]
SURNAMES = ["Annaýew", "Atayew", "Babaýew", "Berdiýew", "Çaryýew", "Durdyýew", "Gurbanow", "Hojaýew",
            "Ataýew", "Kakaýew", "Meredow", "Myradow", "Nurmyradow", "Orazow", "Öwezow", "Rejepow", "Saparow",
            "Taganow", "Garlyýew", "Ýazmyradow", "Allaberdiýew", "Esenow", "Amanow", "Bäşimow", "Jumaýew"]


def _name(rnd: random.Random) -> str:
    surname = rnd.choice(SURNAMES)
    if rnd.random() < 0.45:
        return f"{surname}a {rnd.choice(FEMALE)}"
    return f"{surname} {rnd.choice(MALE)}"


def create_demo_students(db: Session, default_count: int = 20) -> int:
    """Talyby ýok toparlara synag talyplaryny döredýär; döredilen talyplaryň sanyny gaýtarýar."""
    have = set(db.scalars(select(m.Student.group_id).group_by(m.Student.group_id)))
    created = 0
    for group in db.scalars(select(m.Group).order_by(m.Group.name)):
        if group.id in have:
            continue
        rnd = random.Random(f"talyp-{group.name}")  # her gezek şol bir atlar
        count = group.student_count or default_count
        names: set[str] = set()
        while len(names) < count:
            names.add(_name(rnd))
        subs = sorted(group.subgroups, key=lambda s: s.name)
        for i, name in enumerate(sorted(names)):
            sub = subs[i * len(subs) // count] if subs else None
            db.add(m.Student(full_name=name, group_id=group.id, subgroup_id=sub.id if sub else None, active=True))
            created += 1
    db.commit()
    return created


def student_counts(db: Session) -> dict[int, int]:
    return dict(db.execute(select(m.Student.group_id, func.count()).group_by(m.Student.group_id)).all())


if __name__ == "__main__":
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        print(f"Döredilen talyp: {create_demo_students(session)}")
