#!/usr/bin/env python3
"""Quick diagnostic of parser extraction quality."""
import sys, json, re
sys.path.insert(0, '/root/workspace/CIAF-visor/scripts')

from pathlib import Path
import fitz

# Import parser functions
from parse_all import (
    clean_text, extract_fecha_suceso, extract_hora_suceso,
    extract_estacion, extract_provincia, extract_entidades,
    extract_tipo, extract_expediente, extract_severity,
    extract_victims_count, extract_heridos_count,
    extract_tipo_suceso, extract_recomendaciones, split_sections
)

# Test files from each era
tests = [
    ("2007/ID291207290408CIAF.pdf", 2007, "pre-rd810"),
    ("2009/0011_09_CIAF.pdf", 2009, "rd810"),
    ("2015/151222150217IFCIAF.pdf", 2015, "rd623"),
    ("2024/2024-64-0625-if.pdf", 2024, "rd623"),
    ("2024/2024-122-1213-if.pdf", 2024, "rd623"),
    ("2012/12IF1224140612CIAF.pdf", 2012, "rd810"),
]

for pdf_path, year, era in tests:
    full_path = Path(f"/root/workspace/CIAF-visor/pdfs/{pdf_path}")
    if not full_path.exists():
        print(f"\n{'='*60}")
        print(f"SKIP: {pdf_path} not found")
        continue
    
    doc = fitz.open(str(full_path))
    text = "".join([p.get_text() for p in doc])
    doc.close()
    cleaned = clean_text(text)
    
    print(f"\n{'='*60}")
    print(f"{era} — {pdf_path}")
    print(f"{'='*60}")
    print(f"  expediente:  {extract_expediente(cleaned)}")
    print(f"  tipo:        {extract_tipo(cleaned, full_path.name)}")
    print(f"  tipo_suceso: {extract_tipo_suceso(cleaned)}")
    print(f"  fecha:       {extract_fecha_suceso(cleaned)}")
    print(f"  hora:        {extract_hora_suceso(cleaned)}")
    print(f"  estacion:    {extract_estacion(cleaned)}")
    print(f"  provincia:   {extract_provincia(cleaned)}")
    print(f"  severity:    {extract_severity(cleaned, full_path.name)}")
    print(f"  victims:     {extract_victims_count(cleaned)}")
    print(f"  heridos:     {extract_heridos_count(cleaned)}")
    print(f"  entidades:   {extract_entidades(cleaned)}")
    
    sections = split_sections(cleaned)
    recs = extract_recomendaciones(sections, cleaned)
    print(f"  recomendaciones: {len(recs)}")
