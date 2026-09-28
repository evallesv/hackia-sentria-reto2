import io
import subprocess
import time
from pathlib import Path

import pytest
from fastapi import HTTPException
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from app.services.extraction import extract_pdf_pages
from app.services.ocr import parse_tsv


def tsv(words):
    header = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
        "left\ttop\twidth\theight\tconf\ttext\n"
    )
    return header + "\n".join(
        f"5\t1\t1\t1\t{line}\t{index}\t0\t0\t20\t10\t{confidence}\t{text}"
        for index, (line, text, confidence) in enumerate(words, 1)
    )


def test_ocr_preserves_lines_numbers_and_marks_transcription():
    text = parse_tsv(
        tsv(
            [
                (1, "Cotizacion", 97),
                (1, "sintetica", 96),
                (2, "TOTAL", 97),
                (2, "USD", 96),
                (2, "2065.10", 96),
            ]
        )
    )
    assert text == "Cotizacion sintetica\nTOTAL USD 2065.10"
    assert text.ocr is True


def test_uncertain_numeric_token_blocks_ocr():
    with pytest.raises(HTTPException, match="Importe o número OCR dudoso"):
        parse_tsv(tsv([(1, "Cotizacion", 98), (1, "sintetica", 97), (2, "55.00", 50)]))


@pytest.mark.parametrize(
    "raw", ["", "not a tsv", tsv([(1, "Texto", -1)]), tsv([(1, "Documento", float("nan"))])]
)
def test_empty_or_invalid_ocr_does_not_invent_text(raw):
    with pytest.raises(HTTPException):
        parse_tsv(raw)


def test_mixed_pdf_keeps_page_numbers_and_applies_ocr_only_where_needed(tmp_path, monkeypatch):
    from pypdf import PdfReader

    from app.services import ocr

    stream = io.BytesIO()
    page = canvas.Canvas(stream)
    page.drawString(30, 700, "Documento digital: texto verificable en primera pagina")
    page.showPage()
    page.line(10, 10, 100, 100)
    page.save()
    path = tmp_path / "mixed.pdf"
    path.write_bytes(stream.getvalue())
    assert PdfReader(path).pages[1].get_contents() is not None
    seen = []

    def recognize(path, page_number, deadline):
        seen.append(page_number)
        return parse_tsv(
            tsv([(1, "Cotizacion", 98), (1, "sintetica", 99), (2, "USD", 99), (2, "55.00", 97)])
        )

    monkeypatch.setattr(ocr, "recognize_page", recognize)
    pages = extract_pdf_pages(path, ocr_enabled=True)
    assert [number for number, _ in pages] == [1, 2]
    assert seen == [2]
    assert not getattr(pages[0][1], "ocr", False)
    assert pages[1][1].ocr is True


def test_ocr_page_limit_checked_before_recognition(tmp_path, monkeypatch):
    from app.services import ocr

    stream = io.BytesIO()
    page = canvas.Canvas(stream)
    for _ in range(6):
        page.line(10, 10, 100, 100)
        page.showPage()
    page.save()
    path = tmp_path / "long.pdf"
    path.write_bytes(stream.getvalue())

    def forbidden(*args):
        raise AssertionError("No OCR work before validating page limit")

    monkeypatch.setattr(ocr, "recognize_page", forbidden)
    with pytest.raises(HTTPException, match="5 páginas OCR"):
        extract_pdf_pages(path, ocr_enabled=True)


def test_blank_pdf_stays_unreadable_with_ocr_enabled(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    path = tmp_path / "empty.pdf"
    writer.write(path)
    pages = extract_pdf_pages(path, ocr_enabled=True)
    assert "DOCUMENTO ESCANEADO" in pages[0][1]


def test_missing_ocr_engine_blocks_transcription(monkeypatch):
    from app.services import ocr

    monkeypatch.setattr(ocr.shutil, "which", lambda name: None)
    with pytest.raises(HTTPException, match="OCR local no disponible"):
        ocr.recognize_page(Path("unused.pdf"), 1, time.monotonic() + 45)


def test_ocr_timeout_uses_fixed_argv_and_releases_lock(monkeypatch):
    from app.services import ocr

    monkeypatch.setattr(ocr.shutil, "which", lambda name: "/usr/bin/tesseract")

    def timeout(argv, **kwargs):
        assert kwargs["shell"] is False
        assert kwargs["env"] == {"PATH": ocr.os.defpath, "OMP_THREAD_LIMIT": "1"}
        assert "spa+eng" in argv and argv[-1] == "tsv"
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(ocr.subprocess, "run", timeout)
    path = Path(__file__).resolve().parents[1] / "data/demo/ocr/cotizacion-escaneada.pdf"
    with pytest.raises(HTTPException, match="OCR falló"):
        ocr.recognize_page(path, 1, time.monotonic() + 45)
    assert not ocr.RENDER_LOCK.locked()


def test_oversized_page_is_rejected_before_rendering(tmp_path, monkeypatch):
    from app.services import ocr

    monkeypatch.setattr(ocr.shutil, "which", lambda name: "/usr/bin/tesseract")
    writer = PdfWriter()
    writer.add_blank_page(width=8000, height=8000)
    path = tmp_path / "oversized.pdf"
    writer.write(path)
    with pytest.raises(HTTPException, match="Página demasiado grande"):
        ocr.recognize_page(path, 1, time.monotonic() + 45)
