"""Sapak faýllaryny app-yň içinde görkezmek üçin PDF-e öwürmek (LibreOffice, headless).

PDF asyl faýlyň ýanynda saklanýar ("<açar>.pdf"), şonuň üçin her faýl diňe bir gezek öwrülýär.
"""
import logging
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("uvicorn.error")

CONVERTIBLE = {".ppt", ".pptx", ".pps", ".ppsx", ".odp", ".doc", ".docx", ".odt", ".xls", ".xlsx", ".txt"}
IMAGES = {".jpg", ".jpeg", ".png"}
TIMEOUT_SECONDS = 180

_lock = threading.Lock()  # LibreOffice bir profilde bir wagtda diňe bir gezek işleýär


def preview_kind(file_name: str | None) -> str | None:
    """App-yň içinde nähili görkezilýär: "pdf", "image" ýa-da None (diňe ýüklemek)."""
    ext = Path(file_name or "").suffix.lower()
    if ext == ".pdf" or ext in CONVERTIBLE:
        return "pdf"
    return "image" if ext in IMAGES else None


def _soffice() -> str | None:
    if settings.soffice_path:
        return settings.soffice_path
    found = shutil.which("soffice")
    if found:
        return found
    for base in (r"C:\Program Files", r"C:\Program Files (x86)"):
        path = Path(base) / "LibreOffice" / "program" / "soffice.exe"
        if path.is_file():
            return str(path)
    return None


def pdf_path(source: Path) -> Path:
    return source.with_name(source.name + ".pdf")


def ensure_pdf(source: Path) -> Path | None:
    """Faýlyň PDF görnüşini gaýtarýar (gerek bolsa öwürýär); başartmasa None."""
    if source.suffix.lower() == ".pdf":
        return source
    target = pdf_path(source)
    if target.is_file():
        return target
    soffice = _soffice()
    if soffice is None or not source.is_file():
        log.warning("PDF-e öwrülmedi: LibreOffice ýa-da faýl tapylmady (%s)", source.name)
        return None
    with _lock:
        if target.is_file():  # başga sorag eýýäm öwrendir
            return target
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "profile"
            try:
                subprocess.run(
                    [soffice, "--headless", "--norestore", f"-env:UserInstallation={profile.as_uri()}",
                     "--convert-to", "pdf", "--outdir", tmp, str(source)],
                    check=True, timeout=TIMEOUT_SECONDS, capture_output=True,
                )
            except (subprocess.SubprocessError, OSError) as exc:
                log.warning("PDF-e öwrülmedi (%s): %s", source.name, exc)
                return None
            made = Path(tmp) / (source.stem + ".pdf")
            if not made.is_file():
                log.warning("PDF-e öwrülmedi (%s): netije faýly ýok", source.name)
                return None
            shutil.move(str(made), target)
    return target
