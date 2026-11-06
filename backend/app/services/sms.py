"""SMS ibermek. Häzir SMS üpjün edijisi birikdirilmedik: kod diňe serweriň penjiresine ýazylýar (synag üçin).
Hakyky SMS üçin şu funksiýany üpjün edijiniň API-si bilen çalyşmak ýeterlik."""
import logging

log = logging.getLogger("uvicorn.error")


def send_sms(phone: str, text: str) -> None:
    log.warning("[SMS birikdirilmedik] %s: %s", phone, text)
