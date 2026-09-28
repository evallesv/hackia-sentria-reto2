"""Genera fixtures sintéticos trazables; no simula extracción desde PDF."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data/demo"


def generate(case):
    source_dir = ROOT / "sources" / case
    source_dir.mkdir(parents=True, exist_ok=True)
    kinds = {
        "incident": "INCIDENT_REPORT",
        "inspection": "WORKSHOP_REPORT",
        "billing": "BILLING_DOCUMENT",
        "tariff": "TARIFF",
    }
    evidence = [
        {
            "id": "ev_incident",
            "document_id": "incident",
            "location": "línea 1",
            "text": "Colisión frontal. Daño en parachoques, pintura y alineación frontal.",
        },
        {
            "id": "ev_inspection",
            "document_id": "inspection",
            "location": "línea 1",
            "text": "Se confirma daño frontal. Cambiar parachoques, pintar y alinear.",
        },
    ]
    rows = [
        (
            "paint",
            "Pintura frontal",
            "PAINT",
            "FRONT",
            "HOUR",
            "8",
            "45.00" if case == "A" else "55.00",
            "360.00" if case == "A" else "440.00",
        ),
        (
            "bumper",
            "Parachoques frontal",
            "BUMPER",
            "FRONT",
            "UNIT",
            "1",
            "1480.00" if case == "C" else "1490.00",
            "1480.00" if case == "C" else "1490.00",
        ),
    ]
    rates = [
        ("PAINT", "HOUR", "45.00"),
        ("BUMPER", "UNIT", "1480.00" if case == "C" else "1490.00"),
    ]
    if case == "C":
        rows += [
            ("alignment", "Alineación frontal", "ALIGN", "FRONT", "UNIT", "1", "170.00", "170.00"),
            (
                "alignment_copy",
                "Alineación frontal",
                "ALIGN",
                "FRONT",
                "UNIT",
                "1",
                "170.00",
                "170.00",
            ),
            (
                "steering",
                "Reparación de dirección",
                "STEER",
                "STEERING",
                "UNIT",
                "1",
                "170.00",
                "170.00",
            ),
        ]
        rates += [("ALIGN", "UNIT", "170.00"), ("STEER", "UNIT", "170.00")]
    items, tariffs = [], []
    for index, (ident, desc, code, damage, unit, qty, price, total) in enumerate(rows, 1):
        evidence.append(
            {
                "id": f"ev_{ident}",
                "document_id": "billing",
                "location": f"línea {index}",
                "text": f"{desc}: {qty} {unit} × USD {price} = USD {total}",
            }
        )
        items.append(
            {
                "id": ident,
                "description": desc,
                "service_code": code,
                "damage_code": damage,
                "unit": unit,
                "quantity": qty,
                "unit_price": price,
                "line_total": total,
                "evidence_id": f"ev_{ident}",
            }
        )
    if case != "D":
        for code, unit, rate in rates:
            evidence.append(
                {
                    "id": f"ev_rate_{code}",
                    "document_id": "tariff",
                    "location": f"registro {code}",
                    "text": f"{code}: USD {rate} por {unit}",
                }
            )
            tariffs.append(
                {
                    "service_code": code,
                    "unit": unit,
                    "allowed_rate": rate,
                    "evidence_id": f"ev_rate_{code}",
                }
            )
    documents = []
    for doc, kind in kinds.items():
        if case == "D" and doc == "tariff":
            continue
        text = "\n".join(e["text"] for e in evidence if e["document_id"] == doc) + "\n"
        filename = f"{doc}.txt"
        (source_dir / filename).write_text(text)
        documents.append(
            {
                "id": doc,
                "kind": kind,
                "filename": filename,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "active": True,
            }
        )
    subtotal = {"A": "1850.00", "B": "1930.00", "C": "2430.00", "D": "1930.00"}[case]
    taxes = {"A": "129.50", "B": "135.10", "C": "170.10", "D": "135.10"}[case]
    total = {"A": "1979.50", "B": "2065.10", "C": "2600.10", "D": "2065.10"}[case]
    payload = {
        "schema_version": "1.0",
        "claim_id": f"DEMO-{case}",
        "currency": "USD",
        "billing_kind": "INVOICE",
        "documents": documents,
        "evidence": evidence,
        "reported_damage_codes": ["FRONT"],
        "inspected_damage_codes": ["FRONT"],
        "items": items,
        "tariffs": tariffs,
        "subtotal": subtotal,
        "taxes": taxes,
        "total": total,
    }
    (ROOT / f"case_{case}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    for case in "ABCD":
        generate(case)
