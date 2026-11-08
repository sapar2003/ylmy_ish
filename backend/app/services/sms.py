"""SMS ibermek. Häzir SMS üpjün edijisi birikdirilmedik: kod serweriň penjiresine we synag üçin
backend/sms_kody.txt faýlyna ýazylýar (penjirä basmak serweri saklap biler, faýly okamak howpsuz).
Hakyky SMS üçin şu funksiýany üpjün edijiniň API-si bilen çalyşmak ýeterlik."""
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger("uvicorn.error")
CODES_FILE = Path(__file__).resolve().parents[2] / "sms_kody.txt"


def send_sms(phone: str, text: str) -> None:
    log.warning("[SMS birikdirilmedik] %s: %s", phone, text)
    with CODES_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {phone}  {text}\n")
