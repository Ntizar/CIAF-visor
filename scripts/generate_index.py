#!/usr/bin/env python3
"""Genera index.json consolidado a partir de los archivos JSON por año."""
import json
import os
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path("/root/workspace/CIAF-visor/data/reports")
DATA_DIR = Path("/root/workspace/CIAF-visor/data")

all_reports = []
stats_by_year = {}

for year_file in sorted(REPORTS_DIR.glob("*.json")):
    year = int(year_file.stem)
    with open(year_file, encoding='utf-8') as f:
        reports = json.load(f)
    all_reports.extend(reports)
    stats_by_year[str(year)] = {
        "total": len(reports),
        "victimas": sum(r.get("consecuencias", {}).get("victimas_mortales", 0) for r in reports),
        "heridos": sum(r.get("consecuencias", {}).get("heridos", 0) for r in reports),
    }

# Stats globales
total_victims = sum(r.get("consecuencias", {}).get("victimas_mortales", 0) for r in all_reports)
total_heridos = sum(r.get("consecuencias", {}).get("heridos", 0) for r in all_reports)

# Tipos de informe
tipos = sorted(set(r.get("tipo", "") for r in all_reports if r.get("tipo")))

# Entidades
entidades_set = set()
for r in all_reports:
    for ent in r.get("entidades", []):
        entidades_set.add(ent)

# Severidades
severidades = sorted(set(r.get("gravedad", "") for r in all_reports if r.get("gravedad")))

# Cobertura
with_title = sum(1 for r in all_reports if r.get("titulo"))
with_conclusions = sum(1 for r in all_reports if r.get("conclusiones"))
with_recs = sum(1 for r in all_reports if r.get("recomendaciones"))
with_coords = sum(1 for r in all_reports if r.get("ubicacion", {}).get("lat"))

index = {
    "title": "CIAF - Centro de Información de Accidentes Ferroviarios",
    "description": "Visor de datos del Centro de Información de Accidentes Ferroviarios de España",
    "years_available": sorted(stats_by_year.keys()),
    "total_reports": len(all_reports),
    "total_victims": total_victims,
    "total_heridos": total_heridos,
    "report_types": tipos,
    "severities": severidades,
    "entities": sorted(entidades_set),
    "fecha_generacion": datetime.now().isoformat(),
    "estadisticas_por_anio": stats_by_year,
    "cobertura": {
        "con_titulo": f"{with_title}/{len(all_reports)} ({100*with_title/len(all_reports):.1f}%)",
        "con_conclusiones": f"{with_conclusions}/{len(all_reports)} ({100*with_conclusions/len(all_reports):.1f}%)",
        "con_recomendaciones": f"{with_recs}/{len(all_reports)} ({100*with_recs/len(all_reports):.1f}%)",
        "con_coordenadas": f"{with_coords}/{len(all_reports)} ({100*with_coords/len(all_reports):.1f}%)",
    }
}

output_path = DATA_DIR / "index.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"✅ index.json generado: {len(all_reports)} informes totales")
print(f"   Años: {index['years_available']}")
print(f"   Víctimas mortales: {total_victims}")
print(f"   Heridos: {total_heridos}")
print(f"   Entidades: {len(entidades_set)}")
print(f"   Con título: {with_title}/{len(all_reports)} ({100*with_title/len(all_reports):.1f}%)")
print(f"   Con conclusiones: {with_conclusions}/{len(all_reports)} ({100*with_conclusions/len(all_reports):.1f}%)")
print(f"   Con recomendaciones: {with_recs}/{len(all_reports)} ({100*with_recs/len(all_reports):.1f}%)")
print(f"   Con coordenadas: {with_coords}/{len(all_reports)} ({100*with_coords/len(all_reports):.1f}%)")
