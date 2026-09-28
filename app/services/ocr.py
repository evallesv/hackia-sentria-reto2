"""OCR local acotado; nunca se expone como herramienta del modelo."""

import csv
import io
import math
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from fastapi import HTTPException

RENDER_LOCK = threading.Lock()  # PDFium no permite llamadas concurrentes.
MAX_OCR_PAGES = 5


class PageText(str):
    ocr = True


def parse_tsv(raw: str) -> PageText:
    if len(raw) > 2_000_000:
        raise HTTPException(422, "Salida OCR demasiado grande")
    reader = csv.DictReader(io.StringIO(raw), delimiter="\t")
    required = {"level", "block_num", "par_num", "line_num", "conf", "text"}
    if not required.issubset(reader.fieldnames or []):
        raise HTTPException(422, "Salida OCR inválida")
    lines: dict[tuple[str, ...], list[str]] = {}
    confidences = []
    try:
        for row in reader:
            if row["level"] != "5":
                continue
            word = row["text"].strip()
            if not word:
                continue
            confidence = float(row["conf"])
            if not math.isfinite(confidence) or not 0 <= confidence <= 100:
                raise ValueError("confidence")
            if any(char.isdigit() for char in word) and confidence < 85:
                raise HTTPException(422, "Importe o número OCR dudoso; usa un PDF más legible")
            if confidence < 50:
                raise HTTPException(422, "Texto OCR dudoso; usa un PDF más legible")
            confidences.append(confidence)
            key = (row["block_num"], row["par_num"], row["line_num"])
            lines.setdefault(key, []).append(word)
    except (KeyError, ValueError, TypeError, AttributeError):
        raise HTTPException(422, "Salida OCR inválida") from None
    text = "\n".join(" ".join(words) for words in lines.values())
    if not confidences or sum(confidences) / len(confidences) < 75 or len(text) < 20:
        raise HTTPException(422, "OCR sin texto suficientemente legible")
    if len(text) > 50_000:
        raise HTTPException(422, "Texto OCR demasiado grande")
    return PageText(text)


def recognize_page(path: Path, page_number: int, deadline: float) -> PageText:
    executable = shutil.which("tesseract")
    if not executable:
        raise HTTPException(422, "OCR local no disponible; instala Tesseract o usa un PDF digital")
    # El mutex cubre creación, renderizado y liberación de todos los objetos PDFium.
    if not RENDER_LOCK.acquire(timeout=max(0, min(10, deadline - time.monotonic()))):
        raise HTTPException(503, "OCR ocupado; vuelve a intentarlo")
    try:
        import pypdfium2 as pdfium

        with tempfile.TemporaryDirectory(prefix="sentria-ocr-") as temporary:
            image_path = Path(temporary) / "page.png"
            output = Path(temporary) / "result"
            with pdfium.PdfDocument(str(path)) as document:
                page = document[page_number - 1]
                try:
                    width, height = page.get_size()
                    scale = 300 / 72
                    if width <= 0 or height <= 0 or width * height * scale**2 > 12_000_000:
                        raise HTTPException(422, "Página demasiado grande para OCR")
                    bitmap = page.render(scale=scale)
                    try:
                        image = bitmap.to_pil()
                        try:
                            image.save(image_path)
                        finally:
                            image.close()
                    finally:
                        bitmap.close()
                finally:
                    page.close()
            remaining = min(15, deadline - time.monotonic())
            if remaining <= 0:
                raise HTTPException(422, "OCR excedió su tiempo máximo")
            subprocess.run(
                [executable, str(image_path), str(output), "-l", "spa+eng", "--psm", "6", "tsv"],
                check=True,
                timeout=remaining,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={"PATH": os.defpath, "OMP_THREAD_LIMIT": "1"},
                shell=False,
            )
            result = output.with_suffix(".tsv")
            if result.stat().st_size > 2_000_000:
                raise HTTPException(422, "Salida OCR demasiado grande")
            return parse_tsv(result.read_text(encoding="utf-8"))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            422, "OCR falló o excedió su tiempo máximo; usa un PDF más legible"
        ) from None
    finally:
        RENDER_LOCK.release()
