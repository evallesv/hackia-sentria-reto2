import shutil
from pathlib import Path
from threading import Lock

from app.models import DocumentKind


class StandardTariff:
    def __init__(self, path: Path, seed: Path):
        self.path = path
        self.lock = Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            shutil.copyfile(seed, path)

    def attach(self, service, claim_id):
        with self.lock:
            claim = service.get_claim(claim_id)
            if any(d.kind == DocumentKind.TARIFF and d.active for d in claim.documents):
                return
            service.upload_document(
                claim_id, self.path.read_bytes(), "tarifario_estandar.xlsx", DocumentKind.TARIFF
            )
